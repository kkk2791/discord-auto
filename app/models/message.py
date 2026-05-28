from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PresetMessage(Base):
    __tablename__ = "preset_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序序号")
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    schedule = relationship("Schedule", back_populates="messages")

    def __repr__(self) -> str:
        return f"<PresetMessage id={self.id} order={self.sort_order}>"
