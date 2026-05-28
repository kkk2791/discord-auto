"""仪表盘路由"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func

from app.database import async_session_factory
from app.models.account import Account
from app.models.log import ScheduleLog, ReplyLog
from app.models.channel import ChannelConfig
from app.models.keyword import Keyword
from app.models.schedule import Schedule

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse(
        request, "dashboard.html",
        {"active_page": "dashboard"},
    )


@router.get("/api/status")
async def api_status():
    """获取所有账号运行状态"""
    from app.services.discord_client import client_manager
    async with async_session_factory() as session:
        result = await session.execute(select(Account))
        accounts = result.scalars().all()

    account_list = []
    for acc in accounts:
        state = client_manager.get_state(acc.id)
        account_list.append({
            "id": acc.id,
            "name": acc.name,
            "username": acc.username,
            "status": state.status if state else acc.status,
            "is_active": acc.is_active,
            "is_enabled": acc.is_enabled,
            "last_online": acc.last_online_at.isoformat() if acc.last_online_at else None,
        })

    return {
        "accounts": account_list,
        "active_count": client_manager.active_count,
        "total_count": client_manager.total_count,
    }


@router.get("/api/stats")
async def api_stats():
    """统计信息"""
    today = datetime.now(timezone.utc).date()
    week_ago = today - timedelta(days=7)

    async with async_session_factory() as session:
        total_accounts = (await session.execute(select(func.count(Account.id)))).scalar() or 0
        active_accounts = (await session.execute(
            select(func.count(Account.id)).where(Account.is_active == True)
        )).scalar() or 0

        # 今日发言数
        today_schedule = (await session.execute(
            select(func.count(ScheduleLog.id)).where(
                func.date(ScheduleLog.sent_at) == today
            )
        )).scalar() or 0

        # 今日回复数
        today_reply = (await session.execute(
            select(func.count(ReplyLog.id)).where(
                func.date(ReplyLog.replied_at) == today
            )
        )).scalar() or 0

        # 本周趋势
        week_schedule = (await session.execute(
            select(func.count(ScheduleLog.id)).where(
                func.date(ScheduleLog.sent_at) >= week_ago
            )
        )).scalar() or 0

        week_reply = (await session.execute(
            select(func.count(ReplyLog.id)).where(
                func.date(ReplyLog.replied_at) >= week_ago
            )
        )).scalar() or 0

        return {
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "today_schedule": today_schedule,
            "today_reply": today_reply,
            "week_schedule": week_schedule,
            "week_reply": week_reply,
        }


@router.get("/accounts", response_class=HTMLResponse)
async def accounts_page(request: Request):
    return templates.TemplateResponse(
        request, "accounts.html",
        {"active_page": "accounts"},
    )


@router.get("/schedules", response_class=HTMLResponse)
async def schedules_page(request: Request):
    return templates.TemplateResponse(
        request, "schedules.html",
        {"active_page": "schedules"},
    )


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    return templates.TemplateResponse(
        request, "logs.html",
        {"active_page": "logs"},
    )
