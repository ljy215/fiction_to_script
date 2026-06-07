from datetime import datetime

from pydantic import BaseModel, Field

from app.agents.script_profiles import ScriptType


class GenerationTaskCreate(BaseModel):
    source_document_id: int
    script_type: ScriptType | None = None


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


class ScriptDocumentUpdate(BaseModel):
    yaml_content: str = Field(min_length=1)


class ScriptYamlValidationCreate(BaseModel):
    yaml_content: str = Field(min_length=1)


class ScriptYamlValidationErrorRead(BaseModel):
    path: str
    message: str


class ScriptYamlValidationResult(BaseModel):
    valid: bool
    errors: list[ScriptYamlValidationErrorRead]


class GenerationTaskRead(BaseModel):
    id: int
    owner_id: int
    project_id: int
    source_document_id: int
    script_document_id: int | None
    status: str
    current_node: str
    provider: str
    model: str
    graph_state: str | None
    error_message: str | None
    progress: int
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}
