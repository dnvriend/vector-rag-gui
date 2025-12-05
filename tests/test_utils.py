"""Tests for logging configuration module.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from vector_rag_gui.logging_config import get_logger, setup_logging


class TestLoggingConfig:
    """Tests for logging configuration."""

    def test_get_logger(self) -> None:
        """Test getting a logger instance."""
        logger = get_logger(__name__)
        assert logger is not None
        assert logger.name == __name__

    def test_setup_logging_default(self) -> None:
        """Test setup_logging with default verbosity."""
        # Should not raise
        setup_logging(0)

    def test_setup_logging_verbose(self) -> None:
        """Test setup_logging with verbose levels."""
        setup_logging(1)  # INFO
        setup_logging(2)  # DEBUG
        setup_logging(3)  # TRACE
