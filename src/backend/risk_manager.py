"""Risk management system for Pocket Option Trading Bot."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass

from .models import (
    TradeRequest, 
    TradeResult, 
    Balance, 
    ValidationResult,
    TradingStatus
)
from .config import TradingConfig


logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """Risk metrics for current trading session."""
    
    daily_loss: float
    daily_loss_percent: float
    consecutive_losses: int
    trades_today: int
    last_loss_time: Optional[datetime]
    is_paused: bool
    pause_reason: Optional[str]


class RiskManager:
    """Manages trading risk and position sizing."""
    
    def __init__(self, config: TradingConfig):
        """Initialize risk manager with configuration."""
        self.config = config
        self.trade_history: List[TradeResult] = []
        self.daily_start_balance: Optional[float] = None
        self.is_paused = False
        self.pause_reason: Optional[str] = None
        self.pause_until: Optional[datetime] = None
        
    def validate_trade_request(self, request: TradeRequest, balance: Balance) -> ValidationResult:
        """
        Validate a trade request against all risk management rules.
        
        Args:
            request: The trade request to validate
            balance: Current account balance
            
        Returns:
            ValidationResult with validation status and any error messages
        """
        logger.info(f"Validating trade request: {request.symbol} {request.direction} ${request.amount}")
        
        # Check if trading is paused
        if self.is_trading_paused():
            return ValidationResult(
                is_valid=False,
                error_message=f"Trading is paused: {self.pause_reason}"
            )
        
        # Validate trade amount against balance
        amount_validation = self._validate_trade_amount(request.amount, balance.available_balance)
        if not amount_validation.is_valid:
            return amount_validation
            
        # Check daily loss limits
        daily_limit_validation = self._validate_daily_limits(balance)
        if not daily_limit_validation.is_valid:
            return daily_limit_validation
            
        # Check consecutive losses
        consecutive_loss_validation = self._validate_consecutive_losses()
        if not consecutive_loss_validation.is_valid:
            return consecutive_loss_validation
            
        # Demo mode validation for new users
        demo_validation = self._validate_demo_mode(request)
        if not demo_validation.is_valid:
            return demo_validation
            
        logger.info("Trade request validation passed")
        return ValidationResult(is_valid=True)
    
    def calculate_position_size(self, balance: float, risk_percent: Optional[float] = None) -> float:
        """
        Calculate optimal position size based on account balance and risk percentage.
        
        Args:
            balance: Current account balance
            risk_percent: Risk percentage (defaults to config max_trade_percent)
            
        Returns:
            Calculated position size
        """
        if risk_percent is None:
            risk_percent = self.config.max_trade_percent
            
        # Ensure risk percent doesn't exceed maximum
        risk_percent = min(risk_percent, self.config.max_trade_percent)
        
        position_size = balance * (risk_percent / 100)
        
        # Apply minimum and maximum bounds
        min_trade = 1.0  # Minimum trade amount
        max_trade = balance * (self.config.max_trade_percent / 100)
        
        position_size = max(min_trade, min(position_size, max_trade))
        
        logger.info(f"Calculated position size: ${position_size:.2f} ({risk_percent}% of ${balance:.2f})")
        return round(position_size, 2)
    
    def check_daily_limits(self, current_balance: float) -> bool:
        """
        Check if daily loss limits have been exceeded.
        
        Args:
            current_balance: Current account balance
            
        Returns:
            True if within limits, False if limits exceeded
        """
        if self.daily_start_balance is None:
            self.daily_start_balance = current_balance
            return True
            
        daily_loss = self.daily_start_balance - current_balance
        daily_loss_percent = (daily_loss / self.daily_start_balance) * 100
        
        if daily_loss_percent >= self.config.max_daily_loss_percent:
            self._pause_trading(f"Daily loss limit exceeded: {daily_loss_percent:.2f}%")
            return False
            
        return True
    
    def should_pause_trading(self, recent_losses: int) -> bool:
        """
        Check if trading should be paused due to consecutive losses.
        
        Args:
            recent_losses: Number of recent consecutive losses
            
        Returns:
            True if trading should be paused
        """
        if recent_losses >= self.config.consecutive_loss_limit:
            self._pause_trading(f"Consecutive loss limit reached: {recent_losses} losses")
            return True
            
        return False
    
    def record_trade_result(self, trade_result: TradeResult) -> None:
        """
        Record a trade result for risk tracking.
        
        Args:
            trade_result: The completed trade result
        """
        self.trade_history.append(trade_result)
        
        # Keep only today's trades for performance
        today = datetime.now().date()
        self.trade_history = [
            trade for trade in self.trade_history 
            if trade.timestamp.date() == today
        ]
        
        # Check for consecutive losses
        consecutive_losses = self._count_consecutive_losses()
        if consecutive_losses >= self.config.consecutive_loss_limit:
            self.should_pause_trading(consecutive_losses)
            
        logger.info(f"Recorded trade result: {trade_result.trade_id} - {'WIN' if trade_result.is_win else 'LOSS'}")
    
    def get_risk_metrics(self, current_balance: float) -> RiskMetrics:
        """
        Get current risk metrics.
        
        Args:
            current_balance: Current account balance
            
        Returns:
            Current risk metrics
        """
        if self.daily_start_balance is None:
            self.daily_start_balance = current_balance
            
        daily_loss = max(0, self.daily_start_balance - current_balance)
        daily_loss_percent = (daily_loss / self.daily_start_balance) * 100 if self.daily_start_balance > 0 else 0
        
        consecutive_losses = self._count_consecutive_losses()
        trades_today = len(self.trade_history)
        
        last_loss_time = None
        for trade in reversed(self.trade_history):
            if not trade.is_win:
                last_loss_time = trade.timestamp
                break
                
        return RiskMetrics(
            daily_loss=daily_loss,
            daily_loss_percent=daily_loss_percent,
            consecutive_losses=consecutive_losses,
            trades_today=trades_today,
            last_loss_time=last_loss_time,
            is_paused=self.is_paused,
            pause_reason=self.pause_reason
        )
    
    def is_trading_paused(self) -> bool:
        """
        Check if trading is currently paused.
        
        Returns:
            True if trading is paused
        """
        # Check if pause has expired
        if self.pause_until and datetime.now() > self.pause_until:
            self._resume_trading()
            
        return self.is_paused
    
    def resume_trading(self) -> bool:
        """
        Manually resume trading (admin override).
        
        Returns:
            True if trading was resumed
        """
        if self.is_paused:
            self._resume_trading()
            logger.info("Trading manually resumed by user")
            return True
        return False
    
    def reset_daily_metrics(self, new_balance: float) -> None:
        """
        Reset daily metrics (typically called at start of new trading day).
        
        Args:
            new_balance: Starting balance for the new day
        """
        self.daily_start_balance = new_balance
        self.trade_history.clear()
        if self.is_paused and self.pause_reason and "Daily loss" in self.pause_reason:
            self._resume_trading()
        logger.info(f"Daily metrics reset with starting balance: ${new_balance:.2f}")
    
    def _validate_trade_amount(self, amount: float, available_balance: float) -> ValidationResult:
        """Validate trade amount against balance and limits."""
        if amount <= 0:
            return ValidationResult(
                is_valid=False,
                error_message="Trade amount must be positive"
            )
            
        if amount > available_balance:
            return ValidationResult(
                is_valid=False,
                error_message=f"Insufficient balance: ${amount:.2f} requested, ${available_balance:.2f} available"
            )
            
        max_trade_amount = available_balance * (self.config.max_trade_percent / 100)
        if amount > max_trade_amount:
            return ValidationResult(
                is_valid=False,
                error_message=f"Trade amount ${amount:.2f} exceeds maximum allowed ${max_trade_amount:.2f} ({self.config.max_trade_percent}% of balance)"
            )
            
        return ValidationResult(is_valid=True)
    
    def _validate_daily_limits(self, balance: Balance) -> ValidationResult:
        """Validate against daily loss limits."""
        if not self.check_daily_limits(balance.total_balance):
            daily_loss = self.daily_start_balance - balance.total_balance if self.daily_start_balance else 0
            daily_loss_percent = (daily_loss / self.daily_start_balance) * 100 if self.daily_start_balance else 0
            return ValidationResult(
                is_valid=False,
                error_message=f"Daily loss limit exceeded: {daily_loss_percent:.2f}% (max {self.config.max_daily_loss_percent}%)"
            )
        return ValidationResult(is_valid=True)
    
    def _validate_consecutive_losses(self) -> ValidationResult:
        """Validate against consecutive loss limits."""
        consecutive_losses = self._count_consecutive_losses()
        if consecutive_losses >= self.config.consecutive_loss_limit:
            return ValidationResult(
                is_valid=False,
                error_message=f"Consecutive loss limit reached: {consecutive_losses} losses (max {self.config.consecutive_loss_limit})"
            )
        return ValidationResult(is_valid=True)
    
    def _validate_demo_mode(self, request: TradeRequest) -> ValidationResult:
        """Validate demo mode requirements."""
        if self.config.demo_mode and not request.is_demo:
            return ValidationResult(
                is_valid=False,
                error_message="Real trading is disabled. System is in demo mode."
            )
        return ValidationResult(is_valid=True)
    
    def _count_consecutive_losses(self) -> int:
        """Count consecutive losses from most recent trades."""
        consecutive_losses = 0
        for trade in reversed(self.trade_history):
            if trade.is_win is False:
                consecutive_losses += 1
            elif trade.is_win is True:
                break
        return consecutive_losses
    
    def _pause_trading(self, reason: str, duration_minutes: int = 60) -> None:
        """Pause trading with specified reason and duration."""
        self.is_paused = True
        self.pause_reason = reason
        self.pause_until = datetime.now() + timedelta(minutes=duration_minutes)
        logger.warning(f"Trading paused: {reason} (until {self.pause_until})")
    
    def _resume_trading(self) -> None:
        """Resume trading."""
        self.is_paused = False
        self.pause_reason = None
        self.pause_until = None
        logger.info("Trading resumed")