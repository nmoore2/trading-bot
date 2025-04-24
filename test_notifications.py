from alpaca_client import AlpacaClient
from indicators import TechnicalIndicators
from formatter import DataFormatter
from gpt_signal_checker import GPTSignalChecker
from notification_service import NotificationService
from trading_service import TradingService

def test_notification(gpt_response):
    """Test notification with a specific GPT response"""
    # Initialize components
    alpaca = AlpacaClient()
    notifier = NotificationService()
    trading = TradingService(alpaca)
    
    # Get market data
    df = alpaca.get_klines(limit=20)
    if df is None:
        print("Failed to get market data")
        return
        
    # Calculate indicators
    df = TechnicalIndicators.calculate_all_indicators(df)
    
    # Force signal generation with test mode
    has_signal, trade_info = TechnicalIndicators.check_long_setup(df, test_mode=True)
    
    if has_signal:
        # Send notification
        trade = trading.execute_signal(trade_info, gpt_response)
        notifier.send_trading_signal(trade_info, gpt_response, trade)
        return True
    return False

def main():
    # Test BUY signal
    print("\nTesting BUY signal notification...")
    gpt_buy = """Based on the analysis, this appears to be a strong BUY setup with clear support levels."""
    test_notification(gpt_buy)
    
    # Test SELL signal
    print("\nTesting SELL signal notification...")
    gpt_sell = """Market conditions suggest a SELL opportunity with overhead resistance."""
    test_notification(gpt_sell)
    
    # Test WAIT signal
    print("\nTesting WAIT signal notification...")
    gpt_wait = """Given the current conditions, it's better to WAIT for a clearer setup."""
    test_notification(gpt_wait)

if __name__ == "__main__":
    main() 