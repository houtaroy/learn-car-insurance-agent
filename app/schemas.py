from ag_ui.core import InputContent
from pydantic import BaseModel


class ChatRequest(BaseModel):
    content: str | list[InputContent]


class ChatResponse(BaseModel):
    reply: str


class FileUploadResponse(BaseModel):
    url: str
