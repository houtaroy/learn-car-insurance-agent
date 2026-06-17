from ag_ui.core import (
    AssistantMessage,
    FunctionCall,
    ImageInputContent,
    InputContent,
    InputContentUrlSource,
    Message as AGUIMessage,
    ReasoningMessage,
    TextInputContent,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from sqlmodel import Session

from app.services.message import list_recent_run_messages


UserContent = str | list[InputContent]


def list_conversation_messages(
    session: Session,
    conversation_id: str,
    run_limit: int,
    cursor: int | None = None,
) -> list[AGUIMessage]:
    records = list_recent_run_messages(session, conversation_id, run_limit, cursor)
    messages: list[AGUIMessage] = []

    for record in records:
        for item in (record.input or []) + (record.output or []):
            message = _build_agui_message(str(record.id), item)
            if message is not None:
                messages.append(message)

    return messages


def _build_agui_message(record_id: str, item: dict[str, object]) -> AGUIMessage | None:
    match item:
        case {"role": "user", "content": content}:
            return UserMessage(
                id=record_id,
                content=_build_user_content(content),
            )
        case {"role": "assistant", "id": str(message_id), "content": list(content)}:
            return AssistantMessage(
                id=message_id,
                content=_build_assistant_content(content),
            )
        case {"type": "reasoning", "id": str(message_id), "summary": list(summary)}:
            content = _build_reasoning_content(summary)
            if content:
                return ReasoningMessage(
                    id=message_id,
                    content=content,
                )
        case {
            "type": "function_call",
            "id": str(message_id),
            "call_id": str(call_id),
            "name": str(name),
            "arguments": str(arguments),
        }:
            return AssistantMessage(
                id=message_id,
                tool_calls=[
                    ToolCall(
                        id=call_id,
                        function=FunctionCall(
                            name=name,
                            arguments=arguments,
                        ),
                    )
                ],
            )
        case {
            "type": "function_call_output",
            "call_id": str(call_id),
            "output": str(output),
        }:
            return ToolMessage(
                id=record_id,
                tool_call_id=call_id,
                content=output,
            )

    return None


def _build_user_content(content: object) -> UserContent:
    match content:
        case str() as text:
            return text
        case list() as parts:
            return [_build_user_content_part(part) for part in parts]
        case _:
            raise ValueError("用户消息内容仅支持字符串或内容列表")


def _build_user_content_part(part: object) -> InputContent:
    match part:
        case {"type": "input_text", "text": str(text)}:
            return TextInputContent(text=text)
        case {"type": "input_image", "image_url": str(image_url)}:
            return ImageInputContent(
                source=InputContentUrlSource(value=image_url),
            )
        case _:
            raise ValueError("用户消息内容仅支持文本和图片 URL")


def _build_assistant_content(content: list[object]) -> str:
    texts: list[str] = []
    for part in content:
        match part:
            case {"type": "output_text", "text": str(text)}:
                texts.append(text)
    return "\n".join(texts)


def _build_reasoning_content(summary: list[object]) -> str:
    texts: list[str] = []
    for part in summary:
        match part:
            case {"type": "summary_text", "text": str(text)}:
                texts.append(text)
    return "\n".join(texts)
