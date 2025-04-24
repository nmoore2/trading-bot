from alpaca_client import AlpacaClient
from indicators import TechnicalIndicators
import time

def main():
    # Initialize clients
    client = AlpacaClient()
    indicators = TechnicalIndicators()
    
    print("\n=== Testing Signal Logic ===")
    
    # Get current price and position
    print("\nChecking current position and price...")
    position = client.get_position()
    current_price = client.get_current_price()
    
    if not current_price:
        print("✗ Failed to get current price")
        return
        
    print(f"\nCurrent BTC/USD price: ${current_price:,.2f}")
    
    if position:
        print("\nCurrent position:")
        print(f"Side: {position['side']}")
        print(f"Quantity: {position['qty']}")
        print(f"Entry Price: ${float(position['avg_entry_price']):,.2f}")
        print(f"Market Value: ${float(position['market_value']):,.2f}")
        print(f"Unrealized P&L: ${float(position['unrealized_pl']):,.2f}")
        
        # Get stop loss and take profit from open orders
        orders = client.get_open_orders()
        if orders:
            for order in orders:
                if order['type'] == 'stop':
                    print(f"Stop Loss: ${float(order['stop_price']):,.2f}")
                elif order['type'] == 'limit':
                    print(f"Take Profit: ${float(order['limit_price']):,.2f}")
    else:
        print("\nNo open position")
        
        # Optional: Execute test trade
        print("\nWould you like to execute a test trade? (y/n)")
        if input().lower() == 'y':
            print("\nExecuting test trade...")
            order = client.place_market_order('BUY', 0.001)  # Small test quantity
            
            if order:
                print("✓ Test trade executed")
                print("\nWaiting 5 seconds to check position...")
                time.sleep(5)
                
                position = client.get_position()
                if position:
                    print("\nPosition opened:")
                    print(f"Quantity: {position['qty']}")
                    print(f"Entry Price: ${float(position['avg_entry_price']):,.2f}")
                    print(f"Market Value: ${float(position['market_value']):,.2f}")
                    
                    print("\nClosing position...")
                    if client.close_position():
                        print("✓ Position closed")
                    else:
                        print("✗ Failed to close position")
                else:
                    print("✗ No position found")
            else:
                print("✗ Failed to execute test trade")

if __name__ == "__main__":
    main() 