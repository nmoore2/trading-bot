from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from config import ALPACA_API_KEY, ALPACA_API_SECRET, SYMBOL

def main():
    print("\n=== Alpaca API Connection Test ===")
    
    # Initialize client
    print("\nInitializing client...")
    client = CryptoHistoricalDataClient()
    
    print(f"\nRequesting current price for {SYMBOL}")
    
    try:
        # Get latest bar (no time parameters needed)
        print("\nSending request to Alpaca...")
        bars = client.get_crypto_bars(
            CryptoBarsRequest(
                symbol_or_symbols=SYMBOL,
                timeframe=TimeFrame.Minute,
                limit=1  # Just get the latest bar
            )
        )
        
        if bars is not None:
            print("\nResponse received!")
            df = bars.df.reset_index()
            
            if not df.empty:
                print("\nCurrent Market Data:")
                latest = df.iloc[-1]
                print(f"Price: ${latest['close']:,.2f}")
                print(f"Volume: {latest['volume']:.3f}")
                print(f"VWAP: ${latest.get('vwap', 0):,.2f}")
            else:
                print("\nNo data in response")
        else:
            print("\nNo response from API")
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        print("\nFull error traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    main() 