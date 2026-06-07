from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ChapterSummary(Base):
    __tablename__ = "chapter_summaries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    source_document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id"), index=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"), index=True)
    chapter_order: Mapped[int] = mapped_column(Integer)
    chapter_title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(80), default="mock")
    model: Mapped[str] = mapped_column(String(120), default="mock-chapter-summarizer")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
