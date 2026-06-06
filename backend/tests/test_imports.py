import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.storage import LocalFileStorage, get_file_storage


class ImportApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.storage_root = self.root / "files"
        db_path = self.root / "imports-test.sqlite3"
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
            "email": "imports@example.com",
            "password": "strong-password",
            "username": "imports",
        }
        self.client.post("/auth/register", json=payload)
        login_response = self.client.post(
            "/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def create_project(self, headers: dict[str, str]) -> int:
        response = self.client.post(
            "/projects",
            headers=headers,
            json={"name": "导入测试项目", "script_type": "film"},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def test_import_pasted_text(self):
        headers = self.auth_headers()
        project_id = self.create_project(headers)

        response = self.client.post(
            f"/projects/{project_id}/imports/text",
            headers=headers,
            json={"text": "第一章\n故事开始。"},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["source_type"], "pasted_text")
        self.assertEqual(payload["content_text"], "第一章\n故事开始。")
        self.assertEqual(payload["content_length"], len("第一章\n故事开始。"))
        self.assertIsNone(payload["stored_file_id"])

    def test_import_txt_file(self):
        headers = self.auth_headers()
        project_id = self.create_project(headers)

        response = self.client.post(
            f"/projects/{project_id}/imports/txt",
            headers=headers,
            files={"file": ("novel.txt", "第一章\n文本导入。".encode("utf-8"), "text/plain")},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["source_type"], "txt_file")
        self.assertEqual(payload["original_filename"], "novel.txt")
        self.assertEqual(payload["content_text"], "第一章\n文本导入。")
        self.assertIsNotNone(payload["stored_file_id"])
        self.assertTrue(any(self.storage_root.rglob("*.txt")))

    def test_import_docx_file_extracts_plain_text(self):
        headers = self.auth_headers()
        project_id = self.create_project(headers)
        document = Document()
        document.add_paragraph("第一章")
        document.add_paragraph("这是 docx 正文。")
        buffer = BytesIO()
        document.save(buffer)

        response = self.client.post(
            f"/projects/{project_id}/imports/docx",
            headers=headers,
            files={
                "file": (
                    "novel.docx",
                    buffer.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["source_type"], "docx_file")
        self.assertEqual(payload["original_filename"], "novel.docx")
        self.assertEqual(payload["content_text"], "第一章\n这是 docx 正文。")
        self.assertIsNotNone(payload["stored_file_id"])

    def test_empty_docx_file_is_rejected(self):
        headers = self.auth_headers()
        project_id = self.create_project(headers)
        document = Document()
        buffer = BytesIO()
        document.save(buffer)

        response = self.client.post(
            f"/projects/{project_id}/imports/docx",
            headers=headers,
            files={
                "file": (
                    "empty.docx",
                    buffer.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_unsupported_file_type_is_rejected(self):
        headers = self.auth_headers()
        project_id = self.create_project(headers)

        response = self.client.post(
            f"/projects/{project_id}/imports/txt",
            headers=headers,
            files={"file": ("novel.pdf", b"%PDF", "application/pdf")},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(list(self.storage_root.rglob("*")))


if __name__ == "__main__":
    unittest.main()
