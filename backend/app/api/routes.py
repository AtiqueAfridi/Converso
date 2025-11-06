"""HTTP route definitions for the chatbot API."""

from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAIError

from app.dependencies import get_chat_service
from app.models.request_response_models import ChatRequest, ChatResponse, HealthResponse
from app.services.chat_service import ChatService

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check() -> HealthResponse:
    """Return service health status."""

    return HealthResponse(status="ok", details="Service is operational")


@router.post("/chat", response_model=ChatResponse, summary="Send a chat message")
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """Process a chat message and return the assistant reply."""

    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty",
        )

    try:
        return chat_service.chat(request)
    except OpenAIError as exc:  # pragma: no cover - third-party exception path
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream LLM provider error: {exc}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - catch-all for unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(exc)}",
        ) from exc
