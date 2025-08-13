"""API Manager for Pocket Option Trading Bot."""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import aiohttp
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import (
    MarketData, Signal, TradeRequest, TradeResult, Balance, 
    NotificationMessage, TradeDirection, SignalType
)
from .config import get_config_manager


logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreaker:
    """Circuit breaker for API error handling."""
    
    failure_threshold: int = 5
    timeout: int = 60
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    
    def record_success(self) -> None:
        """Record a successful operation."""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
        
    def record_failure(self) -> None:
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            
    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
            
        if self.state == CircuitBreakerState.OPEN:
            if (self.last_failure_time and 
                datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout)):
                self.state = CircuitBreakerState.HALF_OPEN
                return True
            return False
            
        # HALF_OPEN state
        return True


@dataclass
class RateLimiter:
    """Rate limiter for API calls."""
    
    max_requests: int
    time_window: int  # seconds
    requests: List[datetime] = None
    
    def __post_init__(self):
        if self.requests is None:
            self.requests = []
    
    def can_make_request(self) -> bool:
        """Check if a request can be made."""
        now = datetime.now()
        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < timedelta(seconds=self.time_window)]
        
        return len(self.requests) < self.max_requests
    
    def record_request(self) -> None:
        """Record a new request."""
        self.requests.append(datetime.now())
    
    def wait_time(self) -> float:
        """Get time to wait before next request."""
        if self.can_make_request():
            return 0.0
            
        if not self.requests:
            return 0.0
            
        oldest_request = min(self.requests)
        wait_until = oldest_request + timedelta(seconds=self.time_window)
        wait_time = (wait_until - datetime.now()).total_seconds()
        return max(0.0, wait_time)


