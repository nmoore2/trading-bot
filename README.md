# AI Trading Signals Bot

An automated cryptocurrency trading bot that uses technical analysis and AI-driven signals to execute trades on Alpaca Markets.

## Features

- Real-time market data monitoring
- Technical analysis indicators (RSI, Volume, CVD)
- Automated trade execution with bracket orders
- Stop loss and take profit management
- Position tracking and P&L monitoring
- Trade history logging
- Paper trading support

## Requirements

- Python 3.8+
- Alpaca Markets account (with API keys)
- Required Python packages (see requirements.txt)

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-trading-signals.git
cd ai-trading-signals
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `config.py` file with your Alpaca API credentials:
```python
ALPACA_API_KEY = 'your_api_key'
ALPACA_API_SECRET = 'your_api_secret'
SYMBOL = 'BTC/USD'
INTERVAL = '1m'
USE_PAPER = True  # Set to False for live trading
```

## Usage

Run the trading bot:
```bash
python main.py
```

Close all positions:
```bash
python close_position.py
```

## Configuration

- `SYMBOL`: Trading pair (default: BTC/USD)
- `INTERVAL`: Timeframe for analysis (1m, 5m, 15m, 1h, 1d)
- `USE_PAPER`: Toggle between paper trading and live trading

## Safety Features

- Automatic stop loss and take profit orders
- Position size management (1% of portfolio per trade)
- Error handling and logging
- Paper trading mode for testing

## Disclaimer

This software is for educational purposes only. Use at your own risk. The authors take no responsibility for any financial losses incurred through the use of this software. 