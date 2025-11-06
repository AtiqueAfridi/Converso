"""Service layer for conversation management operations."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from uuid import uuid4

from app.core.config import Settings
from app.models.conversation_models import (
    ConversationCreate,
    ConversationDetail,
    ConversationExportRequest,
    ConversationSearchRequest,
    ConversationSearchResponse,
    ConversationSummary,
    ConversationUpdate,
    ShareConversationRequest,
    ShareConversationResponse,
)
from app.repositories.conversation_repository import ConversationRepository
from app.vectorstore.store_setup import VectorStoreManager


class ConversationService:
    """Business logic for conversation management."""

    def __init__(
        self,
        settings: Settings,
        repository: ConversationRepository,
        vector_manager: VectorStoreManager,
    ) -> None:
        """Initialize the conversation service."""

        self._settings = settings
        self._repository = repository
        self._vector_manager = vector_manager
        self._share_tokens: Dict[str, dict] = {}  # In-memory store for share tokens

    def create_conversation(self, request: ConversationCreate, user_id: Optional[str] = None) -> ConversationDetail:
        """Create a new conversation thread."""

        conversation_id = str(uuid4())
        metadata = self._repository.create(
            conversation_id=conversation_id,
            title=request.title,
            user_id=user_id,
        )

        return ConversationDetail(
            conversation_id=metadata["conversation_id"],
            title=metadata["title"],
            created_at=datetime.fromisoformat(metadata["created_at"]),
            updated_at=datetime.fromisoformat(metadata["updated_at"]),
            message_count=metadata["message_count"],
            is_archived=metadata.get("is_archived", False),
        )

    def list_conversations(
        self,
        user_id: Optional[str] = None,
        limit: Optional[int] = None,
        include_archived: bool = False,
    ) -> List[ConversationSummary]:
        """List all conversations for a user."""

        all_conversations = self._repository.get_all(user_id=user_id, limit=limit)
        summaries = []

        for metadata in all_conversations:
            if not include_archived and metadata.get("is_archived", False):
                continue

            # Get preview from last message
            preview = self._get_conversation_preview(metadata["conversation_id"])

            summaries.append(
                ConversationSummary(
                    conversation_id=metadata["conversation_id"],
                    title=metadata["title"],
                    created_at=datetime.fromisoformat(metadata["created_at"]),
                    updated_at=datetime.fromisoformat(metadata["updated_at"]),
                    message_count=metadata.get("message_count", 0),
                    preview=preview,
                )
            )

        return summaries

    def get_conversation(self, conversation_id: str) -> Optional[ConversationDetail]:
        """Get conversation details by ID."""

        metadata = self._repository.get(conversation_id)
        if not metadata:
            return None

        return ConversationDetail(
            conversation_id=metadata["conversation_id"],
            title=metadata["title"],
            created_at=datetime.fromisoformat(metadata["created_at"]),
            updated_at=datetime.fromisoformat(metadata["updated_at"]),
            message_count=metadata.get("message_count", 0),
            is_archived=metadata.get("is_archived", False),
        )

    def update_conversation(
        self,
        conversation_id: str,
        request: ConversationUpdate,
    ) -> Optional[ConversationDetail]:
        """Update conversation metadata (e.g., rename)."""

        metadata = self._repository.update(conversation_id, title=request.title)
        if not metadata:
            return None

        return ConversationDetail(
            conversation_id=metadata["conversation_id"],
            title=metadata["title"],
            created_at=datetime.fromisoformat(metadata["created_at"]),
            updated_at=datetime.fromisoformat(metadata["updated_at"]),
            message_count=metadata.get("message_count", 0),
            is_archived=metadata.get("is_archived", False),
        )

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""

        # Note: In a production system, you'd want to also delete messages from ChromaDB
        # For now, we'll just delete the metadata
        return self._repository.delete(conversation_id)

    def search_conversations(
        self,
        request: ConversationSearchRequest,
        user_id: Optional[str] = None,
    ) -> ConversationSearchResponse:
        """Search across conversations."""

        results = self._repository.search(query=request.query, user_id=user_id, limit=request.limit)
        summaries = []

        for metadata in results:
            preview = self._get_conversation_preview(metadata["conversation_id"])
            summaries.append(
                ConversationSummary(
                    conversation_id=metadata["conversation_id"],
                    title=metadata["title"],
                    created_at=datetime.fromisoformat(metadata["created_at"]),
                    updated_at=datetime.fromisoformat(metadata["updated_at"]),
                    message_count=metadata.get("message_count", 0),
                    preview=preview,
                )
            )

        return ConversationSearchResponse(conversations=summaries, total=len(summaries))

    def export_conversation(
        self,
        conversation_id: str,
        request: ConversationExportRequest,
    ) -> tuple[Union[str, bytes], str]:
        """Export conversation in the requested format. Returns (content, filename)."""

        messages = self._get_all_messages(conversation_id)
        metadata = self._repository.get(conversation_id)
        
        if not metadata:
            raise ValueError(f"Conversation {conversation_id} not found")

        if request.format == "json":
            return self._export_json(conversation_id, metadata, messages)
        elif request.format == "txt":
            return self._export_txt(conversation_id, metadata, messages)
        elif request.format == "pdf":
            return self._export_pdf(conversation_id, metadata, messages)
        else:
            raise ValueError(f"Unsupported export format: {request.format}")

    def create_share_link(
        self,
        conversation_id: str,
        request: ShareConversationRequest,
    ) -> ShareConversationResponse:
        """Generate a shareable link for a conversation."""

        # Verify conversation exists
        if not self._repository.get(conversation_id):
            raise ValueError(f"Conversation {conversation_id} not found")

        # Generate secure token
        share_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)

        # Store token mapping
        self._share_tokens[share_token] = {
            "conversation_id": conversation_id,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat(),
        }

        share_url = f"/api/shared/{share_token}"

        return ShareConversationResponse(
            share_token=share_token,
            share_url=share_url,
            expires_at=expires_at,
        )

    def get_shared_conversation(self, share_token: str) -> Optional[dict]:
        """Retrieve a conversation via share token."""

        token_data = self._share_tokens.get(share_token)
        if not token_data:
            return None

        # Check expiration
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        if datetime.utcnow() > expires_at:
            # Token expired, remove it
            del self._share_tokens[share_token]
            return None

        conversation_id = token_data["conversation_id"]
        metadata = self._repository.get(conversation_id)
        if not metadata:
            return None

        messages = self._get_all_messages(conversation_id)

        return {
            "conversation_id": conversation_id,
            "title": metadata["title"],
            "messages": messages,
            "shared_at": datetime.fromisoformat(token_data["created_at"]),
        }

    def _get_conversation_preview(self, conversation_id: str, max_length: int = 100) -> Optional[str]:
        """Get a preview of the last message in a conversation."""

        messages = self._get_all_messages(conversation_id, limit=1)
        if messages:
            last_message = messages[-1]
            content = last_message.get("content", "")
            if len(content) > max_length:
                return content[:max_length] + "..."
            return content
        return None

    def _get_all_messages(self, conversation_id: str, limit: Optional[int] = None) -> List[dict]:
        """Retrieve all messages for a conversation."""

        try:
            # Access the ChromaDB store through vector_manager
            store = self._vector_manager._store
            results = store.get(
                where={"conversation_id": conversation_id},
                include=["metadatas", "documents"],
            )
            metadatas = results.get("metadatas", [])
            documents = results.get("documents", [])

            messages = []
            for metadata, content in zip(metadatas, documents):
                messages.append(
                    {
                        "role": metadata.get("role", "unknown"),
                        "content": content,
                        "timestamp": metadata.get("timestamp", ""),
                    }
                )

            # Sort by timestamp
            messages.sort(key=lambda m: m.get("timestamp", ""))

            if limit:
                messages = messages[-limit:]

            return messages
        except Exception:
            return []

    def _export_json(self, conversation_id: str, metadata: dict, messages: List[dict]) -> tuple[str, str]:
        """Export conversation as JSON."""

        export_data = {
            "conversation_id": conversation_id,
            "title": metadata.get("title", ""),
            "created_at": metadata.get("created_at", ""),
            "updated_at": metadata.get("updated_at", ""),
            "message_count": len(messages),
            "messages": messages,
        }

        content = json.dumps(export_data, indent=2, ensure_ascii=False)
        filename = f"conversation_{conversation_id[:8]}.json"
        return content, filename

    def _export_txt(self, conversation_id: str, metadata: dict, messages: List[dict]) -> tuple[str, str]:
        """Export conversation as plain text."""

        lines = [
            f"Conversation: {metadata.get('title', 'Untitled')}",
            f"ID: {conversation_id}",
            f"Created: {metadata.get('created_at', '')}",
            f"Updated: {metadata.get('updated_at', '')}",
            f"Messages: {len(messages)}",
            "",
            "=" * 80,
            "",
        ]

        for msg in messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            lines.append(f"[{role}] ({timestamp})")
            lines.append(content)
            lines.append("")

        content = "\n".join(lines)
        filename = f"conversation_{conversation_id[:8]}.txt"
        return content, filename

    def _export_pdf(self, conversation_id: str, metadata: dict, messages: List[dict]) -> tuple[bytes, str]:
        """Export conversation as PDF. Returns (binary_content, filename)."""

        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

            # Create PDF in memory
            import io

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            # Title
            title = Paragraph(f"<b>{metadata.get('title', 'Untitled Conversation')}</b>", styles["Title"])
            story.append(title)
            story.append(Spacer(1, 0.2 * inch))

            # Metadata
            meta_text = f"ID: {conversation_id}<br/>"
            meta_text += f"Created: {metadata.get('created_at', '')}<br/>"
            meta_text += f"Updated: {metadata.get('updated_at', '')}<br/>"
            meta_text += f"Messages: {len(messages)}"
            story.append(Paragraph(meta_text, styles["Normal"]))
            story.append(Spacer(1, 0.3 * inch))

            # Messages
            for msg in messages:
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "").replace("\n", "<br/>")
                timestamp = msg.get("timestamp", "")

                msg_text = f"<b>[{role}]</b> ({timestamp})<br/>{content}"
                story.append(Paragraph(msg_text, styles["Normal"]))
                story.append(Spacer(1, 0.2 * inch))

            doc.build(story)
            buffer.seek(0)
            content = buffer.getvalue()
            filename = f"conversation_{conversation_id[:8]}.pdf"
            return content, filename
        except ImportError:
            # Fallback to TXT if reportlab not available
            txt_content, txt_filename = self._export_txt(conversation_id, metadata, messages)
            return txt_content.encode("utf-8"), txt_filename.replace(".txt", ".pdf")

