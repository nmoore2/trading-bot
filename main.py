from binance_client import BinanceClient
from alpaca_client import AlpacaClient
from mexc_client import MEXCClient
from notification_service import NotificationService
from gpt_signal_checker import GPTSignalChecker
from indicators import TechnicalIndicators
import time
from datetime import datetime, timedelta
from config import SYMBOL, MEXC_SYMBOL, RSI_OVERSOLD, RSI_OVERBOUGHT, VOLUME_LOOKBACK, VOLUME_THRESHOLD, INTERVAL
import json
import sys
from trade_history import TradeHistory
import argparse
import traceback

# Initialize clients
binance_client = BinanceClient()
alpaca_client = AlpacaClient()
mexc_client = MEXCClient()
trade_history = TradeHistory()
notifier = NotificationService()

def create_market_data():
    """Create market data dictionary with technical indicators"""
    try:
        # Get market data from Binance
        df = binance_client.get_klines(limit=100)
        if df is None or len(df) == 0:
            print("No data received from Binance")
            notifier.send_error("Failed to get market data from Binance")
            return None

        # Get current price
        current_price = binance_client.get_current_price()
        if current_price is None:
            print("Failed to get current price")
            notifier.send_error("Failed to get current price from Binance")
            return None

        print("\nMarket Data Summary:")
        print(f"Current Price: ${current_price:,.2f}")
        # print(f"RSI: {df.iloc[-1]['rsi']:.1f}")
        print(f"Volume vs 5-bar Average: {df.iloc[-1]['volume_ratio_5']:.1f}x")

        print("\nVWAP Reclaim (5m) Conditions:")
        print(f"VWAP Reclaim: {'✓' if df.iloc[-1]['close'] > df.iloc[-1]['vwap'] and df.iloc[-2]['close'] <= df.iloc[-2]['vwap'] else '✗'}")
        print(f"Rising Volume: {'✓' if df.iloc[-1]['volume'] > df.iloc[-1]['volume_ma_5'] and df.iloc[-1]['volume'] > df.iloc[-1]['volume_ma_20'] else '✗'}")
        # print(f"RSI Cross 50: {'✓' if df.iloc[-1]['rsi'] > 50 and df.iloc[-2]['rsi'] <= 50 else '✗'}")
        print(f"CVD Rising: {'✓' if df.iloc[-1]['cvd'] > df.iloc[-2]['cvd'] and df.iloc[-2]['cvd'] > df.iloc[-3]['cvd'] else '✗'}")

        print("\nMomentum Strategy Conditions:")
        print(f"Price > EMA: {'✓' if df.iloc[-1]['close'] > df.iloc[-1]['ema_5'] else '✗'}")
        print(f"Higher Highs: {'✓' if df.iloc[-1]['high'] > df.iloc[-2]['high'] and df.iloc[-2]['high'] > df.iloc[-3]['high'] else '✗'}")
        print(f"Higher Lows: {'✓' if df.iloc[-1]['low'] > df.iloc[-2]['low'] and df.iloc[-2]['low'] > df.iloc[-3]['low'] else '✗'}")
        print(f"Volume > Avg: {'✓' if df.iloc[-1]['volume'] > df.iloc[-1]['volume_ma_5'] else '✗'}")
        # print(f"RSI > 40: {'✓' if df.iloc[-1]['rsi'] > 40 else '✗'}")

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

def execute_trade(signal_type, entry_price, stop_loss, take_profit, strategy_name="original", signals=None):
    """Execute trade on MEXC based on signal"""
    try:
        # Calculate position size based on account balance
        balance = mexc_client.get_account_balance()
        if not balance:
            print("Failed to get account balance")
            return False
            
        # Find USDT balance
        usdt_balance = next((asset['free'] for asset in balance['balances'] if asset['asset'] == 'USDT'), 0)
        
        # Use 1% of USDT balance for the trade
        position_size = float(usdt_balance) * 0.01 / entry_price
        
        # Place order on MEXC
        order = mexc_client.place_order(
            symbol=MEXC_SYMBOL,
            side='BUY' if signal_type == 'LONG' else 'SELL',
            quantity=position_size,
            price=entry_price
        )
        
        if not order:
            print("Failed to place order")
            return False
            
        # Record trade in history
        trade_history.add_trade({
            'exchange': 'MEXC',
            'symbol': MEXC_SYMBOL,
            'type': signal_type,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'strategy': strategy_name,
            'timestamp': datetime.now().isoformat(),
            'order_id': order['orderId']
        })
            
        # Send notification
        notifier.send_trade_notification(
            exchange='MEXC',
            symbol=MEXC_SYMBOL,
            signal_type=signal_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
            strategy_name=strategy_name
        )
            
            return True
            
    except Exception as e:
        print(f"Error executing trade: {str(e)}")
        traceback.print_exc()
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

