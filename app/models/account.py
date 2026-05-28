from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="账号别名")
    token: Mapped[str] = mapped_column(Text, nullable=False, comment="Discord token")
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="Discord 用户名")
    user_id: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="Discord 用户 ID")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已连接")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="启动时自动连接")
    status: Mapped[str] = mapped_column(
        String(20), default="offline",
        comment="online/offline/error/connecting"
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_online_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    channels = relationship("ChannelConfig", back_populates="account", cascade="all, delete-orphan")
    keywords = relationship("Keyword", back_populates="account", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="account", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Account id={self.id} name={self.name!r} status={self.status}>"
