"""Dependency wiring for the FastAPI application."""

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.repositories.conversation_repository import ConversationRepository
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.document_processor import DocumentProcessor
from app.services.document_service import DocumentService
from app.services.document_store import DocumentStore
from app.services.retrieval_service import RetrievalService
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
    retrieval_service = get_retrieval_service()
    return ChatService(
        settings=settings,
        vector_manager=vector_manager,
        conversation_repository=conversation_repository,
        retrieval_service=retrieval_service,
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


@lru_cache
def get_document_processor() -> DocumentProcessor:
    """Return a singleton document processor instance."""

    settings = get_settings()
    return DocumentProcessor(settings=settings)


@lru_cache
def get_document_store() -> DocumentStore:
    """Return a singleton document store instance."""

    settings = get_settings()
    return DocumentStore(settings=settings)


@lru_cache
def get_retrieval_service() -> RetrievalService:
    """Return a singleton retrieval service instance."""

    document_store = get_document_store()
    return RetrievalService(document_store=document_store)


@lru_cache
def get_document_service() -> DocumentService:
    """Return a singleton document service instance."""

    settings = get_settings()
    processor = get_document_processor()
    document_store = get_document_store()
    retrieval_service = get_retrieval_service()
    return DocumentService(
        settings=settings,
        processor=processor,
        document_store=document_store,
        retrieval_service=retrieval_service,
    )
