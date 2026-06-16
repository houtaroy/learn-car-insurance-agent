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
    run_limit: int,
    cursor: int | None = None,
) -> list[AGUIMessage]:
    records = list_recent_run_messages(session, run_limit, cursor)
    messages: list[AGUIMessage] = []

    for record in records:
        for item in (record.input or []) + (record.output or []):
            match (item.get("role"), item.get("type")):
                case ("user", _):
                    messages.append(
                        UserMessage(
                            id=str(record.id),
                            content=_build_user_content(item["content"]),
                        )
                    )
                case ("assistant", _):
                    messages.append(
                        AssistantMessage(
                            id=item["id"],
                            content=_build_assistant_content(item["content"]),
                        )
                    )
                case (_, "reasoning"):
                    content = "\n".join(
                        part["text"]
                        for part in item["summary"]
                        if part["type"] == "summary_text"
                    )
                    if content:
                        messages.append(
                            ReasoningMessage(
                                id=item["id"],
                                content=content,
                            )
                        )
                case (_, "function_call"):
                    messages.append(
                        AssistantMessage(
                            id=item["id"],
                            tool_calls=[
                                ToolCall(
                                    id=item["call_id"],
                                    function=FunctionCall(
                                        name=item["name"],
                                        arguments=item["arguments"],
                                    ),
                                )
                            ],
                        )
                    )
                case (_, "function_call_output"):
                    messages.append(
                        ToolMessage(
                            id=str(record.id),
                            tool_call_id=item["call_id"],
                            content=item["output"],
                        )
                    )

    return messages


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


def _build_assistant_content(content: list[dict[str, object]]) -> str:
    return "\n".join(
        text
        for part in content
        if part["type"] == "output_text"
        for text in [part["text"]]
        if isinstance(text, str)
    )
