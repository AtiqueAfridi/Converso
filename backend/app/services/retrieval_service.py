"""Advanced retrieval service with multiple retrieval strategies."""

from __future__ import annotations

from typing import List

from langchain_core.documents import Document

from app.services.document_store import DocumentStore


class RetrievalService:
    """Service for intelligent document retrieval using multiple strategies."""

    def __init__(self, document_store: DocumentStore) -> None:
        """Initialize the retrieval service."""

        self._document_store = document_store

    def retrieve(
        self,
        query: str,
        retrieval_method: str | None = None,
        k: int = 5,
        document_ids: List[str] | None = None,
    ) -> List[Document]:
        """Retrieve relevant document chunks using the specified method."""

        # Auto-select retrieval method based on query complexity
        if not retrieval_method:
            retrieval_method = self._select_retrieval_method(query)

        if retrieval_method == "similarity":
            return self._similarity_search(query, k, document_ids)
        elif retrieval_method == "hybrid":
            return self._hybrid_search(query, k, document_ids)
        elif retrieval_method == "rerank":
            return self._reranked_search(query, k, document_ids)
        else:
            # Default to similarity search
            return self._similarity_search(query, k, document_ids)

    def _select_retrieval_method(self, query: str) -> str:
        """Automatically select the best retrieval method based on query characteristics."""

        query_lower = query.lower()
        query_length = len(query.split())

        # Simple, short queries -> similarity search
        if query_length <= 5:
            return "similarity"

        # Complex queries with multiple concepts -> hybrid or rerank
        # Check for question words, conjunctions, or complex structure
        complex_indicators = ["how", "why", "what", "explain", "compare", "difference", "and", "or", "but"]
        has_complex_indicators = any(indicator in query_lower for indicator in complex_indicators)

        if has_complex_indicators or query_length > 10:
            return "rerank"  # Use reranking for complex queries
        else:
            return "hybrid"  # Use hybrid for medium complexity

    def _similarity_search(
        self,
        query: str,
        k: int,
        document_ids: List[str] | None = None,
    ) -> List[Document]:
        """Standard similarity search using embeddings."""

        filter_metadata = None
        if document_ids:
            # Note: ChromaDB doesn't support OR filters easily, so we'll search all and filter
            results = self._document_store.search_similar(query, k=k * 2)
            # Filter by document_ids
            filtered = [doc for doc in results if doc.metadata.get("document_id") in document_ids]
            return filtered[:k]
        else:
            return self._document_store.search_similar(query, k=k)

    def _hybrid_search(
        self,
        query: str,
        k: int,
        document_ids: List[str] | None = None,
    ) -> List[Document]:
        """Hybrid search combining similarity and keyword matching."""

        # Get more results from similarity search
        similarity_results = self._similarity_search(query, k=k * 2, document_ids=document_ids)

        # Simple keyword-based reranking
        query_keywords = set(query.lower().split())
        scored_results = []

        for doc in similarity_results:
            content_lower = doc.page_content.lower()
            # Count keyword matches
            keyword_matches = sum(1 for keyword in query_keywords if keyword in content_lower)
            score = keyword_matches / len(query_keywords) if query_keywords else 0
            scored_results.append((score, doc))

        # Sort by score and return top k
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored_results[:k]]

    def _reranked_search(
        self,
        query: str,
        k: int,
        document_ids: List[str] | None = None,
    ) -> List[Document]:
        """Reranked search with multiple scoring factors."""

        # Get initial candidates
        candidates = self._similarity_search(query, k=k * 3, document_ids=document_ids)

        if not candidates:
            return []

        # Rerank using multiple factors
        query_lower = query.lower()
        query_keywords = set(query_lower.split())
        query_length = len(query_keywords)

        scored_results = []

        for doc in candidates:
            content_lower = doc.page_content.lower()
            content_length = len(doc.page_content.split())

            # Factor 1: Keyword density
            keyword_matches = sum(1 for keyword in query_keywords if keyword in content_lower)
            keyword_score = keyword_matches / query_length if query_length > 0 else 0

            # Factor 2: Content length (prefer medium-length chunks)
            ideal_length = 200  # words
            length_score = 1.0 - abs(content_length - ideal_length) / ideal_length
            length_score = max(0, min(1, length_score))

            # Factor 3: Position in document (prefer earlier chunks for context)
            chunk_index = doc.metadata.get("chunk_index", 0)
            total_chunks = doc.metadata.get("total_chunks", 1)
            position_score = 1.0 - (chunk_index / max(total_chunks, 1))
            position_score = max(0.5, position_score)  # Don't penalize too much

            # Combined score (weighted)
            final_score = (
                keyword_score * 0.5 +  # Keyword matching is most important
                length_score * 0.2 +  # Content length
                position_score * 0.3,  # Position in document
            )

            scored_results.append((final_score, doc))

        # Sort by score and return top k
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored_results[:k]]

