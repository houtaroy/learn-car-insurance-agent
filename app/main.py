from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from openai import APIError, AsyncOpenAI

from app.config import Settings, get_settings
from app.schemas import ChatRequest, ChatResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.settings = settings
    app.state.openai_client = build_openai_client(settings)
    try:
        yield
    finally:
        await app.state.openai_client.close()


app = FastAPI(title="学习车险智能体", lifespan=lifespan)


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


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_app_settings),
    client: AsyncOpenAI = Depends(get_openai_client),
) -> ChatResponse:
    try:
        response = await client.responses.create(
            model=settings.openai_model,
            input=request.message,
            reasoning={"effort": "none"},
        )
    except APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI API 请求失败：{exc.message}",
        ) from exc

    return ChatResponse(reply=response.output_text)
