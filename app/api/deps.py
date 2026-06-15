from collections.abc import Generator

from fastapi import Request
from openai import AsyncOpenAI
from sqlmodel import Session

from app.config import Settings
from app.database import engine


def build_openai_client(settings: Settings) -> AsyncOpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY 未配置。")

    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_openai_client(request: Request) -> AsyncOpenAI:
    return request.app.state.openai_client


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session
