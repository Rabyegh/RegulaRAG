"""
Application-level exception hierarchy.

Defines a structured set of exceptions for the RegulaRAG platform, enabling
consistent error handling across all modules.
"""

from __future__ import annotations

from http import HTTPStatus


class RegulaRAGError(Exception):
    """Base exception for all RegulaRAG application errors.

    All custom exceptions in this project must inherit from this class so
    that callers can catch application-level errors with a single handler.
    """

    message: str = "An unexpected error occurred."
    http_status: int = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message: str | None = None, **context: object) -> None:
        self.message = message or self.__class__.message
        self.context = context
        super().__init__(self.message)

    def __repr__(self) -> str:
        ctx = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
        return f"{self.__class__.__name__}(message={self.message!r}, {ctx})"


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------


class ConfigurationError(RegulaRAGError):
    """Raised when required configuration is missing or invalid."""

    message = "Application configuration error."
    http_status = HTTPStatus.INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# Ingestion errors (future Phase 2)
# ---------------------------------------------------------------------------


class IngestionError(RegulaRAGError):
    """Raised when document ingestion fails."""

    message = "Document ingestion failed."
    http_status = HTTPStatus.UNPROCESSABLE_ENTITY


class DocumentNotFoundError(RegulaRAGError):
    """Raised when a requested document cannot be located."""

    message = "Document not found."
    http_status = HTTPStatus.NOT_FOUND


# ---------------------------------------------------------------------------
# Retrieval errors (future Phase 4)
# ---------------------------------------------------------------------------


class RetrievalError(RegulaRAGError):
    """Raised when the retrieval pipeline encounters an unrecoverable error."""

    message = "Retrieval operation failed."
    http_status = HTTPStatus.INTERNAL_SERVER_ERROR


class EmbeddingError(RetrievalError):
    """Raised when embedding generation fails."""

    message = "Failed to generate embeddings."


# ---------------------------------------------------------------------------
# RAG errors (future Phase 4)
# ---------------------------------------------------------------------------


class RAGError(RegulaRAGError):
    """Raised when the RAG pipeline fails."""

    message = "RAG pipeline error."
    http_status = HTTPStatus.INTERNAL_SERVER_ERROR


class LLMError(RAGError):
    """Raised when the language model call fails."""

    message = "Language model call failed."


class ContextLengthError(LLMError):
    """Raised when the context exceeds the model's token limit."""

    message = "Input context exceeds the model's token limit."
    http_status = HTTPStatus.UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# Knowledge Graph errors (future Phase 5)
# ---------------------------------------------------------------------------


class GraphError(RegulaRAGError):
    """Raised when a Knowledge Graph operation fails."""

    message = "Knowledge Graph operation failed."
    http_status = HTTPStatus.INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# Validation / API errors
# ---------------------------------------------------------------------------


class ValidationError(RegulaRAGError):
    """Raised when request or data validation fails."""

    message = "Validation error."
    http_status = HTTPStatus.UNPROCESSABLE_ENTITY


class NotFoundError(RegulaRAGError):
    """Raised when a requested resource does not exist."""

    message = "Resource not found."
    http_status = HTTPStatus.NOT_FOUND


class AuthenticationError(RegulaRAGError):
    """Raised when authentication fails."""

    message = "Authentication required."
    http_status = HTTPStatus.UNAUTHORIZED


class AuthorizationError(RegulaRAGError):
    """Raised when a user lacks permission for an action."""

    message = "Permission denied."
    http_status = HTTPStatus.FORBIDDEN
