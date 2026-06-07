import json
import time
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from app.api.projects import get_owned_project
from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models import Chapter, GenerationTask, ScriptDocument, SourceDocument, User
from app.schemas import (
    GenerationTaskCreate,
    GenerationTaskRead,
    ScriptDocumentRead,
    ScriptDocumentUpdate,
    ScriptYamlValidationCreate,
    ScriptYamlValidationResult,
)
from app.services.chapters import MINIMUM_CHAPTER_COUNT
from app.services.script_generation import run_generation_task_with_engine
from app.services.script_validation import validate_script_yaml

router = APIRouter(prefix="/projects/{project_id}", tags=["generation"])


def _generation_task_payload(task: GenerationTask) -> dict[str, object]:
    return {
        "id": task.id,
        "owner_id": task.owner_id,
        "project_id": task.project_id,
        "source_document_id": task.source_document_id,
        "script_document_id": task.script_document_id,
        "status": task.status,
        "current_node": task.current_node,
        "provider": task.provider,
        "model": task.model,
        "graph_state": task.graph_state,
        "error_message": task.error_message,
        "progress": task.progress,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }


def _sse_event(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


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


def _next_script_version_number(db: Session, project_id: int, owner_id: int) -> int:
    latest_version = db.scalar(
        select(func.max(ScriptDocument.version_number)).where(
            ScriptDocument.project_id == project_id,
            ScriptDocument.owner_id == owner_id,
        )
    )
    return int(latest_version or 0) + 1


@router.post("/generation-tasks", response_model=GenerationTaskRead, status_code=status.HTTP_201_CREATED)
def create_generation_task(
    project_id: int,
    payload: GenerationTaskCreate,
    background_tasks: BackgroundTasks,
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
        current_node="queued",
        progress=0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    background_tasks.add_task(run_generation_task_with_engine, db.get_bind(), task.id)
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


@router.get("/generation-tasks/{task_id}/events")
def stream_generation_task_events(
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

    engine = db.get_bind()
    owner_id = current_user.id

    def event_stream():
        SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        last_payload = None
        while True:
            stream_db = SessionLocal()
            try:
                current_task = stream_db.execute(
                    select(GenerationTask).where(
                        GenerationTask.id == task_id,
                        GenerationTask.project_id == project_id,
                        GenerationTask.owner_id == owner_id,
                    )
                ).scalar_one_or_none()
                if current_task is None:
                    yield _sse_event("error", {"detail": "Generation task not found"})
                    break

                payload = _generation_task_payload(current_task)
                serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                if serialized != last_payload:
                    yield _sse_event("task", payload)
                    last_payload = serialized

                if current_task.status in {"succeeded", "failed"}:
                    yield _sse_event("done", payload)
                    break
            finally:
                stream_db.close()
            time.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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
        .limit(1)
    ).scalars().first()
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script document not found")
    return script


@router.get("/scripts", response_model=list[ScriptDocumentRead])
def list_script_documents(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    get_owned_project(db, project_id, current_user.id)
    return (
        db.execute(
            select(ScriptDocument)
            .where(ScriptDocument.project_id == project_id, ScriptDocument.owner_id == current_user.id)
            .order_by(ScriptDocument.version_number.desc(), ScriptDocument.id.desc())
        )
        .scalars()
        .all()
    )


@router.patch("/scripts/{script_id}", response_model=ScriptDocumentRead)
def update_script_document(
    project_id: int,
    script_id: int,
    payload: ScriptDocumentUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    get_owned_project(db, project_id, current_user.id)
    script = db.execute(
        select(ScriptDocument).where(
            ScriptDocument.id == script_id,
            ScriptDocument.project_id == project_id,
            ScriptDocument.owner_id == current_user.id,
        )
    ).scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script document not found")

    next_script = ScriptDocument(
        owner_id=script.owner_id,
        project_id=script.project_id,
        source_document_id=script.source_document_id,
        title=script.title,
        script_type=script.script_type,
        yaml_content=payload.yaml_content,
        version_number=_next_script_version_number(db, project_id, current_user.id),
    )
    db.add(next_script)
    db.commit()
    db.refresh(next_script)
    return next_script


@router.post("/scripts/{script_id}/restore", response_model=ScriptDocumentRead)
def restore_script_document(
    project_id: int,
    script_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    get_owned_project(db, project_id, current_user.id)
    script = db.execute(
        select(ScriptDocument).where(
            ScriptDocument.id == script_id,
            ScriptDocument.project_id == project_id,
            ScriptDocument.owner_id == current_user.id,
        )
    ).scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script document not found")

    restored = ScriptDocument(
        owner_id=script.owner_id,
        project_id=script.project_id,
        source_document_id=script.source_document_id,
        title=script.title,
        script_type=script.script_type,
        yaml_content=script.yaml_content,
        version_number=_next_script_version_number(db, project_id, current_user.id),
    )
    db.add(restored)
    db.commit()
    db.refresh(restored)
    return restored


@router.post("/scripts/validate", response_model=ScriptYamlValidationResult)
def validate_script_document_yaml(
    project_id: int,
    payload: ScriptYamlValidationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    get_owned_project(db, project_id, current_user.id)
    return validate_script_yaml(payload.yaml_content)
