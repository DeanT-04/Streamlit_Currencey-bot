"""Core data models for Pocket Option Trading Bot."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class SignalType(Enum):
    """Trading signal types."""
    BUY = "BUY"
    SELL = "SELL"


class TradeDirection(Enum):
    """Trade direction types."""
    CALL = "CALL"
    PUT = "PUT"


@dataclass
class MarketData:
    """Market data structure for candlestick information."""
    
    symbol: str
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    
    def __post_init__(self):
        """Validate market data after initialization."""
        # Check for negative values first
        if any(price < 0 for price in [self.open_price, self.high_price, self.low_price, self.close_price]):
            raise ValueError("Prices cannot be negative")
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")
        
        # Then check price relationships
        if self.high_price < max(self.open_price, self.close_price):
            raise ValueError("High price cannot be less than open or close price")
        if self.low_price > min(self.open_price, self.close_price):
            raise ValueError("Low price cannot be greater than open or close price")


@dataclass
class Signal:
    """Trading signal structure."""
    
    symbol: str
    signal_type: SignalType
    confidence: float
    timestamp: datetime
    rsi_value: float
    sma_value: float
    current_price: float
    
    def __post_init__(self):
        """Validate signal data after initialization."""
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        if not 0 <= self.rsi_value <= 100:
            raise ValueError("RSI value must be between 0 and 100")
        if self.sma_value < 0:
            raise ValueError("SMA value cannot be negative")
        if self.current_price < 0:
            raise ValueError("Current price cannot be negative")


@dataclass
class TradeRequest:
    """Trade request structure."""
    
    symbol: str
    direction: TradeDirection
    amount: float
    expiration_time: int
    is_demo: bool
    
    def __post_init__(self):
        """Validate trade request after initialization."""
        if self.amount <= 0:
            raise ValueError("Trade amount must be positive")
        if self.expiration_time <= 0:
            raise ValueError("Expiration time must be positive")


@dataclass
class TradeResult:
    """Trade result structure."""
    
    trade_id: str
    symbol: str
    direction: TradeDirection
    amount: float
    entry_price: float
    exit_price: Optional[float]
    profit_loss: Optional[float]
    is_win: Optional[bool]
    timestamp: datetime
    
    def __post_init__(self):
        """Validate trade result after initialization."""
        if self.amount <= 0:
            raise ValueError("Trade amount must be positive")
        if self.entry_price < 0:
            raise ValueError("Entry price cannot be negative")
        if self.exit_price is not None and self.exit_price < 0:
            raise ValueError("Exit price cannot be negative")


@dataclass
class Balance:
    """Account balance structure."""
    
    total_balance: float
    available_balance: float
    currency: str
    timestamp: datetime
    
    def __post_init__(self):
        """Validate balance data after initialization."""
        if self.total_balance < 0:
            raise ValueError("Total balance cannot be negative")
        if self.available_balance < 0:
            raise ValueError("Available balance cannot be negative")
        if self.available_balance > self.total_balance:
            raise ValueError("Available balance cannot exceed total balance")


@dataclass
class NotificationMessage:
    """Notification message structure."""
    
    message_type: str
    title: str
    content: str
    timestamp: datetime
    priority: str = "normal"
    
    def __post_init__(self):
        """Validate notification message after initialization."""
        valid_priorities = ["low", "normal", "high", "critical"]
        if self.priority not in valid_priorities:
            raise ValueError(f"Priority must be one of: {valid_priorities}")


@dataclass
class TradingStatus:
    """Trading engine status structure."""
    
    is_active: bool
    current_pairs: list[str]
    last_signal_time: Optional[datetime]
    last_trade_time: Optional[datetime]
    total_trades_today: int
    wins_today: int
    losses_today: int
    profit_loss_today: float
    
    def __post_init__(self):
        """Validate trading status after initialization."""
        if self.total_trades_today < 0:
            raise ValueError("Total trades cannot be negative")
        if self.wins_today < 0:
            raise ValueError("Wins cannot be negative")
        if self.losses_today < 0:
            raise ValueError("Losses cannot be negative")
        if self.wins_today + self.losses_today > self.total_trades_today:
            raise ValueError("Wins + losses cannot exceed total trades")


@dataclass
class PerformanceMetrics:
    """Performance metrics structure."""
    
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit_loss: float
    average_profit: float
    average_loss: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    
    def __post_init__(self):
        """Validate performance metrics after initialization."""
        if self.total_trades < 0:
            raise ValueError("Total trades cannot be negative")
        if self.winning_trades < 0:
            raise ValueError("Winning trades cannot be negative")
        if self.losing_trades < 0:
            raise ValueError("Losing trades cannot be negative")
        if self.winning_trades + self.losing_trades != self.total_trades:
            raise ValueError("Winning + losing trades must equal total trades")
        if not 0 <= self.win_rate <= 100:
            raise ValueError("Win rate must be between 0 and 100")


@dataclass
class ValidationResult:
    """Validation result structure."""
    
    is_valid: bool
    error_message: Optional[str] = None
    warnings: list[str] = None
    
    def __post_init__(self):
        """Initialize warnings list if None."""
        if self.warnings is None:
            self.warnings = []