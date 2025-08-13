"""Tests for utility functions."""

import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.backend.utils import (
    setup_logging,
    validate_currency_pair,
    format_currency,
    calculate_percentage,
    TradingBotError,
    APIError,
    ConfigurationError,
    TradingError,
)


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_validate_currency_pair_valid(self):
        """Test currency pair validation with valid pairs."""
        valid_pairs = [
            "EURUSD",
            "GBPUSD",
            "USDJPY",
            "AUDUSD",
            "EURUSD-OTC",
            "GBPUSD-OTC",
        ]

        for pair in valid_pairs:
            assert validate_currency_pair(pair) is True

    def test_validate_currency_pair_invalid(self):
        """Test currency pair validation with invalid pairs."""
        invalid_pairs = ["", "EUR", "EURUSD123", "123456", "EUR-USD", None]

        for pair in invalid_pairs:
            assert validate_currency_pair(pair) is False

    def test_format_currency_default(self):
        """Test currency formatting with default currency."""
        result = format_currency(123.456)
        assert result == "USD 123.46"

    def test_format_currency_custom(self):
        """Test currency formatting with custom currency."""
        result = format_currency(99.99, "EUR")
        assert result == "EUR 99.99"

    def test_calculate_percentage_normal(self):
        """Test percentage calculation with normal values."""
        result = calculate_percentage(25, 100)
        assert result == 25.0

        result = calculate_percentage(1, 3)
        assert abs(result - 33.333333333333336) < 0.0001

    def test_calculate_percentage_zero_division(self):
        """Test percentage calculation with zero total."""
        result = calculate_percentage(10, 0)
        assert result == 0.0

    def test_setup_logging(self):
        """Test logging setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"

            # Mock the config manager to avoid environment variable requirements
            with patch("src.backend.utils.get_config_manager") as mock_config:
                mock_app_config = type(
                    "AppConfig",
                    (),
                    {"log_level": "INFO", "log_file": "trading_bot.log"},
                )()
                mock_config.return_value.get_app_config.return_value = mock_app_config

                logger = setup_logging("DEBUG", str(log_file))

                try:
                    assert logger.name == "trading_bot"
                    assert logger.level == logging.DEBUG
                    assert len(logger.handlers) == 2  # Console and file handlers
                    assert log_file.exists()
                finally:
                    # Clean up handlers to release file locks
                    for handler in logger.handlers[:]:
                        handler.close()
                        logger.removeHandler(handler)

    def test_custom_exceptions(self):
        """Test custom exception classes."""
        # Test base exception
        with pytest.raises(TradingBotError):
            raise TradingBotError("Base error")

        # Test API exception
        with pytest.raises(APIError):
            raise APIError("API error")

        # Test configuration exception
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Config error")

        # Test trading exception
        with pytest.raises(TradingError):
            raise TradingError("Trading error")

        # Test inheritance
        with pytest.raises(TradingBotError):
            raise APIError("API error inherits from TradingBotError")
