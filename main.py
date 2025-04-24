from binance_client import BinanceClient
from alpaca_client import AlpacaClient
from notification_service import NotificationService
from gpt_signal_checker import GPTSignalChecker
from indicators import TechnicalIndicators
import time
from datetime import datetime, timedelta
from config import SYMBOL, RSI_OVERSOLD, RSI_OVERBOUGHT, VOLUME_LOOKBACK, VOLUME_THRESHOLD, INTERVAL
import json
import sys
from trade_history import TradeHistory
import argparse
import traceback

# Initialize clients
binance_client = BinanceClient()
alpaca_client = AlpacaClient()
trade_history = TradeHistory()

def create_market_data():
    """Create market data dictionary with technical indicators"""
    try:
        # Get market data from Binance
        df = binance_client.get_klines(limit=100)
        if df is None or len(df) == 0:
            print("No data received from Binance")
            return None

        # Get current price
        current_price = binance_client.get_current_price()
        if current_price is None:
            print("Failed to get current price")
            return None

        # Create market data dictionary
        market_data = {
            'timestamp': datetime.now(),
            'symbol': SYMBOL,
            'price': {
                'current': current_price,
                'price_change_pct': ((current_price - df.iloc[-2]['close']) / df.iloc[-2]['close']) * 100
            },
            'technical_indicators': {
                'rsi': df.iloc[-1]['rsi'],
                'vwap': df.iloc[-1]['vwap'],
                'volume': {
                    'current': df.iloc[-1]['volume'],
                    'average': df.iloc[-1]['volume_ma_5']
                }
            },
            'signal_analysis': {
                'signals': {
                    'vwap_reclaim': df.iloc[-1]['close'] > df.iloc[-1]['vwap'] and df.iloc[-2]['close'] <= df.iloc[-2]['vwap'],
                    'rising_volume': df.iloc[-1]['volume'] > df.iloc[-1]['volume_ma_5'],
                    'rsi_cross_50': df.iloc[-1]['rsi'] > 50 and df.iloc[-2]['rsi'] <= 50
                },
                'levels': {
                    'entry': current_price,
                    'stop_loss': current_price * 0.99,  # 1% stop loss
                    'target': current_price * 1.02,  # 2% take profit
                    'risk_reward_ratio': 2.0
                }
            }
        }

        print("\nMarket Data Summary:")
        print(f"Current Price: ${current_price:,.2f}")
        print(f"RSI: {market_data['technical_indicators']['rsi']:.1f}")
        print(f"Volume vs 5-bar Average: {market_data['technical_indicators']['volume']['current'] / market_data['technical_indicators']['volume']['average']:.1f}x")
        print("\nSignal Conditions:")
        print(f"VWAP Reclaim: {'✓' if market_data['signal_analysis']['signals']['vwap_reclaim'] else '✗'}")
        print(f"Rising Volume: {'✓' if market_data['signal_analysis']['signals']['rising_volume'] else '✗'}")
        print(f"RSI Cross 50: {'✓' if market_data['signal_analysis']['signals']['rsi_cross_50'] else '✗'}")

        return market_data

    except Exception as e:
        print(f"Error creating market data: {str(e)}")
        print("\nFull error traceback:")
        print(traceback.format_exc())
        return None

def extract_gpt_summary(analysis):
    """Extract key points from GPT analysis"""
    summary = []
    
    # Look for confidence level
    if "Confidence: " in analysis:
        confidence = analysis.split("Confidence: ")[1].split("\n")[0].strip()
        summary.append(f"Confidence: {confidence}")
    
    # Look for key reasoning
    if "Reasoning: " in analysis:
        reasoning = analysis.split("Reasoning: ")[1].split("\n")[0].strip()
        summary.append(f"Reason: {reasoning}")
    
    return " | ".join(summary)

