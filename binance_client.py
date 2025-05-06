from binance.client import Client
from binance.enums import FuturesType
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import traceback
from config import SYMBOL, INTERVAL
from indicators import TechnicalIndicators

class BinanceClient:
    def __init__(self):
        self.client = Client(None, None, tld='us')  # Spot client
        self.futures_client = Client(None, None, tld='com')  # Futures client (default tld)
        
    def get_klines(self, limit=100):
        """Get historical klines/candlestick data"""
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
                print("No klines received")
                return None
                
            print(f"Retrieved {len(klines)} klines\n")
            
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'buy_base_volume',
                'buy_quote_volume', 'ignore'
            ])
            
            # Convert numeric columns
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_volume']
            df[numeric_columns] = df[numeric_columns].astype(float)
            
            # Use quote_volume (USD volume) instead of base volume
            df['volume'] = df['quote_volume']
            
            # Set timestamp as index
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Calculate indicators
            df = TechnicalIndicators.calculate_all_indicators(df)
            
            # Print first and last bar info
            print("First bar:")
            print(f"Time: {df.index[0].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Close: ${df.iloc[0]['close']:,.2f}")
            print(f"RSI: {df.iloc[0]['rsi']}")
            print(f"Volume: ${df.iloc[0]['volume']:,.2f}")
            print("\nLast bar:")
            print(f"Time: {df.index[-1].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Close: ${df.iloc[-1]['close']:,.2f}")
            print(f"RSI: {df.iloc[-1]['rsi']}")
            print(f"Volume: ${df.iloc[-1]['volume']:,.2f}")
            
            return df
            
        except Exception as e:
            print(f"Error getting klines: {str(e)}")
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

    def get_futures_open_interest(self, symbol=None):
        """Get open interest from Binance USDT-margined Futures"""
        try:
            if symbol is None:
                symbol = SYMBOL.replace('/', '') + 'T'
            result = self.futures_client.futures_open_interest(symbol=symbol)
            return result
        except Exception as e:
            print(f"Error fetching futures open interest: {e}")
            return None

    def get_futures_current_price(self, symbol=None):
        """Get the current market price from Binance Futures"""
        try:
            if symbol is None:
                symbol = SYMBOL.replace('/', '') + 'T'
            ticker = self.futures_client.futures_symbol_ticker(symbol=symbol)
            price = float(ticker['price']) if ticker else None
            print(f"Futures Current Price for {symbol}: {price}")
            return price
        except Exception as e:
            print(f"Error fetching futures current price: {e}")
            return None

    def get_futures_klines(self, interval=None, limit=100, symbol=None):
        """Get historical klines/candlestick data from Binance Futures"""
        try:
            if symbol is None:
                symbol = SYMBOL.replace('/', '') + 'T'
            if interval is None:
                interval = INTERVAL
            klines = self.futures_client.futures_klines(symbol=symbol, interval=interval, limit=limit)
            print(f"Fetched {len(klines)} futures klines for {symbol} interval {interval}")
            return klines
        except Exception as e:
            print(f"Error fetching futures klines: {e}")
            return None 