"""Unit tests for data models."""

import pytest
from datetime import datetime
from src.backend.models import (
    MarketData, Signal, TradeRequest, TradeResult, Balance,
    NotificationMessage, TradingStatus, PerformanceMetrics,
    ValidationResult, SignalType, TradeDirection
)


class TestMarketData:
    """Test cases for MarketData model."""
    
    def test_valid_market_data(self):
        """Test creating valid market data."""
        data = MarketData(
            symbol="EURUSD",
            timestamp=datetime.now(),
            open_price=1.1000,
            high_price=1.1050,
            low_price=1.0950,
            close_price=1.1025,
            volume=1000.0
        )
        
        assert data.symbol == "EURUSD"
        assert data.open_price == 1.1000
        assert data.high_price == 1.1050
        assert data.low_price == 1.0950
        assert data.close_price == 1.1025
        assert data.volume == 1000.0
    
    def test_invalid_high_price(self):
        """Test validation of high price."""
        with pytest.raises(ValueError, match="High price cannot be less than"):
            MarketData(
                symbol="EURUSD",
                timestamp=datetime.now(),
                open_price=1.1000,
                high_price=1.0900,  # Lower than open price
                low_price=1.0950,
                close_price=1.1025,
                volume=1000.0
            )
    
    def test_invalid_low_price(self):
        """Test validation of low price."""
        with pytest.raises(ValueError, match="Low price cannot be greater than"):
            MarketData(
                symbol="EURUSD",
                timestamp=datetime.now(),
                open_price=1.1000,
                high_price=1.1050,
                low_price=1.1100,  # Higher than open price
                close_price=1.1025,
                volume=1000.0
            )
    
    def test_negative_prices(self):
        """Test validation of negative prices."""
        with pytest.raises(ValueError, match="Prices cannot be negative"):
            MarketData(
                symbol="EURUSD",
                timestamp=datetime.now(),
                open_price=-1.1000,
                high_price=1.1050,
                low_price=1.0950,
                close_price=1.1025,
                volume=1000.0
            )
    
    def test_negative_volume(self):
        """Test validation of negative volume."""
        with pytest.raises(ValueError, match="Volume cannot be negative"):
            MarketData(
                symbol="EURUSD",
                timestamp=datetime.now(),
                open_price=1.1000,
                high_price=1.1050,
                low_price=1.0950,
                close_price=1.1025,
                volume=-1000.0
            )


class TestSignal:
    """Test cases for Signal model."""
    
    def test_valid_signal(self):
        """Test creating valid signal."""
        signal = Signal(
            symbol="EURUSD",
            signal_type=SignalType.BUY,
            confidence=0.85,
            timestamp=datetime.now(),
            rsi_value=25.0,
            sma_value=1.1000,
            current_price=1.1025
        )
        
        assert signal.symbol == "EURUSD"
        assert signal.signal_type == SignalType.BUY
        assert signal.confidence == 0.85
        assert signal.rsi_value == 25.0
        assert signal.sma_value == 1.1000
        assert signal.current_price == 1.1025
    
    def test_invalid_confidence(self):
        """Test validation of confidence value."""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            Signal(
                symbol="EURUSD",
                signal_type=SignalType.BUY,
                confidence=1.5,  # Invalid confidence
                timestamp=datetime.now(),
                rsi_value=25.0,
                sma_value=1.1000,
                current_price=1.1025
            )
    
    def test_invalid_rsi(self):
        """Test validation of RSI value."""
        with pytest.raises(ValueError, match="RSI value must be between 0 and 100"):
            Signal(
                symbol="EURUSD",
                signal_type=SignalType.BUY,
                confidence=0.85,
                timestamp=datetime.now(),
                rsi_value=150.0,  # Invalid RSI
                sma_value=1.1000,
                current_price=1.1025
            )
    
    def test_negative_sma(self):
        """Test validation of negative SMA."""
        with pytest.raises(ValueError, match="SMA value cannot be negative"):
            Signal(
                symbol="EURUSD",
                signal_type=SignalType.BUY,
                confidence=0.85,
                timestamp=datetime.now(),
                rsi_value=25.0,
                sma_value=-1.1000,  # Negative SMA
                current_price=1.1025
            )


