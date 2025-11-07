"""Pydantic models for document upload and management."""

from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Response after successful document upload."""

    document_id: str = Field(..., description="Unique identifier for the uploaded document.")
    filename: str = Field(..., description="Original filename.")
    chunks_created: int = Field(..., description="Number of text chunks created from the document.")
    message: str = Field(..., description="Success message.")


class DocumentListResponse(BaseModel):
    """Response for listing documents."""

    documents: List[dict] = Field(..., description="List of uploaded documents.")
    total: int = Field(..., description="Total number of documents.", ge=0)


class DocumentRetrievalRequest(BaseModel):
    """Request for document retrieval."""

    query: str = Field(..., description="Search query.", min_length=1)
    retrieval_method: Optional[str] = Field(
        default=None,
        description="Retrieval method: 'similarity', 'hybrid', or 'rerank'. Auto-selected if not provided.",
    )
    k: int = Field(default=5, description="Number of chunks to retrieve.", ge=1, le=20)
    document_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional list of document IDs to search within.",
    )


class DocumentRetrievalResponse(BaseModel):
    """Response containing retrieved document chunks."""

    chunks: List[dict] = Field(..., description="Retrieved document chunks.")
    retrieval_method: str = Field(..., description="Method used for retrieval.")
    total_chunks: int = Field(..., description="Total number of chunks retrieved.", ge=0)

