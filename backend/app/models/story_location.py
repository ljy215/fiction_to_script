from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class StoryLocation(Base):
    __tablename__ = "story_locations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    source_document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id"), index=True)
    location_key: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(180))
    original_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    location_type: Mapped[str] = mapped_column(String(80), default="mixed")
    description: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(80), default="mock")
    model: Mapped[str] = mapped_column(String(120), default="mock-location-extractor")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