class TestTradeRequest:
    """Test cases for TradeRequest model."""
    
    def test_valid_trade_request(self):
        """Test creating valid trade request."""
        request = TradeRequest(
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=10.0,
            expiration_time=60,
            is_demo=True
        )
        
        assert request.symbol == "EURUSD"
        assert request.direction == TradeDirection.CALL
        assert request.amount == 10.0
        assert request.expiration_time == 60
        assert request.is_demo is True
    
    def test_invalid_amount(self):
        """Test validation of trade amount."""
        with pytest.raises(ValueError, match="Trade amount must be positive"):
            TradeRequest(
                symbol="EURUSD",
                direction=TradeDirection.CALL,
                amount=-10.0,  # Negative amount
                expiration_time=60,
                is_demo=True
            )
    
    def test_invalid_expiration_time(self):
        """Test validation of expiration time."""
        with pytest.raises(ValueError, match="Expiration time must be positive"):
            TradeRequest(
                symbol="EURUSD",
                direction=TradeDirection.CALL,
                amount=10.0,
                expiration_time=-60,  # Negative expiration
                is_demo=True
            )


class TestTradeResult:
    """Test cases for TradeResult model."""
    
    def test_valid_trade_result(self):
        """Test creating valid trade result."""
        result = TradeResult(
            trade_id="12345",
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=10.0,
            entry_price=1.1000,
            exit_price=1.1025,
            profit_loss=8.5,
            is_win=True,
            timestamp=datetime.now()
        )
        
        assert result.trade_id == "12345"
        assert result.symbol == "EURUSD"
        assert result.direction == TradeDirection.CALL
        assert result.amount == 10.0
        assert result.entry_price == 1.1000
        assert result.exit_price == 1.1025
        assert result.profit_loss == 8.5
        assert result.is_win is True
    
    def test_invalid_amount(self):
        """Test validation of trade amount."""
        with pytest.raises(ValueError, match="Trade amount must be positive"):
            TradeResult(
                trade_id="12345",
                symbol="EURUSD",
                direction=TradeDirection.CALL,
                amount=-10.0,  # Negative amount
                entry_price=1.1000,
                exit_price=1.1025,
                profit_loss=8.5,
                is_win=True,
                timestamp=datetime.now()
            )
    
    def test_negative_entry_price(self):
        """Test validation of entry price."""
        with pytest.raises(ValueError, match="Entry price cannot be negative"):
            TradeResult(
                trade_id="12345",
                symbol="EURUSD",
                direction=TradeDirection.CALL,
                amount=10.0,
                entry_price=-1.1000,  # Negative entry price
                exit_price=1.1025,
                profit_loss=8.5,
                is_win=True,
                timestamp=datetime.now()
            )


class TestBalance:
    """Test cases for Balance model."""
    
    def test_valid_balance(self):
        """Test creating valid balance."""
        balance = Balance(
            total_balance=1000.0,
            available_balance=950.0,
            currency="USD",
            timestamp=datetime.now()
        )
        
        assert balance.total_balance == 1000.0
        assert balance.available_balance == 950.0
        assert balance.currency == "USD"
    
    def test_negative_total_balance(self):
        """Test validation of negative total balance."""
        with pytest.raises(ValueError, match="Total balance cannot be negative"):
            Balance(
                total_balance=-1000.0,
                available_balance=950.0,
                currency="USD",
                timestamp=datetime.now()
            )
    
    def test_available_exceeds_total(self):
        """Test validation when available balance exceeds total."""
        with pytest.raises(ValueError, match="Available balance cannot exceed total balance"):
            Balance(
                total_balance=1000.0,
                available_balance=1100.0,  # Exceeds total
                currency="USD",
                timestamp=datetime.now()
            )


