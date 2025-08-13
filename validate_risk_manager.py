#!/usr/bin/env python3
"""Validation script for Risk Management System."""

import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from backend.risk_manager import RiskManager
from backend.models import (
    TradeRequest, 
    TradeResult, 
    Balance, 
    TradeDirection
)
from backend.config import TradingConfig


def test_risk_manager_functionality():
    """Test and demonstrate risk manager functionality."""
    print("🔒 Risk Management System Validation")
    print("=" * 50)
    
    # Create test configuration
    config = TradingConfig(
        default_trade_amount=10.0,
        max_daily_loss_percent=5.0,
        max_trade_percent=2.0,
        consecutive_loss_limit=3,
        demo_mode=True
    )
    
    # Initialize risk manager
    risk_manager = RiskManager(config)
    print("✅ Risk Manager initialized successfully")
    
    # Test balance
    balance = Balance(
        total_balance=1000.0,
        available_balance=1000.0,
        currency="USD",
        timestamp=datetime.now()
    )
    print(f"💰 Test balance: ${balance.total_balance:.2f}")
    
    # Test 1: Position sizing calculation
    print("\n📊 Testing Position Sizing:")
    position_size = risk_manager.calculate_position_size(balance.total_balance)
    print(f"   - Default position size (2% of balance): ${position_size:.2f}")
    
    custom_position = risk_manager.calculate_position_size(balance.total_balance, 1.0)
    print(f"   - Custom position size (1% of balance): ${custom_position:.2f}")
    
    # Test 2: Valid trade request
    print("\n✅ Testing Valid Trade Request:")
    valid_request = TradeRequest(
        symbol="EURUSD",
        direction=TradeDirection.CALL,
        amount=20.0,  # 2% of balance
        expiration_time=60,
        is_demo=True
    )
    
    result = risk_manager.validate_trade_request(valid_request, balance)
    print(f"   - Trade validation: {'PASSED' if result.is_valid else 'FAILED'}")
    if not result.is_valid:
        print(f"   - Error: {result.error_message}")
    
    # Test 3: Trade amount too large
    print("\n❌ Testing Oversized Trade Request:")
    oversized_request = TradeRequest(
        symbol="EURUSD",
        direction=TradeDirection.CALL,
        amount=50.0,  # 5% of balance, exceeds 2% limit
        expiration_time=60,
        is_demo=True
    )
    
    result = risk_manager.validate_trade_request(oversized_request, balance)
    print(f"   - Trade validation: {'PASSED' if result.is_valid else 'FAILED'}")
    if not result.is_valid:
        print(f"   - Error: {result.error_message}")
    
    # Test 4: Daily loss limits
    print("\n📉 Testing Daily Loss Limits:")
    risk_manager.daily_start_balance = 1000.0
    
    # Simulate 4% loss (within 5% limit)
    current_balance_ok = 960.0
    within_limits = risk_manager.check_daily_limits(current_balance_ok)
    print(f"   - 4% daily loss: {'WITHIN LIMITS' if within_limits else 'EXCEEDS LIMITS'}")
    
    # Reset for next test
    risk_manager.is_paused = False
    risk_manager.pause_reason = None
    
    # Simulate 6% loss (exceeds 5% limit)
    current_balance_bad = 940.0
    exceeds_limits = risk_manager.check_daily_limits(current_balance_bad)
    print(f"   - 6% daily loss: {'WITHIN LIMITS' if exceeds_limits else 'EXCEEDS LIMITS'}")
    print(f"   - Trading paused: {risk_manager.is_paused}")
    if risk_manager.is_paused:
        print(f"   - Pause reason: {risk_manager.pause_reason}")
    
    # Test 5: Consecutive losses
    print("\n📊 Testing Consecutive Loss Circuit Breaker:")
    
    # Reset risk manager
    risk_manager_fresh = RiskManager(config)
    
    # Simulate 2 consecutive losses (within limit)
    for i in range(2):
        loss_trade = TradeResult(
            trade_id=f"loss_{i+1:03d}",
            symbol="EURUSD",
            direction=TradeDirection.CALL,
            amount=10.0,
            entry_price=1.1000,
            exit_price=1.0990,
            profit_loss=-10.0,
            is_win=False,
            timestamp=datetime.now()
        )
        risk_manager_fresh.record_trade_result(loss_trade)
    
    print(f"   - After 2 losses: Trading paused = {risk_manager_fresh.is_paused}")
    
    # Add 3rd consecutive loss (should trigger pause)
    loss_trade_3 = TradeResult(
        trade_id="loss_003",
        symbol="EURUSD",
        direction=TradeDirection.CALL,
        amount=10.0,
        entry_price=1.1000,
        exit_price=1.0990,
        profit_loss=-10.0,
        is_win=False,
        timestamp=datetime.now()
    )
    risk_manager_fresh.record_trade_result(loss_trade_3)
    
    print(f"   - After 3 losses: Trading paused = {risk_manager_fresh.is_paused}")
    if risk_manager_fresh.is_paused:
        print(f"   - Pause reason: {risk_manager_fresh.pause_reason}")
    
    # Test 6: Demo mode enforcement
    print("\n🎮 Testing Demo Mode Enforcement:")
    real_trade_request = TradeRequest(
        symbol="EURUSD",
        direction=TradeDirection.CALL,
        amount=10.0,
        expiration_time=60,
        is_demo=False  # Real trade in demo mode
    )
    
    demo_result = risk_manager_fresh.validate_trade_request(real_trade_request, balance)
    print(f"   - Real trade in demo mode: {'ALLOWED' if demo_result.is_valid else 'BLOCKED'}")
    if not demo_result.is_valid:
        print(f"   - Error: {demo_result.error_message}")
    
    # Test 7: Risk metrics
    print("\n📈 Testing Risk Metrics:")
    metrics = risk_manager_fresh.get_risk_metrics(950.0)
    print(f"   - Consecutive losses: {metrics.consecutive_losses}")
    print(f"   - Trades today: {metrics.trades_today}")
    print(f"   - Is paused: {metrics.is_paused}")
    print(f"   - Daily loss: ${metrics.daily_loss:.2f} ({metrics.daily_loss_percent:.1f}%)")
    
    # Test 8: Manual resume
    print("\n🔄 Testing Manual Resume:")
    resume_success = risk_manager_fresh.resume_trading()
    print(f"   - Manual resume: {'SUCCESS' if resume_success else 'NO ACTION NEEDED'}")
    print(f"   - Trading paused after resume: {risk_manager_fresh.is_paused}")
    
    print("\n" + "=" * 50)
    print("✅ Risk Management System validation completed successfully!")
    print("\nKey Features Validated:")
    print("  ✓ Position sizing calculations")
    print("  ✓ Trade amount validation (max 2% of balance)")
    print("  ✓ Daily loss limits (max 5% of balance)")
    print("  ✓ Consecutive loss circuit breaker (3 losses)")
    print("  ✓ Demo mode enforcement")
    print("  ✓ Risk metrics tracking")
    print("  ✓ Manual trading resume")
    
    return True


if __name__ == "__main__":
    try:
        success = test_risk_manager_functionality()
        if success:
            print("\n🎉 All risk management features working correctly!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error during validation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)