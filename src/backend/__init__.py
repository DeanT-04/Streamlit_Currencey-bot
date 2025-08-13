"""Backend package for Pocket Option Trading Bot."""

from .models import (
    MarketData,
    Signal,
    TradeRequest,
    TradeResult,
    Balance,
    NotificationMessage,
    TradingStatus,
    PerformanceMetrics,
    ValidationResult,
    SignalType,
    TradeDirection,
)

from .config import (
    TradingConfig,
    APIConfig,
    AppConfig,
    ConfigManager,
    get_config_manager,
)

from .database import (
    DatabaseManager,
    get_database_manager,
)

from .utils import (
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

__all__ = [
    # Models
    "MarketData",
    "Signal",
    "TradeRequest",
    "TradeResult",
    "Balance",
    "NotificationMessage",
    "TradingStatus",
    "PerformanceMetrics",
    "ValidationResult",
    "SignalType",
    "TradeDirection",
    # Configuration
    "TradingConfig",
    "APIConfig",
    "AppConfig",
    "ConfigManager",
    "get_config_manager",
    # Database
    "DatabaseManager",
    "get_database_manager",
    # Utilities
    "setup_logging",
    "validate_currency_pair",
    "format_currency",
    "calculate_percentage",
    "validate_market_data",
    "validate_signal",
    "validate_trade_request",
    "is_numeric",
    "is_positive_number",
    "is_valid_percentage",
    "is_valid_confidence",
    "sanitize_string",
    "safe_float_conversion",
    "safe_int_conversion",
    "validate_email",
    "validate_api_key",
    "format_timestamp",
    "parse_timestamp",
    "clamp_value",
    "calculate_win_rate",
    # Exceptions
    "TradingBotError",
    "APIError",
    "ConfigurationError",
    "TradingError",
]
