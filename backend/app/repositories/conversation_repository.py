"""Repository for conversation metadata operations."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from app.core.config import Settings


class ConversationRepository:
    """Data access layer for conversation metadata."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the conversation repository with ChromaDB storage."""

        self._settings = settings
        self._embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
        # Use a separate collection for conversation metadata
        self._store = Chroma(
            collection_name="conversation_metadata",
            embedding_function=self._embeddings,
            persist_directory=str(settings.chroma_persist_directory),
        )

    def create(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Create a new conversation metadata entry."""

        now = datetime.utcnow().isoformat()
        metadata = {
            "conversation_id": conversation_id,
            "title": title or f"Conversation {conversation_id[:8]}",
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "user_id": user_id or "",
            "is_archived": False,
        }

        # Store metadata as a document (we'll use a dummy embedding)
        document = Document(
            page_content=title or conversation_id,  # Minimal content for embedding
            metadata=metadata,
        )
        self._store.add_documents([document], ids=[conversation_id])
        return metadata

    def get(self, conversation_id: str) -> Optional[dict]:
        """Retrieve conversation metadata by ID."""

        try:
            results = self._store.get(
                ids=[conversation_id],
                include=["metadatas"],
            )
            if results.get("metadatas") and len(results["metadatas"]) > 0:
                return results["metadatas"][0]
            return None
        except Exception:
            return None

    def get_all(self, user_id: Optional[str] = None, limit: Optional[int] = None) -> List[dict]:
        """Retrieve all conversation metadata, optionally filtered by user_id."""

        try:
            where_filter = {}
            if user_id:
                where_filter["user_id"] = user_id

            results = self._store.get(
                where=where_filter if where_filter else None,
                include=["metadatas"],
            )
            metadatas = results.get("metadatas", [])

            # Sort by updated_at descending (most recent first)
            metadatas.sort(key=lambda m: m.get("updated_at", ""), reverse=True)

            if limit:
                metadatas = metadatas[:limit]

            return metadatas
        except Exception:
            return []

    def update(self, conversation_id: str, **updates: dict) -> Optional[dict]:
        """Update conversation metadata fields."""

        metadata = self.get(conversation_id)
        if not metadata:
            return None

        # Update fields
        metadata.update(updates)
        metadata["updated_at"] = datetime.utcnow().isoformat()

        # Update in ChromaDB by deleting and re-adding
        try:
            self._store.delete(ids=[conversation_id])
            document = Document(
                page_content=metadata.get("title", conversation_id),
                metadata=metadata,
            )
            self._store.add_documents([document], ids=[conversation_id])
            return metadata
        except Exception:
            return None

    def delete(self, conversation_id: str) -> bool:
        """Delete conversation metadata."""

        try:
            self._store.delete(ids=[conversation_id])
            return True
        except Exception:
            return False

    def increment_message_count(self, conversation_id: str) -> None:
        """Increment the message count for a conversation."""

        metadata = self.get(conversation_id)
        if metadata:
            current_count = metadata.get("message_count", 0)
            self.update(conversation_id, message_count=current_count + 1)

    def search(self, query: str, user_id: Optional[str] = None, limit: int = 10) -> List[dict]:
        """Search conversations by title or content."""

        try:
            where_filter = {}
            if user_id:
                where_filter["user_id"] = user_id

            # Use similarity search on conversation titles
            results = self._store.similarity_search(
                query=query,
                k=limit,
                filter=where_filter if where_filter else None,
            )

            # Extract metadata from results
            metadatas = [doc.metadata for doc in results]
            return metadatas
        except Exception:
            return []

