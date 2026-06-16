from time import time
from typing import Any

from openai.types.responses import Response
from openai.types.responses.response_input_param import FunctionCallOutput
from sqlalchemy import func
from sqlmodel import Session, col, delete, select

from app.models import Message


def list_messages(
    session: Session,
    cursor: int | None,
    limit: int,
) -> list[Message]:
    statement = select(Message).order_by(col(Message.id).desc()).limit(limit)
    if cursor is not None:
        statement = statement.where(col(Message.id) < cursor)

    return list(reversed(session.exec(statement).all()))


def list_recent_run_messages(
    session: Session,
    run_limit: int,
    cursor: int | None = None,
) -> list[Message]:
    run_id_column = col(Message.run_id)

    latest_runs_statement = (
        select(run_id_column)
        .where(run_id_column.is_not(None))
        .group_by(run_id_column)
    )
    if cursor is not None:
        latest_runs_statement = latest_runs_statement.having(
            func.max(Message.id) < cursor
        )

    latest_runs_statement = latest_runs_statement.order_by(
        func.max(Message.id).desc()
    ).limit(run_limit)

    run_ids = [run_id for run_id in session.exec(latest_runs_statement).all()]
    if not run_ids:
        return []

    statement = (
        select(Message)
        .where(col(Message.run_id).in_(run_ids))
        .order_by(col(Message.id))
    )
    return list(session.exec(statement).all())


def clear_messages(session: Session) -> None:
    session.exec(delete(Message))
    session.commit()


def save_input_message(
    session: Session,
    run_id: str,
    input: list[dict[str, Any]],
) -> None:
    created_at = time()
    session.add(
        Message(
            run_id=run_id,
            input=input,
            created_at=created_at,
            completed_at=created_at,
        )
    )
    session.commit()


def save_response_message(
    session: Session,
    run_id: str,
    response: Response,
) -> None:
    message = Message(
        run_id=run_id,
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


def save_tool_outputs(
    session: Session,
    run_id: str,
    tool_outputs: list[FunctionCallOutput],
) -> None:
    created_at = time()
    serialized_outputs: list[dict[str, Any]] = [
        dict(tool_output) for tool_output in tool_outputs
    ]
    session.add(
        Message(
            run_id=run_id,
            input=serialized_outputs,
            created_at=created_at,
            completed_at=created_at,
        )
    )
    session.commit()