def execute_trade(signal_type, entry_price, stop_loss, take_profit, strategy_name="original"):
    """Execute a trade based on the signal"""
    try:
        # Convert BTC/USD to BTCUSD for Alpaca
        trading_symbol = SYMBOL.replace('/', '')
        
        # Calculate position size (1% of portfolio)
        account = alpaca_client.get_account()
        equity = float(account.equity)
        position_size = equity * 0.01  # 1% of portfolio
        
        # Calculate quantity based on position size and entry price
        quantity = position_size / entry_price
        
        # Round quantity to 6 decimal places for BTC
        quantity = round(quantity, 6)
        
        print(f"\nExecuting {signal_type} trade:")
        print(f"Entry Price: ${entry_price:,.2f}")
        print(f"Stop Loss: ${stop_loss:,.2f}")
        print(f"Take Profit: ${take_profit:,.2f}")
        print(f"Position Size: ${position_size:,.2f}")
        print(f"Quantity: {quantity} BTC")
        
        # Place bracket order with Alpaca
        order = alpaca_client.place_bracket_order(
            symbol=trading_symbol,
            qty=quantity,
            side=signal_type,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        if order:
            print("\nTrade executed successfully!")
            print(f"Order ID: {order.id}")
            
            # Log the trade
            trade_history.log_trade(
                symbol=SYMBOL,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                quantity=quantity,
                side=signal_type,
                strategy=strategy_name
            )
            
            return True
        else:
            print("Failed to execute trade")
            return False
            
    except Exception as e:
        print(f"Error executing trade: {str(e)}")
        return False

def parse_gpt_response(response):
    """Parse GPT response to extract trade parameters"""
    # Look for BUY or SELL recommendation
    side = None
    if "BUY" in response.upper() or "LONG" in response.upper():
        side = "BUY"
    elif "SELL" in response.upper() or "SHORT" in response.upper():
        side = "SELL"
    
    # Get current price for calculations
    current_price = alpaca_client.get_current_price()
    
    if not current_price:
        return None
        
    # Default to 1% stop loss and 2% take profit if not specified
    if side == "BUY":
        stop_loss = current_price * 0.99
        take_profit = current_price * 1.02
    else:
        stop_loss = current_price * 1.01
        take_profit = current_price * 0.98
        
    return {
        "side": side,
        "entry_price": current_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit
    }

def format_data_for_gpt(data):
    """Format market data into a string for GPT analysis"""
    return f"""Please analyze this trading setup for {data['market_data']['symbol']}:

MARKET DATA:
Current Price: ${data['market_data']['price']['current']:,.2f}
Daily Change: {data['market_data']['price']['price_change_pct']:.2f}%

SIGNAL CONDITIONS:
1. VWAP Reclaim: {"Yes" if data['signal_analysis']['signals']['vwap_reclaim'] else "No"}
2. Rising Volume (5-bar): {"Yes" if data['signal_analysis']['signals']['rising_volume'] else "No"}
3. RSI(5) Cross Above 50: {"Yes" if data['signal_analysis']['signals']['rsi_cross_50'] else "No"}

CURRENT INDICATORS:
- RSI(5): {data['technical_indicators']['rsi']:.1f}
- Current Price vs VWAP: ${(data['market_data']['price']['current'] - data['technical_indicators']['vwap']):.2f}
- Volume vs 5-bar Average: {data['technical_indicators']['volume']['current'] / data['technical_indicators']['volume']['average'] if data['technical_indicators']['volume']['average'] > 0 else 1.0:.1f}x

TRADE LEVELS:
Entry: ${data['signal_analysis']['levels']['entry']:,.2f}
Stop Loss: ${data['signal_analysis']['levels']['stop_loss']:,.2f}
Target: ${data['signal_analysis']['levels']['target']:,.2f}
Risk/Reward: {data['signal_analysis']['levels']['risk_reward_ratio']:.1f}

Based on these specific conditions, should we enter a LONG trade or WAIT?
Consider:
1. All three signal conditions must be met (VWAP reclaim, Rising Volume, RSI cross)
2. Risk/Reward ratio should be at least 2:1
3. Current market context

Please provide your analysis and recommendation."""

def test_signals():
    """Test signal detection with historical data"""
    print("\n=== Testing Signal Detection ===")
    
    # Get more historical data for testing
    df = binance_client.get_klines(limit=200)  # Get 200 bars for better testing
    if df is None or df.empty:
        print("No data received from Binance")
        return
        
    # Calculate indicators
    df = TechnicalIndicators.calculate_all_indicators(df)
    
    # Look for signals in each bar
    signals_found = 0
    print("\nScanning for signals...")
    
    for i in range(1, len(df)):
        test_df = df.iloc[:i+1]  # Use data up to current bar
        has_signal, trade_info = TechnicalIndicators.check_long_setup(test_df)
        
        if has_signal:
            signals_found += 1
            current_bar = test_df.iloc[-1]
            print(f"\nSignal {signals_found} found at {current_bar.name}:")
            print(f"Price: ${current_bar['close']:,.2f}")
            print(f"VWAP: ${current_bar['vwap']:,.2f}")
            print(f"RSI: {current_bar['rsi']:.1f}")
            print(f"Volume: ${current_bar['volume']:,.2f}")
            print(f"Volume MA5: ${current_bar['volume_ma_5']:,.2f}")
            print(f"Volume MA20: ${current_bar['volume_ma_20']:,.2f}")
            
            if trade_info and trade_info['levels']:
                print("\nTrade Levels:")
                print(f"Entry: ${trade_info['levels']['entry']:,.2f}")
                print(f"Stop Loss: ${trade_info['levels']['stop_loss']:,.2f}")
                print(f"Take Profit: ${trade_info['levels']['take_profit']:,.2f}")
            
            print("\nSignal Conditions:")
            print(f"VWAP Reclaim: {'✓' if trade_info['signals']['vwap_reclaim'] else '✗'}")
            print(f"Rising Volume: {'✓' if trade_info['signals']['rising_volume'] else '✗'}")
            print(f"RSI Cross 50: {'✓' if trade_info['signals']['rsi_cross_50'] else '✗'}")
            
    print(f"\nFound {signals_found} signals in {len(df)} bars")

def main(test_mode=False):
    """Main function to run the trading bot"""
    if test_mode:
        test_signals()
        return
        
    print("\n==================================================")
    print(f"Starting Trading Bot - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing with {SYMBOL}")
    print("==================================================\n")
    
    # Check for existing positions on startup
    print("\nChecking for existing positions...")
    position = alpaca_client.get_position()
    if position:
        print("\nFound open position:")
        print(f"Side: {position['side']}")
        print(f"Quantity: {position['qty']} {SYMBOL}")
        print(f"Entry Price: ${position['avg_entry_price']:,.2f}")
        print(f"Current Price: ${position['current_price']:,.2f}")
        print(f"Market Value: ${position['market_value']:,.2f}")
        print(f"Unrealized P&L: ${position['unrealized_pl']:.2f} ({position['unrealized_plpc']:.2f}%)")
        
        # Get open orders to find stop loss and take profit levels
        orders = alpaca_client.get_open_orders()
        if orders:
            for order in orders:
                if order['type'] == 'stop':
                    print(f"Stop Loss: ${float(order['stop_price']):,.2f}")
                elif order['type'] == 'limit':
                    print(f"Take Profit: ${float(order['limit_price']):,.2f}")
        else:
            # If no open orders, calculate default levels based on entry price
            entry_price = float(position['avg_entry_price'])
            if position['side'] == 'long':
                print(f"Stop Loss: ${entry_price * 0.99:,.2f}")
                print(f"Take Profit: ${entry_price * 1.02:,.2f}")
            else:
                print(f"Stop Loss: ${entry_price * 1.01:,.2f}")
                print(f"Take Profit: ${entry_price * 0.98:,.2f}")
        
        print("----------------------------------------")
    else:
        print("No open positions found")
        print("----------------------------------------")
    
    try:
        while True:
            print(f"\nChecking for signals - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Check for open positions and display P&L
            position = alpaca_client.get_position()
            if position:
                print("\nCurrent Position:")
                print(f"Side: {position['side']}")
                print(f"Quantity: {position['qty']} {SYMBOL}")
                print(f"Entry Price: ${position['avg_entry_price']:,.2f}")
                print(f"Current Price: ${position['current_price']:,.2f}")
                print(f"Market Value: ${position['market_value']:,.2f}")
                print(f"Unrealized P&L: ${position['unrealized_pl']:.2f} ({position['unrealized_plpc']:.2f}%)")
                
                # Get open orders to find stop loss and take profit levels
                orders = alpaca_client.get_open_orders()
                if orders:
                    for order in orders:
                        if order['type'] == 'stop':
                            print(f"Stop Loss: ${float(order['stop_price']):,.2f}")
                        elif order['type'] == 'limit':
                            print(f"Take Profit: ${float(order['limit_price']):,.2f}")
                else:
                    # If no open orders, calculate default levels based on entry price
                    entry_price = float(position['avg_entry_price'])
                    if position['side'] == 'long':
                        print(f"Stop Loss: ${entry_price * 0.99:,.2f}")
                        print(f"Take Profit: ${entry_price * 1.02:,.2f}")
                    else:
                        print(f"Stop Loss: ${entry_price * 1.01:,.2f}")
                        print(f"Take Profit: ${entry_price * 0.98:,.2f}")
                
                print("----------------------------------------")
            
            # Get market data and check for signals
            market_data = create_market_data()
            if not market_data:
                print("Failed to get market data")
                print("Waiting 30 seconds before retrying...")
                time.sleep(30)
                continue
            
            # Check for original strategy signals
            if market_data.get('signals'):
                # Check original strategy signals
                if market_data['signals'].get('long_setup', False):
                    print("\nOriginal Strategy Signal Detected!")
                    execute_trade(
                        signal_type='BUY',
                        entry_price=market_data['levels']['entry'],
                        stop_loss=market_data['levels']['stop_loss'],
                        take_profit=market_data['levels']['target'],
                        strategy_name='original'
                    )
            
            # Check for momentum strategy signals
            if market_data.get('signals', {}).get('momentum'):
                has_momentum_signal = (
                    market_data['signals']['momentum']['price_above_ema'] and
                    (market_data['signals']['momentum']['higher_highs'] or market_data['signals']['momentum']['higher_lows']) and
                    market_data['signals']['momentum']['volume_above_avg'] and
                    market_data['signals']['momentum']['rsi_above_threshold']
                )
                if has_momentum_signal:
                    print("\nMomentum Strategy Signal Detected!")
                    execute_trade(
                        signal_type='BUY',
                        entry_price=market_data['levels']['entry'],
                        stop_loss=market_data['levels']['stop_loss'],
                        take_profit=market_data['levels']['target'],
                        strategy_name='momentum'
                    )
            
            print("\nWaiting 30 seconds before retrying...")
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\nBot stopped by user")

if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    main(test_mode) 