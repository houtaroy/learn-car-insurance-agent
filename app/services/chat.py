from collections.abc import AsyncIterator

from openai import AsyncOpenAI
from openai.types.responses import Response, ResponseCompletedEvent
from sqlmodel import Session

from app.config import Settings
from app.schemas import ChatStreamEvent
from app.services.message import (
    build_input,
    save_response_message,
    save_user_message,
)


async def chat(
    content: str,
    settings: Settings,
    client: AsyncOpenAI,
    session: Session,
) -> Response:
    save_user_message(session, content)

    input = build_input(session, settings.chat_history_window_size)
    response = await client.responses.create(
        model=settings.openai_model,
        input=input,
        reasoning={"effort": "none"},
    )

    save_response_message(session, response)

    return response


async def chat_stream(
    content: str,
    settings: Settings,
    client: AsyncOpenAI,
    session: Session,
) -> AsyncIterator[ChatStreamEvent]:
    save_user_message(session, content)

    input = build_input(session, settings.chat_history_window_size)

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
