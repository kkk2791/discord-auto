from contextlib import asynccontextmanager
from pathlib import Path
import asyncio

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import get_settings
from app.database import init_db, close_db
from app.utils.logging import setup_logging

settings = get_settings()
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("正在启动 Discord 多账号自动化系统...")

    # 初始化数据库
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    await init_db()

    # 自动连接已启用的账号
    from app.database import async_session_factory
    from sqlalchemy import select
    from app.models.account import Account
    from app.services.discord_client import client_manager
    from app.services.scheduler import start_scheduler

    async with async_session_factory() as session:
        result = await session.execute(
            select(Account).where(Account.is_enabled == True)
        )
        accounts = result.scalars().all()
        for account in accounts:
            logger.info(f"自动连接账号: {account.name}")
            try:
                await asyncio.wait_for(
                    client_manager.connect_account(account),
                    timeout=10.0,
                )
            except asyncio.TimeoutError:
                logger.warning(f"连接账号 {account.name} 超时，跳过")
                account.is_active = False
                account.status = "offline"
            except Exception as e:
                logger.error(f"连接账号 {account.name} 失败: {e}")
                account.is_active = False
                account.status = "error"
                account.error_message = str(e)

    # 启动定时调度器
    await start_scheduler()

    yield

    # 关闭
    from app.services.scheduler import shutdown_scheduler
    from app.services.discord_client import client_manager

    await shutdown_scheduler()
    await client_manager.shutdown_all()
    await close_db()
    logger.info("系统已关闭")


app = FastAPI(
    title=settings.app_name,
    description="Discord 多账号自动化管理系统",
    version="1.0.0",
    lifespan=lifespan,
)

# 静态文件
static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

# 注册路由
from app.routers import dashboard, accounts, channels, keywords, schedules, logs

app.include_router(dashboard.router)
app.include_router(accounts.router)
app.include_router(channels.router)
app.include_router(keywords.router)
app.include_router(schedules.router)
app.include_router(logs.router)
