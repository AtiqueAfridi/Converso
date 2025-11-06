"""Pydantic models for conversation management."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation."""

    title: Optional[str] = Field(
        default=None,
        description="Optional title for the conversation. Auto-generated if not provided.",
    )


class ConversationUpdate(BaseModel):
    """Schema for updating conversation metadata."""

    title: str = Field(..., description="New title for the conversation.", min_length=1, max_length=200)


class ConversationSummary(BaseModel):
    """Schema for conversation summary in list views."""

    conversation_id: str = Field(..., description="Unique identifier for the conversation.")
    title: str = Field(..., description="Conversation title.")
    created_at: datetime = Field(..., description="When the conversation was created.")
    updated_at: datetime = Field(..., description="When the conversation was last updated.")
    message_count: int = Field(..., description="Number of messages in the conversation.", ge=0)
    preview: Optional[str] = Field(
        default=None,
        description="Preview of the last message in the conversation.",
    )


class ConversationListResponse(BaseModel):
    """Schema for listing conversations."""

    conversations: List[ConversationSummary] = Field(..., description="List of conversations.")
    total: int = Field(..., description="Total number of conversations.", ge=0)


class ConversationDetail(BaseModel):
    """Schema for detailed conversation information."""

    conversation_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    is_archived: bool = False


class ConversationExportRequest(BaseModel):
    """Schema for export request parameters."""

    format: Literal["pdf", "txt", "json"] = Field(..., description="Export format.")


class ConversationSearchRequest(BaseModel):
    """Schema for conversation search request."""

    query: str = Field(..., description="Search query string.", min_length=1)
    limit: Optional[int] = Field(default=10, description="Maximum number of results.", ge=1, le=100)


class ConversationSearchResponse(BaseModel):
    """Schema for conversation search results."""

    conversations: List[ConversationSummary] = Field(..., description="Matching conversations.")
    total: int = Field(..., description="Total number of matches.", ge=0)


class ShareConversationRequest(BaseModel):
    """Schema for creating a share link."""

    expires_in_days: Optional[int] = Field(
        default=7,
        description="Number of days until the share link expires.",
        ge=1,
        le=365,
    )


class ShareConversationResponse(BaseModel):
    """Schema for share link response."""

    share_token: str = Field(..., description="Unique token for the shared conversation.")
    share_url: str = Field(..., description="Full URL to access the shared conversation.")
    expires_at: Optional[datetime] = Field(
        default=None,
        description="When the share link expires.",
    )


class SharedConversationResponse(BaseModel):
    """Schema for accessing a shared conversation."""

    conversation_id: str
    title: str
    messages: List[dict] = Field(..., description="List of messages in the conversation.")
    shared_at: datetime

