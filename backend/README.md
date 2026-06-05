# Backend

FastAPI backend for the AI novel-to-script application.

## Start With uv

```bash
uv sync
uv run fastapi dev app/main.py
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
