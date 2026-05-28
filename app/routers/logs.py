"""日志路由"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, desc

from app.database import async_session_factory
from app.models.log import ScheduleLog, ReplyLog

router = APIRouter(tags=["logs"])


@router.post("/api/logs/clear")
async def clear_logs(data: dict = None):
    """手动清除日志"""
    log_type = (data or {}).get("type", "all")  # "schedule" / "reply" / "all"
    async with async_session_factory() as session:
        deleted = {}
        if log_type in ("schedule", "all"):
            result = await session.execute(select(func.count(ScheduleLog.id)))
            deleted["schedule"] = result.scalar() or 0
            await session.execute(ScheduleLog.__table__.delete())
        if log_type in ("reply", "all"):
            result = await session.execute(select(func.count(ReplyLog.id)))
            deleted["reply"] = result.scalar() or 0
            await session.execute(ReplyLog.__table__.delete())
        await session.commit()
    return {"success": True, "deleted": deleted}


@router.get("/api/logs/schedule")
async def list_schedule_logs(page: int = 1, page_size: int = 50):
    offset = (page - 1) * page_size
    async with async_session_factory() as session:
        count_stmt = select(func.count(ScheduleLog.id))
        total = (await session.execute(count_stmt)).scalar() or 0

        result = await session.execute(
            select(ScheduleLog)
            .order_by(desc(ScheduleLog.sent_at))
            .offset(offset)
            .limit(page_size)
        )
        logs = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "items": [
            {
                "id": l.id,
                "account_name": l.account_name,
                "channel_name": l.channel_name,
                "content": l.content,
                "sent_at": l.sent_at.isoformat(),
                "status": l.status,
                "error_message": l.error_message,
            }
            for l in logs
        ],
    }


@router.get("/api/logs/reply")
async def list_reply_logs(page: int = 1, page_size: int = 50):
    offset = (page - 1) * page_size
    async with async_session_factory() as session:
        count_stmt = select(func.count(ReplyLog.id))
        total = (await session.execute(count_stmt)).scalar() or 0

        result = await session.execute(
            select(ReplyLog)
            .order_by(desc(ReplyLog.replied_at))
            .offset(offset)
            .limit(page_size)
        )
        logs = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "items": [
            {
                "id": l.id,
                "account_name": l.account_name,
                "channel_name": l.channel_name,
                "trigger_message": l.trigger_message,
                "reply_content": l.reply_content,
                "keyword": l.keyword,
                "replied_at": l.replied_at.isoformat(),
                "status": l.status,
                "error_message": l.error_message,
            }
            for l in logs
        ],
    }
