from collections.abc import AsyncIterable

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from openai import APIError, AsyncOpenAI
from sqlmodel import Session

from app.config import Settings
from app.deps import get_app_settings, get_openai_client, get_session
from app.models import Message
from app.schemas import ChatRequest, ChatResponse
from app.services import chat as chat_service
from app.services import message as message_service


router = APIRouter()


@router.get("/messages", response_model=list[Message])
def list_messages(
    cursor: int | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[Message]:
    return message_service.list_messages(session, cursor, limit)


@router.delete("/messages", status_code=status.HTTP_204_NO_CONTENT)
def clear_messages(session: Session = Depends(get_session)) -> None:
    message_service.clear_messages(session)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_app_settings),
    client: AsyncOpenAI = Depends(get_openai_client),
    session: Session = Depends(get_session),
) -> ChatResponse:
    try:
        response = await chat_service.chat(
            request.message,
            settings,
            client,
            session,
        )
    except APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI API 请求失败：{exc.message}",
        ) from exc

    return ChatResponse(reply=response.output_text)


@router.post("/chat/stream", response_class=EventSourceResponse)
async def chat_stream(
    request: ChatRequest,
    settings: Settings = Depends(get_app_settings),
    client: AsyncOpenAI = Depends(get_openai_client),
    session: Session = Depends(get_session),
) -> AsyncIterable[ServerSentEvent]:
    stream = chat_service.chat_stream(
        request.message,
        settings,
        client,
        session,
    )

    async for event in stream:
        yield ServerSentEvent(data=event)
