from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ScheduleLog(Base):
    __tablename__ = "schedule_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("schedules.id", ondelete="SET NULL"), nullable=True
    )
    account_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="账号名称")
    channel_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="频道名称")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="发送内容")
    sent_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="发送时间"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="success", comment="success/failed"
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ReplyLog(Base):
    __tablename__ = "reply_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="账号名称")
    channel_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="频道名称")
    trigger_message: Mapped[str] = mapped_column(Text, nullable=False, comment="触发消息")
    reply_content: Mapped[str] = mapped_column(Text, nullable=False, comment="回复内容")
    keyword: Mapped[str] = mapped_column(String(200), nullable=False, comment="匹配的关键词")
    replied_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="回复时间"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="success", comment="success/failed"
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
