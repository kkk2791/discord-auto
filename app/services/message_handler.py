from datetime import datetime, timezone
from typing import Optional

from loguru import logger
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.message import MessageLog
from app.models.account import Account


async def log_sent_message(
    account_id: int,
    channel_id: str,
    channel_name: str,
    guild_id: Optional[str],
    guild_name: Optional[str],
    content: str,
    *,
    message_id: Optional[str] = None,
    is_ai_generated: bool = False,
    ai_prompt: Optional[str] = None,
    status: str = "success",
    error_message: Optional[str] = None,
) -> MessageLog:
    async with async_session_factory() as session:
        log = MessageLog(
            account_id=account_id,
            message_id=message_id,
            channel_id=channel_id,
            channel_name=channel_name,
            guild_id=guild_id,
            guild_name=guild_name,
            content=content,
            direction="sent",
            message_type="text",
            status=status,
            error_message=error_message,
            is_ai_generated=is_ai_generated,
            ai_prompt=ai_prompt,
            created_at=datetime.now(timezone.utc),
        )
        session.add(log)
        await session.commit()
        await session.refresh(log)
        return log


async def get_messages(
    *,
    account_id: Optional[int] = None,
    channel_id: Optional[str] = None,
    guild_id: Optional[str] = None,
    direction: Optional[str] = None,
    is_ai_generated: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[MessageLog], int]:
    async with async_session_factory() as session:
        stmt = select(MessageLog)

        if account_id is not None:
            stmt = stmt.where(MessageLog.account_id == account_id)
        if channel_id is not None:
            stmt = stmt.where(MessageLog.channel_id == channel_id)
        if guild_id is not None:
            stmt = stmt.where(MessageLog.guild_id == guild_id)
        if direction is not None:
            stmt = stmt.where(MessageLog.direction == direction)
        if is_ai_generated is not None:
            stmt = stmt.where(MessageLog.is_ai_generated == is_ai_generated)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(desc(MessageLog.created_at)).offset(offset).limit(limit)
        result = await session.execute(stmt)
        messages = result.scalars().all()

        return messages, total


async def get_message_stats(account_id: Optional[int] = None) -> dict:
    async with async_session_factory() as session:
        stmt = select(MessageLog)
        if account_id is not None:
            stmt = stmt.where(MessageLog.account_id == account_id)

        sub = stmt.subquery()
        sent = select(func.count()).select_from(sub).where(
            sub.c.direction == "sent"
        )
        received = select(func.count()).select_from(sub).where(
            sub.c.direction == "received"
        )
        ai_gen = select(func.count()).select_from(sub).where(
            sub.c.is_ai_generated == True
        )

        sent_result = await session.execute(sent)
        received_result = await session.execute(received)
        ai_result = await session.execute(ai_gen)

        return {
            "total_sent": sent_result.scalar() or 0,
            "total_received": received_result.scalar() or 0,
            "total_ai_generated": ai_result.scalar() or 0,
        }
