from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

from ag_ui.core import (
    Event,
    ImageInputContent,
    InputContent,
    InputContentUrlSource,
    RunErrorEvent,
    RunStartedEvent,
    TextInputContent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    RunFinishedEvent,
    ThinkingEndEvent,
    ThinkingStartEvent,
    ThinkingTextMessageContentEvent,
    ThinkingTextMessageEndEvent,
    ThinkingTextMessageStartEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from openai import AsyncOpenAI
from openai.types.responses import (
    ResponseCompletedEvent,
    ResponseErrorEvent,
    ResponseFailedEvent,
    ResponseIncompleteEvent,
    ResponseInputParam,
    ResponseOutputItemAddedEvent,
    ResponseOutputItemDoneEvent,
    ResponseOutputMessage,
    ResponseReasoningItem,
    ResponseReasoningSummaryTextDeltaEvent,
    ResponseReasoningSummaryTextDoneEvent,
    ResponseTextDeltaEvent,
)
from pydantic import TypeAdapter
from sqlmodel import Session

from app.config import Settings
from app.models import Message
from app.services.message import (
    list_recent_run_messages,
    save_user_input,
    save_assistant_response,
    save_function_call_outputs,
)
from app.services.agent import FunctionCallOutputs, loop


RESPONSE_INPUT_ADAPTER = TypeAdapter(ResponseInputParam)
UserContent = str | list[InputContent]


async def chat(
    conversation_id: str,
    content: UserContent,
    settings: Settings,
    client: AsyncOpenAI,
    session: Session,
) -> AsyncIterator[Event]:
    run_id = create_run_id()

    developer_prompt = load_developer_prompt(settings.developer_prompt_path)
    messages = list_recent_run_messages(
        session,
        conversation_id,
        settings.chat_history_run_limit,
    )
    user_input = build_user_input(content)
    save_user_input(session, conversation_id, run_id, user_input)
    input = build_input(developer_prompt, messages, user_input)

    yield RunStartedEvent(thread_id=conversation_id, run_id=run_id)

    async for event in loop(input, settings, client):
        match event:
            case ResponseOutputItemAddedEvent(item=ResponseReasoningItem()):
                yield ThinkingStartEvent()
                yield ThinkingTextMessageStartEvent()
            case ResponseReasoningSummaryTextDeltaEvent(delta=delta):
                yield ThinkingTextMessageContentEvent(delta=delta)
            case ResponseReasoningSummaryTextDoneEvent():
                yield ThinkingTextMessageEndEvent()
            case ResponseOutputItemDoneEvent(item=ResponseReasoningItem()):
                yield ThinkingEndEvent()
            case ToolCallStartEvent() | ToolCallEndEvent() | ToolCallResultEvent():
                yield event
            case FunctionCallOutputs(outputs=outputs):
                save_function_call_outputs(session, conversation_id, run_id, outputs)
            case ResponseOutputItemAddedEvent(
                item=ResponseOutputMessage(id=message_id)
            ):
                yield TextMessageStartEvent(
                    message_id=message_id,
                    role="assistant",
                )
            case ResponseTextDeltaEvent(item_id=message_id, delta=delta):
                yield TextMessageContentEvent(
                    message_id=message_id,
                    delta=delta,
                )
            case ResponseOutputItemDoneEvent(item=ResponseOutputMessage(id=message_id)):
                yield TextMessageEndEvent(message_id=message_id)
            case ResponseCompletedEvent(response=response):
                save_assistant_response(session, conversation_id, run_id, response)
            case ResponseErrorEvent(code=code, message=message):
                yield RunErrorEvent(code=code, message=message)
                return
            case ResponseFailedEvent(response=response):
                error = response.error
                yield RunErrorEvent(
                    code=error.code if error else None,
                    message=error.message if error else "响应失败",
                )
                return
            case ResponseIncompleteEvent(response=response):
                details = response.incomplete_details
                reason = details.reason if details else None
                yield RunErrorEvent(
                    code=reason,
                    message=(f"响应未完成：{reason}" if reason else "响应未完成"),
                )
                return

    yield RunFinishedEvent(thread_id=conversation_id, run_id=run_id)


def create_run_id() -> str:
    return f"run_{uuid4().hex}"


def load_developer_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def build_input(
    developer_prompt: str,
    messages: list[Message],
    user_input: list[dict[str, object]],
) -> ResponseInputParam:
    response_input: list[object] = [
        {"role": "developer", "content": developer_prompt},
    ]

    for message in messages:
        if message.input:
            response_input.extend(message.input)
        if message.output:
            response_input.extend(message.output)

    response_input.extend(user_input)

    return RESPONSE_INPUT_ADAPTER.validate_python(response_input)


def build_user_input(content: UserContent) -> list[dict[str, object]]:
    return [_build_user_content_input(content)]


def _build_user_content_input(content: UserContent) -> dict[str, object]:
    match content:
        case str() as content:
            return {"role": "user", "content": content}
        case list() as content:
            return {
                "role": "user",
                "content": [_build_input_content_part(item) for item in content],
            }


def _build_input_content_part(item: object) -> dict[str, object]:
    match item:
        case TextInputContent(text=text):
            return {"type": "input_text", "text": text}
        case ImageInputContent(source=InputContentUrlSource(value=image_url)):
            return {
                "type": "input_image",
                "image_url": image_url,
                "detail": "auto",
            }
        case ImageInputContent():
            raise ValueError("图片输入仅支持 URL 来源")
        case _:
            raise ValueError("用户消息内容仅支持文本和图片")
