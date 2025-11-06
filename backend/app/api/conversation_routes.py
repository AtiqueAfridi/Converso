"""HTTP route definitions for conversation management API."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse

from app.dependencies import get_conversation_service
from app.models.conversation_models import (
    ConversationCreate,
    ConversationDetail,
    ConversationExportRequest,
    ConversationListResponse,
    ConversationSearchRequest,
    ConversationSearchResponse,
    ConversationSummary,
    ConversationUpdate,
    ShareConversationRequest,
    ShareConversationResponse,
    SharedConversationResponse,
)
from app.services.conversation_service import ConversationService

router = APIRouter()


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List all conversations",
)
async def list_conversations(
    limit: Optional[int] = Query(default=None, ge=1, le=100, description="Maximum number of conversations to return"),
    include_archived: bool = Query(default=False, description="Include archived conversations"),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationListResponse:
    """Retrieve a list of all conversations."""

    try:
        conversations = conversation_service.list_conversations(
            user_id=None,  # TODO: Add user authentication
            limit=limit,
            include_archived=include_archived,
        )
        return ConversationListResponse(conversations=conversations, total=len(conversations))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list conversations: {str(exc)}",
        ) from exc


@router.post(
    "/conversations",
    response_model=ConversationDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
)
async def create_conversation(
    request: ConversationCreate,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationDetail:
    """Create a new conversation thread."""

    try:
        return conversation_service.create_conversation(request, user_id=None)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(exc)}",
        ) from exc


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    summary="Get conversation details",
)
async def get_conversation(
    conversation_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationDetail:
    """Retrieve details for a specific conversation."""

    conversation = conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )
    return conversation


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    summary="Update conversation (rename)",
)
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdate,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationDetail:
    """Update conversation metadata, primarily for renaming."""

    conversation = conversation_service.update_conversation(conversation_id, request)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )
    return conversation


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
)
async def delete_conversation(
    conversation_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> None:
    """Delete a conversation and all its messages."""

    success = conversation_service.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )


@router.get(
    "/conversations/{conversation_id}/export",
    summary="Export conversation history",
)
async def export_conversation(
    conversation_id: str,
    format: str = Query(..., description="Export format: pdf, txt, or json", regex="^(pdf|txt|json)$"),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> Response:
    """Export conversation history in the specified format."""

    # Verify conversation exists
    conversation = conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    try:
        export_request = ConversationExportRequest(format=format)  # type: ignore
        content, filename = conversation_service.export_conversation(conversation_id, export_request)

        # Determine content type
        content_types = {
            "pdf": "application/pdf",
            "txt": "text/plain",
            "json": "application/json",
        }

        if format == "pdf":
            # PDF is binary
            return Response(
                content=content if isinstance(content, bytes) else content.encode("utf-8"),
                media_type=content_types[format],
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        else:
            # Text formats
            text_content = content if isinstance(content, str) else content.decode("utf-8")
            return Response(
                content=text_content,
                media_type=content_types[format],
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export conversation: {str(exc)}",
        ) from exc


@router.get(
    "/conversations/search",
    response_model=ConversationSearchResponse,
    summary="Search conversations",
)
async def search_conversations(
    query: str = Query(..., description="Search query string", min_length=1),
    limit: Optional[int] = Query(default=10, ge=1, le=100, description="Maximum number of results"),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationSearchResponse:
    """Search across all conversations by title or content."""

    try:
        search_request = ConversationSearchRequest(query=query, limit=limit)
        return conversation_service.search_conversations(search_request, user_id=None)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(exc)}",
        ) from exc


@router.post(
    "/conversations/{conversation_id}/share",
    response_model=ShareConversationResponse,
    summary="Generate share link",
)
async def share_conversation(
    conversation_id: str,
    request: ShareConversationRequest,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ShareConversationResponse:
    """Generate a shareable link for a conversation."""

    try:
        return conversation_service.create_share_link(conversation_id, request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create share link: {str(exc)}",
        ) from exc


@router.get(
    "/shared/{share_token}",
    response_model=SharedConversationResponse,
    summary="Access shared conversation",
)
async def get_shared_conversation(
    share_token: str,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> SharedConversationResponse:
    """Access a conversation via share token (read-only)."""

    shared_data = conversation_service.get_shared_conversation(share_token)
    if not shared_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found or expired",
        )

    return SharedConversationResponse(
        conversation_id=shared_data["conversation_id"],
        title=shared_data["title"],
        messages=shared_data["messages"],
        shared_at=shared_data["shared_at"],
    )

