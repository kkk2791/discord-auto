import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import Message, TextChannel
from loguru import logger
from sqlalchemy import select

from app.config import get_settings
from app.database import async_session_factory
from app.models.account import Account
from app.models.channel import ChannelConfig
from app.models.keyword import Keyword
from app.models.log import ReplyLog

settings = get_settings()


@dataclass
class ClientState:
    account_id: int
    client: discord.Client
    status: str = "disconnected"
    error_message: Optional[str] = None
    ready: asyncio.Event = field(default_factory=asyncio.Event)
    _ready_fired: bool = False
    _connect_task: Optional[asyncio.Task] = None


class DiscordClientManager:
    def __init__(self) -> None:
        self._clients: dict[int, ClientState] = {}
        self._lock = asyncio.Lock()

    @property
    def active_count(self) -> int:
        return sum(1 for s in self._clients.values() if s.status == "online")

    @property
    def total_count(self) -> int:
        return len(self._clients)

    async def connect_account(self, account: Account) -> bool:
        async with self._lock:
            if account.id in self._clients:
                logger.info(f"账号 {account.name} 已存在，重新连接...")
                await self._disconnect_internal(account.id)

            state = ClientState(account_id=account.id, client=discord.Client())
            self._clients[account.id] = state

        self._register_events(state, account)
        try:
            # 使用 start() 建立完整连接（HTTP 认证 + WebSocket）
            async with asyncio.timeout(20):
                # 后台任务启动 Discord 客户端
                task = asyncio.create_task(state.client.start(account.token))
                state._connect_task = task
                # 等待 on_ready 事件（最多 20 秒）
                await state.ready.wait()
                state.status = "online"
                logger.info(f"账号 '{account.name}' 连接成功")
                return True
        except asyncio.TimeoutError:
            state.status = "error"
            state.error_message = "连接超时（Token 可能无效）"
            await self._update_account_status(account.id, "error", "连接超时（Token 可能无效）")
            logger.error(f"账号 '{account.name}' 连接超时")
            return False
        except Exception as e:
            state.status = "error"
            state.error_message = str(e)
            await self._update_account_status(account.id, "error", str(e))
            logger.error(f"账号 '{account.name}' 连接失败: {e}")
            return False

    async def disconnect_account(self, account_id: int) -> None:
        async with self._lock:
            await self._disconnect_internal(account_id)

    async def _disconnect_internal(self, account_id: int) -> None:
        state = self._clients.pop(account_id, None)
        if state is None:
            return
        # 取消连接任务
        if state._connect_task and not state._connect_task.done():
            state._connect_task.cancel()
            try:
                await asyncio.wait_for(state._connect_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        try:
            await state.client.close()
        except Exception:
            pass

    async def shutdown_all(self) -> None:
        async with self._lock:
            for account_id in list(self._clients.keys()):
                await self._disconnect_internal(account_id)
        logger.info("所有 Discord 客户端已断开")

    async def get_client(self, account_id: int) -> Optional[discord.Client]:
        state = self._clients.get(account_id)
        if state is None:
            return None
        try:
            await asyncio.wait_for(state.ready.wait(), timeout=30)
        except asyncio.TimeoutError:
            logger.warning(f"等待账号 {account_id} 就绪超时")
            return None
        if not state.client.is_ready():
            return None
        return state.client

    def get_state(self, account_id: int) -> Optional[ClientState]:
        return self._clients.get(account_id)

    async def send_message(
        self, account_id: int, channel_id: int, content: str,
    ) -> dict:
        client = await self.get_client(account_id)
        if client is None:
            return {"success": False, "error": "客户端未就绪"}

        try:
            channel = client.get_channel(channel_id)
            if channel is None:
                channel = await client.fetch_channel(channel_id)
            if channel is None or not isinstance(channel, (TextChannel, discord.DMChannel)):
                return {"success": False, "error": "频道未找到或不是文字频道"}

            sent = await channel.send(content)
            return {"success": True, "message_id": str(sent.id)}
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return {"success": False, "error": str(e)}

    def _register_events(self, state: ClientState, account: Account) -> None:
        client = state.client

        @client.event
        async def on_ready():
            state.status = "online"
            state.error_message = None
            if not state._ready_fired:
                state._ready_fired = True
                state.ready.set()
            await self._update_account_status(
                account.id, "online",
                extra={"username": str(client.user), "user_id": str(client.user.id)},
            )
            logger.info(
                f"账号 '{account.name}' 就绪: {client.user} "
                f"(ID: {client.user.id}) 在 {len(client.guilds)} 个服务器中"
            )

        @client.event
        async def on_message(message: Message):
            # 不处理自己的消息
            if message.author == client.user:
                return
            # 只处理文字频道
            if not message.guild:
                return
            if not isinstance(message.channel, TextChannel):
                return

            # 异步检查关键词
            await self._check_keywords_and_reply(account, message)

        @client.event
        async def on_disconnect():
            await self._update_account_status(account.id, "offline")

        @client.event
        async def on_error(event: str, *args, **kwargs):
            logger.error(f"Discord 事件错误 [{account.name}]: {event}")

    async def _check_keywords_and_reply(self, account: Account, message: Message) -> None:
        """检查消息是否包含关键词，匹配则 AI 回复（使用同步 sqlite3 避免 greenlet 冲突）"""
        import sqlite3
        db_path = settings.data_dir / "discord_auto.db"

        try:
            def _query():
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                try:
                    # 查询启用了监听的频道
                    cur = conn.execute(
                        "SELECT id, name, channel_id FROM channel_configs "
                        "WHERE account_id = ? AND monitor_reply = 1 AND channel_id = ?",
                        (account.id, str(message.channel.id))
                    )
                    ch = cur.fetchone()
                    if ch is None:
                        return None, []

                    # 查询启用的关键词
                    cur = conn.execute(
                        "SELECT id, keyword, channel_id FROM keywords "
                        "WHERE account_id = ? AND enabled = 1 "
                        "AND (channel_id IS NULL OR channel_id = ?)",
                        (account.id, ch["id"])
                    )
                    keywords = [{"id": r[0], "keyword": r[1], "channel_id": r[2]} for r in cur.fetchall()]
                    return ch, keywords
                finally:
                    conn.close()

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, _query)
            channel_info, keywords = result

            if channel_info is None or not keywords:
                return

            msg_lower = message.content.lower()
            matched_kw = None
            for kw in keywords:
                if kw["keyword"].lower() in msg_lower:
                    matched_kw = kw
                    break

            if matched_kw is None:
                return

            # 关键词匹配成功！
            logger.info(
                f"关键词 '{matched_kw['keyword']}' 触发回复: "
                f"账号={account.name} 频道={message.channel.name}"
            )

            from app.services.deepseek import deepseek_service
            trigger_text = message.content
            context = (
                f"频道: #{message.channel.name}"
                f"（服务器: {message.guild.name if message.guild else 'N/A'}）\n"
                f"消息内容: {trigger_text}"
            )

            ai_result = await deepseek_service.generate_message(
                prompt=f"回复这条消息，消息有关键词「{matched_kw['keyword']}」。简短回复，像真人网友一样自然，别暴露自己是AI，不要用标点表情轰炸。",
                context=context,
                style="brief",
            )

            reply_content = ai_result.get("content", "")
            if not reply_content:
                logger.warning("AI 回复为空")
                return

            # 发送回复
            res = await self.send_message(account.id, message.channel.id, reply_content)

            # 记录日志（也用同步 sqlite3）
            def _log():
                conn2 = sqlite3.connect(str(db_path))
                try:
                    conn2.execute(
                        "INSERT INTO reply_logs (account_name, channel_name, trigger_message, "
                        "reply_content, keyword, replied_at, status, error_message) "
                        "VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?)",
                        (
                            account.name,
                            str(message.channel.name),
                            trigger_text,
                            reply_content,
                            matched_kw["keyword"],
                            "success" if res.get("success") else "failed",
                            res.get("error") if not res.get("success") else None,
                        )
                    )
                    conn2.commit()
                finally:
                    conn2.close()

            await loop.run_in_executor(None, _log)

            if res.get("success"):
                logger.info(f"✅ 回复成功: {account.name} -> #{message.channel.name}")
            else:
                logger.error(f"❌ 回复失败: {res.get('error')}")

        except Exception as e:
            logger.exception(f"关键词检查出错: {e}")

    async def _update_account_status(
        self, account_id: int, status: str,
        *, error_msg: Optional[str] = None, extra: Optional[dict] = None,
    ) -> None:
        """更新账号状态（同步 sqlite3 避免 greenlet 冲突）"""
        import sqlite3
        db_path = settings.data_dir / "discord_auto.db"

        def _update():
            conn = sqlite3.connect(str(db_path))
            try:
                now = datetime.now(timezone.utc).isoformat()
                if status == "online":
                    username = (extra or {}).get("username", "")
                    user_id = (extra or {}).get("user_id", "")
                    conn.execute(
                        "UPDATE accounts SET status = ?, is_active = 1, "
                        "username = COALESCE(NULLIF(?, ''), username), "
                        "user_id = COALESCE(NULLIF(?, ''), user_id), "
                        "error_message = NULL, "
                        "last_online_at = ?, updated_at = ? "
                        "WHERE id = ?",
                        (status, username, user_id, now, now, account_id)
                    )
                else:
                    conn.execute(
                        "UPDATE accounts SET status = ?, is_active = 0, "
                        "error_message = ?, updated_at = ? WHERE id = ?",
                        (status, error_msg, now, account_id)
                    )
                conn.commit()
            finally:
                conn.close()

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _update)


client_manager = DiscordClientManager()
