from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    StopLossRequest,
    TakeProfitRequest
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus, PositionSide
from alpaca.data.enums import CryptoFeed
import pandas as pd
from datetime import datetime, timedelta, timezone
from config import ALPACA_API_KEY, ALPACA_API_SECRET, SYMBOL, INTERVAL, USE_PAPER
import time

class AlpacaClient:
    def __init__(self):
        # Initialize market data client
        self.data_client = CryptoHistoricalDataClient()
        
        # Initialize trading client
        self.trading_client = TradingClient(
            ALPACA_API_KEY,
            ALPACA_API_SECRET,
            paper=USE_PAPER
        )
        
        # Map our interval to Alpaca's TimeFrame
        self.timeframe_map = {
            '1m': TimeFrame.Minute,
            '5m': TimeFrame.Minute,
            '15m': TimeFrame.Minute,
            '1h': TimeFrame.Hour,
            '1d': TimeFrame.Day
        }
        
    def get_klines(self, limit=20):
        """Fetch historical bars data"""
        try:
            print("\nFetching historical bars...")
            
            # Get the correct timeframe for the request
            timeframe = self.timeframe_map.get(INTERVAL)
            if not timeframe:
                print(f"Invalid interval: {INTERVAL}")
                return None
                
            print(f"Using interval: {INTERVAL}")
            print(f"Symbol: {SYMBOL}")
            
            # Calculate start time based on limit and interval
            interval_minutes = int(INTERVAL.replace('m', '')) if 'm' in INTERVAL else 60
            start_time = datetime.now(timezone.utc) - timedelta(minutes=interval_minutes * limit)
            
            # Create request with start time
            request_params = CryptoBarsRequest(
                symbol_or_symbols=SYMBOL,
                timeframe=timeframe,
                start=start_time,
                limit=limit
            )
            
            # Get bars from US feed
            print("Requesting data from Alpaca...")
            bars = self.data_client.get_crypto_bars(request_params, feed=CryptoFeed.US)
            
            if bars is None:
                print("No data received from Alpaca")
                return None
                
            # Convert to DataFrame
            print("Converting to DataFrame...")
            df = bars.df.reset_index()
            
            if len(df) == 0:
                print("DataFrame is empty")
                return None
                
            # Rename columns to match our existing format
            df = df.rename(columns={
                'timestamp': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # Group by timestamp to combine data from all exchanges
            df = df.groupby('timestamp').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).reset_index()
            
            print(f"Retrieved {len(df)} bars")
            
            # Print first and last bar for debugging
            if len(df) > 0:
                print("\nFirst bar:")
                print(f"Time: {df.iloc[0]['timestamp']}")
                print(f"Close: ${df.iloc[0]['close']:,.2f}")
                print(f"Volume: {df.iloc[0]['volume']:,.2f}")
                
                print("\nLast bar:")
                print(f"Time: {df.iloc[-1]['timestamp']}")
                print(f"Close: ${df.iloc[-1]['close']:,.2f}")
                print(f"Volume: {df.iloc[-1]['volume']:,.2f}")
            
            return df
            
        except Exception as e:
            print(f"Error fetching klines: {e}")
            import traceback
            print("\nFull error traceback:")
            print(traceback.format_exc())
            return None
            
    def get_current_price(self):
        """Get the current market price for the symbol"""
        try:
            # Get the latest bar
            df = self.get_klines(limit=1)
            if df is not None and not df.empty:
                return float(df.iloc[-1]['close'])
            return None
        except Exception as e:
            print(f"Error getting current price: {e}")
            return None

    def place_market_order(self, side, quantity):
        """Place a market order"""
        try:
            # Convert BTC/USD to BTCUSD for trading
            trading_symbol = SYMBOL.replace('/', '')
            
            order_data = MarketOrderRequest(
                symbol=trading_symbol,  # Use converted symbol
                qty=quantity,
                side=OrderSide.BUY if side == 'BUY' else OrderSide.SELL,
                time_in_force=TimeInForce.GTC
            )
            
            order = self.trading_client.submit_order(order_data)
            print(f"\nPlaced {'PAPER' if USE_PAPER else 'LIVE'} market order:")
            print(f"Side: {side}, Quantity: {quantity} {SYMBOL}")
            return order
            
        except Exception as e:
            print(f"Error placing market order: {e}")
            return None

    def place_limit_order(self, side, quantity, limit_price):
        """Place a limit order"""
        try:
            order_data = LimitOrderRequest(
                symbol=SYMBOL,
                qty=quantity,
                side=OrderSide.BUY if side == 'BUY' else OrderSide.SELL,
                time_in_force=TimeInForce.GTC,
                limit_price=limit_price
            )
            
            order = self.trading_client.submit_order(order_data)
            print(f"\nPlaced {'PAPER' if USE_PAPER else 'LIVE'} limit order:")
            print(f"Side: {side}, Quantity: {quantity}, Limit Price: {limit_price}")
            return order
            
        except Exception as e:
            print(f"Error placing limit order: {e}")
            return None

    def place_stop_order(self, side, quantity, stop_price):
        """Place a stop order"""
        try:
            order_data = StopOrderRequest(
                symbol=SYMBOL,
                qty=quantity,
                side=OrderSide.BUY if side == 'BUY' else OrderSide.SELL,
                time_in_force=TimeInForce.GTC,
                stop_price=stop_price
            )
            
            order = self.trading_client.submit_order(order_data)
            print(f"\nPlaced {'PAPER' if USE_PAPER else 'LIVE'} stop order:")
            print(f"Side: {side}, Quantity: {quantity}, Stop Price: {stop_price}")
            return order
            
        except Exception as e:
            print(f"Error placing stop order: {e}")
            return None

    def place_bracket_order(self, side, quantity, entry_price, stop_loss, take_profit):
        """
        Place a bracket order that includes an entry order with stop loss and take profit orders.
        
        Args:
            side (str): 'BUY' or 'SELL'
            quantity (float): Amount of crypto to trade
            entry_price (float): Current market price for entry
            stop_loss (float): Price level for stop loss
            take_profit (float): Price level for take profit
            
        Returns:
            dict: Order information if successful, None if failed
        """
        try:
            # Create the bracket order
            order_data = MarketOrderRequest(
                symbol=SYMBOL,
                qty=quantity,
                side=OrderSide.BUY if side == 'BUY' else OrderSide.SELL,
                time_in_force=TimeInForce.GTC,
                order_class='bracket',
                stop_loss=StopLossRequest(
                    stop_price=stop_loss,
                    limit_price=stop_loss * 0.99  # Set a limit price slightly below stop to ensure execution
                ),
                take_profit=TakeProfitRequest(
                    limit_price=take_profit
                )
            )
            
            order = self.trading_client.submit_order(order_data)
            
            print(f"\nBracket order submitted:")
            print(f"Entry Order ID: {order.id}")
            print(f"Stop Loss: ${stop_loss:,.2f}")
            print(f"Take Profit: ${take_profit:,.2f}")
            
            return order
            
        except Exception as e:
            print(f"Error placing bracket order: {e}")
            return None

    def get_position(self):
        """Get the current position for the symbol"""
        try:
            # Get all positions
            positions = self.trading_client.get_all_positions()
            
            # Convert BTC/USD to BTCUSD for position lookup
            trading_symbol = SYMBOL.replace('/', '')
            
            # Find our symbol's position
            for position in positions:
                if position.symbol == trading_symbol:  # Match against converted symbol
                    # Get values from position object
                    quantity = float(position.qty)
                    entry_price = float(position.avg_entry_price)
                    current_price = float(position.current_price)
                    market_value = float(position.market_value)
                    cost_basis = float(position.cost_basis)
                    
                    # Calculate P&L using cost basis
                    unrealized_pl = market_value - cost_basis
                    unrealized_plpc = (unrealized_pl / cost_basis) * 100
                    
                    return {
                        'symbol': SYMBOL,  # Keep original format in return
                        'qty': quantity,
                        'avg_entry_price': entry_price,
                        'current_price': current_price,
                        'market_value': market_value,
                        'cost_basis': cost_basis,
                        'unrealized_pl': unrealized_pl,
                        'unrealized_plpc': unrealized_plpc,
                        'side': position.side
                    }
            
            print(f"No open position found for {SYMBOL}")
            return None
            
        except Exception as e:
            print(f"Error getting position: {str(e)}")
            return None

    def get_account_balance(self):
        """Get account balance and positions"""
        try:
            account = self.trading_client.get_account()
            positions = self.trading_client.get_all_positions()
            
            # Format balances
            balances = {
                'buying_power': float(account.buying_power),
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'positions': {
                    pos.symbol: {
                        'qty': float(pos.qty),
                        'avg_price': float(pos.avg_entry_price),
                        'market_value': float(pos.market_value),
                        'unrealized_pl': float(pos.unrealized_pl)
                    } for pos in positions
                }
            }
            
            return balances
            
        except Exception as e:
            print(f"Error getting balance: {e}")
            return None

    def get_open_orders(self):
        """Get all open orders"""
        try:
            # Get all orders
            orders = self.trading_client.get_orders()
            
            # Filter for our symbol and open status
            trading_symbol = SYMBOL.replace('/', '')
            open_orders = [
                order for order in orders 
                if order.symbol == trading_symbol and order.status == 'open'
            ]
            
            return [{
                'id': order.id,
                'symbol': order.symbol,
                'side': order.side,
                'qty': float(order.qty),
                'filled_qty': float(order.filled_qty),
                'type': order.type,
                'status': order.status,
                'stop_price': float(order.stop_price) if hasattr(order, 'stop_price') and order.stop_price else None,
                'limit_price': float(order.limit_price) if hasattr(order, 'limit_price') and order.limit_price else None,
                'created_at': order.created_at
            } for order in open_orders]
        except Exception as e:
            print(f"Error getting open orders: {str(e)}")
            return None

    def get_account(self):
        """Get account information"""
        try:
            return self.trading_client.get_account()
        except Exception as e:
            print(f"Error getting account info: {str(e)}")
            return None

    def cancel_all_orders(self):
        """Cancel all open orders"""
        try:
            cancelled = self.trading_client.cancel_orders()
            print(f"Cancelled {len(cancelled)} orders")
            return cancelled
        except Exception as e:
            print(f"Error cancelling orders: {e}")
            return None

    def close_position(self):
        """Close the current position"""
        try:
            # Convert BTC/USD to BTCUSD for trading
            trading_symbol = SYMBOL.replace('/', '')
            
            # Get current position
            position = self.get_position()
            if not position:
                print(f"No position to close for {SYMBOL}")
                return False
            
            # Place market order to close
            side = 'SELL' if float(position['qty']) > 0 else 'BUY'
            qty = abs(float(position['qty']))
            
            print(f"\nClosing position: {side} {qty} {SYMBOL}")
            close_order = self.place_market_order(side, qty)
            return close_order is not None
            
        except Exception as e:
            print(f"Error closing position: {e}")
            return False

    def place_entry_order(self, side, quantity, stop_loss, take_profit):
        """Place an entry order and store exit levels for monitoring"""
        try:
            # Create the market order request
            order_data = MarketOrderRequest(
                symbol=SYMBOL,
                qty=quantity,
                side=OrderSide.BUY if side == 'BUY' else OrderSide.SELL,
                time_in_force=TimeInForce.GTC
            )
            
            # Submit the order
            order = self.trading_client.submit_order(order_data)
            print(f"\nPlaced {'PAPER' if USE_PAPER else 'LIVE'} market order:")
            print(f"Side: {side}, Quantity: {quantity}")
            
            # Store exit levels for monitoring
            self.exit_levels = {
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }
            
            print(f"\nOrder placed with exit levels:")
            print(f"Stop Loss: ${stop_loss:,.2f}")
            print(f"Take Profit: ${take_profit:,.2f}")
            
            return order
            
        except Exception as e:
            print(f"Error placing entry order: {e}")
            return None

    def check_exit_conditions(self):
        """Check if we should exit based on price levels"""
        try:
            # Get all positions
            positions = self.trading_client.get_all_positions()
            position = None
            
            # Find our position
            for pos in positions:
                if pos.symbol == SYMBOL.replace('/', ''):
                    position = pos
                    break
                    
            if not position or not hasattr(self, 'exit_levels'):
                return None
                
            # Get current price from position
            current_price = float(position.current_price)
            
            # Check stop loss
            if current_price <= self.exit_levels['stop_loss']:
                print(f"\nStop loss triggered at ${current_price:,.2f}")
                print(f"P&L: ${float(position.unrealized_pl):,.2f} ({float(position.unrealized_plpc) * 100:.2f}%)")
                self.trading_client.close_position(SYMBOL.replace('/', ''))
                return True
                
            # Check take profit
            if current_price >= self.exit_levels['take_profit']:
                print(f"\nTake profit triggered at ${current_price:,.2f}")
                print(f"P&L: ${float(position.unrealized_pl):,.2f} ({float(position.unrealized_plpc) * 100:.2f}%)")
                self.trading_client.close_position(SYMBOL.replace('/', ''))
                return True
                
            return None
            
        except Exception as e:
            print(f"Error checking exit conditions: {e}")
            return None

    def get_historical_bars(self, limit=100):
        """Get historical bars from Alpaca"""
        try:
            # Convert our interval to Alpaca's TimeFrame
            timeframe = self.timeframe_map.get(INTERVAL)
            if not timeframe:
                print(f"Unsupported interval: {INTERVAL}")
                return None

            # Convert BTC/USD to BTCUSD for Alpaca
            trading_symbol = SYMBOL.replace('/', '')

            # Create request
            request = CryptoBarsRequest(
                symbol_or_symbols=trading_symbol,
                timeframe=timeframe,
                limit=limit,
                feed=CryptoFeed.US
            )

            # Get bars
            print(f"\nFetching historical bars...")
            print(f"Using interval: {INTERVAL}")
            print(f"Symbol: {SYMBOL}")
            print("Requesting data from Alpaca...")
            bars = self.data_client.get_crypto_bars(request)
            
            # Convert to DataFrame
            print("Converting to DataFrame...")
            df = bars.df
            
            if df.empty:
                print("No data received from Alpaca")
                return None
                
            # Reset index to make timestamp a column
            df = df.reset_index()
            
            # Rename columns to match our format
            df = df.rename(columns={
                'timestamp': 'time',
                'close': 'close',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'volume': 'volume',  # This is the base volume
                'trade_count': 'trades',
                'vwap': 'vwap'
            })
            
            # Calculate quote volume (volume * close price)
            df['quote_volume'] = df['volume'] * df['close']
            
            # Set time as index
            df = df.set_index('time')
            
            # Print first and last bars for debugging
            print(f"\nRetrieved {len(df)} bars")
            print("\nFirst bar:")
            print(f"Time: {df.index[0]}")
            print(f"Close: ${df.iloc[0]['close']:,.2f}")
            print(f"Volume: ${df.iloc[0]['quote_volume']:,.2f}")
            
            print("\nLast bar:")
            print(f"Time: {df.index[-1]}")
            print(f"Close: ${df.iloc[-1]['close']:,.2f}")
            print(f"Volume: ${df.iloc[-1]['quote_volume']:,.2f}")
            
            return df
            
        except Exception as e:
            print(f"Error getting historical bars: {str(e)}")
            return None 