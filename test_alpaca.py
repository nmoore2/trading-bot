from alpaca_client import AlpacaClient
from config import SYMBOL
import pandas as pd
import time

def test_market_data():
    print(f"\nTesting market data fetching for {SYMBOL}...")
    client = AlpacaClient()
    
    # Test getting klines
    df = client.get_klines(limit=5)
    if df is not None and not df.empty:
        print("\n✓ Successfully fetched market data:")
        print("\nLatest 5 candles:")
        pd.set_option('display.float_format', lambda x: '%.2f' % x)
        print(df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail())
    else:
        print("✗ Failed to fetch market data")
    
    # Test getting account info
    print("\nTesting account information...")
    balance = client.get_account_balance()
    if balance:
        print("\n✓ Successfully fetched account info:")
        print(f"Portfolio Value: ${balance['portfolio_value']:,.2f}")
        print(f"Buying Power: ${balance['buying_power']:,.2f}")
        print(f"Cash: ${balance['cash']:,.2f}")
    else:
        print("✗ Failed to fetch account information")
    
    return client

def test_trade_cycle(client):
    print("\nTesting complete trade cycle...")
    
    # Place a small market buy order (0.001 BTC)
    print("\n1. Placing market buy order...")
    buy_order = client.place_market_order('BUY', 0.001)
    if not buy_order:
        print("✗ Failed to place buy order")
        return
    
    print("✓ Buy order placed successfully")
    
    # Wait and check position with retries
    print("\n2. Checking position (with retries)...")
    max_retries = 3
    position = None
    
    for i in range(max_retries):
        time.sleep(5)  # Wait between checks
        position = client.get_position()
        if position:
            print("✓ Position opened successfully:")
            print(f"Quantity: {position['qty']} {SYMBOL}")
            print(f"Entry Price: ${float(position['avg_entry_price']):,.2f}")
            print(f"Market Value: ${float(position['market_value']):,.2f}")
            break
        print(f"Attempt {i+1}/{max_retries}: Waiting for position to be visible...")
    
    if not position:
        print("✗ Failed to confirm position after multiple attempts")
        return
    
    time.sleep(5)  # Small delay before selling
    
    # Close position
    print("\n3. Closing position...")
    result = client.close_position()
    if result:
        print("✓ Position closed successfully")
    else:
        print("✗ Failed to close position")
        return
    
    # Verify position is closed with retries
    print("\n4. Verifying position closure...")
    for i in range(max_retries):
        time.sleep(5)  # Wait between checks
        final_position = client.get_position()
        if not final_position:
            print("✓ Position fully closed")
            break
        print(f"Attempt {i+1}/{max_retries}: Waiting for position to close...")
    else:
        print("✗ Position still open after multiple attempts")
        return
    
    print("\n✓ Complete trade cycle test successful!")

if __name__ == "__main__":
    client = test_market_data()
    test_trade_cycle(client) 