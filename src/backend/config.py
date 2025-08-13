"""Configuration management for Pocket Option Trading Bot."""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class TradingConfig:
    """Trading configuration settings."""

    default_trade_amount: float
    max_daily_loss_percent: float
    max_trade_percent: float
    consecutive_loss_limit: int
    demo_mode: bool


@dataclass
class APIConfig:
    """API configuration settings."""

    pocket_option_email: str
    pocket_option_password: str
    alpha_vantage_api_key: str
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None


@dataclass
class AppConfig:
    """Application configuration settings."""

    database_url: str
    log_level: str
    log_file: str
    debug_mode: bool
    streamlit_port: int


class ConfigManager:
    """Manages application configuration from environment variables."""

    def __init__(self):
        """Initialize configuration manager."""
        self._validate_required_env_vars()

    def get_trading_config(self) -> TradingConfig:
        """Get trading configuration."""
        return TradingConfig(
            default_trade_amount=float(os.getenv("DEFAULT_TRADE_AMOUNT", "10.0")),
            max_daily_loss_percent=float(os.getenv("MAX_DAILY_LOSS_PERCENT", "5.0")),
            max_trade_percent=float(os.getenv("MAX_TRADE_PERCENT", "2.0")),
            consecutive_loss_limit=int(os.getenv("CONSECUTIVE_LOSS_LIMIT", "3")),
            demo_mode=os.getenv("POCKET_OPTION_DEMO_MODE", "true").lower() == "true",
        )

    def get_api_config(self) -> APIConfig:
        """Get API configuration."""
        return APIConfig(
            pocket_option_email=os.getenv("POCKET_OPTION_EMAIL", ""),
            pocket_option_password=os.getenv("POCKET_OPTION_PASSWORD", ""),
            alpha_vantage_api_key=os.getenv("ALPHA_VANTAGE_API_KEY", ""),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        )

    def get_app_config(self) -> AppConfig:
        """Get application configuration."""
        return AppConfig(
            database_url=os.getenv("DATABASE_URL", "sqlite:///trading_bot.db"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "trading_bot.log"),
            debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true",
            streamlit_port=int(os.getenv("STREAMLIT_PORT", "8501")),
        )

    def _validate_required_env_vars(self) -> None:
        """Validate that required environment variables are set."""
        required_vars = [
            "POCKET_OPTION_EMAIL",
            "POCKET_OPTION_PASSWORD",
            "ALPHA_VANTAGE_API_KEY",
        ]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                f"Please check your .env file."
            )


# Global configuration instance - initialized lazily
_config_manager = None


def get_config_manager() -> ConfigManager:
    """Get or create the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
