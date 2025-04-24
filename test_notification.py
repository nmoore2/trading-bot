from notification_service import NotificationService
from datetime import datetime
import time

def test_notifications():
    print("\nTesting trading notifications...")
    notifier = NotificationService()
    
    # Create test trade data
    trade_info = {
        'signal_strength': 85.0,
        'signals': {
            'price_above_vwap': True,
            'vwap_cross_up': True,
            'rsi_cross_50': True,
            'volume_rising': True,
            'strong_volume': True,
            'momentum_positive': True
        },
        'levels': {
            'entry': 93000.00,
            'stop_loss': 92800.00,
            'target': 93400.00,
            'risk_reward_ratio': 2.0
        },
        'metrics': {
            'rsi': 65.5,
            'volume_ratio': 2.5,
            'price_momentum': 0.8
        }
    }
    
    gpt_analysis = """
Based on the current market conditions, this setup presents a strong trading opportunity:
1. Strong momentum with price showing clear upward movement
2. Volume is significantly above average (2.5x)
3. RSI at 65.5 shows strong momentum without being overbought
4. Risk/reward ratio of 2.0 meets our minimum criteria
RECOMMENDATION: ENTER LONG position with strict stop loss at $92,800."""

    executed_trade = {
        'quantity': 0.5,
        'entry_price': 93000.00,
        'stop_loss': 92800.00,
        'target': 93400.00,
        'entry_time': datetime.now().isoformat(),
        'exit_time': datetime.now().isoformat(),
        'pnl': 150.25,
        'pnl_percent': 0.32
    }

    # Test 1: Signal with execution
    print("\n1. Testing signal notification with trade execution...")
    result = notifier.send_trading_signal(trade_info, gpt_analysis, executed_trade)
    if result:
        print("✓ Signal notification sent")
    else:
        print("✗ Failed to send signal notification")

    # Wait 3 seconds
    print("Waiting...")
    time.sleep(3)

    # Test 2: Trade closure
    print("\n2. Testing trade closure notification...")
    result = notifier.send_trade_closed(
        trade=executed_trade,
        exit_price=93300.50,
        reason="Target reached"
    )
    if result:
        print("✓ Trade closure notification sent")
    else:
        print("✗ Failed to send closure notification")

    # Wait 3 seconds
    print("Waiting...")
    time.sleep(3)

    # Test 3: Error notification
    print("\n3. Testing error notification...")
    result = notifier.send_error("Test error message: Unable to fetch market data")
    if result:
        print("✓ Error notification sent")
    else:
        print("✗ Failed to send error notification")

if __name__ == "__main__":
    test_notifications() 