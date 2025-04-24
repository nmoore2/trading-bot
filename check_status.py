from config import SYMBOL
from alpaca_client import AlpacaClient

def main():
    client = AlpacaClient()
    
    # Get current position
    position = client.get_position()
    
    if position:
        print(f"\nOpen Position in {SYMBOL}:")
        print(f"Side: {position['side']}")
        print(f"Quantity: {position['qty']}")
        print(f"Entry Price: ${float(position['avg_entry_price']):,.2f}")
        print(f"Market Value: ${float(position['market_value']):,.2f}")
        print(f"Unrealized P&L: ${float(position['unrealized_pl']):,.2f}")
        print(f"Unrealized P&L %: {float(position['unrealized_plpc']):,.2f}%")
    else:
        print(f"\nNo open position in {SYMBOL}")

if __name__ == "__main__":
    main() 