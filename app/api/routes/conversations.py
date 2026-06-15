from ag_ui.core import Message as AGUIMessage
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.api.deps import get_session
from app.services import conversation as conversation_service


router = APIRouter(prefix="/conversations", tags=["conversations"])
THREAD_ID = "thread_1"


@router.get("/{conversation_id}/messages", response_model=list[AGUIMessage])
def list_conversation_messages(
    conversation_id: str,
    cursor: int | None = Query(
        default=None,
        ge=1,
        description="当前页最早一轮的起始数据库 ID",
    ),
    limit: int = Query(default=10, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[AGUIMessage]:
    if conversation_id != THREAD_ID:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        )

    return conversation_service.list_conversation_messages(
        session=session,
        run_limit=limit,
        cursor=cursor,
    )
