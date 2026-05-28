#!/usr/bin/env python3
import uvicorn

from app.config import get_settings

settings = get_settings()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower(),
    )
