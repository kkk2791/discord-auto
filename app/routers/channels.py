"""频道管理路由"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.database import async_session_factory
from app.models.account import Account
from app.models.channel import ChannelConfig

router = APIRouter(tags=["channels"])


@router.get("/api/accounts/{account_id}/channels")
async def list_channels(account_id: int):
    async with async_session_factory() as session:
        result = await session.execute(
            select(ChannelConfig)
            .where(ChannelConfig.account_id == account_id)
            .order_by(ChannelConfig.id)
        )
        channels = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "channel_id": c.channel_id,
            "guild_name": c.guild_name,
            "guild_id": c.guild_id,
            "monitor_reply": c.monitor_reply,
            "auto_speak": c.auto_speak,
        }
        for c in channels
    ]


@router.post("/api/accounts/{account_id}/channels")
async def create_channel(account_id: int, data: dict):
    name = data.get("name", "").strip()
    channel_id = str(data.get("channel_id", "")).strip()
    if not name or not channel_id:
        return JSONResponse({"success": False, "error": "名称和频道ID不能为空"}, status_code=400)

    async with async_session_factory() as session:
        result = await session.execute(select(Account).where(Account.id == account_id))
        if not result.scalar_one_or_none():
            return JSONResponse({"success": False, "error": "账号不存在"}, status_code=404)

        ch = ChannelConfig(
            account_id=account_id,
            name=name,
            channel_id=channel_id,
            guild_id=data.get("guild_id"),
            guild_name=data.get("guild_name"),
            monitor_reply=data.get("monitor_reply", False),
            auto_speak=data.get("auto_speak", False),
        )
        session.add(ch)
        await session.commit()
        await session.refresh(ch)

    return {"success": True, "id": ch.id}


@router.put("/api/channels/{channel_id}")
async def update_channel(channel_id: int, data: dict):
    async with async_session_factory() as session:
        result = await session.execute(
            select(ChannelConfig).where(ChannelConfig.id == channel_id)
        )
        ch = result.scalar_one_or_none()
        if not ch:
            return JSONResponse({"success": False, "error": "频道不存在"}, status_code=404)

        if "name" in data:
            ch.name = data["name"].strip()
        if "channel_id" in data:
            ch.channel_id = str(data["channel_id"]).strip()
        if "guild_name" in data:
            ch.guild_name = data.get("guild_name")
        if "monitor_reply" in data:
            ch.monitor_reply = data["monitor_reply"]
        if "auto_speak" in data:
            ch.auto_speak = data["auto_speak"]

        await session.commit()

    return {"success": True}


@router.delete("/api/channels/{channel_id}")
async def delete_channel(channel_id: int):
    async with async_session_factory() as session:
        result = await session.execute(
            select(ChannelConfig).where(ChannelConfig.id == channel_id)
        )
        ch = result.scalar_one_or_none()
        if not ch:
            return JSONResponse({"success": False, "error": "频道不存在"}, status_code=404)
        await session.delete(ch)
        await session.commit()

    return {"success": True}
