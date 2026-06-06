from datetime import datetime

from pydantic import BaseModel, Field


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

    model_config = {"from_attributes": True}
