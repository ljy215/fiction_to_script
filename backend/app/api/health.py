from fastapi import APIRouter

from app.db.session import check_db_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "fiction-to-script-backend",
        "version": "0.1.0",
    }


@router.get("/health/db")
def database_health_check():
    check_db_connection()
    return {
        "status": "ok",
        "database": "reachable",
    }
