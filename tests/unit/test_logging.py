"""
Unit tests for application logging configuration.

Verifies that the logging setup completes without errors and that
the logger factory returns a usable logger.
"""

from __future__ import annotations

import logging

import pytest

from regularag.core.logging import configure_logging, get_logger


@pytest.mark.unit
class TestConfigureLogging:
    """Tests for the configure_logging function."""

    def test_configure_logging_console_format(self) -> None:
        """configure_logging should not raise for console format."""
        configure_logging(log_level="INFO", log_format="console")
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_configure_logging_json_format(self) -> None:
        """configure_logging should not raise for json format."""
        configure_logging(log_level="DEBUG", log_format="json")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_configure_logging_warning_level(self) -> None:
        configure_logging(log_level="WARNING", log_format="console")
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_configure_logging_adds_handler(self) -> None:
        configure_logging(log_level="INFO", log_format="console")
        root = logging.getLogger()
        assert len(root.handlers) >= 1


@pytest.mark.unit
class TestGetLogger:
    """Tests for the get_logger factory."""

    def test_get_logger_returns_bound_logger(self) -> None:
        logger = get_logger(__name__)
        assert logger is not None

    def test_get_logger_different_names(self) -> None:
        logger_a = get_logger("module.a")
        logger_b = get_logger("module.b")
        assert logger_a is not None
        assert logger_b is not None

    def test_logger_can_log_info(self) -> None:
        """Logger should not raise when logging an info message."""
        configure_logging(log_level="INFO", log_format="console")
        logger = get_logger(__name__)
        # Should not raise.
        logger.info("Test log message", key="value")

    def test_logger_can_log_warning(self) -> None:
        configure_logging(log_level="INFO", log_format="console")
        logger = get_logger(__name__)
        logger.warning("Test warning", context="test")
