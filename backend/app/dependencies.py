"""Dependency wiring for the FastAPI application."""

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.repositories.conversation_repository import ConversationRepository
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.vectorstore.store_setup import VectorStoreManager


@lru_cache
def get_vector_store_manager() -> VectorStoreManager:
    """Return a singleton vector store manager instance."""

    settings = get_settings()
    return VectorStoreManager(settings=settings)


@lru_cache
def get_conversation_repository() -> ConversationRepository:
    """Return a singleton conversation repository instance."""

    settings = get_settings()
    return ConversationRepository(settings=settings)


@lru_cache
def get_chat_service() -> ChatService:
    """Return a singleton chat service instance."""

    settings = get_settings()
    vector_manager = get_vector_store_manager()
    conversation_repository = get_conversation_repository()
    return ChatService(
        settings=settings,
        vector_manager=vector_manager,
        conversation_repository=conversation_repository,
    )


@lru_cache
def get_conversation_service() -> ConversationService:
    """Return a singleton conversation service instance."""

    settings = get_settings()
    repository = get_conversation_repository()
    vector_manager = get_vector_store_manager()
    return ConversationService(
        settings=settings,
        repository=repository,
        vector_manager=vector_manager,
    )
