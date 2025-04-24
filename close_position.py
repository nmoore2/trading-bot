from config import SYMBOL
from alpaca_client import AlpacaClient

def main():
    """Close any open position for the configured trading symbol."""
    try:
        client = AlpacaClient()
        
        # Get all positions
        positions = client.trading_client.get_all_positions()
        position = None
        
        # Find our position
        symbol = SYMBOL.replace('/', '')  # Convert BTC/USD to BTCUSD
        for pos in positions:
            if pos.symbol == symbol:
                position = pos
                break
        
        if position:
            # Close the position with a market order
            client.trading_client.close_position(symbol)
            print(f"\nClosed position for {SYMBOL}:")
            print(f"Quantity: {position.qty}")
            print(f"Entry Price: ${float(position.avg_entry_price):,.2f}")
            print(f"Current Price: ${float(position.current_price):,.2f}")
            print(f"P&L: ${float(position.unrealized_pl):,.2f} ({float(position.unrealized_plpc) * 100:.2f}%)")
        else:
            print(f"\nNo open position found for {SYMBOL}")
            
    except Exception as e:
        print(f"Error closing position: {e}")

if __name__ == "__main__":
    main() 