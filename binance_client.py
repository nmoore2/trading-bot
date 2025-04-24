from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd
from datetime import datetime, timedelta, timezone
from config import SYMBOL, INTERVAL
import time
import traceback
from indicators import TechnicalIndicators

class BinanceClient:
    def __init__(self):
        # Initialize Binance client with US endpoint
        self.client = Client(tld='us')  # Use Binance.US
        
        # Map our interval to Binance's interval
        self.interval_map = {
            '1m': Client.KLINE_INTERVAL_1MINUTE,
            '5m': Client.KLINE_INTERVAL_5MINUTE,
            '15m': Client.KLINE_INTERVAL_15MINUTE,
            '1h': Client.KLINE_INTERVAL_1HOUR,
            '1d': Client.KLINE_INTERVAL_1DAY
        }
        
    def get_klines(self, limit=20):
        """Fetch historical klines (candlestick data)"""
        try:
            print("\nFetching historical klines...")
            
            # Convert symbol to Binance format
            binance_symbol = SYMBOL.replace('/', '') + 'T'  # Add 'T' for Binance.US
            print(f"Using Binance.US symbol: {binance_symbol}")
            
            print("Requesting data from Binance...")
            # Fetch klines from Binance
            klines = self.client.get_klines(
                symbol=binance_symbol,
                interval=self.interval_map[INTERVAL],
                limit=limit
            )

            if not klines:
                print("No data received from Binance")
                return None
                
            print("Converting to DataFrame...")
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            # Convert data types
            df = df.astype({
                'timestamp': 'int64',
                'open': 'float64',
                'high': 'float64',
                'low': 'float64',
                'close': 'float64',
                'volume': 'float64',
                'quote_volume': 'float64',
                'trades': 'int64'
            })
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Use quote_volume instead of base volume
            df['volume'] = df['quote_volume']
            
            # Remove any bars with zero volume or price
            df = df[(df['volume'] > 0) & (df['close'] > 0)]
            
            if len(df) == 0:
                print("No valid data after filtering")
                return None
                
            # Calculate all indicators
            print("Calculating indicators...")
            df = TechnicalIndicators.calculate_all_indicators(df)
            
            print(f"Retrieved {len(df)} bars")
            
            # Print first and last bar for debugging
            if len(df) > 0:
                print("\nFirst bar:")
                print(f"Time: {df.iloc[0]['timestamp']}")
                print(f"Close: ${df.iloc[0]['close']:,.2f}")
                print(f"Volume: ${df.iloc[0]['volume']:,.2f}")
                print(f"RSI: {df.iloc[0]['rsi']:.1f}")
                
                print("\nLast bar:")
                print(f"Time: {df.iloc[-1]['timestamp']}")
                print(f"Close: ${df.iloc[-1]['close']:,.2f}")
                print(f"Volume: ${df.iloc[-1]['volume']:,.2f}")
                print(f"RSI: {df.iloc[-1]['rsi']:.1f}")

            return df

        except Exception as e:
            print(f"Error fetching klines: {e}")
            import traceback
            print("\nFull error traceback:")
            print(traceback.format_exc())
            return None
            
    def get_current_price(self):
        """Get the current market price for the symbol"""
        try:
            # Convert BTC/USD to BTCUSDT for Binance.US
            binance_symbol = SYMBOL.replace('/', '') + 'T'  # Add 'T' for Binance.US
            
            # Get ticker price
            ticker = self.client.get_symbol_ticker(symbol=binance_symbol)
            if ticker:
                return float(ticker['price'])
            return None
        except Exception as e:
            print(f"Error getting current price: {e}")
            return None

    def get_open_interest(self):
        """Get open interest data from Binance"""
        try:
            # Convert symbol format for Binance.US
            binance_symbol = SYMBOL.replace('/', '') + 'T'  # Add 'T' for Binance.US
            
            # Get ticker data which includes 24h volume
            ticker = self.client.get_ticker(symbol=binance_symbol)
            
            return {
                'symbol': SYMBOL,
                'open_interest': float(ticker['volume']),  # Using 24h volume as a proxy
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            print(f"Error getting open interest: {e}")
            return None 