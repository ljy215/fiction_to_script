# Backend

FastAPI backend for the AI novel-to-script application.

## Start With uv

```bash
uv sync
uv run fastapi dev app/main.py
```

The backend loads `.env.example` by default and lets `.env` override it. For local secrets, copy the example file:

```bash
copy .env.example .env
```

## Start With pip

```bash
python -m venv .venv
pip install -r requirements.txt
fastapi dev app/main.py
```

## Health Check

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/db
```

## Database

The backend uses SQLite and SQLAlchemy for the MVP. The default local database URL is:

```text
sqlite:///./storage/data/app.sqlite3
```

The application initializes the database connection on startup and creates the SQLite file under `storage/data`.

Run the database connection test:

```bash
uv run python -m unittest tests.test_db
```

## Authentication

Available endpoints:

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

Run authentication tests:

```bash
uv run python -m unittest tests.test_auth
```

Run all backend tests:

```bash
uv run python -m unittest
```

## Projects API

Available endpoints:

- `POST /projects`
- `GET /projects`
- `GET /projects/{project_id}`
- `PATCH /projects/{project_id}`
- `DELETE /projects/{project_id}`

All project endpoints require a Bearer token and only return projects owned by the current user.

## Required Configuration

- `BAILIAN_API_KEY`
- `BAILIAN_BASE_URL`
- `BAILIAN_MODEL`
- `JWT_SECRET`
- `DATABASE_URL`
- `FILE_STORAGE_DIR`
