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
    validate_market_data,
    validate_signal,
    validate_trade_request,
    is_numeric,
    is_positive_number,
    is_valid_percentage,
    is_valid_confidence,
    sanitize_string,
    safe_float_conversion,
    safe_int_conversion,
    validate_email,
    validate_api_key,
    format_timestamp,
    parse_timestamp,
    clamp_value,
    calculate_win_rate,
    TradingBotError,
    APIError,
    ConfigurationError,
    TradingError,
)
from src.backend.models import (
    MarketData, Signal, TradeRequest, SignalType, TradeDirection
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


class TestDataValidation:
    """Test cases for data validation functions."""
    
    def test_validate_market_data_valid(self):
        """Test market data validation with valid data."""
        from datetime import datetime
        
        data = MarketData(
            symbol="EURUSD",
            timestamp=datetime.now(),
            open_price=1.1000,
            high_price=1.1050,
            low_price=1.0950,
            close_price=1.1025,
            volume=1000.0
        )
        
        result = validate_market_data(data)
        assert result.is_valid is True
        assert result.error_message is None
    
    def test_validate_market_data_invalid_symbol(self):
        """Test market data validation with invalid symbol."""
        from datetime import datetime
        
        data = MarketData(
            symbol="INVALID",
            timestamp=datetime.now(),
            open_price=1.1000,
            high_price=1.1050,
            low_price=1.0950,
            close_price=1.1025,
            volume=1000.0
        )
        
        result = validate_market_data(data)
        assert result.is_valid is False
        assert "Invalid currency pair format" in result.error_message
    
    def test_validate_signal_valid(self):
        """Test signal validation with valid signal."""
        from datetime import datetime
        
        signal = Signal(
            symbol="EURUSD",
            signal_type=SignalType.BUY,
            confidence=0.85,
            timestamp=datetime.now(),
            rsi_value=25.0,
            sma_value=1.1000,
            current_price=1.1025
        )
        
        result = validate_signal(signal)
        assert result.is_valid is True
    
    def test_validate_signal_low_confidence(self):
        """Test signal validation with low confidence."""
        from datetime import datetime
        
        signal = Signal(
            symbol="EURUSD",
            signal_type=SignalType.BUY,
            confidence=0.5,  # Low confidence
            timestamp=datetime.now(),
            rsi_value=25.0,
            sma_value=1.1000,
            current_price=1.1025
        )
        
        result = validate_signal(signal)
        assert result.is_valid is True
        assert "Low confidence signal detected" in result.warnings
    
    def test_validate_trade_request_valid(self):
        """Test trade request validation with valid request."""
        request = TradeRequest(
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=10.0,
            expiration_time=60,
            is_demo=True
        )
        
        result = validate_trade_request(request)
        assert result.is_valid is True
    
    def test_validate_trade_request_small_amount(self):
        """Test trade request validation with small amount."""
        request = TradeRequest(
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=0.5,  # Small amount
            expiration_time=60,
            is_demo=True
        )
        
        result = validate_trade_request(request)
        assert result.is_valid is True
        assert "Very small trade amount" in result.warnings


class TestTypeChecking:
    """Test cases for type checking functions."""
    
    def test_is_numeric(self):
        """Test numeric type checking."""
        assert is_numeric(10) is True
        assert is_numeric(10.5) is True
        assert is_numeric("10") is False
        assert is_numeric(True) is False  # Boolean is not considered numeric
        assert is_numeric(None) is False
    
    def test_is_positive_number(self):
        """Test positive number checking."""
        assert is_positive_number(10) is True
        assert is_positive_number(10.5) is True
        assert is_positive_number(0) is False
        assert is_positive_number(-10) is False
        assert is_positive_number("10") is False
    
    def test_is_valid_percentage(self):
        """Test percentage validation."""
        assert is_valid_percentage(50) is True
        assert is_valid_percentage(0) is True
        assert is_valid_percentage(100) is True
        assert is_valid_percentage(-10) is False
        assert is_valid_percentage(150) is False
        assert is_valid_percentage("50") is False
    
    def test_is_valid_confidence(self):
        """Test confidence score validation."""
        assert is_valid_confidence(0.5) is True
        assert is_valid_confidence(0) is True
        assert is_valid_confidence(1) is True
        assert is_valid_confidence(-0.1) is False
        assert is_valid_confidence(1.5) is False
        assert is_valid_confidence("0.5") is False


class TestStringUtilities:
    """Test cases for string utility functions."""
    
    def test_sanitize_string(self):
        """Test string sanitization."""
        assert sanitize_string("Hello World") == "Hello World"
        assert sanitize_string("Hello@#$%World") == "HelloWorld"
        assert sanitize_string("Test-String_123") == "Test-String_123"
        assert sanitize_string("A" * 200, max_length=50) == "A" * 50
        assert sanitize_string(123) == ""  # Non-string input
    
    def test_validate_email(self):
        """Test email validation."""
        assert validate_email("test@example.com") is True
        assert validate_email("user.name@domain.co.uk") is True
        assert validate_email("invalid-email") is False
        assert validate_email("@domain.com") is False
        assert validate_email("user@") is False
        assert validate_email(123) is False
    
    def test_validate_api_key(self):
        """Test API key validation."""
        assert validate_api_key("abcdef1234567890") is True
        assert validate_api_key("short") is False  # Too short
        assert validate_api_key("invalid-key!") is False  # Special characters
        assert validate_api_key(123) is False  # Not a string


class TestConversionUtilities:
    """Test cases for conversion utility functions."""
    
    def test_safe_float_conversion(self):
        """Test safe float conversion."""
        assert safe_float_conversion("10.5") == 10.5
        assert safe_float_conversion(10) == 10.0
        assert safe_float_conversion("invalid") == 0.0
        assert safe_float_conversion("invalid", default=5.0) == 5.0
        assert safe_float_conversion(None) == 0.0
    
    def test_safe_int_conversion(self):
        """Test safe integer conversion."""
        assert safe_int_conversion("10") == 10
        assert safe_int_conversion(10.5) == 10
        assert safe_int_conversion("invalid") == 0
        assert safe_int_conversion("invalid", default=5) == 5
        assert safe_int_conversion(None) == 0


class TestDateTimeUtilities:
    """Test cases for datetime utility functions."""
    
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        from datetime import datetime
        
        dt = datetime(2024, 1, 15, 10, 30, 45)
        assert format_timestamp(dt) == "2024-01-15 10:30:45"
        assert format_timestamp(dt, "%Y-%m-%d") == "2024-01-15"
        assert format_timestamp("invalid") == "Invalid timestamp"
    
    def test_parse_timestamp(self):
        """Test timestamp parsing."""
        result = parse_timestamp("2024-01-15 10:30:45")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        
        assert parse_timestamp("invalid") is None
        assert parse_timestamp("2024-01-15", "%Y-%m-%d %H:%M:%S") is None


class TestMathUtilities:
    """Test cases for math utility functions."""
    
    def test_clamp_value(self):
        """Test value clamping."""
        assert clamp_value(5, 0, 10) == 5
        assert clamp_value(-5, 0, 10) == 0
        assert clamp_value(15, 0, 10) == 10
        assert clamp_value(7.5, 5.0, 10.0) == 7.5
    
    def test_calculate_win_rate(self):
        """Test win rate calculation."""
        assert calculate_win_rate(7, 10) == 70.0
        assert calculate_win_rate(0, 10) == 0.0
        assert calculate_win_rate(10, 10) == 100.0
        assert calculate_win_rate(5, 0) == 0.0  # Zero division protection
