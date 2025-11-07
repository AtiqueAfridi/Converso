"""Service layer for document management operations."""

from __future__ import annotations

from typing import List

from app.core.config import Settings
from app.models.document_models import DocumentRetrievalRequest, DocumentRetrievalResponse, DocumentUploadResponse
from app.services.document_processor import DocumentProcessor
from app.services.document_store import DocumentStore
from app.services.retrieval_service import RetrievalService


class DocumentService:
    """Business logic for document upload and retrieval."""

    def __init__(
        self,
        settings: Settings,
        processor: DocumentProcessor,
        document_store: DocumentStore,
        retrieval_service: RetrievalService,
    ) -> None:
        """Initialize the document service."""

        self._settings = settings
        self._processor = processor
        self._document_store = document_store
        self._retrieval_service = retrieval_service

    def upload_document(self, file_content: bytes, filename: str) -> DocumentUploadResponse:
        """Process and store an uploaded document."""

        # Validate file
        is_valid, error_message = self._processor.validate_file(file_content, filename)
        if not is_valid:
            raise ValueError(error_message)

        # Extract text
        text_content = self._processor.extract_text(file_content, filename)

        if not text_content or not text_content.strip():
            raise ValueError("No text content could be extracted from the file")

        # Chunk text
        chunks = self._processor.chunk_text(text_content)

        if not chunks:
            raise ValueError("Failed to create text chunks from document")

        # Store in vector database
        document_id = self._document_store.store_document(
            filename=filename,
            chunks=chunks,
            metadata={"file_size": len(file_content)},
        )

        return DocumentUploadResponse(
            document_id=document_id,
            filename=filename,
            chunks_created=len(chunks),
            message=f"Document '{filename}' uploaded and processed successfully",
        )

    def list_documents(self) -> List[dict]:
        """List all uploaded documents."""

        return self._document_store.list_documents()

    def retrieve_documents(self, request: DocumentRetrievalRequest) -> DocumentRetrievalResponse:
        """Retrieve relevant document chunks based on query."""

        chunks = self._retrieval_service.retrieve(
            query=request.query,
            retrieval_method=request.retrieval_method,
            k=request.k,
            document_ids=request.document_ids,
        )

        # Format chunks for response
        formatted_chunks = []
        for chunk in chunks:
            formatted_chunks.append(
                {
                    "content": chunk.page_content,
                    "metadata": {
                        "document_id": chunk.metadata.get("document_id"),
                        "filename": chunk.metadata.get("filename"),
                        "chunk_index": chunk.metadata.get("chunk_index"),
                        "total_chunks": chunk.metadata.get("total_chunks"),
                    },
                }
            )

        # Determine which method was used
        method_used = request.retrieval_method or self._retrieval_service._select_retrieval_method(request.query)

        return DocumentRetrievalResponse(
            chunks=formatted_chunks,
            retrieval_method=method_used,
            total_chunks=len(formatted_chunks),
        )

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its chunks."""

        return self._document_store.delete_document(document_id)

