"""Business logic for orchestrating chat interactions."""

from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import RunnableSerializable
from langchain_openai import ChatOpenAI

from app.core.config import Settings
from app.models.request_response_models import ChatRequest, ChatResponse
from app.repositories.conversation_repository import ConversationRepository
from app.services.retrieval_service import RetrievalService
from app.vectorstore.store_setup import VectorStoreManager


class ReasoningResult(BaseModel):
    """Structured output schema expected from the LLM."""

    reasoning_steps: List[str] = Field(
        ..., description="Step-by-step reasoning leading to the answer."
    )
    answer: str = Field(..., description="The final assistant reply the user will see.")


class ChatService:
    """Primary entry point for chat interactions."""

    SYSTEM_PROMPT = (
        "You are GPT-5, an advanced assistant with strong reasoning skills. "
        "You must ground answers in the provided context snippets when relevant. "
        "When document chunks are provided, prioritize information from those documents. "
        "If the context is empty, rely on your own knowledge but acknowledge when information is missing. "
        "Respond concisely, clearly, and directly answer the user's intent. "
        "Highlight key points and avoid unnecessary verbosity."
    )

    def __init__(
        self,
        settings: Settings,
        vector_manager: VectorStoreManager,
        conversation_repository: Optional[ConversationRepository] = None,
        retrieval_service: Optional[RetrievalService] = None,
    ) -> None:
        self._settings = settings
        self._vector_manager = vector_manager
        self._conversation_repository = conversation_repository
        self._retrieval_service = retrieval_service
        self._parser = JsonOutputParser(pydantic_object=ReasoningResult)
        self._prompt: RunnableSerializable = self._build_prompt()
        self._llm = self._build_llm()
        self._chain = self._prompt | self._llm | self._parser

    def _build_llm(self) -> ChatOpenAI:
        """Initialise the LangChain ChatOpenAI client."""

        if not self._settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set in environment or .env file")

        kwargs = {
            "api_key": self._settings.openai_api_key,
            "model": self._settings.llm_model,
            "temperature": self._settings.llm_temperature,
            "max_retries": 2,
        }
        if self._settings.openai_base_url:
            kwargs["base_url"] = self._settings.openai_base_url

        # Note: Reasoning model_kwargs is only supported by certain models (e.g., o1, o3)
        # For GPT-4o and other standard models, omit this parameter
        if "o1" in self._settings.llm_model.lower() or "o3" in self._settings.llm_model.lower():
            kwargs["model_kwargs"] = {"reasoning": {"effort": "medium"}}

        return ChatOpenAI(**kwargs)

    def _build_prompt(self) -> RunnableSerializable:
        """Construct the reusable chat prompt template."""

        template = ChatPromptTemplate.from_messages(
            [
                ("system", self.SYSTEM_PROMPT),
                (
                    "system",
                    "Conversation history:\n{conversation_history}\n\nRelevant context (from conversation and uploaded documents):\n{context_snippets}\n\nWhen document chunks are provided, prioritize them and cite the source document. Structure your response clearly with key points highlighted.",
                ),
                (
                    "human",
                    "{user_message}\n\nUse the above information and return JSON using the format instructions.\n{format_instructions}",
                ),
            ]
        )
        return template

    def _prepare_context(self, conversation_id: str, query: str) -> List[str]:
        """Fetch contextual snippets from conversation history and uploaded documents."""

        context_snippets = []

        # Get conversation history snippets
        relevant_docs = self._vector_manager.get_relevant_messages(conversation_id, query)
        for doc in relevant_docs:
            context_snippets.append(f"{doc.metadata.get('role', 'unknown')}: {doc.page_content}")

        # Get document chunks if retrieval service is available
        if self._retrieval_service:
            try:
                document_chunks = self._retrieval_service.retrieve(query=query, k=3)
                for chunk in document_chunks:
                    filename = chunk.metadata.get("filename", "document")
                    context_snippets.append(f"[Document: {filename}]: {chunk.page_content}")
            except Exception:
                # If document retrieval fails, continue without it
                pass

        return context_snippets

    def _prepare_history(self, conversation_id: str) -> List[str]:
        """Return ordered, recent conversation history for grounding context."""

        limit = self._settings.max_context_messages
        recent_docs = self._vector_manager.get_recent_messages(conversation_id, limit)
        return [
            f"{doc.metadata.get('role', 'unknown')}: {doc.page_content}"
            for doc in recent_docs
        ]

    def _invoke_chain(
        self,
        user_message: str,
        conversation_id: str,
        context_snippets: List[str],
        conversation_history: List[str],
    ) -> ReasoningResult:
        """Execute the LangChain pipeline and return the structured result."""

        formatted_history = "\n".join(conversation_history) or "(no prior messages)"
        formatted_context = "\n".join(context_snippets) or "(no retrieved context)"
        result_dict = self._chain.invoke(
            {
                "user_message": user_message,
                "conversation_history": formatted_history,
                "context_snippets": formatted_context,
                "format_instructions": self._parser.get_format_instructions(),
            }
        )
        # JsonOutputParser returns a dict, convert to ReasoningResult
        if isinstance(result_dict, dict):
            # Handle case where LLM might not return expected structure
            if "answer" not in result_dict:
                # Fallback: use the entire response as answer if structure is wrong
                answer = result_dict.get("response") or str(result_dict)
                reasoning_steps = result_dict.get("reasoning_steps", [])
                if not isinstance(reasoning_steps, list):
                    reasoning_steps = []
                return ReasoningResult(answer=answer, reasoning_steps=reasoning_steps)
            return ReasoningResult(**result_dict)
        # If it's already a ReasoningResult, return as-is
        return result_dict

    def _store_turn(self, conversation_id: str, user_message: str, response: ReasoningResult) -> None:
        """Persist the round-trip conversation in the vector store."""

        self._vector_manager.add_message(conversation_id, "user", user_message)
        self._vector_manager.add_message(conversation_id, "assistant", response.answer)

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Process a chat request and return the assistant's response."""

        conversation_id = request.conversation_id or str(uuid4())
        
        # Ensure conversation metadata exists
        if self._conversation_repository:
            existing = self._conversation_repository.get(conversation_id)
            if not existing:
                # Auto-create conversation metadata if it doesn't exist
                first_message_preview = request.message[:50] + "..." if len(request.message) > 50 else request.message
                self._conversation_repository.create(
                    conversation_id=conversation_id,
                    title=f"Chat: {first_message_preview}",
                )
        
        context_snippets = self._prepare_context(conversation_id, request.message)
        history_snippets = self._prepare_history(conversation_id)
        reasoning_result = self._invoke_chain(
            user_message=request.message,
            conversation_id=conversation_id,
            context_snippets=context_snippets,
            conversation_history=history_snippets,
        )
        self._store_turn(conversation_id, request.message, reasoning_result)
        
        # Increment message count
        if self._conversation_repository:
            self._conversation_repository.increment_message_count(conversation_id)

        return ChatResponse(
            conversation_id=conversation_id,
            response=reasoning_result.answer,
            reasoning_steps=reasoning_result.reasoning_steps,
            retrieved_context=context_snippets if context_snippets else None,
        )
