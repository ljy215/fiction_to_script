from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.base import Base


def _connect_args(database_url: str) -> dict[str, object]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def create_db_engine(database_url: str | None = None) -> Engine:
    settings = get_settings()
    url = database_url or settings.database_url
    settings.ensure_local_directories()

    return create_engine(
        url,
        connect_args=_connect_args(url),
        pool_pre_ping=True,
    )


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    migrate_sqlite_schema(engine)
    check_db_connection()


def migrate_sqlite_schema(db_engine: Engine) -> None:
    if db_engine.dialect.name != "sqlite":
        return

    inspector = inspect(db_engine)
    if "generation_tasks" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("generation_tasks")}
    migrations = []
    if "current_node" not in columns:
        migrations.append(
            "ALTER TABLE generation_tasks "
            "ADD COLUMN current_node VARCHAR(80) NOT NULL DEFAULT 'queued'"
        )
    if "graph_state" not in columns:
        migrations.append("ALTER TABLE generation_tasks ADD COLUMN graph_state TEXT")

    if not migrations:
        return

    with db_engine.begin() as connection:
        for migration in migrations:
            connection.execute(text(migration))


def check_db_connection() -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
