"""Signal Processing Engine for Pocket Option Trading Bot."""

import logging
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .models import MarketData, Signal, SignalType
from .api_manager import get_api_manager


logger = logging.getLogger(__name__)


@dataclass
class TechnicalIndicators:
    """Container for technical indicator values."""
    
    rsi: float
    sma: float
    current_price: float
    timestamp: datetime


class SignalProcessor:
    """Signal processing engine with RSI/SMA crossover strategy."""
    
    def __init__(self, rsi_period: int = 14, sma_period: int = 20):
        """
        Initialize signal processor.
        
        Args:
            rsi_period: Period for RSI calculation (default 14)
            sma_period: Period for SMA calculation (default 20)
        """
        self.rsi_period = rsi_period
        self.sma_period = sma_period
        self.api_manager = None
        
        # Signal generation thresholds
        self.rsi_oversold_threshold = 30
        self.rsi_overbought_threshold = 70
        
        # Confidence scoring weights
        self.rsi_weight = 0.4
        self.sma_weight = 0.3
        self.validation_weight = 0.3
        
        logger.info(f"SignalProcessor initialized with RSI period: {rsi_period}, SMA period: {sma_period}")
    
    async def _get_api_manager(self):
        """Get API manager instance."""
        if self.api_manager is None:
            self.api_manager = await get_api_manager()
        return self.api_manager
    
    def calculate_rsi(self, prices: List[float], period: int = None) -> float:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            prices: List of closing prices (most recent last)
            period: RSI period (default uses instance period)
            
        Returns:
            RSI value between 0 and 100
            
        Raises:
            ValueError: If insufficient data or invalid parameters
        """
        if period is None:
            period = self.rsi_period
            
        if len(prices) < period + 1:
            raise ValueError(f"Need at least {period + 1} prices for RSI calculation, got {len(prices)}")
        
        if period <= 0:
            raise ValueError("RSI period must be positive")
        
        if not prices or any(price <= 0 for price in prices):
            raise ValueError("All prices must be positive")
        
        # Calculate price changes
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Separate gains and losses
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        # Calculate initial average gain and loss
        if len(gains) < period:
            raise ValueError(f"Insufficient data for RSI calculation")
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Calculate RSI using Wilder's smoothing method
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        # Avoid division by zero
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        logger.debug(f"RSI calculated: {rsi:.2f} (avg_gain: {avg_gain:.6f}, avg_loss: {avg_loss:.6f})")
        return rsi
    
    def calculate_sma(self, prices: List[float], period: int = None) -> float:
        """
        Calculate Simple Moving Average (SMA).
        
        Args:
            prices: List of closing prices (most recent last)
            period: SMA period (default uses instance period)
            
        Returns:
            SMA value
            
        Raises:
            ValueError: If insufficient data or invalid parameters
        """
        if period is None:
            period = self.sma_period
            
        if len(prices) < period:
            raise ValueError(f"Need at least {period} prices for SMA calculation, got {len(prices)}")
        
        if period <= 0:
            raise ValueError("SMA period must be positive")
        
        if not prices or any(price <= 0 for price in prices):
            raise ValueError("All prices must be positive")
        
        # Calculate SMA using the most recent 'period' prices
        recent_prices = prices[-period:]
        sma = sum(recent_prices) / period
        
        logger.debug(f"SMA calculated: {sma:.5f} (period: {period})")
        return sma
    
    def calculate_technical_indicators(self, market_data: List[MarketData]) -> TechnicalIndicators:
        """
        Calculate all technical indicators from market data.
        
        Args:
            market_data: List of market data (chronologically ordered, most recent last)
            
        Returns:
            TechnicalIndicators object with calculated values
            
        Raises:
            ValueError: If insufficient data
        """
        if not market_data:
            raise ValueError("Market data cannot be empty")
        
        # Extract closing prices
        prices = [candle.close_price for candle in market_data]
        
        # Ensure we have enough data for both indicators
        min_required = max(self.rsi_period + 1, self.sma_period)
        if len(prices) < min_required:
            raise ValueError(f"Need at least {min_required} data points, got {len(prices)}")
        
        # Calculate indicators
        rsi = self.calculate_rsi(prices)
        sma = self.calculate_sma(prices)
        current_price = prices[-1]
        
        return TechnicalIndicators(
            rsi=rsi,
            sma=sma,
            current_price=current_price,
            timestamp=market_data[-1].timestamp
        )
    
    def generate_signal(self, market_data: List[MarketData]) -> Optional[Signal]:
        """
        Generate trading signal based on RSI/SMA crossover strategy.
        
        Strategy Rules:
        - BUY (CALL): RSI < 30 (oversold) AND current_price > SMA (uptrend)
        - SELL (PUT): RSI > 70 (overbought) AND current_price < SMA (downtrend)
        
        Args:
            market_data: List of market data (chronologically ordered, most recent last)
            
        Returns:
            Signal object if conditions are met, None otherwise
        """
        try:
            if not market_data:
                logger.warning("No market data provided for signal generation")
                return None
            
            # Calculate technical indicators
            indicators = self.calculate_technical_indicators(market_data)
            
            symbol = market_data[-1].symbol
            signal_type = None
            
            # Apply signal generation rules
            if (indicators.rsi < self.rsi_oversold_threshold and 
                indicators.current_price > indicators.sma):
                signal_type = SignalType.BUY
                logger.info(f"BUY signal generated for {symbol}: RSI={indicators.rsi:.2f}, Price={indicators.current_price:.5f} > SMA={indicators.sma:.5f}")
                
            elif (indicators.rsi > self.rsi_overbought_threshold and 
                  indicators.current_price < indicators.sma):
                signal_type = SignalType.SELL
                logger.info(f"SELL signal generated for {symbol}: RSI={indicators.rsi:.2f}, Price={indicators.current_price:.5f} < SMA={indicators.sma:.5f}")
            
            if signal_type is None:
                logger.debug(f"No signal generated for {symbol}: RSI={indicators.rsi:.2f}, Price={indicators.current_price:.5f}, SMA={indicators.sma:.5f}")
                return None
            
            # Calculate initial confidence score
            confidence = self.calculate_signal_confidence(indicators, signal_type)
            
            signal = Signal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                timestamp=indicators.timestamp,
                rsi_value=indicators.rsi,
                sma_value=indicators.sma,
                current_price=indicators.current_price
            )
            
            logger.info(f"Signal generated: {signal.signal_type.value} {signal.symbol} with confidence {signal.confidence:.3f}")
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal: {str(e)}")
            return None
    
    def calculate_signal_confidence(self, indicators: TechnicalIndicators, signal_type: SignalType) -> float:
        """
        Calculate confidence score for a signal based on technical indicators.
        
        Confidence factors:
        - RSI strength: How far RSI is from neutral (50)
        - SMA divergence: How far price is from SMA
        - Signal clarity: How well conditions are met
        
        Args:
            indicators: Technical indicators
            signal_type: Type of signal (BUY/SELL)
            
        Returns:
            Confidence score between 0 and 1
        """
        try:
            # RSI confidence component
            if signal_type == SignalType.BUY:
                # For BUY signals, lower RSI is better (more oversold)
                rsi_confidence = (self.rsi_oversold_threshold - indicators.rsi) / self.rsi_oversold_threshold
            else:  # SELL
                # For SELL signals, higher RSI is better (more overbought)
                rsi_confidence = (indicators.rsi - self.rsi_overbought_threshold) / (100 - self.rsi_overbought_threshold)
            
            # Clamp RSI confidence between 0 and 1
            rsi_confidence = max(0, min(1, rsi_confidence))
            
            # SMA divergence confidence component
            price_sma_diff = abs(indicators.current_price - indicators.sma)
            price_sma_percent = price_sma_diff / indicators.sma
            
            # Higher divergence gives higher confidence (up to 1% divergence = max confidence)
            sma_confidence = min(1.0, price_sma_percent / 0.01)
            
            # Combine confidence components
            total_confidence = (
                rsi_confidence * self.rsi_weight +
                sma_confidence * self.sma_weight +
                0.5 * self.validation_weight  # Base validation confidence (will be updated after API validation)
            )
            
            # Ensure confidence is between 0 and 1
            total_confidence = max(0, min(1, total_confidence))
            
            logger.debug(f"Confidence calculation: RSI={rsi_confidence:.3f}, SMA={sma_confidence:.3f}, Total={total_confidence:.3f}")
            return total_confidence
            
        except Exception as e:
            logger.error(f"Error calculating signal confidence: {str(e)}")
            return 0.5  # Default confidence
    
    async def validate_signal_with_alpha_vantage(self, signal: Signal) -> float:
        """
        Validate signal against Alpha Vantage data and update confidence.
        
        Args:
            signal: Signal to validate
            
        Returns:
            Updated confidence score
        """
        try:
            api_manager = await self._get_api_manager()
            is_valid = await api_manager.validate_signal(signal.symbol, signal)
            
            if is_valid:
                # Increase confidence for validated signals
                validation_boost = 0.2
                new_confidence = min(1.0, signal.confidence + validation_boost)
                logger.info(f"Signal validated by Alpha Vantage, confidence boosted from {signal.confidence:.3f} to {new_confidence:.3f}")
                return new_confidence
            else:
                # Decrease confidence for invalidated signals
                validation_penalty = 0.3
                new_confidence = max(0.0, signal.confidence - validation_penalty)
                logger.warning(f"Signal invalidated by Alpha Vantage, confidence reduced from {signal.confidence:.3f} to {new_confidence:.3f}")
                return new_confidence
                
        except Exception as e:
            logger.error(f"Error validating signal with Alpha Vantage: {str(e)}")
            # Return original confidence if validation fails
            return signal.confidence
    
    async def process_market_data_and_generate_signal(self, symbol: str, timeframe: str = "1m") -> Optional[Signal]:
        """
        Fetch market data and generate signal in one operation.
        
        Args:
            symbol: Currency pair symbol
            timeframe: Timeframe for market data
            
        Returns:
            Generated signal or None
        """
        try:
            api_manager = await self._get_api_manager()
            
            # Fetch enough market data for calculations
            required_candles = max(self.rsi_period + 1, self.sma_period) + 10  # Extra buffer
            market_data = await api_manager.get_market_data(symbol, timeframe, required_candles)
            
            if not market_data:
                logger.warning(f"No market data received for {symbol}")
                return None
            
            # Generate signal
            signal = self.generate_signal(market_data)
            
            if signal:
                # Validate signal with Alpha Vantage
                updated_confidence = await self.validate_signal_with_alpha_vantage(signal)
                
                # Create new signal with updated confidence
                validated_signal = Signal(
                    symbol=signal.symbol,
                    signal_type=signal.signal_type,
                    confidence=updated_confidence,
                    timestamp=signal.timestamp,
                    rsi_value=signal.rsi_value,
                    sma_value=signal.sma_value,
                    current_price=signal.current_price
                )
                
                return validated_signal
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing market data for {symbol}: {str(e)}")
            return None
    
    def get_signal_strength_description(self, confidence: float) -> str:
        """
        Get human-readable description of signal strength.
        
        Args:
            confidence: Confidence score between 0 and 1
            
        Returns:
            String description of signal strength
        """
        if confidence >= 0.8:
            return "Very Strong"
        elif confidence >= 0.6:
            return "Strong"
        elif confidence >= 0.4:
            return "Moderate"
        elif confidence >= 0.2:
            return "Weak"
        else:
            return "Very Weak"
    
    def update_parameters(self, rsi_period: int = None, sma_period: int = None, 
                         rsi_oversold: int = None, rsi_overbought: int = None) -> None:
        """
        Update signal processor parameters.
        
        Args:
            rsi_period: New RSI period
            sma_period: New SMA period
            rsi_oversold: New RSI oversold threshold
            rsi_overbought: New RSI overbought threshold
        """
        if rsi_period is not None:
            if rsi_period <= 0:
                raise ValueError("RSI period must be positive")
            self.rsi_period = rsi_period
            logger.info(f"RSI period updated to {rsi_period}")
        
        if sma_period is not None:
            if sma_period <= 0:
                raise ValueError("SMA period must be positive")
            self.sma_period = sma_period
            logger.info(f"SMA period updated to {sma_period}")
        
        if rsi_oversold is not None:
            if not 0 <= rsi_oversold <= 100:
                raise ValueError("RSI oversold threshold must be between 0 and 100")
            self.rsi_oversold_threshold = rsi_oversold
            logger.info(f"RSI oversold threshold updated to {rsi_oversold}")
        
        if rsi_overbought is not None:
            if not 0 <= rsi_overbought <= 100:
                raise ValueError("RSI overbought threshold must be between 0 and 100")
            self.rsi_overbought_threshold = rsi_overbought
            logger.info(f"RSI overbought threshold updated to {rsi_overbought}")
        
        # Validate threshold relationship
        if self.rsi_oversold_threshold >= self.rsi_overbought_threshold:
            raise ValueError("RSI oversold threshold must be less than overbought threshold")


# Global signal processor instance
_signal_processor: Optional[SignalProcessor] = None


def get_signal_processor(rsi_period: int = 14, sma_period: int = 20) -> SignalProcessor:
    """
    Get or create the global signal processor instance.
    
    Args:
        rsi_period: RSI period (only used for initial creation)
        sma_period: SMA period (only used for initial creation)
        
    Returns:
        SignalProcessor instance
    """
    global _signal_processor
    if _signal_processor is None:
        _signal_processor = SignalProcessor(rsi_period, sma_period)
    return _signal_processor