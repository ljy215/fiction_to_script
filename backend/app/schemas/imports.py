from datetime import datetime

from pydantic import BaseModel, Field

from app.services.chapters import MINIMUM_CHAPTER_COUNT


class TextImportCreate(BaseModel):
    text: str = Field(min_length=1)


class SourceDocumentRead(BaseModel):
    id: int
    owner_id: int
    project_id: int
    stored_file_id: int | None
    source_type: str
    original_filename: str | None
    content_text: str
    content_length: int
    created_at: datetime
    chapter_count: int = 0
    minimum_chapters_required: int = MINIMUM_CHAPTER_COUNT
    is_generation_ready: bool = False

    model_config = {"from_attributes": True}


class ChapterRead(BaseModel):
    id: int
    owner_id: int
    project_id: int
    source_document_id: int
    order: int
    title: str
    content_text: str
    content_length: int
    created_at: datetime

    model_config = {"from_attributes": True}
