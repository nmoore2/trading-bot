from alpaca_client import AlpacaClient
import time

def main():
    # Initialize client
    client = AlpacaClient()
    
    # Test 1: Place a small market buy order
    print("\n=== Test 1: Market Buy Order ===")
    quantity = 0.001  # Small test quantity
    order = client.place_market_order('BUY', quantity)
    
    if order:
        print("✓ Market buy order placed")
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
        print("✗ Failed to place market buy order")
        
    time.sleep(2)  # Wait between tests
    
    # Test 2: Place a market sell order
    print("\n=== Test 2: Market Sell Order ===")
    quantity = 0.001  # Small test quantity
    order = client.place_market_order('SELL', quantity)
    
    if order:
        print("✓ Market sell order placed")
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
        print("✗ Failed to place market sell order")
        
    # Test 3: Check account balance
    print("\n=== Test 3: Account Info ===")
    balance = client.get_account_balance()
    if balance:
        print("\nAccount Balance:")
        print(f"Portfolio Value: ${float(balance['portfolio_value']):,.2f}")
        print(f"Buying Power: ${float(balance['buying_power']):,.2f}")
        print(f"Cash: ${float(balance['cash']):,.2f}")
    else:
        print("✗ Failed to get account balance")

if __name__ == "__main__":
    main() 