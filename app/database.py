from pathlib import Path

from sqlalchemy import Index, inspect, text
from sqlalchemy.engine import make_url
from sqlmodel import SQLModel, create_engine

from app.config import get_settings
from app.models import Message


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

    if "run_id" not in {
        column["name"] for column in inspect(engine).get_columns(Message.__tablename__)
    }:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE message ADD COLUMN run_id VARCHAR"))

    Index(
        "ix_message_run_id",
        Message.__table__.c.run_id,
    ).create(bind=engine, checkfirst=True)
