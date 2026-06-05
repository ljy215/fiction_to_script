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
```

## Required Configuration

- `BAILIAN_API_KEY`
- `BAILIAN_BASE_URL`
- `BAILIAN_MODEL`
- `JWT_SECRET`
- `DATABASE_URL`
- `FILE_STORAGE_DIR`
