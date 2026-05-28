from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    channel_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("channel_configs.id", ondelete="SET NULL"), nullable=True,
        comment="空=所有当前账号的监听频道"
    )
    keyword: Mapped[str] = mapped_column(String(200), nullable=False, comment="触发关键词")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    account = relationship("Account", back_populates="keywords")
    channel = relationship("ChannelConfig", back_populates="keywords")

    def __repr__(self) -> str:
        return f"<Keyword id={self.id} keyword={self.keyword!r}>"