class APIManager:
    """Centralized API manager with connection pooling and error handling."""
    
    def __init__(self):
        """Initialize API manager."""
        self.config = get_config_manager()
        self.api_config = self.config.get_api_config()
        
        # Circuit breakers for different APIs
        self.pocket_option_breaker = CircuitBreaker()
        self.alpha_vantage_breaker = CircuitBreaker()
        self.telegram_breaker = CircuitBreaker()
        
        # Rate limiters
        self.pocket_option_limiter = RateLimiter(max_requests=60, time_window=60)  # 60 req/min
        self.alpha_vantage_limiter = RateLimiter(max_requests=5, time_window=60)   # 5 req/min
        self.telegram_limiter = RateLimiter(max_requests=30, time_window=60)       # 30 req/min
        
        # HTTP session with connection pooling
        self.session = self._create_session()
        
        # Async session for concurrent operations
        self._async_session: Optional[aiohttp.ClientSession] = None
        
        # Mock mode for testing
        self.mock_mode = False
        self.mock_responses = {}
        
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    async def _get_async_session(self) -> aiohttp.ClientSession:
        """Get or create async session."""
        if self._async_session is None or self._async_session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=20, limit_per_host=10)
            self._async_session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
        return self._async_session
    
    async def close(self) -> None:
        """Close all connections."""
        if self._async_session and not self._async_session.closed:
            await self._async_session.close()
        self.session.close()
    
    def set_mock_mode(self, enabled: bool, responses: Dict[str, Any] = None) -> None:
        """Enable/disable mock mode for testing."""
        self.mock_mode = enabled
        if responses:
            self.mock_responses = responses
    
    async def _execute_with_circuit_breaker(
        self, 
        breaker: CircuitBreaker, 
        limiter: RateLimiter,
        operation_name: str,
        operation_func
    ) -> Any:
        """Execute operation with circuit breaker and rate limiting."""
        if not breaker.can_execute():
            raise Exception(f"{operation_name} circuit breaker is OPEN")
        
        # Check rate limiting
        if not limiter.can_make_request():
            wait_time = limiter.wait_time()
            if wait_time > 0:
                logger.info(f"Rate limit reached for {operation_name}, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
        
        try:
            limiter.record_request()
            result = await operation_func()
            breaker.record_success()
            return result
            
        except Exception as e:
            breaker.record_failure()
            logger.error(f"{operation_name} failed: {str(e)}")
            raise
    
    # Pocket Option API Methods
    
    async def get_market_data(self, symbol: str, timeframe: str = "1m", limit: int = 50) -> List[MarketData]:
        """Get market data from Pocket Option API."""
        if self.mock_mode:
            return self._get_mock_market_data(symbol, limit)
        
        async def _fetch_market_data():
            # This is a placeholder implementation
            # In a real implementation, you would integrate with the actual Pocket Option API
            logger.info(f"Fetching market data for {symbol} with timeframe {timeframe}")
            
            # Simulate API call delay
            await asyncio.sleep(0.1)
            
            # Generate mock data for now
            return self._generate_mock_market_data(symbol, limit)
        
        return await self._execute_with_circuit_breaker(
            self.pocket_option_breaker,
            self.pocket_option_limiter,
            "Pocket Option Market Data",
            _fetch_market_data
        )
    
    async def place_trade(self, trade_request: TradeRequest) -> TradeResult:
        """Place a trade through Pocket Option API."""
        if self.mock_mode:
            return self._get_mock_trade_result(trade_request)
        
        async def _place_trade():
            logger.info(f"Placing trade: {trade_request.symbol} {trade_request.direction.value} ${trade_request.amount}")
            
            # Simulate API call delay
            await asyncio.sleep(0.2)
            
            # Generate mock trade result for now
            return self._generate_mock_trade_result(trade_request)
        
        return await self._execute_with_circuit_breaker(
            self.pocket_option_breaker,
            self.pocket_option_limiter,
            "Pocket Option Trade Execution",
            _place_trade
        )
    
    async def get_account_balance(self) -> Balance:
        """Get account balance from Pocket Option API."""
        if self.mock_mode:
            return self._get_mock_balance()
        
        async def _fetch_balance():
            logger.info("Fetching account balance")
            
            # Simulate API call delay
            await asyncio.sleep(0.1)
            
            # Generate mock balance for now
            return Balance(
                total_balance=1000.0,
                available_balance=950.0,
                currency="USD",
                timestamp=datetime.now()
            )
        
        return await self._execute_with_circuit_breaker(
            self.pocket_option_breaker,
            self.pocket_option_limiter,
            "Pocket Option Balance",
            _fetch_balance
        )
    
    # Alpha Vantage API Methods
    
    async def validate_signal(self, symbol: str, signal: Signal) -> bool:
        """Validate signal against Alpha Vantage data."""
        if self.mock_mode:
            return self._get_mock_signal_validation(signal)
        
        async def _validate_signal():
            logger.info(f"Validating signal for {symbol}")
            
            # Convert symbol format if needed (e.g., EURUSD -> EUR/USD)
            av_symbol = self._convert_symbol_for_alpha_vantage(symbol)
            
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "FX_INTRADAY",
                "from_symbol": av_symbol.split("/")[0],
                "to_symbol": av_symbol.split("/")[1],
                "interval": "1min",
                "apikey": self.api_config.alpha_vantage_api_key
            }
            
            session = await self._get_async_session()
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"Alpha Vantage API error: {response.status}")
                
                data = await response.json()
                
                # Check for API errors
                if "Error Message" in data:
                    raise Exception(f"Alpha Vantage error: {data['Error Message']}")
                
                if "Note" in data:
                    raise Exception("Alpha Vantage rate limit exceeded")
                
                # Validate signal against recent data
                return self._validate_signal_against_data(signal, data)
        
        return await self._execute_with_circuit_breaker(
            self.alpha_vantage_breaker,
            self.alpha_vantage_limiter,
            "Alpha Vantage Signal Validation",
            _validate_signal
        )
    
    # Telegram API Methods
    
    def send_notification(self, message: NotificationMessage) -> bool:
        """Send notification via Telegram."""
        if not self.api_config.telegram_bot_token or not self.api_config.telegram_chat_id:
            logger.warning("Telegram credentials not configured, skipping notification")
            return False
        
        if self.mock_mode:
            logger.info(f"Mock notification sent: {message.title}")
            return True
        
        try:
            if not self.telegram_breaker.can_execute():
                logger.error("Telegram circuit breaker is OPEN")
                return False
            
            if not self.telegram_limiter.can_make_request():
                wait_time = self.telegram_limiter.wait_time()
                if wait_time > 0:
                    logger.info(f"Telegram rate limit reached, waiting {wait_time:.2f}s")
                    time.sleep(wait_time)
            
            self.telegram_limiter.record_request()
            
            url = f"https://api.telegram.org/bot{self.api_config.telegram_bot_token}/sendMessage"
            
            text = f"*{message.title}*\n\n{message.content}"
            
            payload = {
                "chat_id": self.api_config.telegram_chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            
            response = self.session.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.telegram_breaker.record_success()
                logger.info(f"Notification sent successfully: {message.title}")
                return True
            else:
                self.telegram_breaker.record_failure()
                logger.error(f"Failed to send notification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.telegram_breaker.record_failure()
            logger.error(f"Error sending notification: {str(e)}")
            return False
    
    # Helper methods
    
    def _convert_symbol_for_alpha_vantage(self, symbol: str) -> str:
        """Convert symbol format for Alpha Vantage API."""
        # Convert EURUSD to EUR/USD format
        if len(symbol) == 6:
            return f"{symbol[:3]}/{symbol[3:]}"
        return symbol
    
    def _validate_signal_against_data(self, signal: Signal, av_data: Dict) -> bool:
        """Validate signal against Alpha Vantage data."""
        try:
            time_series = av_data.get("Time Series (1min)", {})
            if not time_series:
                logger.warning("No time series data from Alpha Vantage")
                return False
            
            # Get the most recent data point
            latest_time = max(time_series.keys())
            latest_data = time_series[latest_time]
            
            current_price = float(latest_data["4. close"])
            
            # Simple validation: check if current price is close to signal price
            price_diff_percent = abs(current_price - signal.current_price) / signal.current_price * 100
            
            # Allow up to 0.1% difference
            is_valid = price_diff_percent <= 0.1
            
            logger.info(f"Signal validation: price diff {price_diff_percent:.3f}%, valid: {is_valid}")
            return is_valid
            
        except Exception as e:
            logger.error(f"Error validating signal: {str(e)}")
            return False
    
    # Mock data generation methods for testing
    
    def _get_mock_market_data(self, symbol: str, limit: int) -> List[MarketData]:
        """Get mock market data for testing."""
        return self.mock_responses.get("market_data", self._generate_mock_market_data(symbol, limit))
    
    def _generate_mock_market_data(self, symbol: str, limit: int) -> List[MarketData]:
        """Generate mock market data."""
        import random
        
        data = []
        base_price = 1.1000  # Base price for EUR/USD
        current_time = datetime.now()
        
        for i in range(limit):
            # Generate realistic price movement
            price_change = random.uniform(-0.0010, 0.0010)
            base_price += price_change
            
            high = base_price + random.uniform(0, 0.0005)
            low = base_price - random.uniform(0, 0.0005)
            open_price = base_price + random.uniform(-0.0003, 0.0003)
            close_price = base_price + random.uniform(-0.0003, 0.0003)
            
            data.append(MarketData(
                symbol=symbol,
                timestamp=current_time - timedelta(minutes=limit-i),
                open_price=open_price,
                high_price=max(high, open_price, close_price),
                low_price=min(low, open_price, close_price),
                close_price=close_price,
                volume=random.uniform(1000, 10000)
            ))
        
        return data
    
    def _get_mock_trade_result(self, trade_request: TradeRequest) -> TradeResult:
        """Get mock trade result for testing."""
        return self.mock_responses.get("trade_result", self._generate_mock_trade_result(trade_request))
    
    def _generate_mock_trade_result(self, trade_request: TradeRequest) -> TradeResult:
        """Generate mock trade result."""
        import random
        
        return TradeResult(
            trade_id=f"mock_trade_{int(time.time())}",
            symbol=trade_request.symbol,
            direction=trade_request.direction,
            amount=trade_request.amount,
            entry_price=1.1000 + random.uniform(-0.001, 0.001),
            exit_price=None,  # Will be set when trade closes
            profit_loss=None,  # Will be calculated when trade closes
            is_win=None,  # Will be determined when trade closes
            timestamp=datetime.now()
        )
    
    def _get_mock_balance(self) -> Balance:
        """Get mock balance for testing."""
        return self.mock_responses.get("balance", Balance(
            total_balance=1000.0,
            available_balance=950.0,
            currency="USD",
            timestamp=datetime.now()
        ))
    
    def _get_mock_signal_validation(self, signal: Signal) -> bool:
        """Get mock signal validation for testing."""
        return self.mock_responses.get("signal_validation", True)


# Global API manager instance
_api_manager: Optional[APIManager] = None


async def get_api_manager() -> APIManager:
    """Get or create the global API manager instance."""
    global _api_manager
    if _api_manager is None:
        _api_manager = APIManager()
    return _api_manager


async def close_api_manager() -> None:
    """Close the global API manager instance."""
    global _api_manager
    if _api_manager:
        await _api_manager.close()
        _api_manager = None