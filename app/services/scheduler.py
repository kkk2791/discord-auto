import random
import hashlib
import sqlite3
from datetime import datetime, date, timezone, timedelta
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.config import get_settings

settings = get_settings()

scheduler = AsyncIOScheduler(
    timezone=settings.scheduler_timezone,
    job_defaults={
        "coalesce": True,
        "max_instances": 1,
        "misfire_grace_time": 60,
    },
)

DB_PATH = settings.data_dir / "discord_auto.db"


def _get_db() -> sqlite3.Connection:
    """获取同步 sqlite3 连接（避免 APScheduler 上下文中 greenlet 冲突）"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _parse_time(t_str: str) -> tuple[int, int]:
    parts = t_str.strip().split(":")
    return int(parts[0]), int(parts[1])


def _is_in_window(now_h: int, now_m: int, start_h: int, start_m: int, end_h: int, end_m: int) -> bool:
    now_total = now_h * 60 + now_m
    start_total = start_h * 60 + start_m
    end_total = end_h * 60 + end_m
    if start_total <= end_total:
        return start_total <= now_total <= end_total
    return now_total >= start_total or now_total <= end_total


async def _check_and_run_schedules():
    """每分钟 tick，检查所有启用的 Schedule"""
    today_str = date.today().isoformat()
    import pytz
    tz = pytz.timezone(settings.scheduler_timezone)
    local_now = datetime.now(timezone.utc).astimezone(tz)
    local_h = local_now.hour
    local_m = local_now.minute

    # 使用同步 sqlite3 查询所有启用的定时任务
    conn = _get_db()
    try:
        cur = conn.execute(
            "SELECT s.id, s.account_id, s.channel_id, s.name, s.time_start, s.time_end, "
            "s.message_mode, s.enabled, s.last_sent_date, s.current_index, s.max_per_window, "
            "a.name as account_name "
            "FROM schedules s JOIN accounts a ON s.account_id = a.id "
            "WHERE s.enabled = 1"
        )
        schedules = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    for sched in schedules:
        try:
            await _process_schedule(sched, today_str, local_h, local_m)
        except Exception as e:
            logger.exception(f"定时任务 {sched['name']} (id={sched['id']}) 处理出错: {e}")


async def _process_schedule(schedule: dict, today_str: str, now_h: int, now_m: int):
    """处理单个定时任务（支持一个时间段发送多条消息）"""
    start_h, start_m = _parse_time(schedule["time_start"])
    end_h, end_m = _parse_time(schedule["time_end"])

    if not _is_in_window(now_h, now_m, start_h, start_m, end_h, end_m):
        return

    max_per = schedule.get("max_per_window", 1) or 1

    # 使用 last_sent_date + current_index 追踪发送进度
    if schedule["last_sent_date"] == today_str and schedule["current_index"] >= max_per:
        return  # 今天已经发够了

    # 新的一天，重置计数器
    if schedule["last_sent_date"] != today_str:
        schedule["current_index"] = 0

    # 计算理想发送时间点（均匀分布在窗口内）
    now_total = now_h * 60 + now_m
    start_total = start_h * 60 + start_m
    end_total = end_h * 60 + end_m
    if end_total <= start_total:
        end_total += 1440
    if now_total < start_total:
        now_total += 1440  # 跨天情况
    window_minutes = max(end_total - start_total, max_per)  # 至少和条数一样大

    elapsed = now_total - start_total  # 窗口内过了多少分钟
    # 计算当前应该发第几条（第1条在窗口开始时立即发送）
    expected_count = 1 + int(elapsed * (max_per - 1) / max(1, window_minutes - 1))

    if expected_count <= schedule["current_index"]:
        return  # 还没到发送时机

    # === 执行发送 ===
    content = await _get_message_content(schedule)
    if not content:
        logger.warning(f"定时任务 {schedule['name']} 没有可用的消息内容")
        return

    # 获取频道信息
    conn = _get_db()
    try:
        cur = conn.execute(
            "SELECT id, name, channel_id FROM channel_configs WHERE id = ?",
            (schedule["channel_id"],)
        )
        ch = cur.fetchone()
        if ch is None:
            logger.error(f"定时任务 {schedule['name']} 的频道不存在")
            return
        channel_id_int = int(ch["channel_id"])
        channel_name = ch["name"]
    finally:
        conn.close()

    from app.services.discord_client import client_manager
    res = await client_manager.send_message(schedule["account_id"], channel_id_int, content)

    # 更新状态和日志
    conn = _get_db()
    try:
        new_index = schedule["current_index"] + 1

        conn.execute(
            "UPDATE schedules SET last_sent_date = ?, current_index = ?, "
            "updated_at = ? WHERE id = ?",
            (today_str, new_index, datetime.now(timezone.utc).isoformat(), schedule["id"])
        )
        conn.execute(
            "INSERT INTO schedule_logs (schedule_id, account_name, channel_name, content, "
            "sent_at, status, error_message) VALUES (?, ?, ?, ?, datetime('now'), ?, ?)",
            (schedule["id"], schedule["account_name"], channel_name, content,
                "success" if res.get("success") else "failed",
                res.get("error") if not res.get("success") else None,
            )
        )
        conn.commit()
    finally:
        conn.close()

    if res.get("success"):
        logger.info(f"✅ 定时发言成功 ({new_index}/{max_per}): {schedule['name']} -> {content[:50]}")
    else:
        logger.error(f"❌ 定时发言失败: {schedule['name']} -> {res.get('error')}")


async def _get_message_content(schedule: dict) -> str:
    """获取要发送的消息内容"""
    if schedule["message_mode"] == "ai":
        from app.services.deepseek import deepseek_service
        result = await deepseek_service.generate_message(
            prompt="生成一条在Discord频道发送的日常消息，内容自然随意。",
            style="casual",
        )
        return result.get("content", "")

    # custom / mixed 模式：从数据库读取预设消息
    conn = _get_db()
    try:
        cur = conn.execute(
            "SELECT id, content, sort_order FROM preset_messages "
            "WHERE schedule_id = ? ORDER BY sort_order",
            (schedule["id"],)
        )
        messages = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    if not messages:
        return ""

    if schedule["message_mode"] == "mixed":
        if schedule["current_index"] % 2 == 0:
            msg_idx = (schedule["current_index"] // 2) % len(messages)
            msg = messages[msg_idx]
            conn = _get_db()
            try:
                conn.execute(
                    "UPDATE preset_messages SET last_sent_at = ? WHERE id = ?",
                    (datetime.now(timezone.utc).isoformat(), msg["id"])
                )
                conn.commit()
            finally:
                conn.close()
            return msg["content"]
        else:
            from app.services.deepseek import deepseek_service
            result = await deepseek_service.generate_message(
                prompt="生成一条在Discord频道发送的日常消息，内容自然随意。",
                style="casual",
            )
            return result.get("content", "")

    # random 模式：随机选一条（使用系统随机，每次都不同）
    if schedule["message_mode"] == "random":
        import secrets
        msg = secrets.choice(messages)
        conn = _get_db()
        try:
            conn.execute(
                "UPDATE preset_messages SET last_sent_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), msg["id"])
            )
            conn.commit()
        finally:
            conn.close()
        return msg["content"]

    # custom 模式：顺序轮换
    idx = schedule["current_index"] % len(messages)
    msg = messages[idx]

    conn = _get_db()
    try:
        conn.execute(
            "UPDATE preset_messages SET last_sent_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), msg["id"])
        )
        conn.commit()
    finally:
        conn.close()

    return msg["content"]


async def _cleanup_old_logs():
    """清理超过一年的日志"""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
    conn = _get_db()
    try:
        cur = conn.execute("DELETE FROM schedule_logs WHERE sent_at < ?", (cutoff,))
        del_s = cur.rowcount
        cur = conn.execute("DELETE FROM reply_logs WHERE replied_at < ?", (cutoff,))
        del_r = cur.rowcount
        conn.commit()
    finally:
        conn.close()

    if del_s or del_r:
        logger.info(f"已清理 {del_s} 条发言日志, {del_r} 条回复日志")


async def start_scheduler() -> None:
    scheduler.add_job(
        _check_and_run_schedules,
        trigger=IntervalTrigger(minutes=1),
        id="check_schedules",
        replace_existing=True,
        name="定时任务检查",
    )
    scheduler.add_job(
        _cleanup_old_logs,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_logs",
        replace_existing=True,
        name="日志清理",
    )
    scheduler.start()
    logger.info(f"定时调度器已启动 (时区={settings.scheduler_timezone})")


async def shutdown_scheduler() -> None:
    scheduler.shutdown(wait=False)
    logger.info("定时调度器已关闭")
