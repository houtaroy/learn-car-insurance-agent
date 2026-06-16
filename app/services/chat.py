from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

from ag_ui.core import (
    Event,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ThinkingEndEvent,
    ThinkingStartEvent,
    ThinkingTextMessageContentEvent,
    ThinkingTextMessageEndEvent,
    ThinkingTextMessageStartEvent,
    ToolCallStartEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
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


def create_run_id() -> str:
    return f"run_{uuid4().hex}"


def load_developer_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def build_input(
    developer_prompt: str,
    messages: list[Message],
    current_input: list[dict[str, object]],
) -> ResponseInputParam:
    input: list[object] = [
        {"role": "developer", "content": developer_prompt},
    ]

    for message in messages:
        if message.input:
            input.extend(message.input)
        if message.output:
            input.extend(message.output)

    input.extend(current_input)

    return RESPONSE_INPUT_ADAPTER.validate_python(input)


def get_tool_calls(response: Response) -> list[ResponseFunctionToolCall]:
    return [
        item for item in response.output if isinstance(item, ResponseFunctionToolCall)
    ]


async def chat(
    content: str,
    settings: Settings,
    client: AsyncOpenAI,
    session: Session,
) -> Response:
    run_id = create_run_id()

    developer_prompt = load_developer_prompt(settings.developer_prompt_path)
    messages = list_recent_run_messages(session, settings.chat_history_run_limit)
    current_input: list[dict[str, object]] = [{"role": "user", "content": content}]
    save_input_message(session, run_id, current_input)
    input = build_input(developer_prompt, messages, current_input)

    while True:
        response = await client.responses.create(
            model=settings.openai_model,
            input=input,
            reasoning={"effort": "none"},
            tools=TOOLS,
            parallel_tool_calls=False,
        )

        save_response_message(session, run_id, response)

        tool_calls = get_tool_calls(response)
        if tool_calls:
            input.extend(
                item.model_dump(mode="json", exclude_none=True)
                for item in response.output
            )
            tool_outputs: list[FunctionCallOutput] = []
            for tool_call in tool_calls:
                result = call_tool(tool_call)
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": tool_call.call_id,
                        "output": result,
                    }
                )
            save_tool_outputs(session, run_id, tool_outputs)
            input.extend(tool_outputs)
            continue

        return response


async def chat_stream(
    content: str,
    settings: Settings,
    client: AsyncOpenAI,
    session: Session,
) -> AsyncIterator[Event]:
    run_id = create_run_id()

    developer_prompt = load_developer_prompt(settings.developer_prompt_path)
    messages = list_recent_run_messages(session, settings.chat_history_run_limit)
    current_input: list[dict[str, object]] = [{"role": "user", "content": content}]
    save_input_message(session, run_id, current_input)
    input = build_input(developer_prompt, messages, current_input)

    yield RunStartedEvent(thread_id=THREAD_ID, run_id=run_id)

    while True:
        stream = await client.responses.create(
            model=settings.openai_model,
            reasoning={"effort": "minimal"},
            input=input,
            tools=TOOLS,
            parallel_tool_calls=False,
            stream=True,
        )

        completed_event = None

        async with stream:
            async for event in stream:
                match event:
                    case ResponseOutputItemAddedEvent(item=item):
                        match item:
                            case ResponseReasoningItem():
                                yield ThinkingStartEvent()
                                yield ThinkingTextMessageStartEvent()
                            case ResponseOutputMessage(id=message_id):
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
                    case ResponseOutputItemDoneEvent(item=item):
                        match item:
                            case ResponseReasoningItem():
                                yield ThinkingEndEvent()
                            case ResponseOutputMessage(id=message_id):
                                yield TextMessageEndEvent(message_id=message_id)
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
                    case ResponseCompletedEvent():
                        completed_event = event

        if completed_event is None:
            yield RunErrorEvent(message="响应流结束但未收到完成事件")
            return

        response = completed_event.response
        save_response_message(session, run_id, response)

        tool_calls = get_tool_calls(response)
        if tool_calls:
            tool_outputs: list[FunctionCallOutput] = []
            for tool_call in tool_calls:
                yield ToolCallStartEvent(
                    tool_call_id=tool_call.call_id,
                    tool_call_name=tool_call.name,
                )
                result = call_tool(tool_call)
                yield ToolCallEndEvent(tool_call_id=tool_call.call_id)
                yield ToolCallResultEvent(
                    message_id=f"msg_{uuid4().hex}",
                    tool_call_id=tool_call.call_id,
                    content=result,
                    role="tool",
                )
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": tool_call.call_id,
                        "output": result,
                    }
                )
            save_tool_outputs(session, run_id, tool_outputs)
            input.extend(
                item.model_dump(mode="json", exclude_none=True)
                for item in response.output
            )
            input.extend(tool_outputs)
            continue

        yield RunFinishedEvent(thread_id=THREAD_ID, run_id=run_id)
        return
