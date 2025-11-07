"""Service for storing and retrieving document chunks in ChromaDB."""

from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import uuid4

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from app.core.config import Settings


class DocumentStore:
    """Manages document storage and retrieval in ChromaDB."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the document store."""

        self._settings = settings
        self._embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
        self._store = Chroma(
            collection_name="document_chunks",
            embedding_function=self._embeddings,
            persist_directory=str(settings.chroma_persist_directory),
        )

    def store_document(
        self,
        filename: str,
        chunks: List[str],
        metadata: dict | None = None,
    ) -> str:
        """Store document chunks in the vector store."""

        document_id = str(uuid4())
        base_metadata = {
            "document_id": document_id,
            "filename": filename,
            "uploaded_at": datetime.utcnow().isoformat(),
            "chunk_count": len(chunks),
        }
        if metadata:
            base_metadata.update(metadata)

        documents = []
        ids = []

        for idx, chunk in enumerate(chunks):
            chunk_metadata = {
                **base_metadata,
                "chunk_index": idx,
                "total_chunks": len(chunks),
            }
            documents.append(Document(page_content=chunk, metadata=chunk_metadata))
            ids.append(f"{document_id}_chunk_{idx}")

        self._store.add_documents(documents, ids=ids)
        return document_id

    def search_similar(
        self,
        query: str,
        k: int = 5,
        filter_metadata: dict | None = None,
    ) -> List[Document]:
        """Perform similarity search on document chunks."""

        try:
            return self._store.similarity_search(
                query=query,
                k=k,
                filter=filter_metadata,
            )
        except Exception:
            return []

    def get_document_chunks(self, document_id: str) -> List[Document]:
        """Retrieve all chunks for a specific document."""

        try:
            results = self._store.get(
                where={"document_id": document_id},
                include=["metadatas", "documents"],
            )
            metadatas = results.get("metadatas", [])
            documents = results.get("documents", [])

            chunks = []
            for metadata, content in zip(metadatas, documents):
                chunks.append(Document(page_content=content, metadata=metadata))

            # Sort by chunk_index
            chunks.sort(key=lambda doc: doc.metadata.get("chunk_index", 0))
            return chunks
        except Exception:
            return []

    def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a document."""

        try:
            # Get all chunk IDs for this document
            results = self._store.get(
                where={"document_id": document_id},
                include=["metadatas"],
            )
            ids = results.get("ids", [])
            if ids:
                self._store.delete(ids=ids)
            return True
        except Exception:
            return False

    def list_documents(self) -> List[dict]:
        """List all stored documents with metadata."""

        try:
            # Get unique document IDs
            results = self._store.get(include=["metadatas"])
            metadatas = results.get("metadatas", [])

            # Group by document_id
            documents_map = {}
            for metadata in metadatas:
                doc_id = metadata.get("document_id")
                if doc_id and doc_id not in documents_map:
                    documents_map[doc_id] = {
                        "document_id": doc_id,
                        "filename": metadata.get("filename", "unknown"),
                        "uploaded_at": metadata.get("uploaded_at", ""),
                        "chunk_count": metadata.get("chunk_count", 0),
                    }

            return list(documents_map.values())
        except Exception:
            return []

