from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.api.deps import get_session
from app.models import Message
from app.services import message as message_service


router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("", response_model=list[Message])
def list_messages(
    cursor: int | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[Message]:
    return message_service.list_messages(session, cursor, limit)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_messages(session: Session = Depends(get_session)) -> None:
    message_service.clear_messages(session)
