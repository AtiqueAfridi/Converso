"""Vector store management utilities for conversation memory."""

from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import uuid4

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from app.core.config import Settings


class VectorStoreManager:
    """Encapsulates vector store setup and CRUD operations."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
        self._store = Chroma(
            collection_name="chat_memory",
            embedding_function=self._embeddings,
            persist_directory=str(settings.chroma_persist_directory),
        )

    def add_message(self, conversation_id: str, role: str, content: str) -> None:
        """Persist a single conversation turn in the vector store."""

        document = Document(
            page_content=content,
            metadata={
                "conversation_id": conversation_id,
                "role": role,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        self._store.add_documents([document], ids=[str(uuid4())])
        # Note: Chroma 0.4.x+ automatically persists, persist() is deprecated
        # Keeping for compatibility but it's a no-op in newer versions

    def get_relevant_messages(self, conversation_id: str, query: str, k: int = 4) -> List[Document]:
        """Retrieve the most relevant conversation snippets for the current query."""

        try:
            return self._store.similarity_search(
                query=query,
                k=k,
                filter={"conversation_id": conversation_id},
            )
        except Exception:
            # If no messages exist or search fails, return empty list
            return []

    def get_recent_messages(self, conversation_id: str, limit: int) -> List[Document]:
        """Return the most recent messages from the conversation sorted by time."""

        try:
            results = self._store.get(
                where={"conversation_id": conversation_id},
                include=["metadatas", "documents"],
            )
            metadatas = results.get("metadatas", [])
            documents = results.get("documents", [])
            merged = []
            for metadata, content in zip(metadatas, documents):
                merged.append(
                    Document(
                        page_content=content,
                        metadata=metadata,
                    )
                )
            merged.sort(key=lambda doc: doc.metadata.get("timestamp", ""))
            return merged[-limit:] if limit else merged
        except Exception:
            # If no messages exist or retrieval fails, return empty list
            return []
