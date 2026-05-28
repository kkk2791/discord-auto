from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ChannelConfig(Base):
    __tablename__ = "channel_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="频道显示名称")
    channel_id: Mapped[str] = mapped_column(String(30), nullable=False, comment="Discord 频道 ID")
    guild_id: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="服务器 ID")
    guild_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    monitor_reply: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否监听此频道进行关键词回复")
    auto_speak: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否用于定时发言")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    account = relationship("Account", back_populates="channels")
    keywords = relationship("Keyword", back_populates="channel", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="channel", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ChannelConfig id={self.id} name={self.name!r}>"
