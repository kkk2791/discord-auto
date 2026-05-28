from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    channel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("channel_configs.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="任务名称")
    time_start: Mapped[str] = mapped_column(
        String(5), nullable=False, comment="时间段开始 HH:MM"
    )
    time_end: Mapped[str] = mapped_column(
        String(5), nullable=False, comment="时间段结束 HH:MM"
    )
    message_mode: Mapped[str] = mapped_column(
        String(10), default="custom", comment="custom/ai/mixed"
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sent_date: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True, comment="上次发送日期 YYYY-MM-DD"
    )
    current_index: Mapped[int] = mapped_column(
        Integer, default=0, comment="当前轮换到的消息序号"
    )
    max_per_window: Mapped[int] = mapped_column(
        Integer, default=1, comment="一个时间段内最多发送条数"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    account = relationship("Account", back_populates="schedules")
    channel = relationship("ChannelConfig", back_populates="schedules")
    messages = relationship("PresetMessage", back_populates="schedule", cascade="all, delete-orphan",
                            order_by="PresetMessage.sort_order")

    def __repr__(self) -> str:
        return f"<Schedule id={self.id} name={self.name!r}>"
