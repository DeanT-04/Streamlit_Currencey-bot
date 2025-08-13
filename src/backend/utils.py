"""Utility functions for Pocket Option Trading Bot."""

import logging
import sys
from typing import Optional
from pathlib import Path

from .config import get_config_manager


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
