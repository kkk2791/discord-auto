"""账号管理路由"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.database import async_session_factory
from app.models.account import Account

router = APIRouter(tags=["accounts"])


@router.get("/api/accounts")
async def list_accounts():
    async with async_session_factory() as session:
        result = await session.execute(select(Account).order_by(Account.id))
        accounts = result.scalars().all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "username": a.username,
            "user_id": a.user_id,
            "is_active": a.is_active,
            "is_enabled": a.is_enabled,
            "status": a.status,
            "error_message": a.error_message,
            "last_online_at": a.last_online_at.isoformat() if a.last_online_at else None,
            "created_at": a.created_at.isoformat(),
        }
        for a in accounts
    ]


@router.post("/api/accounts")
async def create_account(data: dict):
    name = data.get("name", "").strip()
    token = data.get("token", "").strip()
    if not name or not token:
        return JSONResponse({"success": False, "error": "名称和Token不能为空"}, status_code=400)

    async with async_session_factory() as session:
        account = Account(name=name, token=token)
        session.add(account)
        await session.commit()
        await session.refresh(account)

    # 添加后自动尝试连接
    from app.services.discord_client import client_manager
    ok = await client_manager.connect_account(account)
    if ok:
        async with async_session_factory() as session:
            result = await session.execute(select(Account).where(Account.id == account.id))
            acct = result.scalar_one_or_none()
            if acct:
                acct.is_active = True
                acct.status = "online"
                await session.commit()

    return {"success": True, "id": account.id, "connected": ok}


@router.put("/api/accounts/{account_id}")
async def update_account(account_id: int, data: dict):
    async with async_session_factory() as session:
        result = await session.execute(select(Account).where(Account.id == account_id))
        account = result.scalar_one_or_none()
        if not account:
            return JSONResponse({"success": False, "error": "账号不存在"}, status_code=404)

        if "name" in data:
            account.name = data["name"].strip()
        if "token" in data and data["token"].strip():
            account.token = data["token"].strip()
        if "is_enabled" in data:
            account.is_enabled = data["is_enabled"]

        await session.commit()

    return {"success": True}


@router.delete("/api/accounts/{account_id}")
async def delete_account(account_id: int):
    from app.services.discord_client import client_manager
    await client_manager.disconnect_account(account_id)

    async with async_session_factory() as session:
        result = await session.execute(select(Account).where(Account.id == account_id))
        account = result.scalar_one_or_none()
        if not account:
            return JSONResponse({"success": False, "error": "账号不存在"}, status_code=404)
        await session.delete(account)
        await session.commit()

    return {"success": True}


@router.post("/api/accounts/{account_id}/toggle")
async def toggle_account(account_id: int):
    from app.services.discord_client import client_manager

    async with async_session_factory() as session:
        result = await session.execute(select(Account).where(Account.id == account_id))
        account = result.scalar_one_or_none()
        if not account:
            return JSONResponse({"success": False, "error": "账号不存在"}, status_code=404)

        if account.is_active:
            await client_manager.disconnect_account(account_id)
            account.is_active = False
            account.status = "offline"
        else:
            ok = await client_manager.connect_account(account)
            account.is_active = ok
            account.is_enabled = True

        await session.commit()

    return {"success": True}


@router.post("/api/accounts/{account_id}/connect")
async def connect_account(account_id: int):
    from app.services.discord_client import client_manager

    async with async_session_factory() as session:
        result = await session.execute(select(Account).where(Account.id == account_id))
        account = result.scalar_one_or_none()
        if not account:
            return JSONResponse({"success": False, "error": "账号不存在"}, status_code=404)

        ok = await client_manager.connect_account(account)
        if ok:
            account.is_active = True
            account.status = "online"
        else:
            account.status = "error"
        await session.commit()

    return {"success": ok}
