from datetime import datetime
import json
from pathlib import Path
from notification_service import NotificationService

class TradingService:
    def __init__(self, alpaca_client):
        self.client = alpaca_client
        self.trades_file = Path('trades.json')
        self.trades = self._load_trades()
        self.notifier = NotificationService()
        
    def _load_trades(self):
        """Load trades from file"""
        if self.trades_file.exists():
            with open(self.trades_file, 'r') as f:
                return json.load(f)
        return {'open_trades': [], 'closed_trades': []}
        
    def _save_trades(self):
        """Save trades to file"""
        with open(self.trades_file, 'w') as f:
            json.dump(self.trades, f, indent=2)
            
    def execute_signal(self, signal):
        """Execute a trading signal by placing orders and recording the trade"""
        try:
            # Get current price for entry
            current_price = self.client.get_current_price()
            if not current_price:
                print("Failed to get current price")
                return None

            # Calculate position size based on risk management
            quantity = self.calculate_position_size(current_price, signal['stop_loss'])
            if not quantity:
                print("Position size calculation failed")
                return None

            # Place bracket order with entry, stop loss, and take profit
            order = self.client.place_bracket_order(
                side=signal['side'],
                quantity=quantity,
                entry_price=current_price,
                stop_loss=signal['stop_loss'],
                take_profit=signal['take_profit']
            )
            
            if not order:
                print("Failed to place bracket order")
                self.notifier.send_error("Failed to place bracket order")
                return None

            # Record the trade
            trade = {
                'order_id': order['id'],
                'entry_time': datetime.now().isoformat(),
                'entry_price': current_price,
                'side': signal['side'],
                'quantity': quantity,
                'stop_loss': signal['stop_loss'],
                'take_profit': signal['take_profit'],
                'status': 'open',
                'signal_data': signal['data']
            }
            
            # Add to open trades and save
            self.trades['open_trades'].append(trade)
            self._save_trades()
            
            # Send notification
            self.notifier.send_trade_opened(trade)
            
            return trade
            
        except Exception as e:
            print(f"Error executing signal: {str(e)}")
            self.notifier.send_error(f"Error executing signal: {str(e)}")
            return None
        
    def open_trade(self, entry_price, quantity, stop_loss, target):
        """Record a new trade"""
        trade = {
            'entry_time': datetime.now().isoformat(),
            'entry_price': entry_price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'target': target,
            'status': 'open'
        }
        self.trades['open_trades'].append(trade)
        self._save_trades()
        return trade
        
    def close_trade(self, trade, exit_price, reason):
        """Close an existing trade"""
        # Close the position in Alpaca
        position = self.client.get_position()
        if not position:
            print("No open position found in Alpaca")
            return None

        # Cancel any existing orders for this position
        self.client.cancel_all_orders()
            
        # Close the position with a market order
        result = self.client.close_position()
        if not result:
            print("Failed to close position in Alpaca")
            self.notifier.send_error(f"Failed to close position in Alpaca\nReason: {reason}")
            return None
            
        trade['exit_time'] = datetime.now().isoformat()
        trade['exit_price'] = exit_price
        trade['status'] = 'closed'
        trade['reason'] = reason
        
        # Calculate P&L
        pnl = float(position['unrealized_pl'])  # Use actual unrealized P&L from position
        trade['pnl'] = pnl
        trade['pnl_percent'] = float(position['unrealized_plpc']) * 100  # Use actual P&L percentage
        
        # Move from open to closed trades
        self.trades['open_trades'].remove(trade)
        self.trades['closed_trades'].append(trade)
        self._save_trades()
        
        # Send notification
        self.notifier.send_trade_closed(trade, exit_price, reason)
        
        return trade
        
    def calculate_position_size(self, entry_price, stop_loss):
        """Calculate position size based on risk management rules"""
        try:
            # Get account balance
            account = self.client.get_account_balance()
            if not account:
                print("Failed to get account balance")
                return None
                
            portfolio_value = float(account['portfolio_value'])
            risk_amount = portfolio_value * 0.001  # Risk 0.1% of portfolio per trade
            
            # Calculate risk per unit
            risk_per_unit = abs(entry_price - stop_loss)
            if risk_per_unit <= 0:
                print("Invalid risk per unit")
                return None
                
            # Calculate quantity
            quantity = risk_amount / risk_per_unit
            quantity = round(quantity, 6)  # Round to 6 decimal places for crypto
            
            print(f"\nPosition Size Calculation:")
            print(f"Portfolio Value: ${portfolio_value:,.2f}")
            print(f"Risk Amount: ${risk_amount:,.2f}")
            print(f"Risk Per Unit: ${risk_per_unit:,.2f}")
            print(f"Quantity: {quantity}")
            
            return quantity
            
        except Exception as e:
            print(f"Error calculating position size: {e}")
            return None
        
    def get_unrealized_pnl(self):
        """Calculate unrealized P&L for open trades"""
        position = self.client.get_position()
        if position:
            return float(position['unrealized_pl'])
        return 0
        
    def get_realized_pnl(self):
        """Calculate realized P&L from closed trades"""
        return sum(trade['pnl'] for trade in self.trades['closed_trades'])
        
    def get_total_pnl(self):
        """Get total P&L (realized + unrealized)"""
        return self.get_realized_pnl() + self.get_unrealized_pnl()
        
    def get_trade_stats(self):
        """Get trading statistics"""
        closed_trades = self.trades['closed_trades']
        if not closed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0
            }
            
        winning_trades = [t for t in closed_trades if t['pnl'] > 0]
        losing_trades = [t for t in closed_trades if t['pnl'] <= 0]
        
        total_trades = len(closed_trades)
        win_rate = len(winning_trades) / total_trades * 100
        
        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor
        } 