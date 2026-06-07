import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app


VALID_YAML = """
schema_version: "1.0"
document:
  id: "script_doc_001"
  project_id: "project_001"
  title: "Demo Script"
  status: "draft"
  created_at: "2026-06-07T10:00:00+08:00"
  updated_at: "2026-06-07T10:00:00+08:00"
source:
  novel_title: "Demo Novel"
  source_language: "en"
  output_language: "zh-CN"
  minimum_chapters_required: 3
  chapter_count: 3
  input_files: []
  chapters:
    - id: "ch_001"
      order: 1
      title: "Chapter 1"
      summary: "Opening"
    - id: "ch_002"
      order: 2
      title: "Chapter 2"
      summary: "Conflict"
    - id: "ch_003"
      order: 3
      title: "Chapter 3"
      summary: "Decision"
script_config:
  script_type: "film"
  script_type_label: "Film"
  fidelity_policy: "faithful"
  output_mode: "single_document"
generation:
  provider: "mock"
  model: "mock-script-writer"
  generated_at: "2026-06-07T10:00:00+08:00"
characters:
  - id: "char_001"
    name: "Hero"
    role: "protagonist"
locations:
  - id: "loc_001"
    name: "Main Room"
    type: "interior"
events:
  - id: "evt_001"
    chapter_id: "ch_001"
    order: 1
    summary: "Hero finds a clue."
    participants: ["char_001"]
    location_id: "loc_001"
adaptation:
  logline: "A hero follows a clue."
  theme: "Choice"
  strategy:
    preserved_events: ["evt_001"]
    merged_events: []
    omitted_events: []
    added_bridges: []
script:
  scenes:
    - id: "sc_001"
      order: 1
      heading: "INT. MAIN ROOM - NIGHT"
      location_id: "loc_001"
      source_refs:
        - chapter_id: "ch_001"
          event_id: "evt_001"
      lines:
        - id: "line_001"
          type: "action"
          text: "The room is silent."
        - id: "line_002"
          type: "dialogue"
          character_id: "char_001"
          speaker: "Hero"
          text: "I need the truth."
"""


class ScriptValidationApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "script-validation-test.sqlite3"
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

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        self.temp_dir.cleanup()

    def auth_headers(self) -> dict[str, str]:
        payload = {
            "email": "script-validation@example.com",
            "password": "strong-password",
            "username": "script-validation",
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
            json={"name": "Validation Project", "script_type": "film"},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def validate_yaml(self, yaml_content: str) -> dict:
        headers = self.auth_headers()
        project_id = self.create_project(headers)
        response = self.client.post(
            f"/projects/{project_id}/scripts/validate",
            headers=headers,
            json={"yaml_content": yaml_content},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_valid_yaml_passes_validation(self):
        payload = self.validate_yaml(VALID_YAML)

        self.assertTrue(payload["valid"])
        self.assertEqual(payload["errors"], [])

    def test_missing_required_field_fails_validation(self):
        payload = self.validate_yaml(VALID_YAML.replace('schema_version: "1.0"\n', ""))

        self.assertFalse(payload["valid"])
        self.assertIn("schema_version", {error["path"] for error in payload["errors"]})

    def test_wrong_character_reference_fails_validation(self):
        payload = self.validate_yaml(VALID_YAML.replace('character_id: "char_001"', 'character_id: "char_missing"'))

        self.assertFalse(payload["valid"])
        self.assertIn(
            "script.scenes[0].lines[1].character_id",
            {error["path"] for error in payload["errors"]},
        )

    def test_sensitive_field_fails_validation(self):
        payload = self.validate_yaml(VALID_YAML + '\napi_key: "sk-1234567890abcdefghijklmnop"\n')

        self.assertFalse(payload["valid"])
        self.assertIn("api_key", {error["path"] for error in payload["errors"]})


if __name__ == "__main__":
    unittest.main()
