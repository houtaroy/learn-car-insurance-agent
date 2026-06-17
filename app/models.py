from typing import Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    conversation_id: str | None = Field(default=None, index=True)
    run_id: str | None = Field(default=None, index=True)
    response_id: str | None = Field(default=None, index=True, unique=True)
    model: str | None = None
    input: list[dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    output: list[dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    created_at: float
    completed_at: float | None = None
