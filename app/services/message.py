from time import time

from openai.types.responses import Response, ResponseInputParam
from pydantic import TypeAdapter
from sqlmodel import Session, col, delete, select

from app.models import Message


RESPONSE_INPUT_ADAPTER = TypeAdapter(ResponseInputParam)


def list_messages(
    session: Session,
    cursor: int | None,
    limit: int,
) -> list[Message]:
    statement = select(Message).order_by(col(Message.id).desc()).limit(limit)
    if cursor is not None:
        statement = statement.where(col(Message.id) < cursor)

    return list(reversed(session.exec(statement).all()))


def clear_messages(session: Session) -> None:
    session.exec(delete(Message))
    session.commit()


def build_input(
    session: Session,
    window_size: int,
) -> ResponseInputParam:
    input: list[object] = [
        {"role": "developer", "content": "你是一个车险助手"},
    ]

    statement = select(Message).order_by(col(Message.id).desc()).limit(window_size)
    messages = session.exec(statement).all()

    for message in reversed(messages):
        if message.input:
            input.extend(message.input)
        if message.output:
            input.extend(message.output)

    return RESPONSE_INPUT_ADAPTER.validate_python(input)


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