def display_position(position, orders=None):
    """Display current position information"""
    if position:
        print("\nCurrent Position:")
        print(f"Side: {'LONG' if float(position['qty']) > 0 else 'SHORT'}")
        print(f"Quantity: {abs(float(position['qty'])):.6f} {SYMBOL}")
        print(f"Entry Price: ${float(position['avg_entry_price']):,.2f}")
        print(f"Current Price: ${float(position['current_price']):,.2f}")
        print(f"Market Value: ${float(position['market_value']):,.2f}")
        print(f"Unrealized P&L: ${float(position['unrealized_pl']):,.2f} ({float(position['unrealized_plpc'])*100:.2f}%)")
        
        # Get stop loss and take profit from open orders
        stop_loss = None
        take_profit = None
        
        if orders:
            for order in orders:
                if order.get('type') == 'stop':
                    stop_loss = float(order.get('stop_price', 0))
                elif order.get('type') == 'limit':
                    take_profit = float(order.get('limit_price', 0))
                    
        # If no orders found, calculate default levels
        if not stop_loss or not take_profit:
            entry_price = float(position['avg_entry_price'])
            if float(position['qty']) > 0:  # Long position
                stop_loss = entry_price * 0.99  # 1% below entry
                take_profit = entry_price * 1.02  # 2% above entry
            else:  # Short position
                stop_loss = entry_price * 1.01  # 1% above entry
                take_profit = entry_price * 0.98  # 2% below entry
                
        print(f"Stop Loss: ${stop_loss:,.2f}")
        print(f"Take Profit: ${take_profit:,.2f}")
    else:
        print("\nNo open position")

def main(test_mode=False):
    """Main function to run the trading bot"""
    if test_mode:
        test_signals()
        return
        
    print("\n==================================================")
    print(f"Starting Trading Bot - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing with {SYMBOL}")
    print("==================================================\n")
    
    try:
        while True:
            print(f"\nChecking for signals - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Check for open positions and display P&L
            position = alpaca_client.get_position()
            if position:
                orders = alpaca_client.get_open_orders()
                display_position(position, orders)
            else:
                print("\nNo open positions")
                print("----------------------------------------")
            
            # Get market data and check for signals
            market_data = create_market_data()
            if not market_data:
                print("Failed to get market data")
                print("Waiting 30 seconds before retrying...")
                time.sleep(30)
                continue
            
            # Check for VWAP reclaim strategy signals
            if market_data.get('signals'):
                if market_data['signals'].get('long_setup', False):
                    print("\nVWAP Reclaim (5m) Signal Detected!")
                    execute_trade(
                        signal_type='BUY',
                        entry_price=market_data['levels']['entry'],
                        stop_loss=market_data['levels']['stop_loss'],
                        take_profit=market_data['levels']['target'],
                        strategy_name='vwap_reclaim_5m',
                        signals=market_data['signals']
                    )
            
            # Check for momentum strategy signals
            if market_data.get('signals', {}).get('momentum'):
                momentum_signals = market_data['signals']['momentum']
                has_momentum_signal = (
                    momentum_signals['price_above_ema'] and
                    (momentum_signals['higher_highs'] or momentum_signals['higher_lows']) and
                    momentum_signals['volume_above_avg'] and
                    momentum_signals['rsi_above_threshold']
                )
                if has_momentum_signal:
                    print("\nMomentum Strategy Signal Detected!")
                    execute_trade(
                        signal_type='BUY',
                        entry_price=market_data['levels']['entry'],
                        stop_loss=market_data['levels']['stop_loss'],
                        take_profit=market_data['levels']['target'],
                        strategy_name='momentum',
                        signals=momentum_signals
                    )
            
            print("\nWaiting 30 seconds before retrying...")
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\nBot stopped by user")

if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    main(test_mode) 