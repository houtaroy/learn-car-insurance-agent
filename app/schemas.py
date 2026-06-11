from openai.types.responses import (
    ResponseCompletedEvent,
    ResponseCreatedEvent,
    ResponseOutputItemAddedEvent,
    ResponseOutputItemDoneEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
    ResponseTextDeltaEvent,
    ResponseReasoningSummaryTextDeltaEvent,
)
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    reply: str


ChatStreamEvent = (
    ResponseCreatedEvent
    | ResponseOutputItemAddedEvent
    | ResponseReasoningSummaryTextDeltaEvent
    | ResponseFunctionCallArgumentsDeltaEvent
    | ResponseTextDeltaEvent
    | ResponseOutputItemDoneEvent
    | ResponseCompletedEvent
)
