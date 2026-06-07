from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class StoryEvent(Base):
    __tablename__ = "story_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    source_document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id"), index=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"), index=True)
    event_key: Mapped[str] = mapped_column(String(80), index=True)
    event_order: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    participants_json: Mapped[str] = mapped_column(Text, default="[]")
    location_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    consequence: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(80), default="mock")
    model: Mapped[str] = mapped_column(String(120), default="mock-event-extractor")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
