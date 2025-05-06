import pandas as pd
import numpy as np

class TechnicalIndicators:
    @staticmethod
    def calculate_vwap(df):
        """Calculate VWAP and check for reclaim signal"""
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['cumulative_volume'] = df['volume'].cumsum()
        df['cumulative_pv'] = (df['typical_price'] * df['volume']).cumsum()
        df['vwap'] = df['cumulative_pv'] / df['cumulative_volume']
        
        # VWAP reclaim signal (price crosses above VWAP)
        df['vwap_reclaim'] = (df['close'] > df['vwap']) & (df['close'].shift(1) <= df['vwap'].shift(1))
        return df

    @staticmethod
    def calculate_rsi(df, period=14):
        """Calculate RSI and add to dataframe"""
        # Calculate price changes
        delta = df['close'].diff()
        
        # Separate gains and losses
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Print RSI values for debugging
        # print("\nRSI Analysis:")
        # print(f"Current RSI: {df['rsi'].iloc[-1]:.1f}")
        # print(f"Previous RSI: {df['rsi'].iloc[-2]:.1f}")
        
        # RSI cross above 50 signal
        df['rsi_cross_50'] = (df['rsi'] > 50) & (df['rsi'].shift(1) <= 50)
        return df

    @staticmethod
    def calculate_volume(df, lookback=5):
        """Check if volume is rising vs previous bars and calculate additional volume metrics"""
        # Handle zero or NaN volumes first
        df['volume'] = df['volume'].replace(0, np.nan)
        df['volume'] = df['volume'].fillna(df['volume'].mean())
        
        # Calculate volume moving averages
        df['volume_ma_5'] = df['volume'].rolling(window=lookback, min_periods=1).mean()
        df['volume_ma_20'] = df['volume'].rolling(window=20, min_periods=1).mean()
        
        # Calculate volume ratios and trends
        df['volume_ratio_5'] = df['volume'] / df['volume_ma_5']
        df['volume_ratio_20'] = df['volume'] / df['volume_ma_20']
        df['volume_trend'] = df['volume'].pct_change()
        
        # Enhanced volume signal conditions
        df['rising_volume_short'] = df['volume'] > df['volume_ma_5']
        df['rising_volume_long'] = df['volume'] > df['volume_ma_20']
        df['rising_volume'] = df['rising_volume_short'] & df['rising_volume_long']  # Must confirm on both timeframes
        
        # Calculate relative volume (compared to average)
        df['relative_volume'] = df['volume_ratio_5'].round(2)
        
        # Print detailed volume debug info for the last bar
        # if len(df) > 0:
        #     last_bar = df.iloc[-1]
        #     print(f"\nVolume Analysis:")
        #     print(f"Current Volume: ${last_bar['volume']:,.2f}")
        #     print(f"5-bar Avg Volume: ${last_bar['volume_ma_5']:,.2f}")
        #     print(f"20-bar Avg Volume: ${last_bar['volume_ma_20']:,.2f}")
        #     print(f"Relative Volume (5-bar): {last_bar['volume_ratio_5']:.1f}x")
        #     print(f"Relative Volume (20-bar): {last_bar['volume_ratio_20']:.1f}x")
        #     print(f"Volume Trend: {(last_bar['volume_trend']*100):,.1f}%")
        #     print(f"Rising Volume Signal:")
        #     print(f"  - vs 5-bar MA: {'✓' if last_bar['rising_volume_short'] else '✗'}")
        #     print(f"  - vs 20-bar MA: {'✓' if last_bar['rising_volume_long'] else '✗'}")
        #     print(f"  - Overall: {'✓' if last_bar['rising_volume'] else '✗'}")
        
        return df

    @staticmethod
    def calculate_cvd(df):
        """Calculate Cumulative Volume Delta (CVD)"""
        # Calculate volume delta for each bar
        # If close > open, volume is buying pressure
        # If close < open, volume is selling pressure
        df['volume_delta'] = df.apply(
            lambda x: x['volume'] if x['close'] > x['open'] else -x['volume'] if x['close'] < x['open'] else 0,
            axis=1
        )
        
        # Calculate cumulative sum
        df['cvd'] = df['volume_delta'].cumsum()
        
        # Calculate CVD moving averages
        df['cvd_ma5'] = df['cvd'].rolling(window=5).mean()
        df['cvd_ma20'] = df['cvd'].rolling(window=20).mean()
        
        return df

    @staticmethod
    def check_cvd_signals(df):
        """Check for CVD-based signals"""
        current = df.iloc[-1]
        prev = df.iloc[-2]
        prev_prev = df.iloc[-3]
        
        signals = {
            'cvd_rising': current['cvd'] > prev['cvd'] and prev['cvd'] > prev_prev['cvd']
        }
        
        return signals

    @staticmethod
    def calculate_momentum_indicators(df):
        """Calculate additional momentum indicators"""
        # Calculate EMAs
        df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        
        # Calculate price patterns
        df['higher_high'] = (df['high'] > df['high'].shift(1)) & (df['high'].shift(1) > df['high'].shift(2))
        df['higher_low'] = (df['low'] > df['low'].shift(1)) & (df['low'].shift(1) > df['low'].shift(2))
        
        # Calculate volume trend
        df['volume_trend'] = df['volume'].rolling(window=3).mean().pct_change()
        
        # Calculate RSI trend
        df['rsi_trend'] = df['rsi'].rolling(window=3).mean().pct_change()
        
        return df

    @staticmethod
    def check_momentum_breakout(df):
        """Check for momentum breakout conditions"""
        if len(df) < 20:  # Need enough data for indicators
            return None
            
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Price action signals
        price_above_ema = current['close'] > current['ema_5']
        higher_highs = current['high'] > prev['high']
        higher_lows = current['low'] > prev['low']
        
        # Volume signals
        volume_above_avg = current['volume'] > current['volume_ma_5']
        volume_trending = current['volume_trend'] > 0
        
        # Momentum signals
        rsi_above_threshold = current['rsi'] > 40  # Lowered from 50
        rsi_trending = current['rsi'] > prev['rsi']
        
        # Combine signals
        signals = {
            'price_above_ema': price_above_ema,
            'higher_highs': higher_highs,
            'higher_lows': higher_lows,
            'volume_above_avg': volume_above_avg,
            'volume_trending': volume_trending,
            'rsi_above_threshold': rsi_above_threshold,
            'rsi_trending': rsi_trending
        }
        
        # Calculate entry, stop loss, and take profit levels
        entry = current['close']
        stop_loss = entry * 0.99  # 1% stop loss
        target = entry * 1.02  # 2% take profit
        
        levels = {
            'entry': entry,
            'stop_loss': stop_loss,
            'target': target
        }
        
        # Calculate metrics
        metrics = {
            'rsi': current['rsi'],
            'volume_ratio': current['volume_ratio_5'],
            'price_ema_diff': ((current['close'] - current['ema_5']) / current['ema_5']) * 100
        }
        
        return signals, levels, metrics

    @staticmethod
    def calculate_ema(df):
        """Calculate Exponential Moving Averages"""
        # Calculate EMAs
        df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        return df

    @staticmethod
    def calculate_all_indicators(df):
        """Calculate all technical indicators"""
        df = TechnicalIndicators.calculate_vwap(df)
        df = TechnicalIndicators.calculate_rsi(df)
        df = TechnicalIndicators.calculate_volume(df)
        df = TechnicalIndicators.calculate_cvd(df)
        df = TechnicalIndicators.calculate_momentum_indicators(df)  # This includes EMA calculations
        return df

    @staticmethod
    def check_long_setup(df):
        """Check for long setup conditions"""
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Get CVD signals
        cvd_signals = TechnicalIndicators.check_cvd_signals(df)
        
        # Check VWAP reclaim
        vwap_reclaim = (
            current['close'] > current['vwap'] and
            prev['close'] <= prev['vwap']
        )
        
        # Check volume confirmation
        volume_confirmation = (
            current['volume'] > current['volume_ma_5'] and
            current['volume'] > current['volume_ma_20']
        )
        
        # Check RSI cross above 50
        rsi_cross = (
            current['rsi'] > 50 and
            prev['rsi'] <= 50
        )
        
        # Combine all signals
        signals = {
            'vwap_reclaim': vwap_reclaim,
            'rising_volume': volume_confirmation,
            'rsi_cross_50': rsi_cross,
            'cvd_rising': cvd_signals['cvd_rising']
        }
        
        # Calculate entry, stop loss, and take profit levels
        entry = current['close']
        stop_loss = entry * 0.99  # 1% stop loss
        take_profit = entry * 1.02
        
        # Create trade info dictionary
        trade_info = {
            'signals': signals,
            'levels': {
                'entry': entry,
                'stop_loss': stop_loss,
                'target': take_profit,
                'risk_reward_ratio': 2.0
            },
            'metrics': {
                'rsi': current['rsi'],
                'volume_ratio': current['volume_ratio_5'],
                'cvd': current['cvd']
            }
        }
        
        # Signal is valid if all conditions are met (except volume)
        has_signal = (
            vwap_reclaim and
            # volume_confirmation and  # Commenting out volume requirement
            rsi_cross and
            cvd_signals['cvd_rising']
        )
        
        return has_signal, trade_info 