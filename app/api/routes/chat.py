from collections.abc import AsyncIterable

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from openai import APIError, AsyncOpenAI
from sqlmodel import Session

from app.api.deps import get_app_settings, get_openai_client, get_session
from app.config import Settings
from app.schemas import ChatRequest, ChatResponse
from app.services import chat as chat_service


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_app_settings),
    client: AsyncOpenAI = Depends(get_openai_client),
    session: Session = Depends(get_session),
) -> ChatResponse:
    try:
        response = await chat_service.chat(
            request.content,
            settings,
            client,
            session,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI API 请求失败：{exc.message}",
        ) from exc

    return ChatResponse(reply=response.output_text)


@router.post("/stream", response_class=EventSourceResponse)
async def chat_stream(
    request: ChatRequest,
    settings: Settings = Depends(get_app_settings),
    client: AsyncOpenAI = Depends(get_openai_client),
    session: Session = Depends(get_session),
) -> AsyncIterable[ServerSentEvent]:
    try:
        stream = chat_service.chat_stream(
            request.content,
            settings,
            client,
            session,
        )
        async for event in stream:
            yield ServerSentEvent(
                raw_data=event.model_dump_json(by_alias=True, exclude_none=True)
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
