import json
from datetime import datetime

class DataFormatter:
    @staticmethod
    def format_for_gpt(df):
        """Format market data and indicators for GPT analysis"""
        try:
            print("\nFormatting data for GPT analysis...")
            
            # Get the latest candle data
            current = df.iloc[-1]
            previous = df.iloc[-2]
            
            # Calculate price changes
            price_change = ((current['close'] - previous['close']) / previous['close']) * 100
            daily_range = ((current['high'] - current['low']) / current['low']) * 100
            
            # Format the data
            data = {
                'market_data': {
                    'symbol': 'BTCUSDT',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'price': {
                        'current': current['close'],
                        'open': current['open'],
                        'high': current['high'],
                        'low': current['low'],
                        'price_change_pct': price_change,
                        'daily_range_pct': daily_range
                    }
                },
                'technical_indicators': {
                    'rsi': {
                        'value': current['rsi'],
                        'is_oversold': current['rsi_oversold'],
                        'is_overbought': current['rsi_overbought']
                    },
                    'vwap': {
                        'value': current['vwap'],
                        'price_to_vwap_ratio': current['close'] / current['vwap']
                    },
                    'volume': {
                        'current': current['volume'],
                        'average': current['volume_ma'],
                        'ratio': current['volume_ratio']
                    },
                    'momentum': {
                        'value': current['momentum_ma'],
                        'trend': 'bullish' if current['momentum_ma'] > 0 else 'bearish'
                    }
                },
                'trade_setup': {
                    'entry': current['close'],
                    'stop_loss': min(current['low'], previous['low']),
                    'target': current['close'] + (2 * (current['close'] - min(current['low'], previous['low']))),
                    'risk_reward_ratio': 2.0
                }
            }
            
            print("\nFormatted market data:")
            print(json.dumps(data, indent=2))
            
            # Create a detailed prompt for GPT
            prompt = f"""Analyze the following trading setup for BTCUSDT:

Price Action:
- Current Price: ${data['market_data']['price']['current']:,.2f}
- Price Change: {data['market_data']['price']['price_change_pct']:.2f}%
- Daily Range: {data['market_data']['price']['daily_range_pct']:.2f}%

Technical Indicators:
- RSI ({current['rsi']:.1f}): {'Overbought' if current['rsi_overbought'] else 'Oversold' if current['rsi_oversold'] else 'Neutral'}
- VWAP: Price is {data['technical_indicators']['vwap']['price_to_vwap_ratio']:.2f}x VWAP
- Volume: {data['technical_indicators']['volume']['ratio']:.1f}x average volume
- Momentum: {data['technical_indicators']['momentum']['trend'].title()}

Trade Setup:
- Entry: ${data['trade_setup']['entry']:,.2f}
- Stop Loss: ${data['trade_setup']['stop_loss']:,.2f}
- Target: ${data['trade_setup']['target']:,.2f}
- Risk/Reward: {data['trade_setup']['risk_reward_ratio']:.1f}

Based on these conditions, please provide your analysis and recommendation."""

            print("\nPrompt for GPT:")
            print(prompt)
            
            return prompt
            
        except Exception as e:
            print(f"Error formatting data: {e}")
            return None
    
    @staticmethod
    def create_gpt_prompt(data_json):
        """Create a prompt for GPT to analyze the trading setup"""
        return f"""
        Analyze the following market data and determine if it presents a valid long trading setup.
        Consider the following criteria:
        1. Price has reclaimed VWAP from below
        2. Volume is rising compared to the previous {VOLUME_LOOKBACK} bars
        3. RSI(5) has crossed above 50
        4. Overall market context and strength of the setup
        
        Market Data:
        {data_json}
        
        Please provide a concise response in the following format:
        Decision: [Yes/No]
        Confidence: [Low/Medium/High]
        Reasoning: [Brief explanation]
        """ 