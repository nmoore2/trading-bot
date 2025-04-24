from alpaca_client import AlpacaClient
from trading_service import TradingService

def create_dummy_signal():
    """Create a dummy trading signal with strong buy conditions"""
    return {
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

def create_dummy_gpt_analysis():
    """Create a dummy GPT analysis recommending a trade"""
    return """
Based on the current market conditions, this setup presents a strong trading opportunity:

1. Strong momentum with price showing clear upward movement
2. Volume is significantly above average (2.5x)
3. RSI at 65.5 shows strong momentum without being overbought
4. Risk/reward ratio of 2.0 meets our minimum criteria

RECOMMENDATION: ENTER LONG position with strict stop loss at $92,800.
Risk is well-defined and multiple factors align for a potential upward move.
"""

def test_trade_execution():
    print("\nTesting trade execution with dummy signal...")
    
    # Initialize components
    client = AlpacaClient()
    trading = TradingService(client)
    
    # Create dummy signal and analysis
    trade_info = create_dummy_signal()
    gpt_analysis = create_dummy_gpt_analysis()
    
    # Try to execute the trade
    print("\nAttempting to execute trade...")
    trade = trading.execute_signal(trade_info, gpt_analysis)
    
    if trade:
        print("\n✓ Trade execution test successful!")
        print("Trade details saved to trades.json")
    else:
        print("\n✗ Trade execution test failed")

if __name__ == "__main__":
    test_trade_execution() 