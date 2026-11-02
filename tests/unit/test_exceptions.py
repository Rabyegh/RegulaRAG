"""
Unit tests for the application exception hierarchy.

Verifies that all custom exceptions carry correct HTTP status codes,
messages, and context information.
"""

from __future__ import annotations

from http import HTTPStatus

import pytest

from regularag.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    DocumentNotFoundError,
    EmbeddingError,
    GraphError,
    IngestionError,
    LLMError,
    NotFoundError,
    RAGError,
    RegulaRAGError,
    RetrievalError,
    ValidationError,
)


@pytest.mark.unit
class TestRegulaRAGError:
    """Tests for the base exception class."""

    def test_default_message(self) -> None:
        exc = RegulaRAGError()
        assert exc.message == "An unexpected error occurred."

    def test_custom_message(self) -> None:
        exc = RegulaRAGError("Custom error message")
        assert exc.message == "Custom error message"
        assert str(exc) == "Custom error message"

    def test_context_stored(self) -> None:
        exc = RegulaRAGError("Error", document_id="doc-123", phase="ingestion")
        assert exc.context["document_id"] == "doc-123"
        assert exc.context["phase"] == "ingestion"

    def test_default_http_status(self) -> None:
        exc = RegulaRAGError()
        assert exc.http_status == HTTPStatus.INTERNAL_SERVER_ERROR

    def test_repr_contains_class_name(self) -> None:
        exc = RegulaRAGError("Test")
        assert "RegulaRAGError" in repr(exc)

    def test_is_exception(self) -> None:
        exc = RegulaRAGError()
        assert isinstance(exc, Exception)


@pytest.mark.unit
class TestExceptionHierarchy:
    """Verify all exceptions inherit from RegulaRAGError."""

    @pytest.mark.parametrize(
        "exc_class",
        [
            ConfigurationError,
            IngestionError,
            DocumentNotFoundError,
            RetrievalError,
            EmbeddingError,
            RAGError,
            LLMError,
            GraphError,
            ValidationError,
            NotFoundError,
            AuthenticationError,
            AuthorizationError,
        ],
    )
    def test_inherits_from_base(self, exc_class: type[RegulaRAGError]) -> None:
        exc = exc_class()
        assert isinstance(exc, RegulaRAGError)


@pytest.mark.unit
class TestHttpStatusCodes:
    """Verify HTTP status codes match expected values."""

    def test_not_found_status(self) -> None:
        assert NotFoundError().http_status == HTTPStatus.NOT_FOUND

    def test_document_not_found_status(self) -> None:
        assert DocumentNotFoundError().http_status == HTTPStatus.NOT_FOUND

    def test_authentication_error_status(self) -> None:
        assert AuthenticationError().http_status == HTTPStatus.UNAUTHORIZED

    def test_authorization_error_status(self) -> None:
        assert AuthorizationError().http_status == HTTPStatus.FORBIDDEN

    def test_validation_error_status(self) -> None:
        assert ValidationError().http_status == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_ingestion_error_status(self) -> None:
        assert IngestionError().http_status == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_retrieval_error_status(self) -> None:
        assert RetrievalError().http_status == HTTPStatus.INTERNAL_SERVER_ERROR

    def test_rag_error_status(self) -> None:
        assert RAGError().http_status == HTTPStatus.INTERNAL_SERVER_ERROR

    def test_graph_error_status(self) -> None:
        assert GraphError().http_status == HTTPStatus.INTERNAL_SERVER_ERROR
