from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.projects import get_owned_project
from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models import SourceDocument, StoredFile, User
from app.schemas import SourceDocumentRead, TextImportCreate
from app.storage import LocalFileStorage, get_file_storage

router = APIRouter(prefix="/projects/{project_id}/imports", tags=["imports"])


def _clean_text(text: str) -> str:
    cleaned = text.replace("\ufeff", "").strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Imported text cannot be empty",
        )
    return cleaned


def _decode_text_file(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return _clean_text(content.decode(encoding))
        except UnicodeDecodeError:
            continue
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="TXT file must use UTF-8 or GB18030 compatible text encoding",
    )


def _create_source_document(
    db: Session,
    owner_id: int,
    project_id: int,
    source_type: str,
    text: str,
    original_filename: str | None = None,
    stored_file_id: int | None = None,
) -> SourceDocument:
    document = SourceDocument(
        owner_id=owner_id,
        project_id=project_id,
        stored_file_id=stored_file_id,
        source_type=source_type,
        original_filename=original_filename,
        content_text=text,
        content_length=len(text),
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.post("/text", response_model=SourceDocumentRead, status_code=status.HTTP_201_CREATED)
def import_pasted_text(
    project_id: int,
    payload: TextImportCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    get_owned_project(db, project_id, current_user.id)
    text = _clean_text(payload.text)
    return _create_source_document(
        db=db,
        owner_id=current_user.id,
        project_id=project_id,
        source_type="pasted_text",
        text=text,
    )


@router.post("/txt", response_model=SourceDocumentRead, status_code=status.HTTP_201_CREATED)
def import_txt_file(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[LocalFileStorage, Depends(get_file_storage)],
    file: UploadFile = File(...),
):
    get_owned_project(db, project_id, current_user.id)

    filename = Path(file.filename or "").name
    if Path(filename).suffix.lower() != ".txt":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .txt files are supported in this import step",
        )

    stored_payload = storage.save_upload(
        stream=file.file,
        original_filename=filename,
        content_type=file.content_type,
        owner_id=current_user.id,
    )
    stored_file = StoredFile(
        owner_id=current_user.id,
        project_id=project_id,
        **stored_payload.__dict__,
    )
    db.add(stored_file)
    db.flush()

    text = _decode_text_file(storage.absolute_path(stored_payload.relative_path).read_bytes())
    document = SourceDocument(
        owner_id=current_user.id,
        project_id=project_id,
        stored_file_id=stored_file.id,
        source_type="txt_file",
        original_filename=stored_payload.original_filename,
        content_text=text,
        content_length=len(text),
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document
