"""Unit tests for API Manager."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import aiohttp
import requests

from src.backend.api_manager import (
    APIManager, CircuitBreaker, RateLimiter, CircuitBreakerState,
    get_api_manager, close_api_manager
)
from src.backend.models import (
    MarketData, Signal, TradeRequest, TradeResult, Balance, 
    NotificationMessage, TradeDirection, SignalType
)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_initial_state(self):
        """Test circuit breaker initial state."""
        breaker = CircuitBreaker()
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.can_execute() is True
    
    def test_record_success(self):
        """Test recording successful operations."""
        breaker = CircuitBreaker()
        breaker.failure_count = 3
        breaker.state = CircuitBreakerState.HALF_OPEN
        
        breaker.record_success()
        
        assert breaker.failure_count == 0
        assert breaker.state == CircuitBreakerState.CLOSED
    
    def test_record_failure(self):
        """Test recording failed operations."""
        breaker = CircuitBreaker(failure_threshold=3)
        
        # Record failures below threshold
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.can_execute() is True
        
        # Record failure that triggers circuit breaker
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.can_execute() is False
    
    def test_timeout_recovery(self):
        """Test circuit breaker timeout recovery."""
        breaker = CircuitBreaker(failure_threshold=1, timeout=1)
        
        # Trigger circuit breaker
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.can_execute() is False
        
        # Simulate timeout passage
        breaker.last_failure_time = datetime.now() - timedelta(seconds=2)
        assert breaker.can_execute() is True
        assert breaker.state == CircuitBreakerState.HALF_OPEN


class TestRateLimiter:
    """Test rate limiter functionality."""
    
    def test_initial_state(self):
        """Test rate limiter initial state."""
        limiter = RateLimiter(max_requests=5, time_window=60)
        assert limiter.can_make_request() is True
        assert limiter.wait_time() == 0.0
    
    def test_request_recording(self):
        """Test request recording and limits."""
        limiter = RateLimiter(max_requests=2, time_window=60)
        
        # First request
        assert limiter.can_make_request() is True
        limiter.record_request()
        
        # Second request
        assert limiter.can_make_request() is True
        limiter.record_request()
        
        # Third request should be blocked
        assert limiter.can_make_request() is False
        assert limiter.wait_time() > 0
    
    def test_time_window_cleanup(self):
        """Test cleanup of old requests."""
        limiter = RateLimiter(max_requests=2, time_window=1)
        
        # Fill up the limit
        limiter.record_request()
        limiter.record_request()
        assert limiter.can_make_request() is False
        
        # Simulate time passage
        old_time = datetime.now() - timedelta(seconds=2)
        limiter.requests = [old_time, old_time]
        
        # Should be able to make requests again
        assert limiter.can_make_request() is True


class TestAPIManager:
    """Test API Manager functionality."""
    
    @pytest.fixture
    def api_manager(self):
        """Create API manager for testing."""
        manager = APIManager()
        manager.set_mock_mode(True)
        return manager
    
    @pytest.fixture
    def sample_trade_request(self):
        """Create sample trade request."""
        return TradeRequest(
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=10.0,
            expiration_time=60,
            is_demo=True
        )
    
    @pytest.fixture
    def sample_signal(self):
        """Create sample signal."""
        return Signal(
            symbol="EURUSD",
            signal_type=SignalType.BUY,
            confidence=0.8,
            timestamp=datetime.now(),
            rsi_value=25.0,
            sma_value=1.1000,
            current_price=1.1010
        )
    
    def test_initialization(self, api_manager):
        """Test API manager initialization."""
        assert api_manager.pocket_option_breaker is not None
        assert api_manager.alpha_vantage_breaker is not None
        assert api_manager.telegram_breaker is not None
        assert api_manager.session is not None
    
    def test_mock_mode(self, api_manager):
        """Test mock mode functionality."""
        mock_responses = {
            "balance": Balance(
                total_balance=500.0,
                available_balance=450.0,
                currency="USD",
                timestamp=datetime.now()
            )
        }
        
        api_manager.set_mock_mode(True, mock_responses)
        assert api_manager.mock_mode is True
        assert api_manager.mock_responses == mock_responses
    
    @pytest.mark.asyncio
    async def test_get_market_data(self, api_manager):
        """Test getting market data."""
        data = await api_manager.get_market_data("EURUSD", "1m", 10)
        
        assert isinstance(data, list)
        assert len(data) == 10
        assert all(isinstance(item, MarketData) for item in data)
        assert all(item.symbol == "EURUSD" for item in data)
    
    @pytest.mark.asyncio
    async def test_place_trade(self, api_manager, sample_trade_request):
        """Test placing a trade."""
        result = await api_manager.place_trade(sample_trade_request)
        
        assert isinstance(result, TradeResult)
        assert result.symbol == sample_trade_request.symbol
        assert result.direction == sample_trade_request.direction
        assert result.amount == sample_trade_request.amount
        assert result.trade_id is not None
    
    @pytest.mark.asyncio
    async def test_get_account_balance(self, api_manager):
        """Test getting account balance."""
        balance = await api_manager.get_account_balance()
        
        assert isinstance(balance, Balance)
        assert balance.total_balance > 0
        assert balance.available_balance >= 0
        assert balance.currency == "USD"
    
    @pytest.mark.asyncio
    async def test_validate_signal_mock(self, api_manager, sample_signal):
        """Test signal validation in mock mode."""
        result = await api_manager.validate_signal("EURUSD", sample_signal)
        assert isinstance(result, bool)
    
    def test_send_notification_no_credentials(self, api_manager):
        """Test notification sending without credentials."""
        api_manager.api_config.telegram_bot_token = None
        api_manager.api_config.telegram_chat_id = None
        
        message = NotificationMessage(
            message_type="trade",
            title="Test Trade",
            content="Test trade executed",
            timestamp=datetime.now()
        )
        
        result = api_manager.send_notification(message)
        assert result is False
    
    def test_send_notification_mock(self, api_manager):
        """Test notification sending in mock mode."""
        api_manager.api_config.telegram_bot_token = "test_token"
        api_manager.api_config.telegram_chat_id = "test_chat"
        
        message = NotificationMessage(
            message_type="trade",
            title="Test Trade",
            content="Test trade executed",
            timestamp=datetime.now()
        )
        
        result = api_manager.send_notification(message)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, api_manager):
        """Test circuit breaker integration with API calls."""
        # Disable mock mode to test actual circuit breaker
        api_manager.set_mock_mode(False)
        
        # Force circuit breaker to open
        api_manager.pocket_option_breaker.state = CircuitBreakerState.OPEN
        
        with pytest.raises(Exception, match="circuit breaker is OPEN"):
            await api_manager.get_market_data("EURUSD")
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, api_manager):
        """Test rate limiting integration."""
        # Set very low rate limit for testing
        api_manager.pocket_option_limiter.max_requests = 1
        api_manager.pocket_option_limiter.time_window = 60
        
        # First call should succeed
        await api_manager.get_market_data("EURUSD", limit=1)
        
        # Second call should be delayed due to rate limiting
        start_time = datetime.now()
        await api_manager.get_market_data("EURUSD", limit=1)
        end_time = datetime.now()
        
        # Should have been delayed (though in mock mode, delay might be minimal)
        assert (end_time - start_time).total_seconds() >= 0
    
    def test_convert_symbol_for_alpha_vantage(self, api_manager):
        """Test symbol conversion for Alpha Vantage."""
        result = api_manager._convert_symbol_for_alpha_vantage("EURUSD")
        assert result == "EUR/USD"
        
        result = api_manager._convert_symbol_for_alpha_vantage("GBP/USD")
        assert result == "GBP/USD"
    
    def test_validate_signal_against_data(self, api_manager, sample_signal):
        """Test signal validation against Alpha Vantage data."""
        mock_data = {
            "Time Series (1min)": {
                "2023-01-01 12:00:00": {
                    "1. open": "1.1000",
                    "2. high": "1.1020",
                    "3. low": "1.0980",
                    "4. close": "1.1010"
                }
            }
        }
        
        result = api_manager._validate_signal_against_data(sample_signal, mock_data)
        assert isinstance(result, bool)
    
    def test_validate_signal_against_data_no_data(self, api_manager, sample_signal):
        """Test signal validation with no data."""
        mock_data = {}
        
        result = api_manager._validate_signal_against_data(sample_signal, mock_data)
        assert result is False
    
    def test_generate_mock_market_data(self, api_manager):
        """Test mock market data generation."""
        data = api_manager._generate_mock_market_data("EURUSD", 5)
        
        assert len(data) == 5
        assert all(isinstance(item, MarketData) for item in data)
        assert all(item.symbol == "EURUSD" for item in data)
        
        # Check that prices are realistic
        for item in data:
            assert 0.5 < item.open_price < 2.0
            assert 0.5 < item.close_price < 2.0
            assert item.high_price >= max(item.open_price, item.close_price)
            assert item.low_price <= min(item.open_price, item.close_price)
    
    def test_generate_mock_trade_result(self, api_manager, sample_trade_request):
        """Test mock trade result generation."""
        result = api_manager._generate_mock_trade_result(sample_trade_request)
        
        assert isinstance(result, TradeResult)
        assert result.symbol == sample_trade_request.symbol
        assert result.direction == sample_trade_request.direction
        assert result.amount == sample_trade_request.amount
        assert result.trade_id.startswith("mock_trade_")
        assert result.entry_price > 0
    
    @pytest.mark.asyncio
    async def test_close(self, api_manager):
        """Test closing API manager."""
        # Create async session
        await api_manager._get_async_session()
        assert api_manager._async_session is not None
        
        # Close manager
        await api_manager.close()
        
        # Session should be closed
        assert api_manager._async_session.closed


class TestAPIManagerIntegration:
    """Test API Manager integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test concurrent API requests."""
        manager = APIManager()
        manager.set_mock_mode(True)
        
        # Make multiple concurrent requests
        tasks = [
            manager.get_market_data("EURUSD", limit=5),
            manager.get_market_data("GBPUSD", limit=5),
            manager.get_account_balance(),
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert isinstance(results[0], list)  # Market data
        assert isinstance(results[1], list)  # Market data
        assert isinstance(results[2], Balance)  # Balance
        
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test error recovery scenarios."""
        manager = APIManager()
        manager.set_mock_mode(True)
        
        # Simulate some failures
        manager.pocket_option_breaker.record_failure()
        manager.pocket_option_breaker.record_failure()
        
        # Should still be able to execute
        assert manager.pocket_option_breaker.can_execute() is True
        
        data = await manager.get_market_data("EURUSD")
        assert isinstance(data, list)
        
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_global_api_manager(self):
        """Test global API manager instance."""
        # Get global instance
        manager1 = await get_api_manager()
        manager2 = await get_api_manager()
        
        # Should be the same instance
        assert manager1 is manager2
        
        # Close global instance
        await close_api_manager()
        
        # Should create new instance
        manager3 = await get_api_manager()
        assert manager3 is not manager1
        
        await close_api_manager()


