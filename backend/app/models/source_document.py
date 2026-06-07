from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.services.chapters import MINIMUM_CHAPTER_COUNT


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    stored_file_id: Mapped[int | None] = mapped_column(ForeignKey("stored_files.id"), nullable=True)
    source_type: Mapped[str] = mapped_column(String(40))
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_text: Mapped[str] = mapped_column(Text)
    content_length: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    owner = relationship("User", back_populates="source_documents")
    project = relationship("Project", back_populates="source_documents")
    stored_file = relationship("StoredFile")
    chapters = relationship("Chapter", back_populates="source_document", cascade="all, delete-orphan")

    @property
    def chapter_count(self) -> int:
        return len(self.chapters)

    @property
    def minimum_chapters_required(self) -> int:
        return MINIMUM_CHAPTER_COUNT

    @property
    def is_generation_ready(self) -> bool:
        return self.chapter_count >= MINIMUM_CHAPTER_COUNT
