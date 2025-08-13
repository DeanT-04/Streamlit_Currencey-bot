"""Unit tests for database functionality."""

import pytest
import tempfile
import os
from datetime import datetime, date
from pathlib import Path

from src.backend.database import DatabaseManager
from src.backend.models import TradeResult, TradeDirection


class TestDatabaseManager:
    """Test cases for DatabaseManager."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        
        db_manager = DatabaseManager(temp_file.name)
        
        yield db_manager
        
        # Cleanup
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
    
    def test_database_initialization(self, temp_db):
        """Test database schema initialization."""
        # Check if tables exist by trying to query them
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check trades table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
            assert cursor.fetchone() is not None
            
            # Check daily_performance table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_performance'")
            assert cursor.fetchone() is not None
    
    def test_save_trade(self, temp_db):
        """Test saving trade to database."""
        trade = TradeResult(
            trade_id="test_123",
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=10.0,
            entry_price=1.1000,
            exit_price=1.1025,
            profit_loss=8.5,
            is_win=True,
            timestamp=datetime.now()
        )
        
        result = temp_db.save_trade(trade)
        assert result is True
        
        # Verify trade was saved
        trades = temp_db.get_trades(limit=1)
        assert len(trades) == 1
        assert trades[0].trade_id == "test_123"
        assert trades[0].symbol == "EURUSD"
        assert trades[0].amount == 10.0
    
    def test_get_trades_with_filters(self, temp_db):
        """Test getting trades with various filters."""
        # Create test trades
        trades = [
            TradeResult(
                trade_id="trade_1",
                symbol="EURUSD",
                direction=TradeDirection.CALL,
                amount=10.0,
                entry_price=1.1000,
                exit_price=1.1025,
                profit_loss=8.5,
                is_win=True,
                timestamp=datetime(2024, 1, 1, 10, 0, 0)
            ),
            TradeResult(
                trade_id="trade_2",
                symbol="GBPUSD",
                direction=TradeDirection.PUT,
                amount=15.0,
                entry_price=1.2500,
                exit_price=1.2475,
                profit_loss=12.0,
                is_win=True,
                timestamp=datetime(2024, 1, 2, 11, 0, 0)
            ),
            TradeResult(
                trade_id="trade_3",
                symbol="EURUSD",
                direction=TradeDirection.CALL,
                amount=20.0,
                entry_price=1.1050,
                exit_price=1.1040,
                profit_loss=-20.0,
                is_win=False,
                timestamp=datetime(2024, 1, 3, 12, 0, 0)
            )
        ]
        
        # Save all trades
        for trade in trades:
            temp_db.save_trade(trade)
        
        # Test filter by symbol
        eurusd_trades = temp_db.get_trades(symbol="EURUSD")
        assert len(eurusd_trades) == 2
        
        # Test filter by date range
        start_date = datetime(2024, 1, 2, 0, 0, 0)
        end_date = datetime(2024, 1, 3, 23, 59, 59)
        date_filtered_trades = temp_db.get_trades(start_date=start_date, end_date=end_date)
        assert len(date_filtered_trades) == 2
        
        # Test limit
        limited_trades = temp_db.get_trades(limit=2)
        assert len(limited_trades) == 2
    
    def test_update_daily_performance(self, temp_db):
        """Test updating daily performance metrics."""
        # Create test trades for today
        today = date.today()
        trades = [
            TradeResult(
                trade_id="daily_1",
                symbol="EURUSD",
                direction=TradeDirection.CALL,
                amount=10.0,
                entry_price=1.1000,
                exit_price=1.1025,
                profit_loss=8.5,
                is_win=True,
                timestamp=datetime.combine(today, datetime.min.time())
            ),
            TradeResult(
                trade_id="daily_2",
                symbol="GBPUSD",
                direction=TradeDirection.PUT,
                amount=15.0,
                entry_price=1.2500,
                exit_price=1.2475,
                profit_loss=12.0,
                is_win=True,
                timestamp=datetime.combine(today, datetime.min.time())
            ),
            TradeResult(
                trade_id="daily_3",
                symbol="EURUSD",
                direction=TradeDirection.CALL,
                amount=20.0,
                entry_price=1.1050,
                exit_price=1.1040,
                profit_loss=-20.0,
                is_win=False,
                timestamp=datetime.combine(today, datetime.min.time())
            )
        ]
        
        # Save trades
        for trade in trades:
            temp_db.save_trade(trade)
        
        # Update daily performance
        result = temp_db.update_daily_performance(today)
        assert result is True
        
        # Verify performance metrics
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_performance WHERE date = ?", (today,))
            row = cursor.fetchone()
            
            assert row is not None
            assert row['total_trades'] == 3
            assert row['winning_trades'] == 2
            assert row['losing_trades'] == 1
            assert row['total_profit_loss'] == 0.5  # 8.5 + 12.0 - 20.0
            assert abs(row['win_rate'] - 66.67) < 0.1  # Approximately 66.67%
    
    def test_get_performance_metrics(self, temp_db):
        """Test getting performance metrics."""
        # Create test trades
        trades = [
            TradeResult(
                trade_id="perf_1",
                symbol="EURUSD",
                direction=TradeDirection.CALL,
                amount=10.0,
                entry_price=1.1000,
                exit_price=1.1025,
                profit_loss=8.5,
                is_win=True,
                timestamp=datetime.now()
            ),
            TradeResult(
                trade_id="perf_2",
                symbol="GBPUSD",
                direction=TradeDirection.PUT,
                amount=15.0,
                entry_price=1.2500,
                exit_price=1.2475,
                profit_loss=12.0,
                is_win=True,
                timestamp=datetime.now()
            ),
            TradeResult(
                trade_id="perf_3",
                symbol="EURUSD",
                direction=TradeDirection.CALL,
                amount=20.0,
                entry_price=1.1050,
                exit_price=1.1040,
                profit_loss=-20.0,
                is_win=False,
                timestamp=datetime.now()
            )
        ]
        
        # Save trades
        for trade in trades:
            temp_db.save_trade(trade)
        
        # Get performance metrics
        metrics = temp_db.get_performance_metrics(days=30)
        
        assert metrics.total_trades == 3
        assert metrics.winning_trades == 2
        assert metrics.losing_trades == 1
        assert abs(metrics.win_rate - 66.67) < 0.1
        assert metrics.total_profit_loss == 0.5
        assert metrics.average_profit == 10.25  # (8.5 + 12.0) / 2
        assert metrics.average_loss == -20.0
    
    def test_cleanup_old_data(self, temp_db):
        """Test cleaning up old data."""
        # Create old trade (more than 90 days ago)
        old_trade = TradeResult(
            trade_id="old_trade",
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=10.0,
            entry_price=1.1000,
            exit_price=1.1025,
            profit_loss=8.5,
            is_win=True,
            timestamp=datetime(2023, 1, 1, 10, 0, 0)  # Old date
        )
        
        # Create recent trade
        recent_trade = TradeResult(
            trade_id="recent_trade",
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=10.0,
            entry_price=1.1000,
            exit_price=1.1025,
            profit_loss=8.5,
            is_win=True,
            timestamp=datetime.now()
        )
        
        # Save both trades
        temp_db.save_trade(old_trade)
        temp_db.save_trade(recent_trade)
        
        # Verify both trades exist
        all_trades = temp_db.get_trades()
        assert len(all_trades) == 2
        
        # Cleanup old data (keep last 90 days)
        result = temp_db.cleanup_old_data(days_to_keep=90)
        assert result is True
        
        # Verify only recent trade remains
        remaining_trades = temp_db.get_trades()
        assert len(remaining_trades) == 1
        assert remaining_trades[0].trade_id == "recent_trade"
    
    def test_database_error_handling(self, temp_db):
        """Test database error handling."""
        # Test with invalid trade (this should be caught by model validation)
        with pytest.raises(ValueError):
            invalid_trade = TradeResult(
                trade_id="invalid",
                symbol="EURUSD",
                direction=TradeDirection.CALL,
                amount=-10.0,  # Invalid negative amount
                entry_price=1.1000,
                exit_price=1.1025,
                profit_loss=8.5,
                is_win=True,
                timestamp=datetime.now()
            )
    
    def test_connection_context_manager(self, temp_db):
        """Test database connection context manager."""
        # Test successful connection
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
        
        # Connection should be closed after context
        # We can't directly test this, but the context manager should handle cleanup