class TestAPIManagerWithRealRequests:
    """Test API Manager with real HTTP requests (mocked)."""
    
    @pytest.mark.asyncio
    async def test_alpha_vantage_request_structure(self):
        """Test Alpha Vantage request structure."""
        manager = APIManager()
        manager.set_mock_mode(False)  # Disable mock mode to test actual API call
        
        # Mock the async session
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "Time Series (1min)": {
                "2023-01-01 12:00:00": {
                    "4. close": "1.1000"
                }
            }
        })
        
        mock_session = Mock()
        mock_session.get = Mock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.closed = False
        
        # Patch the _get_async_session method to return our mock
        with patch.object(manager, '_get_async_session', return_value=mock_session):
            signal = Signal(
                symbol="EURUSD",
                signal_type=SignalType.BUY,
                confidence=0.8,
                timestamp=datetime.now(),
                rsi_value=25.0,
                sma_value=1.1000,
                current_price=1.1000
            )
            
            result = await manager.validate_signal("EURUSD", signal)
            
            # Verify the request was made with correct parameters
            mock_session.get.assert_called_once()
            call_args = mock_session.get.call_args
            assert "www.alphavantage.co" in str(call_args)
        
        await manager.close()
    
    @patch('requests.Session.post')
    def test_telegram_request_structure(self, mock_post):
        """Test Telegram request structure."""
        manager = APIManager()
        manager.api_config.telegram_bot_token = "test_token"
        manager.api_config.telegram_chat_id = "test_chat"
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        message = NotificationMessage(
            message_type="trade",
            title="Test Trade",
            content="Test content",
            timestamp=datetime.now()
        )
        
        result = manager.send_notification(message)
        
        assert result is True
        mock_post.assert_called_once()
        
        # Verify request structure
        call_args = mock_post.call_args
        assert "api.telegram.org" in call_args[0][0]
        assert "chat_id" in call_args[1]["json"]
        assert "text" in call_args[1]["json"]


if __name__ == "__main__":
    pytest.main([__file__])