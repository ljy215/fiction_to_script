from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    novel_title: str | None = Field(default=None, max_length=180)
    original_author: str | None = Field(default=None, max_length=120)
    script_type: str | None = Field(default=None, max_length=60)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    novel_title: str | None = Field(default=None, max_length=180)
    original_author: str | None = Field(default=None, max_length=120)
    script_type: str | None = Field(default=None, max_length=60)
    description: str | None = None
    status: str | None = Field(default=None, max_length=40)


class ProjectRead(BaseModel):
    id: int
    owner_id: int
    name: str
    novel_title: str | None
    original_author: str | None
    script_type: str | None
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
