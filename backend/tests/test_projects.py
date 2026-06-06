import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app


class ProjectApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "projects-test.sqlite3"
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

    def auth_headers(self, email: str) -> dict[str, str]:
        payload = {
            "email": email,
            "password": "strong-password",
            "username": email.split("@")[0],
        }
        self.client.post("/auth/register", json=payload)
        login_response = self.client.post(
            "/auth/login",
            json={"email": email, "password": payload["password"]},
        )
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_user_can_create_list_update_and_delete_project(self):
        headers = self.auth_headers("writer@example.com")

        create_response = self.client.post(
            "/projects",
            headers=headers,
            json={
                "name": "第一部改编",
                "novel_title": "长夜",
                "original_author": "作者",
                "script_type": "film",
                "description": "测试项目",
            },
        )
        self.assertEqual(create_response.status_code, 201)
        project_id = create_response.json()["id"]

        list_response = self.client.get("/projects", headers=headers)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()), 1)

        update_response = self.client.patch(
            f"/projects/{project_id}",
            headers=headers,
            json={"name": "第一部改编修订", "status": "ready"},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["name"], "第一部改编修订")
        self.assertEqual(update_response.json()["status"], "ready")

        delete_response = self.client.delete(f"/projects/{project_id}", headers=headers)
        self.assertEqual(delete_response.status_code, 204)

        read_response = self.client.get(f"/projects/{project_id}", headers=headers)
        self.assertEqual(read_response.status_code, 404)

    def test_user_cannot_access_another_users_project(self):
        owner_headers = self.auth_headers("owner@example.com")
        other_headers = self.auth_headers("other@example.com")

        create_response = self.client.post(
            "/projects",
            headers=owner_headers,
            json={"name": "私有项目"},
        )
        project_id = create_response.json()["id"]

        list_response = self.client.get("/projects", headers=other_headers)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json(), [])

        read_response = self.client.get(f"/projects/{project_id}", headers=other_headers)
        update_response = self.client.patch(
            f"/projects/{project_id}",
            headers=other_headers,
            json={"name": "越权修改"},
        )
        delete_response = self.client.delete(f"/projects/{project_id}", headers=other_headers)

        self.assertEqual(read_response.status_code, 404)
        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
