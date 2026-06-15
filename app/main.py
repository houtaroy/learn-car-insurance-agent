from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.deps import build_openai_client
from app.api.main import api_router
from app.config import get_settings
from app.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.settings = settings

    create_db_and_tables()

    app.state.openai_client = build_openai_client(settings)

    try:
        yield
    finally:
        await app.state.openai_client.close()


app = FastAPI(title="学习车险智能体", lifespan=lifespan)
app.include_router(api_router)
