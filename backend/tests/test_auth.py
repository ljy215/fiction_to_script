import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app


class AuthApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "auth-test.sqlite3"
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

    def test_register_login_and_read_current_user(self):
        register_response = self.client.post(
            "/auth/register",
            json={
                "email": "writer@example.com",
                "password": "strong-password",
                "username": "writer",
            },
        )
        self.assertEqual(register_response.status_code, 201)
        self.assertEqual(register_response.json()["email"], "writer@example.com")

        login_response = self.client.post(
            "/auth/login",
            json={
                "email": "writer@example.com",
                "password": "strong-password",
            },
        )
        self.assertEqual(login_response.status_code, 200)
        token = login_response.json()["access_token"]
        self.assertTrue(token)

        me_response = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["email"], "writer@example.com")

    def test_duplicate_registration_is_rejected(self):
        payload = {
            "email": "writer@example.com",
            "password": "strong-password",
            "username": "writer",
        }

        first_response = self.client.post("/auth/register", json=payload)
        second_response = self.client.post("/auth/register", json=payload)

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 409)

    def test_invalid_password_is_rejected(self):
        self.client.post(
            "/auth/register",
            json={
                "email": "writer@example.com",
                "password": "strong-password",
                "username": "writer",
            },
        )

        login_response = self.client.post(
            "/auth/login",
            json={
                "email": "writer@example.com",
                "password": "wrong-password",
            },
        )

        self.assertEqual(login_response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
