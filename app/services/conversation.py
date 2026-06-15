from ag_ui.core import (
    AssistantMessage,
    FunctionCall,
    Message as AGUIMessage,
    ReasoningMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from sqlmodel import Session

from app.services.message import list_recent_run_messages


def list_conversation_messages(
    session: Session,
    run_limit: int,
    cursor: int | None = None,
) -> list[AGUIMessage]:
    records = list_recent_run_messages(session, run_limit, cursor)
    messages: list[AGUIMessage] = []

    for record in records:
        for item in (record.input or []) + (record.output or []):
            role = item.get("role")
            if role:
                match role:
                    case "user":
                        messages.append(
                            UserMessage(
                                id=str(record.id),
                                content=item["content"],
                            )
                        )
                    case "assistant":
                        text = "\n".join(
                            content["text"]
                            for content in item["content"]
                            if content["type"] == "output_text"
                        )
                        messages.append(
                            AssistantMessage(
                                id=item["id"],
                                content=text,
                            )
                        )
                continue

            match item.get("type"):
                case "reasoning":
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
                case "function_call":
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
                case "function_call_output":
                    messages.append(
                        ToolMessage(
                            id=str(record.id),
                            tool_call_id=item["call_id"],
                            content=item["output"],
                        )
                    )

    return messages
