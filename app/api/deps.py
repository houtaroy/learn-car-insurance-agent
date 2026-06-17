from collections.abc import Generator

import alibabacloud_oss_v2 as oss
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


def build_oss_client(settings: Settings) -> oss.Client:
    required_settings = {
        "OSS_ACCESS_KEY_ID": settings.oss_access_key_id,
        "OSS_ACCESS_KEY_SECRET": settings.oss_access_key_secret,
        "OSS_REGION": settings.oss_region,
        "OSS_BUCKET": settings.oss_bucket,
    }
    missing = [name for name, value in required_settings.items() if not value]
    if missing:
        raise RuntimeError(f"OSS 配置缺失：{', '.join(missing)}")

    config = oss.config.load_default()
    config.credentials_provider = oss.credentials.StaticCredentialsProvider(
        settings.oss_access_key_id,
        settings.oss_access_key_secret,
    )
    config.region = settings.oss_region
    return oss.Client(config)


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_oss_client(request: Request) -> oss.Client:
    return request.app.state.oss_client


def get_openai_client(request: Request) -> AsyncOpenAI:
    return request.app.state.openai_client


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session
