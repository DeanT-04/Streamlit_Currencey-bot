"""Utility functions for Pocket Option Trading Bot."""

import logging
import sys
from typing import Optional, Any, Union, List
from pathlib import Path
from datetime import datetime
import re

from .config import get_config_manager
from .models import MarketData, Signal, TradeRequest, ValidationResult


def setup_logging(
    log_level: Optional[str] = None, log_file: Optional[str] = None
) -> logging.Logger:
    """Set up logging configuration for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file

    Returns:
        Configured logger instance
    """
    app_config = get_config_manager().get_app_config()

    level = log_level or app_config.log_level
    file_path = log_file or app_config.log_file

    # Create logs directory if it doesn't exist
    log_path = Path(file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure logging format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Create logger
    logger = logging.getLogger("trading_bot")
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(file_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def validate_currency_pair(pair: str) -> bool:
    """Validate currency pair format.

    Args:
        pair: Currency pair string (e.g., 'EURUSD', 'GBPUSD-OTC')

    Returns:
        True if valid format, False otherwise
    """
    if not pair or len(pair) < 6:
        return False

    # Basic validation for currency pair format
    base_pair = pair.split("-")[0]  # Remove OTC suffix if present

    if len(base_pair) != 6:
        return False

    # Check if it contains only letters
    return base_pair.isalpha()


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount for display.

    Args:
        amount: Amount to format
        currency: Currency symbol

    Returns:
        Formatted currency string
    """
    return f"{currency} {amount:.2f}"


def calculate_percentage(value: float, total: float) -> float:
    """Calculate percentage with zero division protection.

    Args:
        value: Numerator value
        total: Denominator value

    Returns:
        Percentage as float (0-100)
    """
    if total == 0:
        return 0.0
    return (value / total) * 100


class TradingBotError(Exception):
    """Base exception for trading bot errors."""

    pass


class APIError(TradingBotError):
    """Exception for API-related errors."""

    pass


class ConfigurationError(TradingBotError):
    """Exception for configuration-related errors."""

    pass


class TradingError(TradingBotError):
    """Exception for trading-related errors."""

    pass


def validate_market_data(data: MarketData) -> ValidationResult:
    """Validate market data structure and values.
    
    Args:
        data: MarketData object to validate
        
    Returns:
        ValidationResult with validation status and any errors
    """
    warnings = []
    
    try:
        # Basic validation is handled by MarketData.__post_init__
        # Additional business logic validation
        
        if not validate_currency_pair(data.symbol):
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid currency pair format: {data.symbol}"
            )
        
        # Check for reasonable price ranges (basic sanity check)
        price_range = data.high_price - data.low_price
        avg_price = (data.high_price + data.low_price) / 2
        
        if price_range / avg_price > 0.1:  # More than 10% range
            warnings.append("Unusually large price range detected")
        
        # Check timestamp is not too far in future
        if data.timestamp > datetime.now():
            time_diff = (data.timestamp - datetime.now()).total_seconds()
            if time_diff > 300:  # More than 5 minutes in future
                warnings.append("Timestamp is significantly in the future")
        
        return ValidationResult(is_valid=True, warnings=warnings)
        
    except ValueError as e:
        return ValidationResult(is_valid=False, error_message=str(e))


def validate_signal(signal: Signal) -> ValidationResult:
    """Validate trading signal structure and values.
    
    Args:
        signal: Signal object to validate
        
    Returns:
        ValidationResult with validation status and any errors
    """
    warnings = []
    
    try:
        # Basic validation is handled by Signal.__post_init__
        # Additional business logic validation
        
        if not validate_currency_pair(signal.symbol):
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid currency pair format: {signal.symbol}"
            )
        
        # Check signal strength
        if signal.confidence < 0.6:
            warnings.append("Low confidence signal detected")
        
        # Check RSI extreme values
        if signal.rsi_value < 10 or signal.rsi_value > 90:
            warnings.append("Extreme RSI value detected")
        
        # Check if current price is reasonable compared to SMA
        price_sma_diff = abs(signal.current_price - signal.sma_value) / signal.sma_value
        if price_sma_diff > 0.05:  # More than 5% difference
            warnings.append("Large deviation from SMA detected")
        
        return ValidationResult(is_valid=True, warnings=warnings)
        
    except ValueError as e:
        return ValidationResult(is_valid=False, error_message=str(e))


def validate_trade_request(request: TradeRequest) -> ValidationResult:
    """Validate trade request structure and values.
    
    Args:
        request: TradeRequest object to validate
        
    Returns:
        ValidationResult with validation status and any errors
    """
    warnings = []
    
    try:
        # Basic validation is handled by TradeRequest.__post_init__
        # Additional business logic validation
        
        if not validate_currency_pair(request.symbol):
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid currency pair format: {request.symbol}"
            )
        
        # Check trade amount limits
        if request.amount < 1.0:
            warnings.append("Very small trade amount")
        elif request.amount > 1000.0:
            warnings.append("Large trade amount detected")
        
        # Check expiration time
        if request.expiration_time < 60:
            warnings.append("Very short expiration time")
        elif request.expiration_time > 300:
            warnings.append("Long expiration time")
        
        return ValidationResult(is_valid=True, warnings=warnings)
        
    except ValueError as e:
        return ValidationResult(is_valid=False, error_message=str(e))


def is_numeric(value: Any) -> bool:
    """Check if value is numeric (int or float).
    
    Args:
        value: Value to check
        
    Returns:
        True if numeric, False otherwise
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_positive_number(value: Any) -> bool:
    """Check if value is a positive number.
    
    Args:
        value: Value to check
        
    Returns:
        True if positive number, False otherwise
    """
    return is_numeric(value) and value > 0


def is_valid_percentage(value: Any) -> bool:
    """Check if value is a valid percentage (0-100).
    
    Args:
        value: Value to check
        
    Returns:
        True if valid percentage, False otherwise
    """
    return is_numeric(value) and 0 <= value <= 100


def is_valid_confidence(value: Any) -> bool:
    """Check if value is a valid confidence score (0-1).
    
    Args:
        value: Value to check
        
    Returns:
        True if valid confidence, False otherwise
    """
    return is_numeric(value) and 0 <= value <= 1


def sanitize_string(value: str, max_length: int = 100) -> str:
    """Sanitize string input by removing special characters and limiting length.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return ""
    
    # Remove special characters except alphanumeric, spaces, hyphens, underscores
    sanitized = re.sub(r'[^a-zA-Z0-9\s\-_]', '', value)
    
    # Limit length
    return sanitized[:max_length].strip()


def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float with default fallback.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int_conversion(value: Any, default: int = 0) -> int:
    """Safely convert value to int with default fallback.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def validate_email(email: str) -> bool:
    """Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid email format, False otherwise
    """
    if not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_api_key(api_key: str, min_length: int = 10) -> bool:
    """Validate API key format.
    
    Args:
        api_key: API key to validate
        min_length: Minimum required length
        
    Returns:
        True if valid API key format, False otherwise
    """
    if not isinstance(api_key, str):
        return False
    
    return len(api_key.strip()) >= min_length and api_key.isalnum()


def format_timestamp(timestamp: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime object to string.
    
    Args:
        timestamp: Datetime object to format
        format_str: Format string
        
    Returns:
        Formatted timestamp string
    """
    try:
        return timestamp.strftime(format_str)
    except (AttributeError, ValueError):
        return "Invalid timestamp"


def parse_timestamp(timestamp_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """Parse timestamp string to datetime object.
    
    Args:
        timestamp_str: Timestamp string to parse
        format_str: Expected format string
        
    Returns:
        Datetime object or None if parsing fails
    """
    try:
        return datetime.strptime(timestamp_str, format_str)
    except (ValueError, TypeError):
        return None


def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between minimum and maximum bounds.
    
    Args:
        value: Value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Clamped value
    """
    return max(min_val, min(value, max_val))


def calculate_win_rate(wins: int, total: int) -> float:
    """Calculate win rate percentage with zero division protection.
    
    Args:
        wins: Number of wins
        total: Total number of trades
        
    Returns:
        Win rate as percentage (0-100)
    """
    if total == 0:
        return 0.0
    return (wins / total) * 100