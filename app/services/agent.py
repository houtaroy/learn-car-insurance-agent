from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import uuid4

from ag_ui.core import Event, ToolCallEndEvent, ToolCallResultEvent, ToolCallStartEvent
from openai import AsyncOpenAI
from openai.types.responses import (
    ResponseCompletedEvent,
    ResponseErrorEvent,
    ResponseFailedEvent,
    ResponseFunctionToolCall,
    ResponseIncompleteEvent,
    ResponseInputParam,
    ResponseStreamEvent,
)
from openai.types.responses.response_input_param import FunctionCallOutput

from app.config import Settings
from app.services.tool import TOOLS, call_tool


@dataclass(frozen=True)
class FunctionCallOutputs:
    outputs: list[FunctionCallOutput]


AgentLoopEvent = ResponseStreamEvent | Event | FunctionCallOutputs


async def loop(
    input: ResponseInputParam,
    settings: Settings,
    client: AsyncOpenAI,
) -> AsyncIterator[AgentLoopEvent]:
    while True:
        stream = await client.responses.create(
            model=settings.openai_model,
            reasoning={"effort": "minimal"},
            input=input,
            tools=TOOLS,
            parallel_tool_calls=False,
            stream=True,
        )

        completed_event: ResponseCompletedEvent | None = None

        async with stream:
            async for event in stream:
                if isinstance(event, ResponseCompletedEvent):
                    completed_event = event

                yield event

                if isinstance(
                    event,
                    (ResponseErrorEvent, ResponseFailedEvent, ResponseIncompleteEvent),
                ):
                    return

        if not completed_event:
            return

        function_calls = get_function_calls(completed_event)

        if not function_calls:
            return

        input.extend(
            item.model_dump(mode="json", exclude_none=True)
            for item in completed_event.response.output
        )
        function_call_outputs: list[FunctionCallOutput] = []
        for function_call in function_calls:
            yield ToolCallStartEvent(
                tool_call_id=function_call.call_id,
                tool_call_name=function_call.name,
            )
            tool_result = call_tool(function_call)
            yield ToolCallEndEvent(tool_call_id=function_call.call_id)
            yield ToolCallResultEvent(
                message_id=f"msg_{uuid4().hex}",
                tool_call_id=function_call.call_id,
                content=tool_result,
                role="tool",
            )
            function_call_outputs.append(
                FunctionCallOutput(
                    type="function_call_output",
                    call_id=function_call.call_id,
                    output=tool_result,
                )
            )
        input.extend(function_call_outputs)
        yield FunctionCallOutputs(outputs=function_call_outputs)


def get_function_calls(event: ResponseCompletedEvent) -> list[ResponseFunctionToolCall]:
    return [
        item
        for item in event.response.output
        if isinstance(item, ResponseFunctionToolCall)
    ]
