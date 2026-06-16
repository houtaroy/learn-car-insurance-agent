from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from ag_ui.core import (
    Event,
    ImageInputContent,
    InputContent,
    InputContentUrlSource,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextInputContent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
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
    Response,
    ResponseCompletedEvent,
    ResponseErrorEvent,
    ResponseFailedEvent,
    ResponseFunctionToolCall,
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
from openai.types.responses.response_input_param import FunctionCallOutput
from pydantic import TypeAdapter
from sqlmodel import Session

from app.config import Settings
from app.models import Message
from app.services.message import (
    list_recent_run_messages,
    save_input_message,
    save_response_message,
    save_tool_outputs,
)
from app.services.tool import TOOLS, call_tool


RESPONSE_INPUT_ADAPTER = TypeAdapter(ResponseInputParam)
THREAD_ID = "thread_1"
UserContent = str | list[InputContent]


@dataclass
class ChatRun:
    run_id: str
    response_input: ResponseInputParam


async def chat_stream(
    content: UserContent,
    settings: Settings,
    client: AsyncOpenAI,
    session: Session,
) -> AsyncIterator[Event]:
    run = prepare_chat_run(content, settings, session)

    yield RunStartedEvent(thread_id=THREAD_ID, run_id=run.run_id)

    while True:
        stream = await client.responses.create(
            model=settings.openai_model,
            reasoning={"effort": "minimal"},
            input=run.response_input,
            tools=TOOLS,
            parallel_tool_calls=False,
            stream=True,
        )

        completed_event: ResponseCompletedEvent | None = None

        async with stream:
            async for event in stream:
                match event:
                    case ResponseCompletedEvent():
                        completed_event = event
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
                            message=(
                                f"响应未完成：{reason}" if reason else "响应未完成"
                            ),
                        )
                        return
                    case _:
                        for ag_ui_event in to_ag_ui_events(event):
                            yield ag_ui_event

        if completed_event is None:
            yield RunErrorEvent(message="响应流结束但未收到完成事件")
            return

        response = completed_event.response
        save_response_message(session, run.run_id, response)

        tool_calls = get_tool_calls(response)
        if not tool_calls:
            yield RunFinishedEvent(thread_id=THREAD_ID, run_id=run.run_id)
            return

        tool_outputs: list[FunctionCallOutput] = []
        for tool_call in tool_calls:
            yield ToolCallStartEvent(
                tool_call_id=tool_call.call_id,
                tool_call_name=tool_call.name,
            )
            tool_result = call_tool(tool_call)
            yield ToolCallEndEvent(tool_call_id=tool_call.call_id)
            yield ToolCallResultEvent(
                message_id=f"msg_{uuid4().hex}",
                tool_call_id=tool_call.call_id,
                content=tool_result,
                role="tool",
            )
            tool_outputs.append(build_tool_output(tool_call, tool_result))

        save_tool_outputs(session, run.run_id, tool_outputs)
        add_tool_results_to_input(run.response_input, response, tool_outputs)


def prepare_chat_run(
    content: UserContent,
    settings: Settings,
    session: Session,
) -> ChatRun:
    run_id = create_run_id()
    developer_prompt = load_developer_prompt(settings.developer_prompt_path)
    messages = list_recent_run_messages(session, settings.chat_history_run_limit)
    current_input = build_current_input(content)

    save_input_message(session, run_id, current_input)

    return ChatRun(
        run_id=run_id,
        response_input=build_input(developer_prompt, messages, current_input),
    )


def create_run_id() -> str:
    return f"run_{uuid4().hex}"


def load_developer_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def build_input(
    developer_prompt: str,
    messages: list[Message],
    current_input: list[dict[str, object]],
) -> ResponseInputParam:
    response_input: list[object] = [
        {"role": "developer", "content": developer_prompt},
    ]

    for message in messages:
        if message.input:
            response_input.extend(message.input)
        if message.output:
            response_input.extend(message.output)

    response_input.extend(current_input)

    return RESPONSE_INPUT_ADAPTER.validate_python(response_input)


def build_current_input(content: UserContent) -> list[dict[str, object]]:
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


def get_tool_calls(response: Response) -> list[ResponseFunctionToolCall]:
    return [
        item for item in response.output if isinstance(item, ResponseFunctionToolCall)
    ]


def build_tool_output(
    tool_call: ResponseFunctionToolCall,
    result: str,
) -> FunctionCallOutput:
    return {
        "type": "function_call_output",
        "call_id": tool_call.call_id,
        "output": result,
    }


def add_tool_results_to_input(
    response_input: ResponseInputParam,
    response: Response,
    tool_outputs: list[FunctionCallOutput],
) -> None:
    response_input.extend(
        item.model_dump(mode="json", exclude_none=True)
        for item in response.output
    )
    response_input.extend(tool_outputs)


def to_ag_ui_events(event: object) -> Iterator[Event]:
    match event:
        case ResponseOutputItemAddedEvent(item=ResponseReasoningItem()):
            yield ThinkingStartEvent()
            yield ThinkingTextMessageStartEvent()
        case ResponseOutputItemAddedEvent(item=ResponseOutputMessage(id=message_id)):
            yield TextMessageStartEvent(
                message_id=message_id,
                role="assistant",
            )
        case ResponseReasoningSummaryTextDeltaEvent(delta=delta):
            yield ThinkingTextMessageContentEvent(delta=delta)
        case ResponseReasoningSummaryTextDoneEvent():
            yield ThinkingTextMessageEndEvent()
        case ResponseTextDeltaEvent(item_id=message_id, delta=delta):
            yield TextMessageContentEvent(
                message_id=message_id,
                delta=delta,
            )
        case ResponseOutputItemDoneEvent(item=ResponseReasoningItem()):
            yield ThinkingEndEvent()
        case ResponseOutputItemDoneEvent(item=ResponseOutputMessage(id=message_id)):
            yield TextMessageEndEvent(message_id=message_id)
