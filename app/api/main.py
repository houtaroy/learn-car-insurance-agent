from fastapi import APIRouter

from app.api.routes import chat, conversations, messages


api_router = APIRouter()
api_router.include_router(messages.router)
api_router.include_router(conversations.router)
api_router.include_router(chat.router)
