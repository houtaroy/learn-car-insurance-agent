from collections.abc import AsyncIterable, AsyncIterator
from contextlib import asynccontextmanager
from time import time

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.sse import EventSourceResponse
from openai import APIError, AsyncOpenAI
from openai.types.responses import Response, ResponseCompletedEvent, ResponseInputParam
from pydantic import TypeAdapter
from sqlmodel import Session, select, col

from app.config import Settings, get_settings
from app.database import create_db_and_tables, get_session
from app.models import Message
from app.schemas import ChatRequest, ChatResponse, ChatStreamEvent


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    create_db_and_tables()
    app.state.settings = settings
    app.state.openai_client = build_openai_client(settings)
    try:
        yield
    finally:
        await app.state.openai_client.close()


app = FastAPI(title="学习车险智能体", lifespan=lifespan)
RESPONSE_INPUT_ADAPTER = TypeAdapter(ResponseInputParam)


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


def build_input(
    session: Session,
) -> ResponseInputParam:
    conversation: list[object] = [
        {"role": "developer", "content": "你是一个车险助手"},
    ]

    statement = select(Message).order_by(col(Message.id))
    messages = session.exec(statement).all()
    for message in messages:
        if message.input:
            conversation.extend(message.input)
        if message.output:
            conversation.extend(message.output)

    return RESPONSE_INPUT_ADAPTER.validate_python(conversation)


def save_user_message(session: Session, content: str) -> None:
    created_at = time()
    session.add(
        Message(
            input=[{"role": "user", "content": content}],
            created_at=created_at,
            completed_at=created_at,
        )
    )
    session.commit()


def save_response_message(
    session: Session,
    response: Response,
) -> None:
    if response.completed_at is None:
        raise ValueError("只能持久化已完成的响应。")

    message = Message(
        response_id=response.id,
        model=response.model,
        output=[
            item.model_dump(mode="json", exclude_none=True) for item in response.output
        ],
        created_at=response.created_at,
        completed_at=response.completed_at,
    )
    session.add(message)
    session.commit()


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_app_settings),
    client: AsyncOpenAI = Depends(get_openai_client),
    session: Session = Depends(get_session),
) -> ChatResponse:

    save_user_message(session, request.message)

    input = build_input(session)

    try:
        response = await client.responses.create(
            model=settings.openai_model,
            input=input,
            reasoning={"effort": "none"},
        )
    except APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI API 请求失败：{exc.message}",
        ) from exc

    save_response_message(session, response)

    return ChatResponse(reply=response.output_text)


@app.post("/chat/stream", response_class=EventSourceResponse)
async def chat_stream(
    request: ChatRequest,
    settings: Settings = Depends(get_app_settings),
    client: AsyncOpenAI = Depends(get_openai_client),
    session: Session = Depends(get_session),
) -> AsyncIterable[ChatStreamEvent]:

    save_user_message(session, request.message)

    input = build_input(session)

    stream = await client.responses.create(
        model=settings.openai_model,
        reasoning={"effort": "none"},
        input=input,
        stream=True,
    )

    async with stream:
        async for event in stream:
            if isinstance(event, ResponseCompletedEvent):
                save_response_message(session, event.response)
            if isinstance(event, ChatStreamEvent):
                yield event
