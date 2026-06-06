from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.projects import get_owned_project
from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models import StoredFile, User
from app.schemas import StoredFileRead
from app.storage import LocalFileStorage, get_file_storage

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", response_model=StoredFileRead, status_code=status.HTTP_201_CREATED)
def upload_file(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[LocalFileStorage, Depends(get_file_storage)],
    file: UploadFile = File(...),
    project_id: int | None = Form(default=None),
):
    if project_id is not None:
        get_owned_project(db, project_id, current_user.id)

    try:
        stored_payload = storage.save_upload(
            stream=file.file,
            original_filename=file.filename or "upload",
            content_type=file.content_type,
            owner_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path",
        ) from exc

    stored_file = StoredFile(
        owner_id=current_user.id,
        project_id=project_id,
        **stored_payload.__dict__,
    )
    db.add(stored_file)
    db.commit()
    db.refresh(stored_file)
    return stored_file
