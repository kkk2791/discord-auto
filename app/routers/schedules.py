"""定时任务管理路由"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import select, func

from app.database import async_session_factory
from app.models.schedule import Schedule
from app.models.message import PresetMessage
from app.models.account import Account
from app.models.channel import ChannelConfig

router = APIRouter(tags=["schedules"])


@router.get("/api/accounts/{account_id}/schedules")
async def list_schedules(account_id: int):
    async with async_session_factory() as session:
        # 使用子查询统计消息数量，避免 session 关闭后的懒加载
        subq = select(PresetMessage.schedule_id, func.count().label("cnt")).group_by(
            PresetMessage.schedule_id
        ).subquery()

        result = await session.execute(
            select(Schedule, subq.c.cnt)
            .outerjoin(subq, Schedule.id == subq.c.schedule_id)
            .where(Schedule.account_id == account_id)
            .order_by(Schedule.id)
        )
        rows = result.all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "channel_id": s.channel_id,
            "time_start": s.time_start,
            "time_end": s.time_end,
            "message_mode": s.message_mode,
            "enabled": s.enabled,
            "last_sent_date": s.last_sent_date,
            "current_index": s.current_index,
            "max_per_window": s.max_per_window,
            "message_count": cnt or 0,
        }
        for s, cnt in rows
    ]


@router.post("/api/accounts/{account_id}/schedules")
async def create_schedule(account_id: int, data: dict):
    name = data.get("name", "").strip()
    channel_id = data.get("channel_id")
    time_start = data.get("time_start", "").strip()
    time_end = data.get("time_end", "").strip()
    if not name or not channel_id or not time_start or not time_end:
        return JSONResponse({"success": False, "error": "名称、频道和时间段不能为空"}, status_code=400)

    async with async_session_factory() as session:
        result = await session.execute(select(Account).where(Account.id == account_id))
        if not result.scalar_one_or_none():
            return JSONResponse({"success": False, "error": "账号不存在"}, status_code=404)

        s = Schedule(
            account_id=account_id,
            channel_id=channel_id,
            name=name,
            time_start=time_start,
            time_end=time_end,
            message_mode=data.get("message_mode", "custom"),
            max_per_window=data.get("max_per_window", 1),
            enabled=data.get("enabled", True),
        )
        session.add(s)
        await session.commit()
        await session.refresh(s)

    return {"success": True, "id": s.id}


@router.put("/api/schedules/{schedule_id}")
async def update_schedule(schedule_id: int, data: dict):
    async with async_session_factory() as session:
        result = await session.execute(select(Schedule).where(Schedule.id == schedule_id))
        s = result.scalar_one_or_none()
        if not s:
            return JSONResponse({"success": False, "error": "定时任务不存在"}, status_code=404)

        if "name" in data:
            s.name = data["name"].strip()
        if "channel_id" in data:
            s.channel_id = data["channel_id"]
        if "time_start" in data:
            s.time_start = data["time_start"].strip()
            s.last_sent_date = None
            s.current_index = 0
        if "time_end" in data:
            s.time_end = data["time_end"].strip()
            s.last_sent_date = None
            s.current_index = 0
        if "message_mode" in data:
            s.message_mode = data["message_mode"]
        if "max_per_window" in data:
            s.max_per_window = data["max_per_window"]
            s.last_sent_date = None
            s.current_index = 0
        if "enabled" in data:
            s.enabled = data["enabled"]

        await session.commit()

    return {"success": True}


@router.delete("/api/schedules/{schedule_id}")
async def delete_schedule(schedule_id: int):
    async with async_session_factory() as session:
        result = await session.execute(select(Schedule).where(Schedule.id == schedule_id))
        s = result.scalar_one_or_none()
        if not s:
            return JSONResponse({"success": False, "error": "定时任务不存在"}, status_code=404)
        await session.delete(s)
        await session.commit()

    return {"success": True}


@router.post("/api/schedules/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: int):
    async with async_session_factory() as session:
        result = await session.execute(select(Schedule).where(Schedule.id == schedule_id))
        s = result.scalar_one_or_none()
        if not s:
            return JSONResponse({"success": False, "error": "定时任务不存在"}, status_code=404)
        s.enabled = not s.enabled
        await session.commit()

    return {"success": True, "enabled": s.enabled}


# ====== 预设消息管理 ======

@router.get("/api/schedules/{schedule_id}/messages")
async def list_messages(schedule_id: int):
    async with async_session_factory() as session:
        result = await session.execute(
            select(PresetMessage)
            .where(PresetMessage.schedule_id == schedule_id)
            .order_by(PresetMessage.sort_order)
        )
        msgs = result.scalars().all()
    return [
        {
            "id": m.id,
            "content": m.content,
            "sort_order": m.sort_order,
            "last_sent_at": m.last_sent_at.isoformat() if m.last_sent_at else None,
        }
        for m in msgs
    ]


@router.post("/api/schedules/{schedule_id}/messages")
async def create_message(schedule_id: int, data: dict):
    content = data.get("content", "").strip()
    if not content:
        return JSONResponse({"success": False, "error": "消息内容不能为空"}, status_code=400)

    async with async_session_factory() as session:
        # 获取当前最大排序号
        result = await session.execute(
            select(PresetMessage).where(PresetMessage.schedule_id == schedule_id).order_by(PresetMessage.sort_order.desc()).limit(1)
        )
        last = result.scalar_one_or_none()
        next_order = (last.sort_order + 1) if last else 0

        msg = PresetMessage(
            schedule_id=schedule_id,
            content=content,
            sort_order=next_order,
        )
        session.add(msg)
        await session.commit()
        await session.refresh(msg)

    return {"success": True, "id": msg.id}


@router.put("/api/schedule-messages/{message_id}")
async def update_message(message_id: int, data: dict):
    async with async_session_factory() as session:
        result = await session.execute(
            select(PresetMessage).where(PresetMessage.id == message_id)
        )
        msg = result.scalar_one_or_none()
        if not msg:
            return JSONResponse({"success": False, "error": "消息不存在"}, status_code=404)
        if "content" in data:
            msg.content = data["content"].strip()
        if "sort_order" in data:
            msg.sort_order = data["sort_order"]
        await session.commit()

    return {"success": True}


@router.delete("/api/schedule-messages/{message_id}")
async def delete_message(message_id: int):
    async with async_session_factory() as session:
        result = await session.execute(
            select(PresetMessage).where(PresetMessage.id == message_id)
        )
        msg = result.scalar_one_or_none()
        if not msg:
            return JSONResponse({"success": False, "error": "消息不存在"}, status_code=404)
        await session.delete(msg)
        await session.commit()

    return {"success": True}


@router.post("/api/schedules/{schedule_id}/messages/reorder")
async def reorder_messages(schedule_id: int, data: dict):
    """重新排序消息"""
    order = data.get("order", [])
    if not order:
        return JSONResponse({"success": False, "error": "排序数据不能为空"}, status_code=400)

    async with async_session_factory() as session:
        for idx, msg_id in enumerate(order):
            result = await session.execute(
                select(PresetMessage).where(
                    PresetMessage.id == msg_id,
                    PresetMessage.schedule_id == schedule_id,
                )
            )
            msg = result.scalar_one_or_none()
            if msg:
                msg.sort_order = idx
        await session.commit()

    return {"success": True}
