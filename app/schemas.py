from ag_ui.core import InputContent
from pydantic import BaseModel


class ChatRequest(BaseModel):
    content: str | list[InputContent]


class FileUploadResponse(BaseModel):
    url: str
