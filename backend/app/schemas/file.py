from datetime import datetime

from pydantic import BaseModel


class StoredFileRead(BaseModel):
    id: int
    owner_id: int
    project_id: int | None
    original_filename: str
    stored_filename: str
    relative_path: str
    content_type: str | None
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}
