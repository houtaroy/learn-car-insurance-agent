from pathlib import Path

from sqlalchemy.engine import make_url
from sqlmodel import SQLModel, create_engine

from app.config import get_settings


settings = get_settings()
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables() -> None:
    database_path = make_url(settings.database_url).database
    if database_path:
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    SQLModel.metadata.create_all(engine)
