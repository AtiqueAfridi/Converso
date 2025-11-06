"""Dependency wiring for the FastAPI application."""

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.services.chat_service import ChatService
from app.vectorstore.store_setup import VectorStoreManager


@lru_cache
def get_vector_store_manager(settings: Settings | None = None) -> VectorStoreManager:
    """Return a singleton vector store manager instance."""

    settings = settings or get_settings()
    return VectorStoreManager(settings=settings)


@lru_cache
def get_chat_service(settings: Settings | None = None) -> ChatService:
    """Return a singleton chat service instance."""

    settings = settings or get_settings()
    vector_manager = get_vector_store_manager(settings)
    return ChatService(settings=settings, vector_manager=vector_manager)
