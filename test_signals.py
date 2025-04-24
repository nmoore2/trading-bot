from alpaca_client import AlpacaClient
from indicators import TechnicalIndicators
import pandas as pd
import time

def main():
    # Initialize clients
    client = AlpacaClient()
    indicators = TechnicalIndicators()
    
    print("\n=== Testing Signal Logic ===")
    
    # Get recent market data
    print("\nFetching market data...")
    klines = client.get_klines(limit=20)  # Get last 20 candles
    
    if not klines:
        print("✗ Failed to fetch market data")
        return
        
    # Convert to DataFrame
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.astype({
        'open': float,
        'high': float,
        'low': float,
        'close': float,
        'volume': float
    })
    
    # Calculate all indicators
    print("\nCalculating technical indicators...")
    df = indicators.calculate_all_indicators(df)
    
    # Check for long setup
    print("\nChecking for long setup...")
    setup = indicators.check_long_setup(df)
    
    if setup:
        print("\n✓ Long setup detected!")
        print("\nTrade Parameters:")
        print(f"Entry: ${setup['entry']:,.2f}")
        print(f"Stop Loss: ${setup['stop_loss']:,.2f}")
        print(f"Take Profit: ${setup['take_profit']:,.2f}")
        
        # Optional: Execute test trade
        print("\nWould you like to execute a test trade? (y/n)")
        if input().lower() == 'y':
            print("\nExecuting test trade...")
            order = client.place_market_order('BUY', 0.001)  # Small test quantity
            
            if order:
                print("✓ Test trade executed")
                print("\nWaiting 5 seconds to check position...")
                time.sleep(5)
                
                position = client.get_position()
                if position:
                    print("\nPosition opened:")
                    print(f"Quantity: {position['qty']}")
                    print(f"Entry Price: ${float(position['avg_entry_price']):,.2f}")
                    print(f"Market Value: ${float(position['market_value']):,.2f}")
                    
                    print("\nClosing position...")
                    if client.close_position():
                        print("✓ Position closed")
                    else:
                        print("✗ Failed to close position")
                else:
                    print("✗ No position found")
            else:
                print("✗ Failed to execute test trade")
    else:
        print("\n✗ No long setup detected")

if __name__ == "__main__":
    main() 