"""Unit tests for Risk Manager."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.backend.risk_manager import RiskManager, RiskMetrics
from src.backend.models import (
    TradeRequest, 
    TradeResult, 
    Balance, 
    TradeDirection,
    ValidationResult
)
from src.backend.config import TradingConfig


@pytest.fixture
def trading_config():
    """Create a test trading configuration."""
    return TradingConfig(
        default_trade_amount=10.0,
        max_daily_loss_percent=5.0,
        max_trade_percent=2.0,
        consecutive_loss_limit=3,
        demo_mode=True
    )


@pytest.fixture
def risk_manager(trading_config):
    """Create a risk manager instance for testing."""
    return RiskManager(trading_config)


@pytest.fixture
def sample_balance():
    """Create a sample balance for testing."""
    return Balance(
        total_balance=1000.0,
        available_balance=1000.0,
        currency="USD",
        timestamp=datetime.now()
    )


@pytest.fixture
def sample_trade_request():
    """Create a sample trade request for testing."""
    return TradeRequest(
        symbol="EURUSD",
        direction=TradeDirection.CALL,
        amount=20.0,
        expiration_time=60,
        is_demo=True
    )


class TestRiskManager:
    """Test cases for RiskManager class."""
    
    def test_initialization(self, trading_config):
        """Test risk manager initialization."""
        risk_manager = RiskManager(trading_config)
        
        assert risk_manager.config == trading_config
        assert risk_manager.trade_history == []
        assert risk_manager.daily_start_balance is None
        assert not risk_manager.is_paused
        assert risk_manager.pause_reason is None
        assert risk_manager.pause_until is None
    
    def test_calculate_position_size_default(self, risk_manager, sample_balance):
        """Test position size calculation with default risk percentage."""
        position_size = risk_manager.calculate_position_size(sample_balance.total_balance)
        
        # Should be 2% of balance (max_trade_percent)
        expected_size = 1000.0 * 0.02  # 20.0
        assert position_size == expected_size
    
    def test_calculate_position_size_custom_risk(self, risk_manager, sample_balance):
        """Test position size calculation with custom risk percentage."""
        position_size = risk_manager.calculate_position_size(sample_balance.total_balance, 1.0)
        
        # Should be 1% of balance
        expected_size = 1000.0 * 0.01  # 10.0
        assert position_size == expected_size
    
    def test_calculate_position_size_exceeds_max(self, risk_manager, sample_balance):
        """Test position size calculation when requested risk exceeds maximum."""
        position_size = risk_manager.calculate_position_size(sample_balance.total_balance, 5.0)
        
        # Should be capped at max_trade_percent (2%)
        expected_size = 1000.0 * 0.02  # 20.0
        assert position_size == expected_size
    
    def test_calculate_position_size_minimum_bound(self, risk_manager):
        """Test position size calculation with very small balance."""
        small_balance = 10.0
        position_size = risk_manager.calculate_position_size(small_balance)
        
        # Should be at least minimum trade amount (1.0)
        assert position_size >= 1.0
    
    def test_validate_trade_request_valid(self, risk_manager, sample_trade_request, sample_balance):
        """Test validation of a valid trade request."""
        result = risk_manager.validate_trade_request(sample_trade_request, sample_balance)
        
        assert result.is_valid
        assert result.error_message is None
    
    def test_validate_trade_request_insufficient_balance(self, risk_manager, sample_balance):
        """Test validation with insufficient balance."""
        trade_request = TradeRequest(
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=1500.0,  # More than available balance
            expiration_time=60,
            is_demo=True
        )
        
        result = risk_manager.validate_trade_request(trade_request, sample_balance)
        
        assert not result.is_valid
        assert "Insufficient balance" in result.error_message
    
    def test_validate_trade_request_exceeds_max_trade_percent(self, risk_manager, sample_balance):
        """Test validation when trade amount exceeds maximum percentage."""
        trade_request = TradeRequest(
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=50.0,  # 5% of balance, exceeds 2% limit
            expiration_time=60,
            is_demo=True
        )
        
        result = risk_manager.validate_trade_request(trade_request, sample_balance)
        
        assert not result.is_valid
        assert "exceeds maximum allowed" in result.error_message
    
    def test_validate_trade_request_negative_amount(self, risk_manager, sample_balance):
        """Test validation with negative trade amount."""
        # Test the risk manager's validation directly since TradeRequest model 
        # prevents negative amounts in __post_init__
        validation_result = risk_manager._validate_trade_amount(-10.0, sample_balance.available_balance)
        
        assert not validation_result.is_valid
        assert "must be positive" in validation_result.error_message
    
    def test_validate_trade_request_demo_mode_violation(self, risk_manager, sample_balance):
        """Test validation when trying real trade in demo mode."""
        trade_request = TradeRequest(
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=10.0,
            expiration_time=60,
            is_demo=False  # Real trade in demo mode
        )
        
        result = risk_manager.validate_trade_request(trade_request, sample_balance)
        
        assert not result.is_valid
        assert "demo mode" in result.error_message
    
    def test_check_daily_limits_within_limits(self, risk_manager):
        """Test daily limits check when within limits."""
        risk_manager.daily_start_balance = 1000.0
        current_balance = 980.0  # 2% loss, within 5% limit
        
        result = risk_manager.check_daily_limits(current_balance)
        
        assert result is True
        assert not risk_manager.is_paused
    
    def test_check_daily_limits_exceeded(self, risk_manager):
        """Test daily limits check when limits are exceeded."""
        risk_manager.daily_start_balance = 1000.0
        current_balance = 940.0  # 6% loss, exceeds 5% limit
        
        result = risk_manager.check_daily_limits(current_balance)
        
        assert result is False
        assert risk_manager.is_paused
        assert "Daily loss limit exceeded" in risk_manager.pause_reason
    
    def test_check_daily_limits_first_time(self, risk_manager):
        """Test daily limits check when called for the first time."""
        current_balance = 1000.0
        
        result = risk_manager.check_daily_limits(current_balance)
        
        assert result is True
        assert risk_manager.daily_start_balance == current_balance
    
    def test_should_pause_trading_consecutive_losses(self, risk_manager):
        """Test pausing trading due to consecutive losses."""
        result = risk_manager.should_pause_trading(3)  # Equals limit
        
        assert result is True
        assert risk_manager.is_paused
        assert "Consecutive loss limit reached" in risk_manager.pause_reason
    
    def test_should_pause_trading_within_limits(self, risk_manager):
        """Test not pausing when within consecutive loss limits."""
        result = risk_manager.should_pause_trading(2)  # Below limit of 3
        
        assert result is False
        assert not risk_manager.is_paused
    
    def test_record_trade_result_win(self, risk_manager):
        """Test recording a winning trade result."""
        trade_result = TradeResult(
            trade_id="test_001",
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=10.0,
            entry_price=1.1000,
            exit_price=1.1010,
            profit_loss=8.0,
            is_win=True,
            timestamp=datetime.now()
        )
        
        risk_manager.record_trade_result(trade_result)
        
        assert len(risk_manager.trade_history) == 1
        assert risk_manager.trade_history[0] == trade_result
        assert not risk_manager.is_paused
    
    def test_record_trade_result_loss(self, risk_manager):
        """Test recording a losing trade result."""
        trade_result = TradeResult(
            trade_id="test_001",
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=10.0,
            entry_price=1.1000,
            exit_price=1.0990,
            profit_loss=-10.0,
            is_win=False,
            timestamp=datetime.now()
        )
        
        risk_manager.record_trade_result(trade_result)
        
        assert len(risk_manager.trade_history) == 1
        assert risk_manager.trade_history[0] == trade_result
    
    def test_record_consecutive_losses_triggers_pause(self, risk_manager):
        """Test that consecutive losses trigger trading pause."""
        # Record 3 consecutive losses
        for i in range(3):
            trade_result = TradeResult(
                trade_id=f"test_{i:03d}",
                symbol="EURUSD",
                direction=TradeDirection.CALL,
                amount=10.0,
                entry_price=1.1000,
                exit_price=1.0990,
                profit_loss=-10.0,
                is_win=False,
                timestamp=datetime.now()
            )
            risk_manager.record_trade_result(trade_result)
        
        assert risk_manager.is_paused
        assert "Consecutive loss limit reached" in risk_manager.pause_reason
    
    def test_get_risk_metrics(self, risk_manager):
        """Test getting current risk metrics."""
        risk_manager.daily_start_balance = 1000.0
        current_balance = 950.0
        
        # Add some trade history
        trade_result = TradeResult(
            trade_id="test_001",
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=10.0,
            entry_price=1.1000,
            exit_price=1.0990,
            profit_loss=-10.0,
            is_win=False,
            timestamp=datetime.now()
        )
        risk_manager.record_trade_result(trade_result)
        
        metrics = risk_manager.get_risk_metrics(current_balance)
        
        assert isinstance(metrics, RiskMetrics)
        assert metrics.daily_loss == 50.0
        assert metrics.daily_loss_percent == 5.0
        assert metrics.consecutive_losses == 1
        assert metrics.trades_today == 1
        assert metrics.last_loss_time is not None
    
    def test_is_trading_paused_not_paused(self, risk_manager):
        """Test checking if trading is paused when not paused."""
        assert not risk_manager.is_trading_paused()
    
    def test_is_trading_paused_currently_paused(self, risk_manager):
        """Test checking if trading is paused when currently paused."""
        risk_manager._pause_trading("Test pause")
        
        assert risk_manager.is_trading_paused()
    
    def test_is_trading_paused_expired_pause(self, risk_manager):
        """Test checking if trading is paused when pause has expired."""
        # Set pause that expired 1 minute ago
        risk_manager.is_paused = True
        risk_manager.pause_until = datetime.now() - timedelta(minutes=1)
        
        assert not risk_manager.is_trading_paused()
        assert not risk_manager.is_paused
    
    def test_resume_trading_when_paused(self, risk_manager):
        """Test manually resuming trading when paused."""
        risk_manager._pause_trading("Test pause")
        
        result = risk_manager.resume_trading()
        
        assert result is True
        assert not risk_manager.is_paused
        assert risk_manager.pause_reason is None
    
    def test_resume_trading_when_not_paused(self, risk_manager):
        """Test manually resuming trading when not paused."""
        result = risk_manager.resume_trading()
        
        assert result is False
    
    def test_reset_daily_metrics(self, risk_manager):
        """Test resetting daily metrics."""
        # Set up some initial state
        risk_manager.daily_start_balance = 1000.0
        risk_manager.trade_history = [Mock()]
        risk_manager._pause_trading("Daily loss limit exceeded")
        
        new_balance = 1100.0
        risk_manager.reset_daily_metrics(new_balance)
        
        assert risk_manager.daily_start_balance == new_balance
        assert len(risk_manager.trade_history) == 0
        assert not risk_manager.is_paused  # Should resume if paused due to daily loss
    
    def test_validate_trade_request_when_paused(self, risk_manager, sample_trade_request, sample_balance):
        """Test validation when trading is paused."""
        risk_manager._pause_trading("Test pause")
        
        result = risk_manager.validate_trade_request(sample_trade_request, sample_balance)
        
        assert not result.is_valid
        assert "Trading is paused" in result.error_message
    
    def test_count_consecutive_losses_mixed_results(self, risk_manager):
        """Test counting consecutive losses with mixed win/loss results."""
        # Add trades: Win, Loss, Loss, Loss (3 consecutive losses at end)
        trades = [
            (True, "win_001"),
            (False, "loss_001"),
            (False, "loss_002"),
            (False, "loss_003")
        ]
        
        for is_win, trade_id in trades:
            trade_result = TradeResult(
                trade_id=trade_id,
                symbol="EURUSD",
                direction=TradeDirection.CALL,
                amount=10.0,
                entry_price=1.1000,
                exit_price=1.1010 if is_win else 1.0990,
                profit_loss=8.0 if is_win else -10.0,
                is_win=is_win,
                timestamp=datetime.now()
            )
            risk_manager.trade_history.append(trade_result)
        
        consecutive_losses = risk_manager._count_consecutive_losses()
        assert consecutive_losses == 3
    
    def test_count_consecutive_losses_no_losses(self, risk_manager):
        """Test counting consecutive losses when there are no losses."""
        trade_result = TradeResult(
            trade_id="win_001",
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=10.0,
            entry_price=1.1000,
            exit_price=1.1010,
            profit_loss=8.0,
            is_win=True,
            timestamp=datetime.now()
        )
        risk_manager.trade_history.append(trade_result)
        
        consecutive_losses = risk_manager._count_consecutive_losses()
        assert consecutive_losses == 0
    
    def test_pause_trading_with_duration(self, risk_manager):
        """Test pausing trading with custom duration."""
        reason = "Test pause"
        duration = 30
        
        risk_manager._pause_trading(reason, duration)
        
        assert risk_manager.is_paused
        assert risk_manager.pause_reason == reason
        assert risk_manager.pause_until is not None
        
        # Check that pause_until is approximately 30 minutes from now
        expected_time = datetime.now() + timedelta(minutes=duration)
        time_diff = abs((risk_manager.pause_until - expected_time).total_seconds())
        assert time_diff < 5  # Within 5 seconds tolerance


class TestRiskMetrics:
    """Test cases for RiskMetrics dataclass."""
    
    def test_risk_metrics_creation(self):
        """Test creating RiskMetrics instance."""
        metrics = RiskMetrics(
            daily_loss=50.0,
            daily_loss_percent=5.0,
            consecutive_losses=2,
            trades_today=10,
            last_loss_time=datetime.now(),
            is_paused=False,
            pause_reason=None
        )
        
        assert metrics.daily_loss == 50.0
        assert metrics.daily_loss_percent == 5.0
        assert metrics.consecutive_losses == 2
        assert metrics.trades_today == 10
        assert metrics.last_loss_time is not None
        assert not metrics.is_paused
        assert metrics.pause_reason is None


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_zero_balance_position_sizing(self, risk_manager):
        """Test position sizing with zero balance."""
        position_size = risk_manager.calculate_position_size(0.0)
        
        # Should return minimum trade amount
        assert position_size == 1.0
    
    def test_negative_balance_position_sizing(self, risk_manager):
        """Test position sizing with negative balance."""
        position_size = risk_manager.calculate_position_size(-100.0)
        
        # Should return minimum trade amount
        assert position_size == 1.0
    
    def test_very_large_balance_position_sizing(self, risk_manager):
        """Test position sizing with very large balance."""
        large_balance = 1000000.0
        position_size = risk_manager.calculate_position_size(large_balance)
        
        # Should be 2% of balance
        expected_size = large_balance * 0.02
        assert position_size == expected_size
    
    def test_trade_history_cleanup(self, risk_manager):
        """Test that trade history is cleaned up to keep only today's trades."""
        # Add old trade (yesterday)
        old_trade = TradeResult(
            trade_id="old_001",
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=10.0,
            entry_price=1.1000,
            exit_price=1.1010,
            profit_loss=8.0,
            is_win=True,
            timestamp=datetime.now() - timedelta(days=1)
        )
        risk_manager.trade_history.append(old_trade)
        
        # Add new trade (today)
        new_trade = TradeResult(
            trade_id="new_001",
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=10.0,
            entry_price=1.1000,
            exit_price=1.1010,
            profit_loss=8.0,
            is_win=True,
            timestamp=datetime.now()
        )
        
        # Recording new trade should clean up old trades
        risk_manager.record_trade_result(new_trade)
        
        # Should only have today's trade
        assert len(risk_manager.trade_history) == 1
        assert risk_manager.trade_history[0].trade_id == "new_001"