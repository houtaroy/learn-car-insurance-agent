from collections.abc import AsyncIterator
from uuid import uuid4

from openai import AsyncOpenAI
from openai.types.responses import (
    Response,
    ResponseCompletedEvent,
    ResponseFunctionToolCall,
    ResponseInputParam,
)
from openai.types.responses.response_input_param import FunctionCallOutput
from pydantic import TypeAdapter
from sqlmodel import Session

from app.config import Settings
from app.models import Message
from app.schemas import ChatStreamEvent
from app.services.message import (
    list_recent_run_messages,
    save_response_message,
    save_tool_outputs,
    save_user_message,
)
from app.services.tool import TOOLS, call_tool


RESPONSE_INPUT_ADAPTER = TypeAdapter(ResponseInputParam)


def build_input(messages: list[Message]) -> ResponseInputParam:
    input: list[object] = [
        {"role": "developer", "content": "你是一个车险助手"},
    ]

    for message in messages:
        if message.input:
            input.extend(message.input)
        if message.output:
            input.extend(message.output)

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
    run_id = str(uuid4())

    save_user_message(session, run_id, content)

    messages = list_recent_run_messages(session, settings.chat_history_run_limit)
    input = build_input(messages)

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
) -> AsyncIterator[ChatStreamEvent]:
    run_id = str(uuid4())

    save_user_message(session, run_id, content)

    messages = list_recent_run_messages(session, settings.chat_history_run_limit)
    input = build_input(messages)

    while True:
        stream = await client.responses.create(
            model=settings.openai_model,
            reasoning={"effort": "none"},
            input=input,
            tools=TOOLS,
            parallel_tool_calls=False,
            stream=True,
        )

        completed_event = None

        async with stream:
            async for event in stream:
                if isinstance(event, ChatStreamEvent):
                    yield event
                if isinstance(event, ResponseCompletedEvent):
                    completed_event = event

        if completed_event is None:
            return

        response = completed_event.response
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

        return
