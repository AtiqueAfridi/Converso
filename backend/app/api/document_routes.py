"""HTTP route definitions for document upload and management API."""

from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.dependencies import get_document_service
from app.models.document_models import (
    DocumentListResponse,
    DocumentRetrievalRequest,
    DocumentRetrievalResponse,
    DocumentUploadResponse,
)
from app.services.document_service import DocumentService

router = APIRouter()


@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
)
async def upload_document(
    file: UploadFile = File(..., description="Document file (PDF, DOC, DOCX, or CSV)"),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    """Upload and process a document file."""

    # Read file content
    try:
        file_content = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(exc)}",
        ) from exc

    try:
        return document_service.upload_document(file_content, file.filename or "unknown")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(exc)}",
        ) from exc


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List all uploaded documents",
)
async def list_documents(
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    """Retrieve a list of all uploaded documents."""

    try:
        documents = document_service.list_documents()
        return DocumentListResponse(documents=documents, total=len(documents))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(exc)}",
        ) from exc


@router.post(
    "/documents/retrieve",
    response_model=DocumentRetrievalResponse,
    summary="Retrieve relevant document chunks",
)
async def retrieve_documents(
    request: DocumentRetrievalRequest,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentRetrievalResponse:
    """Retrieve relevant document chunks based on a query."""

    try:
        return document_service.retrieve_documents(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval failed: {str(exc)}",
        ) from exc


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service),
) -> None:
    """Delete a document and all its chunks."""

    success = document_service.delete_document(document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

