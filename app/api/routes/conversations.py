from collections.abc import AsyncIterable

from ag_ui.core import Message as AGUIMessage
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from openai import AsyncOpenAI
from sqlmodel import Session

from app.api.deps import get_app_settings, get_openai_client, get_session
from app.config import Settings
from app.schemas import ChatRequest
from app.services import chat as chat_service
from app.services import conversation as conversation_service


router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("/{id}/chat", response_class=EventSourceResponse)
async def chat(
    id: str,
    request: ChatRequest,
    settings: Settings = Depends(get_app_settings),
    client: AsyncOpenAI = Depends(get_openai_client),
    session: Session = Depends(get_session),
) -> AsyncIterable[ServerSentEvent]:
    try:
        stream = chat_service.chat(
            id,
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


@router.get("/{id}/messages", response_model=list[AGUIMessage])
def list_conversation_messages(
    id: str,
    cursor: int | None = Query(
        default=None,
        ge=1,
        description="当前页最早一轮的起始数据库 ID",
    ),
    limit: int = Query(default=10, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[AGUIMessage]:
    return conversation_service.list_conversation_messages(
        session=session,
        conversation_id=id,
        run_limit=limit,
        cursor=cursor,
    )
