from binance.client import Client
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import traceback
from config import SYMBOL, INTERVAL

class BinanceClient:
    def __init__(self):
        # Initialize client with US endpoint
        self.client = Client(tld='us')
        
    def get_klines(self, limit=100):
        """Fetch historical klines/candlestick data"""
        try:
            print("\nFetching historical klines...")
            print(f"Using interval: {INTERVAL}")
            print(f"Symbol: {SYMBOL}")
            
            # Convert BTC/USD to BTCUSDT for Binance
            symbol = SYMBOL.replace('/', '') + 'T'
            print(f"Converted symbol: {symbol}")
            
            # Get klines from Binance
            klines = self.client.get_klines(
                symbol=symbol,
                interval=INTERVAL,
                limit=limit
            )
            
            if not klines:
                print("No data received from Binance")
                return None
                
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'buy_base_volume',
                'buy_quote_volume', 'ignore'
            ])
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Convert string values to float
            df = df.astype({
                'open': float,
                'high': float,
                'low': float,
                'close': float,
                'volume': float,
                'quote_volume': float
            })
            
            # Calculate indicators
            df = self.calculate_indicators(df)
            
            print(f"Retrieved {len(df)} klines")
            
            # Print first and last bar for debugging
            if len(df) > 0:
                print("\nFirst bar:")
                print(f"Time: {df.iloc[0]['timestamp']}")
                print(f"Close: ${df.iloc[0]['close']:,.2f}")
                print(f"RSI: {df.iloc[0].get('rsi', 'N/A')}")
                
                print("\nLast bar:")
                print(f"Time: {df.iloc[-1]['timestamp']}")
                print(f"Close: ${df.iloc[-1]['close']:,.2f}")
                print(f"RSI: {df.iloc[-1].get('rsi', 'N/A')}")
            
            return df
            
        except Exception as e:
            print(f"Error fetching klines: {e}")
            print("\nFull error traceback:")
            print(traceback.format_exc())
            return None
            
    def get_current_price(self):
        """Get the current market price"""
        try:
            # Convert BTC/USD to BTCUSDT for Binance
            symbol = SYMBOL.replace('/', '') + 'T'
            
            # Get ticker price
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            if ticker:
                return float(ticker['price'])
            return None
        except Exception as e:
            print(f"Error getting current price: {e}")
            return None
            
    def calculate_indicators(self, df):
        """Calculate technical indicators"""
        try:
            # Calculate RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=5).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=5).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Calculate volume moving averages
            df['volume_ma_5'] = df['volume'].rolling(window=5).mean()
            df['volume_ma_20'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio_5'] = df['volume'] / df['volume_ma_5']
            
            # Calculate VWAP
            df['vwap'] = (df['quote_volume'].cumsum() / df['volume'].cumsum())
            
            # Calculate CVD (Cumulative Volume Delta)
            df['volume_delta'] = np.where(
                df['close'] >= df['open'],
                df['volume'],
                -df['volume']
            )
            df['cvd'] = df['volume_delta'].cumsum()
            
            # Calculate CVD moving averages
            df['cvd_ma5'] = df['cvd'].rolling(window=5).mean()
            df['cvd_ma20'] = df['cvd'].rolling(window=20).mean()
            
            return df
            
        except Exception as e:
            print(f"Error calculating indicators: {e}")
            return df 