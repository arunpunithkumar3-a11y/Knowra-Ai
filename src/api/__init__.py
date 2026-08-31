from src.api.auth import auth_router
from src.api.business import business_router
from src.api.chat import agent_router
from src.api.document import document_router

buisness_router = business_router
chat_router = agent_router

__all__ = [
    "auth_router",
    "business_router",
    "buisness_router",
    "document_router",
    "agent_router",
    "chat_router",
]