class TestNotificationMessage:
    """Test cases for NotificationMessage model."""
    
    def test_valid_notification(self):
        """Test creating valid notification."""
        notification = NotificationMessage(
            message_type="trade_executed",
            title="Trade Executed",
            content="EURUSD CALL trade executed successfully",
            timestamp=datetime.now(),
            priority="high"
        )
        
        assert notification.message_type == "trade_executed"
        assert notification.title == "Trade Executed"
        assert notification.priority == "high"
    
    def test_invalid_priority(self):
        """Test validation of priority value."""
        with pytest.raises(ValueError, match="Priority must be one of"):
            NotificationMessage(
                message_type="trade_executed",
                title="Trade Executed",
                content="EURUSD CALL trade executed successfully",
                timestamp=datetime.now(),
                priority="invalid"  # Invalid priority
            )


class TestTradingStatus:
    """Test cases for TradingStatus model."""
    
    def test_valid_trading_status(self):
        """Test creating valid trading status."""
        status = TradingStatus(
            is_active=True,
            current_pairs=["EURUSD", "GBPUSD"],
            last_signal_time=datetime.now(),
            last_trade_time=datetime.now(),
            total_trades_today=10,
            wins_today=7,
            losses_today=3,
            profit_loss_today=25.5
        )
        
        assert status.is_active is True
        assert len(status.current_pairs) == 2
        assert status.total_trades_today == 10
        assert status.wins_today == 7
        assert status.losses_today == 3
    
    def test_wins_losses_exceed_total(self):
        """Test validation when wins + losses exceed total trades."""
        with pytest.raises(ValueError, match="Wins \\+ losses cannot exceed total trades"):
            TradingStatus(
                is_active=True,
                current_pairs=["EURUSD"],
                last_signal_time=None,
                last_trade_time=None,
                total_trades_today=10,
                wins_today=7,
                losses_today=5,  # 7 + 5 > 10
                profit_loss_today=25.5
            )


class TestPerformanceMetrics:
    """Test cases for PerformanceMetrics model."""
    
    def test_valid_performance_metrics(self):
        """Test creating valid performance metrics."""
        metrics = PerformanceMetrics(
            total_trades=100,
            winning_trades=75,
            losing_trades=25,
            win_rate=75.0,
            total_profit_loss=250.0,
            average_profit=15.0,
            average_loss=-8.0,
            max_consecutive_wins=5,
            max_consecutive_losses=3
        )
        
        assert metrics.total_trades == 100
        assert metrics.winning_trades == 75
        assert metrics.losing_trades == 25
        assert metrics.win_rate == 75.0
    
    def test_invalid_win_rate(self):
        """Test validation of win rate."""
        with pytest.raises(ValueError, match="Win rate must be between 0 and 100"):
            PerformanceMetrics(
                total_trades=100,
                winning_trades=75,
                losing_trades=25,
                win_rate=150.0,  # Invalid win rate
                total_profit_loss=250.0,
                average_profit=15.0,
                average_loss=-8.0,
                max_consecutive_wins=5,
                max_consecutive_losses=3
            )
    
    def test_trades_mismatch(self):
        """Test validation when winning + losing trades don't match total."""
        with pytest.raises(ValueError, match="Winning \\+ losing trades must equal total trades"):
            PerformanceMetrics(
                total_trades=100,
                winning_trades=75,
                losing_trades=30,  # 75 + 30 != 100
                win_rate=75.0,
                total_profit_loss=250.0,
                average_profit=15.0,
                average_loss=-8.0,
                max_consecutive_wins=5,
                max_consecutive_losses=3
            )


class TestValidationResult:
    """Test cases for ValidationResult model."""
    
    def test_valid_result(self):
        """Test creating valid validation result."""
        result = ValidationResult(
            is_valid=True,
            error_message=None,
            warnings=["Warning message"]
        )
        
        assert result.is_valid is True
        assert result.error_message is None
        assert len(result.warnings) == 1
    
    def test_invalid_result(self):
        """Test creating invalid validation result."""
        result = ValidationResult(
            is_valid=False,
            error_message="Validation failed"
        )
        
        assert result.is_valid is False
        assert result.error_message == "Validation failed"
        assert result.warnings == []  # Should be initialized to empty list