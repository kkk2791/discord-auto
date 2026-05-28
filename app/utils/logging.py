import sys
from pathlib import Path

from loguru import logger

from app.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    logger.remove()

    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.add(
        sys.stdout,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    logger.add(
        log_dir / "discord_auto_{time:YYYY-MM-DD}.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        encoding="utf-8",
    )

    logger.add(
        log_dir / "error_{time:YYYY-MM-DD}.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="90 days",
        compression="gz",
        encoding="utf-8",
    )

    logger.info(f"Logging initialized. Level: {settings.log_level}")
