import sqlite3
from datetime import datetime
import json
import numpy as np

class TradeHistory:
    def __init__(self):
        self.conn = sqlite3.connect('trade_history.db')
        self.create_tables()
        
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Drop existing table if it exists
        cursor.execute('DROP TABLE IF EXISTS trades')
        
        # Create new table with updated schema
        cursor.execute('''
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                strategy TEXT,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                exit_price REAL,
                quantity REAL,
                stop_loss REAL,
                take_profit REAL,
                pnl REAL,
                pnl_percent REAL,
                duration_seconds INTEGER,
                signals TEXT,
                signal_label TEXT,
                status TEXT
            )
        ''')
        self.conn.commit()
        
    def log_trade(self, strategy, symbol, side, entry_price, quantity, stop_loss, take_profit, signals):
        """Log a new trade"""
        try:
            # Convert numpy booleans to Python booleans for JSON serialization
            signals_serializable = {
                k: bool(v) if isinstance(v, (np.bool_, bool)) else v
                for k, v in signals.items()
            }
            
            # If signals is a nested dictionary, convert those values too
            if isinstance(signals, dict):
                for k, v in signals.items():
                    if isinstance(v, dict):
                        signals_serializable[k] = {
                            sub_k: bool(sub_v) if isinstance(sub_v, (np.bool_, bool)) else sub_v
                            for sub_k, sub_v in v.items()
                        }
            
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO trades (
                    timestamp, strategy, symbol, side, entry_price, quantity,
                    stop_loss, take_profit, signals, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                strategy,
                symbol,
                side,
                entry_price,
                quantity,
                stop_loss,
                take_profit,
                json.dumps(signals_serializable),
                'open'
            ))
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error logging trade: {e}")
            return None
        
    def _generate_signal_label(self, strategy, signals):
        """Generate a descriptive label for the signal combination"""
        if strategy == 'original':
            if all(signals.values()):
                return "Full Setup"
            active_signals = [k for k, v in signals.items() if v]
            if active_signals:
                return f"Partial: {', '.join(active_signals)}"
            return "No Signals"
            
        elif strategy == 'momentum':
            label_parts = []
            if signals.get('price_above_ema'):
                label_parts.append("Price>EMA")
            if signals.get('higher_highs'):
                label_parts.append("Higher Highs")
            if signals.get('higher_lows'):
                label_parts.append("Higher Lows")
            if signals.get('volume_above_avg'):
                label_parts.append("Volume>Avg")
            if signals.get('rsi_above_threshold'):
                label_parts.append("RSI>40")
                
            if label_parts:
                return f"Momentum: {', '.join(label_parts)}"
            return "No Momentum"
            
        return "Unknown Strategy"
        
    def close_trade(self, trade_id, exit_price):
        cursor = self.conn.cursor()
        cursor.execute('SELECT entry_price, quantity FROM trades WHERE id = ?', (trade_id,))
        trade = cursor.fetchone()
        
        if trade:
            entry_price, quantity = trade
            pnl = (exit_price - entry_price) * quantity
            pnl_percent = (exit_price - entry_price) / entry_price * 100
            
            cursor.execute('''
                UPDATE trades 
                SET exit_price = ?, pnl = ?, pnl_percent = ?, status = 'CLOSED'
                WHERE id = ?
            ''', (exit_price, pnl, pnl_percent, trade_id))
            self.conn.commit()
            
    def get_strategy_stats(self, strategy):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(pnl) as total_pnl,
                AVG(pnl_percent) as avg_pnl_percent,
                AVG(duration_seconds) as avg_duration
            FROM trades 
            WHERE strategy = ? AND status = 'CLOSED'
        ''', (strategy,))
        
        stats = cursor.fetchone()
        if stats:
            return {
                'total_trades': stats[0],
                'winning_trades': stats[1],
                'total_pnl': stats[2],
                'avg_pnl_percent': stats[3],
                'avg_duration': stats[4]
            }
        return None
        
    def get_open_trades(self, strategy=None):
        cursor = self.conn.cursor()
        if strategy:
            cursor.execute('SELECT * FROM trades WHERE status = "OPEN" AND strategy = ?', (strategy,))
        else:
            cursor.execute('SELECT * FROM trades WHERE status = "OPEN"')
        return cursor.fetchall()
        
    def get_signal_stats(self):
        """Get statistics grouped by signal label"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                signal_label,
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(pnl) as total_pnl,
                AVG(pnl_percent) as avg_pnl_percent,
                AVG(duration_seconds) as avg_duration
            FROM trades 
            WHERE status = 'CLOSED'
            GROUP BY signal_label
            ORDER BY total_trades DESC
        ''')
        
        return cursor.fetchall()
        
    def __del__(self):
        self.conn.close() 