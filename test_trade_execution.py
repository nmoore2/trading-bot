from alpaca_client import AlpacaClient
from trading_service import TradingService

def main():
    # Initialize clients
    alpaca = AlpacaClient()
    trading = TradingService(alpaca)
    
    # Create a test trading signal
    signal = {
        'side': 'BUY',
        'stop_loss': 64350.0,  # About 1% below current price
        'take_profit': 66300.0,  # About 2% above current price
        'data': {
            'price_action': {
                'daily_change': 2.5,
                'daily_range': 1200.0
            },
            'technical_indicators': {
                'rsi': 58,
                'macd': 'bullish',
                'ma_trend': 'upward'
            },
            'analysis': 'Strong bullish momentum with support at $64,350. RSI showing room for upside.'
        }
    }
    
    print("\nAttempting to execute trade with signal:")
    print(f"Side: {signal['side']}")
    print(f"Stop Loss: ${signal['stop_loss']:,.2f}")
    print(f"Take Profit: ${signal['take_profit']:,.2f}")
    print(f"Analysis: {signal['data']['analysis']}")
    
    # Try to execute the trade
    result = trading.execute_signal(signal)
    
    if result:
        print("\nTrade executed successfully!")
        print(f"Order ID: {result['order_id']}")
        print(f"Entry Price: ${result['entry_price']:,.2f}")
        print(f"Quantity: {result['quantity']}")
    else:
        print("\nTrade execution failed.")
        
if __name__ == "__main__":
    main() 