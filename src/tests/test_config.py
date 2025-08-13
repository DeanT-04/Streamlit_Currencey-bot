"""Tests for configuration management."""

import os
import pytest
from unittest.mock import patch

from src.backend.config import ConfigManager


class TestConfigManager:
    """Test cases for ConfigManager."""

    def test_trading_config_defaults(self):
        """Test trading configuration with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config_manager = ConfigManager.__new__(ConfigManager)  # Skip validation
            trading_config = config_manager.get_trading_config()

            assert trading_config.default_trade_amount == 10.0
            assert trading_config.max_daily_loss_percent == 5.0
            assert trading_config.max_trade_percent == 2.0
            assert trading_config.consecutive_loss_limit == 3
            assert trading_config.demo_mode is True

    def test_trading_config_custom_values(self):
        """Test trading configuration with custom values."""
        env_vars = {
            "DEFAULT_TRADE_AMOUNT": "25.0",
            "MAX_DAILY_LOSS_PERCENT": "10.0",
            "MAX_TRADE_PERCENT": "5.0",
            "CONSECUTIVE_LOSS_LIMIT": "5",
            "POCKET_OPTION_DEMO_MODE": "false",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config_manager = ConfigManager.__new__(ConfigManager)  # Skip validation
            trading_config = config_manager.get_trading_config()

            assert trading_config.default_trade_amount == 25.0
            assert trading_config.max_daily_loss_percent == 10.0
            assert trading_config.max_trade_percent == 5.0
            assert trading_config.consecutive_loss_limit == 5
            assert trading_config.demo_mode is False

    def test_api_config(self):
        """Test API configuration."""
        env_vars = {
            "POCKET_OPTION_EMAIL": "test@example.com",
            "POCKET_OPTION_PASSWORD": "testpass",
            "ALPHA_VANTAGE_API_KEY": "testkey123",
            "TELEGRAM_BOT_TOKEN": "bot123:token",
            "TELEGRAM_CHAT_ID": "12345",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config_manager = ConfigManager.__new__(ConfigManager)  # Skip validation
            api_config = config_manager.get_api_config()

            assert api_config.pocket_option_email == "test@example.com"
            assert api_config.pocket_option_password == "testpass"
            assert api_config.alpha_vantage_api_key == "testkey123"
            assert api_config.telegram_bot_token == "bot123:token"
            assert api_config.telegram_chat_id == "12345"

    def test_app_config_defaults(self):
        """Test application configuration with defaults."""
        with patch.dict(os.environ, {}, clear=True):
            config_manager = ConfigManager.__new__(ConfigManager)  # Skip validation
            app_config = config_manager.get_app_config()

            assert app_config.database_url == "sqlite:///trading_bot.db"
            assert app_config.log_level == "INFO"
            assert app_config.log_file == "trading_bot.log"
            assert app_config.debug_mode is False
            assert app_config.streamlit_port == 8501

    def test_missing_required_env_vars(self):
        """Test validation of required environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                ConfigManager()

            assert "Missing required environment variables" in str(exc_info.value)
            assert "POCKET_OPTION_EMAIL" in str(exc_info.value)
            assert "POCKET_OPTION_PASSWORD" in str(exc_info.value)
            assert "ALPHA_VANTAGE_API_KEY" in str(exc_info.value)

    def test_valid_required_env_vars(self):
        """Test successful initialization with required variables."""
        env_vars = {
            "POCKET_OPTION_EMAIL": "test@example.com",
            "POCKET_OPTION_PASSWORD": "testpass",
            "ALPHA_VANTAGE_API_KEY": "testkey123",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            # Should not raise an exception
            config_manager = ConfigManager()
            assert config_manager is not None
