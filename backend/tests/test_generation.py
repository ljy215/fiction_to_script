import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import yaml
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models import ChapterSummary, ScriptDocument, StoryCharacter, StoryEvent, StoryLocation
from app.schemas import ScriptPartialRegenerationCreate
from app.services.partial_regeneration import regenerate_script_yaml
from app.services.script_generation import _build_ai_generation_context, _build_prompt
from app.services.script_validation import validate_script_yaml
from app.storage import LocalFileStorage, get_file_storage
from tests.test_script_validation import VALID_YAML


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
        self.assertNotEqual(updated["id"], script["id"])
        self.assertTrue(updated["yaml_content"].endswith("# edited"))

        versions_response = self.client.get(f"/projects/{project_id}/scripts", headers=headers)
        self.assertEqual(versions_response.status_code, 200)
        versions = versions_response.json()
        self.assertEqual([version["version_number"] for version in versions], [2, 1])

        restore_response = self.client.post(
            f"/projects/{project_id}/scripts/{script['id']}/restore",
            headers=headers,
        )
        self.assertEqual(restore_response.status_code, 200)
        restored = restore_response.json()
        self.assertEqual(restored["version_number"], 3)
        self.assertEqual(restored["yaml_content"], script["yaml_content"])

        fake_client = Mock()
        fake_client.chat_completion.side_effect = [
            '{"text":"AI 强化后的雨夜动作。","speaker":"主人公","character_id":"char_001"}',
            (
                '{"purpose":"AI 补强后的场景目的","conflict":"AI 补强后的场景冲突",'
                '"outcome":"AI 补强后的场景结果","lines":['
                '{"id":"line_001","text":"AI 场景动作。","speaker":"主人公","character_id":"char_001"},'
                '{"id":"line_002","text":"AI 场景对白。","speaker":"主人公","character_id":"char_001"}'
                ']}'
            ),
        ]
        with patch("app.services.partial_regeneration.BailianClient.from_settings", return_value=fake_client):
            line_regeneration_response = self.client.post(
                f"/projects/{project_id}/scripts/{restored['id']}/regenerate",
                headers=headers,
                json={"target_type": "line", "scene_id": "sc_001", "line_id": "line_001", "instruction": "强化雨夜环境"},
            )
            scene_regeneration_response = self.client.post(
                f"/projects/{project_id}/scripts/{line_regeneration_response.json()['id']}/regenerate",
                headers=headers,
                json={"target_type": "scene", "scene_id": "sc_001", "instruction": "补强场景调度"},
            )
        self.assertEqual(line_regeneration_response.status_code, 200)
        line_regenerated = line_regeneration_response.json()
        self.assertEqual(line_regenerated["version_number"], 4)
        self.assertIn("AI 强化后的雨夜动作。", line_regenerated["yaml_content"])
        self.assertTrue(validate_script_yaml(line_regenerated["yaml_content"])["valid"])

        self.assertEqual(scene_regeneration_response.status_code, 200)
        scene_regenerated = scene_regeneration_response.json()
        self.assertEqual(scene_regenerated["version_number"], 5)
        self.assertIn("AI 补强后的场景目的", scene_regenerated["yaml_content"])
        self.assertIn("AI 场景对白。", scene_regenerated["yaml_content"])
        self.assertTrue(validate_script_yaml(scene_regenerated["yaml_content"])["valid"])
        self.assertEqual(fake_client.chat_completion.call_count, 2)

    def test_latest_script_returns_newest_document_after_multiple_generations(self):
        headers = self.auth_headers()
        user_id = self.client.get("/auth/me", headers=headers).json()["id"]
        project_id = self.create_project(headers)
        source_document_id = self.import_text(headers, project_id)

        db = self.SessionTesting()
        try:
            db.add(
                ScriptDocument(
                    owner_id=user_id,
                    project_id=project_id,
                    source_document_id=source_document_id,
                    title="First script",
                    script_type="film",
                    yaml_content="schema_version: 1\n",
                )
            )
            latest_script = ScriptDocument(
                owner_id=user_id,
                project_id=project_id,
                source_document_id=source_document_id,
                title="Second script",
                script_type="film",
                yaml_content="schema_version: 1\nmetadata:\n  title: Second\n",
            )
            db.add(latest_script)
            db.commit()
            db.refresh(latest_script)
            latest_script_id = latest_script.id
        finally:
            db.close()

        script_response = self.client.get(
            f"/projects/{project_id}/scripts/latest",
            headers=headers,
        )

        self.assertEqual(script_response.status_code, 200)
        self.assertEqual(script_response.json()["id"], latest_script_id)

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

    def test_all_script_types_route_to_agent_profiles(self):
        cases = {
            "short_drama": ("短剧剧本", "short_drama_script_graph"),
            "film": ("影视剧本", "film_script_graph"),
            "audio_drama": ("广播剧剧本", "audio_drama_script_graph"),
            "stage_play": ("舞台剧剧本", "stage_play_script_graph"),
        }

        for script_type, (label, graph_name) in cases.items():
            with self.subTest(script_type=script_type):
                headers = self.auth_headers()
                project_id = self.create_project(headers)
                source_document_id = self.import_text(headers, project_id)

                response = self.client.post(
                    f"/projects/{project_id}/generation-tasks",
                    headers=headers,
                    json={"source_document_id": source_document_id, "script_type": script_type},
                )

                self.assertEqual(response.status_code, 201)
                task = response.json()
                task_response = self.client.get(
                    f"/projects/{project_id}/generation-tasks/{task['id']}",
                    headers=headers,
                )
                self.assertEqual(task_response.status_code, 200)
                self.assertEqual(task_response.json()["status"], "succeeded")

                script_response = self.client.get(f"/projects/{project_id}/scripts/latest", headers=headers)
                self.assertEqual(script_response.status_code, 200)
                yaml_content = script_response.json()["yaml_content"]
                payload = yaml.safe_load(yaml_content)
                self.assertEqual(payload["script_config"]["script_type"], script_type)
                self.assertEqual(payload["script_config"]["script_type_label"], label)
                self.assertEqual(payload["script_config"]["agent_profile"], graph_name)
                self.assertIn("writing_strategy", payload["script_config"])
                self.assertEqual(payload["generation"]["graph_name"], graph_name)
                self.assertEqual(payload["generation"]["graph_version"], "1.0")

    def test_prompt_includes_selected_script_type_profile(self):
        project = type(
            "ProjectStub",
            (),
            {
                "id": 1,
                "name": "测试项目",
                "novel_title": "测试小说",
                "original_author": "作者",
                "script_type": "audio_drama",
            },
        )()
        source = type("SourceStub", (), {"id": 1})()
        state = type(
            "StateStub",
            (),
            {
                "script_type": "audio_drama",
                "source_language": "zh-CN",
                "output_language": "zh-CN",
                "chapters": [
                    {
                        "id": "ch_001",
                        "order": 1,
                        "title": "第一章",
                        "content": "雨声里，林晚说：“你听见了吗？”",
                        "content_length": 20,
                    }
                ],
                "chapter_summaries": [],
                "events": [],
                "characters": [],
                "locations": [],
                "adaptation": {},
            },
        )()

        context = _build_ai_generation_context(project, source, state)
        prompt = _build_prompt(project, source, state)

        self.assertEqual(context["agent_profile"]["graph_name"], "audio_drama_script_graph")
        self.assertEqual(context["agent_profile"]["scene_focus"], "用声音建立空间、气氛和人物关系。")
        self.assertIn("广播剧剧本", prompt)
        self.assertIn("generation.graph_name 必须是 audio_drama_script_graph", prompt)
        self.assertIn("增加旁白、音效提示和语气变化。", prompt)

    def test_partial_regeneration_uses_ai_when_bailian_is_configured(self):
        fake_client = Mock()
        fake_client.chat_completion.return_value = '{"text":"AI 改写后的动作细节。","speaker":"Hero","character_id":"char_001"}'

        with patch("app.services.partial_regeneration.BailianClient.from_settings", return_value=fake_client):
            regenerated = regenerate_script_yaml(
                VALID_YAML,
                ScriptPartialRegenerationCreate(
                    target_type="line",
                    scene_id="sc_001",
                    line_id="line_001",
                    instruction="用 AI 改写动作行",
                ),
            )

        self.assertIn("AI 改写后的动作细节。", regenerated)
        self.assertTrue(validate_script_yaml(regenerated)["valid"])
        fake_client.chat_completion.assert_called_once()


if __name__ == "__main__":
    unittest.main()
