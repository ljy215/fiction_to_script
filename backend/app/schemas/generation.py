from datetime import datetime

from pydantic import BaseModel, Field


class GenerationTaskCreate(BaseModel):
    source_document_id: int
    script_type: str | None = Field(default=None, max_length=60)


class ScriptDocumentRead(BaseModel):
    id: int
    owner_id: int
    project_id: int
    source_document_id: int
    title: str
    script_type: str | None
    yaml_content: str
    version_number: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GenerationTaskRead(BaseModel):
    id: int
    owner_id: int
    project_id: int
    source_document_id: int
    script_document_id: int | None
    status: str
    provider: str
    model: str
    error_message: str | None
    progress: int
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}
