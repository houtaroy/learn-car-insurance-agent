from fastapi import APIRouter

from app.api.routes import chat, conversations, files, messages


api_router = APIRouter()
api_router.include_router(messages.router)
api_router.include_router(conversations.router)
api_router.include_router(chat.router)
api_router.include_router(files.router)
