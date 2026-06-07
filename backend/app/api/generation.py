from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.projects import get_owned_project
from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models import Chapter, GenerationTask, ScriptDocument, SourceDocument, User
from app.schemas import GenerationTaskCreate, GenerationTaskRead, ScriptDocumentRead
from app.services.chapters import MINIMUM_CHAPTER_COUNT
from app.services.script_generation import run_generation_task

router = APIRouter(prefix="/projects/{project_id}", tags=["generation"])


def _get_owned_source_document(db: Session, project_id: int, owner_id: int, source_document_id: int) -> SourceDocument:
    document = db.execute(
        select(SourceDocument).where(
            SourceDocument.id == source_document_id,
            SourceDocument.project_id == project_id,
            SourceDocument.owner_id == owner_id,
        )
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source document not found")
    return document


@router.post("/generation-tasks", response_model=GenerationTaskRead, status_code=status.HTTP_201_CREATED)
def create_generation_task(
    project_id: int,
    payload: GenerationTaskCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    project = get_owned_project(db, project_id, current_user.id)
    document = _get_owned_source_document(db, project_id, current_user.id, payload.source_document_id)

    chapter_count = db.scalar(
        select(func.count(Chapter.id)).where(
            Chapter.source_document_id == document.id,
            Chapter.project_id == project_id,
            Chapter.owner_id == current_user.id,
        )
    )
    if (chapter_count or 0) < MINIMUM_CHAPTER_COUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"At least {MINIMUM_CHAPTER_COUNT} chapters are required before generation",
        )

    if payload.script_type:
        project.script_type = payload.script_type
    project.status = "generating"
    task = GenerationTask(
        owner_id=current_user.id,
        project_id=project_id,
        source_document_id=document.id,
        status="pending",
        progress=0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    run_generation_task(db, task.id)
    db.refresh(task)
    return task


@router.get("/generation-tasks/{task_id}", response_model=GenerationTaskRead)
def read_generation_task(
    project_id: int,
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    get_owned_project(db, project_id, current_user.id)
    task = db.execute(
        select(GenerationTask).where(
            GenerationTask.id == task_id,
            GenerationTask.project_id == project_id,
            GenerationTask.owner_id == current_user.id,
        )
    ).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation task not found")
    return task


@router.get("/scripts/latest", response_model=ScriptDocumentRead)
def read_latest_script(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    get_owned_project(db, project_id, current_user.id)
    script = db.execute(
        select(ScriptDocument)
        .where(ScriptDocument.project_id == project_id, ScriptDocument.owner_id == current_user.id)
        .order_by(ScriptDocument.id.desc())
    ).scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script document not found")
    return script
