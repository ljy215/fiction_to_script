import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.storage import LocalFileStorage, get_file_storage


class FileStorageApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        db_path = self.root / "files-test.sqlite3"
        self.storage_root = self.root / "stored-files"
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionTesting = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
        )

        def override_get_db():
            db = self.SessionTesting()
            try:
                yield db
            finally:
                db.close()

        def override_file_storage():
            return LocalFileStorage(self.storage_root)

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_file_storage] = override_file_storage
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        self.temp_dir.cleanup()

    def auth_headers(self) -> dict[str, str]:
        payload = {
            "email": "files@example.com",
            "password": "strong-password",
            "username": "files",
        }
        self.client.post("/auth/register", json=payload)
        login_response = self.client.post(
            "/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_upload_file_saves_to_local_storage_and_records_metadata(self):
        response = self.client.post(
            "/files",
            headers=self.auth_headers(),
            files={"file": ("chapter.txt", b"chapter text", "text/plain")},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["original_filename"], "chapter.txt")
        self.assertEqual(payload["content_type"], "text/plain")
        self.assertEqual(payload["size_bytes"], len(b"chapter text"))

        stored_path = (self.storage_root / payload["relative_path"]).resolve()
        stored_path.relative_to(self.storage_root.resolve())
        self.assertTrue(stored_path.exists())
        self.assertEqual(stored_path.read_bytes(), b"chapter text")

    def test_upload_filename_cannot_escape_storage_root(self):
        response = self.client.post(
            "/files",
            headers=self.auth_headers(),
            files={"file": ("../escape.txt", b"safe", "text/plain")},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["original_filename"], "escape.txt")

        stored_path = (self.storage_root / payload["relative_path"]).resolve()
        stored_path.relative_to(self.storage_root.resolve())
        self.assertTrue(stored_path.exists())
        self.assertFalse((self.root / "escape.txt").exists())


if __name__ == "__main__":
    unittest.main()
