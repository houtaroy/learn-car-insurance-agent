from collections.abc import AsyncIterable

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from openai import AsyncOpenAI
from sqlmodel import Session

from app.api.deps import get_app_settings, get_openai_client, get_session
from app.config import Settings
from app.schemas import ChatRequest
from app.services import chat as chat_service


router = APIRouter(prefix="/chat", tags=["chat"])


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
