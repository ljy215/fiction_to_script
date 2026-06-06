import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.config import get_settings


@dataclass(frozen=True)
class StoredFilePayload:
    original_filename: str
    stored_filename: str
    relative_path: str
    content_type: str | None
    size_bytes: int


class LocalFileStorage:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save_upload(
        self,
        stream: BinaryIO,
        original_filename: str,
        content_type: str | None,
        owner_id: int,
    ) -> StoredFilePayload:
        safe_name = self._safe_filename(original_filename)
        extension = Path(safe_name).suffix.lower()
        stored_filename = f"{uuid.uuid4().hex}{extension}"
        relative_path = Path(f"user_{owner_id}") / stored_filename
        destination = self._resolve_inside_root(relative_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        with destination.open("wb") as output:
            shutil.copyfileobj(stream, output)

        return StoredFilePayload(
            original_filename=safe_name,
            stored_filename=stored_filename,
            relative_path=relative_path.as_posix(),
            content_type=content_type,
            size_bytes=destination.stat().st_size,
        )

    def absolute_path(self, relative_path: str) -> Path:
        return self._resolve_inside_root(Path(relative_path))

    @staticmethod
    def _safe_filename(filename: str | None) -> str:
        raw_name = Path(filename or "upload").name.strip()
        cleaned = raw_name.replace("\x00", "").strip()
        return cleaned or "upload"

    def _resolve_inside_root(self, relative_path: Path) -> Path:
        root = self.root.resolve()
        candidate = (root / relative_path).resolve()
        candidate.relative_to(root)
        return candidate


def get_file_storage() -> LocalFileStorage:
    settings = get_settings()
    return LocalFileStorage(settings.file_storage_dir)
