import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models import ChapterSummary, StoryCharacter, StoryEvent, StoryLocation
from app.services.script_validation import validate_script_yaml
from app.storage import LocalFileStorage, get_file_storage


class GenerationApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.storage_root = self.root / "files"
        db_path = self.root / "generation-test.sqlite3"
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
            "email": "generation@example.com",
            "password": "strong-password",
            "username": "generation",
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
            json={"name": "Script Project", "novel_title": "雨夜来信", "script_type": "film"},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def import_text(self, headers: dict[str, str], project_id: int, chapter_count: int = 3) -> int:
        parts = []
        for index in range(1, chapter_count + 1):
            parts.extend([f"第{index}章 标题{index}", f"第{index}章的主要情节推动主人公继续行动。"])
        response = self.client.post(
            f"/projects/{project_id}/imports/text",
            headers=headers,
            json={"text": "\n".join(parts)},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def test_create_generation_task_builds_mock_script(self):
        headers = self.auth_headers()
        project_id = self.create_project(headers)
        source_document_id = self.import_text(headers, project_id)

        response = self.client.post(
            f"/projects/{project_id}/generation-tasks",
            headers=headers,
            json={"source_document_id": source_document_id, "script_type": "film"},
        )

        self.assertEqual(response.status_code, 201)
        task = response.json()
        task_response = self.client.get(
            f"/projects/{project_id}/generation-tasks/{task['id']}",
            headers=headers,
        )
        self.assertEqual(task_response.status_code, 200)
        task = task_response.json()
        self.assertEqual(task["status"], "succeeded")
        self.assertEqual(task["current_node"], "done")
        self.assertEqual(task["provider"], "mock")
        self.assertIsNotNone(task["script_document_id"])
        self.assertIn("document_parser", task["graph_state"])

        db = self.SessionTesting()
        try:
            summaries = db.query(ChapterSummary).order_by(ChapterSummary.chapter_order).all()
            events = db.query(StoryEvent).order_by(StoryEvent.event_order).all()
            characters = db.query(StoryCharacter).all()
            locations = db.query(StoryLocation).all()
        finally:
            db.close()
        self.assertEqual(len(summaries), 3)
        self.assertEqual(len(events), 3)
        self.assertEqual(len(characters), 1)
        self.assertEqual(len(locations), 1)
        self.assertIn("第1章", summaries[0].summary)
        self.assertEqual(events[0].event_key, "evt_001")
        self.assertEqual(characters[0].character_key, "char_001")
        self.assertEqual(locations[0].location_key, "loc_001")

        script_response = self.client.get(f"/projects/{project_id}/scripts/latest", headers=headers)

        self.assertEqual(script_response.status_code, 200)
        script = script_response.json()
        self.assertIn("schema_version:", script["yaml_content"])
        self.assertIn("adaptation:", script["yaml_content"])
        self.assertIn("script:", script["yaml_content"])
        self.assertIn("sc_003", script["yaml_content"])
        self.assertIn("evt_003", script["yaml_content"])
        validation_result = validate_script_yaml(script["yaml_content"])
        self.assertTrue(validation_result["valid"], validation_result["errors"])

        update_response = self.client.patch(
            f"/projects/{project_id}/scripts/{script['id']}",
            headers=headers,
            json={"yaml_content": script["yaml_content"] + "\n# edited"},
        )

        self.assertEqual(update_response.status_code, 200)
        updated = update_response.json()
        self.assertEqual(updated["version_number"], 2)
        self.assertTrue(updated["yaml_content"].endswith("# edited"))

    def test_generation_requires_three_chapters(self):
        headers = self.auth_headers()
        project_id = self.create_project(headers)
        source_document_id = self.import_text(headers, project_id, chapter_count=2)

        response = self.client.post(
            f"/projects/{project_id}/generation-tasks",
            headers=headers,
            json={"source_document_id": source_document_id, "script_type": "film"},
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
