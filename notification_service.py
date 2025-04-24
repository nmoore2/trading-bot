import requests
from config import PUSHOVER_API_TOKEN, PUSHOVER_USER_KEY, SYMBOL

class NotificationService:
    def __init__(self):
        self.api_token = PUSHOVER_API_TOKEN
        self.user_key = PUSHOVER_USER_KEY
        self.base_url = "https://api.pushover.net/1/messages.json"
        
    def send_notification(self, title, message, priority=0):
        """Send a notification via Pushover"""
        try:
            data = {
                "token": self.api_token,
                "user": self.user_key,
                "title": title,
                "message": message,
                "priority": priority  # 0: normal, 1: high, 2: emergency
            }
            
            response = requests.post(self.base_url, data=data)
            response.raise_for_status()
            return True
            
        except Exception as e:
            print(f"Error sending notification: {e}")
            return False
            
    def send_trading_signal(self, trade_info, gpt_analysis, executed_trade=None):
        """Format and send a trading signal notification"""
        # Extract trade decision from GPT analysis
        decision = "WAIT"
        if "buy" in gpt_analysis.lower() or "long" in gpt_analysis.lower():
            decision = "BUY"
        elif "sell" in gpt_analysis.lower() or "short" in gpt_analysis.lower():
            decision = "SELL"
            
        # Format the signal info
        signal_msg = f"""🔔 {SYMBOL} Signal ({decision})

Entry: ${trade_info['levels']['entry']:.2f}
SL: ${trade_info['levels']['stop_loss']:.2f}
TP: ${trade_info['levels']['target']:.2f}
R/R: {trade_info['levels']['risk_reward_ratio']:.2f}

Strength: {trade_info['signal_strength']:.1f}%
RSI: {trade_info['metrics']['rsi']:.1f}
Vol: {trade_info['metrics']['volume_ratio']:.1f}x"""

        # Add trade execution info if available
        if executed_trade:
            signal_msg += f"\n\n✅ Trade Executed"
        else:
            if decision == "WAIT":
                signal_msg += "\n\n⏸ Waiting - No trade"
            else:
                signal_msg += "\n\n❌ Execution failed"
        
        # Send the notification with high priority
        return self.send_notification(
            title="🚨 Signal Alert",
            message=signal_msg,
            priority=1  # High priority
        )
        
    def send_trade_closed(self, trade, exit_price, reason):
        """Send notification when a trade is closed"""
        message = f"""
🔄 Trade Closed

Symbol: {SYMBOL}
Exit Price: ${exit_price:,.2f}
Reason: {reason}

Trade Summary:
Entry: ${trade['entry_price']:,.2f}
Quantity: {trade['quantity']}
P&L: ${trade['pnl']:,.2f} ({trade['pnl_percent']:,.2f}%)

Trade Duration: {trade['exit_time'][:19]} - {trade['entry_time'][:19]}
"""
        
        # Determine emoji based on P&L
        title_emoji = "🟢" if trade['pnl'] > 0 else "🔴"
        
        return self.send_notification(
            title=f"{title_emoji} Trade Closed",
            message=message,
            priority=1
        )
        
    def send_error(self, error_msg):
        """Send error notification"""
        return self.send_notification(
            title="⚠️ Trading Bot Error",
            message=error_msg,
            priority=2  # Emergency priority for errors
        ) 