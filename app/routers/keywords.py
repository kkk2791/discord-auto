"""关键词管理路由"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.database import async_session_factory
from app.models.keyword import Keyword
from app.models.account import Account

router = APIRouter(tags=["keywords"])


@router.get("/api/accounts/{account_id}/keywords")
async def list_keywords(account_id: int):
    async with async_session_factory() as session:
        result = await session.execute(
            select(Keyword)
            .where(Keyword.account_id == account_id)
            .order_by(Keyword.id)
        )
        keywords = result.scalars().all()
    return [
        {
            "id": k.id,
            "keyword": k.keyword,
            "channel_id": k.channel_id,
            "enabled": k.enabled,
        }
        for k in keywords
    ]


@router.post("/api/accounts/{account_id}/keywords")
async def create_keyword(account_id: int, data: dict):
    keyword = data.get("keyword", "").strip()
    if not keyword:
        return JSONResponse({"success": False, "error": "关键词不能为空"}, status_code=400)

    async with async_session_factory() as session:
        result = await session.execute(select(Account).where(Account.id == account_id))
        if not result.scalar_one_or_none():
            return JSONResponse({"success": False, "error": "账号不存在"}, status_code=404)

        kw = Keyword(
            account_id=account_id,
            keyword=keyword,
            channel_id=data.get("channel_id"),
            enabled=data.get("enabled", True),
        )
        session.add(kw)
        await session.commit()
        await session.refresh(kw)

    return {"success": True, "id": kw.id}


@router.put("/api/keywords/{keyword_id}")
async def update_keyword(keyword_id: int, data: dict):
    async with async_session_factory() as session:
        result = await session.execute(select(Keyword).where(Keyword.id == keyword_id))
        kw = result.scalar_one_or_none()
        if not kw:
            return JSONResponse({"success": False, "error": "关键词不存在"}, status_code=404)

        if "keyword" in data:
            kw.keyword = data["keyword"].strip()
        if "channel_id" in data:
            kw.channel_id = data.get("channel_id")
        if "enabled" in data:
            kw.enabled = data["enabled"]

        await session.commit()

    return {"success": True}


@router.delete("/api/keywords/{keyword_id}")
async def delete_keyword(keyword_id: int):
    async with async_session_factory() as session:
        result = await session.execute(select(Keyword).where(Keyword.id == keyword_id))
        kw = result.scalar_one_or_none()
        if not kw:
            return JSONResponse({"success": False, "error": "关键词不存在"}, status_code=404)
        await session.delete(kw)
        await session.commit()

    return {"success": True}
