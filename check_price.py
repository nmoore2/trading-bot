from alpaca_client import AlpacaClient
from config import SYMBOL
import pandas as pd
from datetime import datetime, timezone, timedelta

def main():
    print(f"\nChecking current price for {SYMBOL}...")
    
    # Use actual system time
    now = datetime.now(timezone.utc)
    print(f"Current UTC time: {now}")
    
    client = AlpacaClient()
    
    # Get latest data
    df = client.get_klines(limit=1)
    if df is not None and not df.empty:
        current = df.iloc[-1]
        print("\nCurrent Market Data:")
        print(f"Bar Time: {current['timestamp']}")
        print(f"Price: ${current['close']:,.2f}")
        print(f"OHLC: ${current['open']:,.2f} / ${current['high']:,.2f} / ${current['low']:,.2f} / ${current['close']:,.2f}")
        print(f"Volume: {current['volume']:.3f}")
        print(f"VWAP: ${current.get('vwap', 0):,.2f}")
        
        # Print raw DataFrame info for debugging
        print("\nRaw DataFrame Info:")
        print(df.dtypes)
        print("\nAll DataFrame Columns:")
        print(df.columns.tolist())
    else:
        print("Failed to fetch market data")

if __name__ == "__main__":
    main() 