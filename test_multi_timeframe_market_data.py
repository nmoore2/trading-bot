import json
import time
from datetime import datetime, timezone, timedelta
from binance_client import BinanceClient
from indicators import TechnicalIndicators
import pandas as pd
from config import SYMBOL
import os
from openai import OpenAI
from config import OPENAI_API_KEY
from notification_service import NotificationService
from hyperliquid_trader import execute_trade, get_open_position
import tiktoken
import logging

# Configure logging to filter out httpx logs
logging.getLogger("httpx").setLevel(logging.WARNING)

# Initialize services
client = OpenAI(api_key=OPENAI_API_KEY)
notification_service = NotificationService()

def get_klines_df(client, interval, limit):
    klines = client.get_futures_klines(interval=interval, limit=limit)
    columns = [
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'buy_base_volume',
        'buy_quote_volume', 'ignore'
    ]
    df = pd.DataFrame(klines, columns=columns)
    df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']] = df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    # Always use quote_volume for volume analysis
    df['volume'] = df['quote_volume']
    return TechnicalIndicators.calculate_all_indicators(df)

def detect_trend(df):
    if 'ema_20' in df.columns:
        if df.iloc[-1]['close'] > df.iloc[-1]['ema_20']:
            return 'bullish'
        elif df.iloc[-1]['close'] < df.iloc[-1]['ema_20']:
            return 'bearish'
    return 'neutral'

def find_last_swing_high_low(df, lookback=20):
    highs = df['high'].tail(lookback)
    lows = df['low'].tail(lookback)
    return highs.max(), lows.min()

def get_session_stats(df):
    df['date'] = df.index.date
    curr_session = df[df['date'] == df['date'].unique()[-1]]
    session_open = curr_session['open'].iloc[0] if not curr_session.empty else None
    session_high = curr_session['high'].max() if not curr_session.empty else None
    session_low = curr_session['low'].min() if not curr_session.empty else None
    return session_open, session_high, session_low

def get_rsi(df):
    return float(df['rsi'].iloc[-1]) if 'rsi' in df.columns else None

def get_volume_metrics(df):
    last = df.iloc[-1]
    return {
        "current": float(last['volume']),
        "relative_to_5bar": float(last['volume_ratio_5']) if 'volume_ratio_5' in last else None,
        "relative_to_20bar": float(last['volume_ratio_20']) if 'volume_ratio_20' in last else None,
        "trend": float(last['volume_trend']*100) if 'volume_trend' in last else None
    }

def get_recent_footprint(df, n=3):
    footprints = []
    for i in range(-n, 0):
        if len(df) + i < 1:
            continue
        bar = df.iloc[i]
        prev_cvd = df.iloc[i-1]['cvd'] if (i-1) >= -len(df) else 0
        delta = bar['cvd'] - prev_cvd
        volume = bar['quote_volume'] if 'quote_volume' in bar else bar['volume']
        footprints.append({
            "time": bar.name.strftime("%H:%M"),
            "delta": delta,
            "volume": volume
        })
    return footprints

def get_delta_clusters(df, threshold=500_000):
    clusters = []
    for i in range(-5, 0):
        if len(df) + i < 1:
            continue
        bar = df.iloc[i]
        prev_cvd = df.iloc[i-1]['cvd'] if (i-1) >= -len(df) else 0
        delta = bar['cvd'] - prev_cvd
        if abs(delta) > threshold:
            clusters.append({
                "price": bar['close'],
                "delta": delta
            })
    return clusters

def get_oi_change_ma(oi_change_history, window=5):
    if len(oi_change_history) < window:
        return 0
    return sum(abs(x) for x in oi_change_history[-window:]) / window

# --- Signal-worthy event detection ---
def shouldSendToGPT(snapshot, last_sent_time, oi_change_history, min_interval_minutes=30, last_recommendation=None, last_confidence=None):
    now = datetime.now(timezone.utc)
    # Cooldown: Only call GPT if >3min since last call, unless last confidence >= 0.85
    if last_sent_time is not None:
        time_since_last = (now - last_sent_time).total_seconds() / 60
        if time_since_last < 3 and (last_confidence is None or last_confidence < 0.85):
            return False, 'cooldown'
    
    # 1. Sudden delta imbalance
    last_delta = snapshot['recent_footprint'][-1]['delta'] if snapshot.get('recent_footprint') else 0
    if abs(last_delta) > 3_000_000:
        return True, 'delta_imbalance'
    
    # 2. Significant open interest change (dynamic threshold)
    oi_change = None  # Not available in flat snapshot unless you add it
    avg_oi_change_5bar = get_oi_change_ma(oi_change_history, window=5)
    isOITriggered = (
        oi_change is not None and
        abs(oi_change) > 100 and
        abs(oi_change) > avg_oi_change_5bar * 2
    )
    if isOITriggered:
        return True, 'oi_change_dynamic'
    
    # 3. Price touches/crosses key levels
    price = snapshot['ltf_price']
    htf_swing_high = snapshot['htf_swing_high']
    htf_swing_low = snapshot['htf_swing_low']
    htf_vwap = snapshot['htf_vwap']
    ltf_vwap = snapshot['ltf_vwap']
    delta_clusters = [c['price'] for c in snapshot.get('delta_clusters',[])]
    if (
        abs(price - htf_swing_high) < 1 or
        abs(price - htf_swing_low) < 1 or
        abs(price - htf_vwap) < 1 or
        abs(price - ltf_vwap) < 1 or
        any(abs(price - dc) < 1 for dc in delta_clusters)
    ):
        return True, 'key_level_touch'
    
    # 4. Divergence (simplified for flat structure)
    htf_rsi = snapshot.get('htf_rsi')
    ltf_rsi = snapshot.get('ltf_rsi')
    # High delta but low volume
    last_volume = snapshot.get('ltf_volume')
    # rel_vol not available in flat snapshot unless you add it
    if abs(last_delta) > 3_000_000 and last_volume is not None and last_volume < 0.5:
        return True, 'high_delta_low_vol'
    # High volume but low delta
    if last_volume is not None and last_volume > 5_000_000 and abs(last_delta) < 0.1 * last_volume:
        return True, 'high_vol_low_delta'
    
    # --- Always send if max interval exceeded ---
    if last_sent_time is None or (now - last_sent_time > timedelta(minutes=min_interval_minutes)):
        return True, 'max_interval'
    
    return False, 'suppressed'

def count_tokens(text, model="gpt-4"):
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))

def flatten_snapshot(htf_df, ltf_df):
    # Get last values
    htf_price = round(float(htf_df.iloc[-1]['close']), 2)
    htf_vwap = round(float(htf_df.iloc[-1]['vwap']), 2) if 'vwap' in htf_df.columns else None
    htf_trend = detect_trend(htf_df)
    htf_swing_high, htf_swing_low = find_last_swing_high_low(htf_df)
    htf_rsi = get_rsi(htf_df)
    
    ltf_price = round(float(ltf_df.iloc[-1]['close']), 2)
    ltf_vwap = round(float(ltf_df.iloc[-1]['vwap']), 2) if 'vwap' in ltf_df.columns else None
    ltf_rsi = get_rsi(ltf_df)
    ltf_oi = None
    ltf_cvd = None
    if 'oi' in ltf_df.columns:
        ltf_oi = round(float(ltf_df.iloc[-1]['oi']), 2)
    if 'cvd' in ltf_df.columns:
        ltf_cvd = round(float(ltf_df.iloc[-1]['cvd']), 2)
    ltf_volume = round(float(ltf_df.iloc[-1]['volume']), 2)
    
    # Delta clusters (last 2)
    delta_clusters = get_delta_clusters(ltf_df, threshold=500_000)
    delta_clusters = delta_clusters[-2:] if len(delta_clusters) > 2 else delta_clusters
    # Recent footprint (last 2)
    recent_footprint = get_recent_footprint(ltf_df, n=2)
    
    # Flattened dict
    return {
        "htf_price": htf_price,
        "htf_vwap": htf_vwap,
        "htf_trend": htf_trend,
        "htf_swing_high": round(float(htf_swing_high), 2),
        "htf_swing_low": round(float(htf_swing_low), 2),
        "htf_rsi": round(float(htf_rsi), 2) if htf_rsi is not None else None,
        "ltf_price": ltf_price,
        "ltf_vwap": ltf_vwap,
        "ltf_rsi": round(float(ltf_rsi), 2) if ltf_rsi is not None else None,
        "ltf_oi": ltf_oi,
        "ltf_cvd": ltf_cvd,
        "ltf_volume": ltf_volume,
        "delta_clusters": [
            {"price": round(c["price"], 2), "delta": round(c["delta"], 2)} for c in delta_clusters
        ],
        "recent_footprint": [
            {"time": f["time"], "delta": round(f["delta"], 2), "volume": round(f["volume"], 2)} for f in recent_footprint
        ]
    }

def send_to_gpt(market_snapshot, trigger_reason):
    GPT_PROMPT = r"""
You are a crypto trading assistant. Given a real-time BTCUSDT market snapshot (flat JSON, see below), respond with a flat JSON object containing:
- recommendation: "ENTER LONG", "ENTER SHORT", or "WAIT"
- entry: number or null
- stop_loss: number or null
- take_profit: number or null
- confidence: float (0.0–1.0)
- explanation: short reason (3-7 words)

Use only the provided fields (support, resistance, VWAP, trend, RSI, OI, CVD, delta, volume, clusters, footprint) to make your decision. If no valid trade exists, return "WAIT".

Output ONLY the JSON.
"""
    prompt = GPT_PROMPT + "\n" + json.dumps(market_snapshot, indent=2)

    # Count input tokens
    input_tokens = count_tokens(prompt, model="gpt-4")
    print(f"[TOKENS] Input tokens: {input_tokens}")

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content

        # Count output tokens
        output_tokens = count_tokens(content, model="gpt-4")
        print(f"[TOKENS] Output tokens: {output_tokens}")
        print("🤖 [ChatGPT] Request successful.")

        # Only print the raw JSON response
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🚨 \033[1mGPT JSON Response\033[0m:")
        try:
            parsed = json.loads(content)
            rec_emoji = {
                "ENTER LONG": "🟢",
                "ENTER SHORT": "🔴",
                "WAIT": "⏸️"
            }.get(parsed.get("recommendation", "WAIT"), "❓")
            print(json.dumps(parsed, indent=2))
            print(f"{rec_emoji} Recommendation: {parsed.get('recommendation')}  |  💬 Explanation: {parsed.get('explanation')}")
        except Exception:
            print(content)
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        gpt_recommendation = json.loads(content)
        def format_price(price):
            if price is None:
                return "N/A"
            return f"${price:,.2f}"
        current_price = market_snapshot.get('ltf_price')
        htf_trend = market_snapshot.get('htf_trend')
        ltf_rsi = market_snapshot.get('ltf_rsi')
        htf_rsi = market_snapshot.get('htf_rsi')
        explanation = gpt_recommendation.get('explanation', '')
        symbol = "BTCUSD"
        message = f"""
🔔 {symbol} Signal Analysis

📊 Market Context:
Price: {format_price(current_price)}
HTF Trend: {htf_trend.upper()}
RSI (LTF/HTF): {ltf_rsi:.1f}/{htf_rsi:.1f}

🚨 Trigger: {trigger_reason}

🤖 GPT Analysis:
Recommendation: {gpt_recommendation['recommendation']}
Entry: {format_price(gpt_recommendation['entry'])}
Stop Loss: {format_price(gpt_recommendation['stop_loss'])}
Take Profit: {format_price(gpt_recommendation['take_profit'])}
Confidence: {gpt_recommendation['confidence']:.2f}
Explanation: {explanation}
"""
        return gpt_recommendation['recommendation'], gpt_recommendation.get('confidence', 0.0), gpt_recommendation
    except json.JSONDecodeError as e:
        error_msg = f"Error parsing GPT response: {str(e)}\nResponse: {content}"
        print(error_msg)
        notification_service.send_notification(
            title="⚠️ GPT Response Error",
            message=error_msg,
            priority=0
        )
        return "WAIT", 0.0, None
    except Exception as e:
        error_msg = f"Error in GPT analysis: {str(e)}"
        print(error_msg)
        notification_service.send_notification(
            title="⚠️ Trading Bot Error",
            message=error_msg,
            priority=0
        )
        return "WAIT", 0.0, None

def calculate_risk_reward(entry, stop_loss, take_profit, side):
    if None in (entry, stop_loss, take_profit):
        return None
    if side == 'BUY':
        risk = entry - stop_loss
        reward = take_profit - entry
    else:  # 'SELL'
        risk = stop_loss - entry
        reward = entry - take_profit
    if risk <= 0:
        return None
    return reward / risk

if __name__ == "__main__":
    binance_client = BinanceClient()
    prev_oi = None
    last_sent_time = None
    last_recommendation = None
    last_confidence = None
    oi_change_history = []
    first_run = True

    while True:
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        # --- HTF (30m) ---
        htf_df = get_klines_df(binance_client, interval='30m', limit=50)
        # --- LTF (1m) ---
        ltf_df = get_klines_df(binance_client, interval='1m', limit=200)

        if first_run:
            print("[INFO] Initial data pull complete. Waiting for next data to enable signal detection.")
            first_run = False
            time.sleep(30)
            continue

        htf_price = float(htf_df.iloc[-1]['close'])
        htf_vwap = float(htf_df.iloc[-1]['vwap']) if 'vwap' in htf_df.columns else None
        htf_trend = detect_trend(htf_df)
        htf_swing_high, htf_swing_low = find_last_swing_high_low(htf_df)
        htf_key_levels = [
            {"type": "resistance", "label": "HTF_SwingHigh", "price": float(htf_swing_high)},
            {"type": "support", "label": "HTF_SwingLow", "price": float(htf_swing_low)}
        ]
        htf_rsi = get_rsi(htf_df)
        htf_volume = get_volume_metrics(htf_df)

        ltf_price = float(ltf_df.iloc[-1]['close'])
        ltf_vwap = float(ltf_df.iloc[-1]['vwap']) if 'vwap' in ltf_df.columns else None
        ltf_session_open, ltf_session_high, ltf_session_low = get_session_stats(ltf_df)
        ltf_oi_now = binance_client.get_futures_open_interest()
        ltf_oi = float(ltf_oi_now['openInterest']) if ltf_oi_now and 'openInterest' in ltf_oi_now else None
        ltf_cvd = float(ltf_df.iloc[-1]['cvd']) if 'cvd' in ltf_df.columns else None
        ltf_rsi = get_rsi(ltf_df)
        ltf_volume = get_volume_metrics(ltf_df)

        # OI change
        ltf_oi_change = None
        if prev_oi is not None and ltf_oi is not None:
            ltf_oi_change = ltf_oi - prev_oi
        prev_oi = ltf_oi
        if ltf_oi_change is not None:
            oi_change_history.append(ltf_oi_change)

        # Recent footprint
        recent_footprint = get_recent_footprint(ltf_df, n=3)
        # Delta clusters
        delta_clusters = get_delta_clusters(ltf_df, threshold=500_000)

        # Compose the payload
        payload = flatten_snapshot(htf_df, ltf_df)

        # Check if we should send to GPT
        should_send, trigger_reason = shouldSendToGPT(payload, last_sent_time, oi_change_history, last_recommendation=last_recommendation, last_confidence=last_confidence)

        if should_send:
            print(f"\nSignal detected: {trigger_reason}")
            last_recommendation, last_confidence, gpt_data = send_to_gpt(payload, trigger_reason)
            last_sent_time = datetime.now(timezone.utc)
            # --- Hyperliquid trade execution ---
            if last_recommendation and last_recommendation.startswith("ENTER"):
                entry_price = float(gpt_data.get('entry')) if gpt_data and gpt_data.get('entry') not in [None, "null", "None", ""] else None
                stop_loss = float(gpt_data.get('stop_loss')) if gpt_data and gpt_data.get('stop_loss') not in [None, "null", "None", ""] else None
                take_profit = float(gpt_data.get('take_profit')) if gpt_data and gpt_data.get('take_profit') not in [None, "null", "None", ""] else None
                side = 'BUY' if "LONG" in last_recommendation else 'SELL'
                rr = calculate_risk_reward(entry_price, stop_loss, take_profit, side)
                threshold = 1.0
                trade_icon = "🟢" if rr is not None and rr >= threshold else "🟡"
                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print(f"🚨 \033[1mTRADE DECISION\033[0m {trade_icon}")
                print(f"📊 Risk/Reward: \033[1m{rr:.1f}\033[0m")
                if rr is None or rr < threshold:
                    print(f"❌ \033[1mSKIPPED\033[0m: Risk/reward below threshold for {side} entry {entry_price}, SL {stop_loss}, TP {take_profit}.")
                else:
                    print(f"🚀 \033[1mTRADE PROCEEDING\033[0m: Risk/reward meets threshold for {side} entry {entry_price}, SL {stop_loss}, TP {take_profit}.")
                    signal = {
                        "side": side,
                        "symbol": "BTC",  # or dynamic if you want
                        "size": 0.001,
                        "order_type": "limit" if entry_price else "market",
                        "limit_price": entry_price,
                        "stop_loss": stop_loss,
                        "take_profit": take_profit
                    }
                    pos = get_open_position(signal["symbol"])
                    new_side = 'LONG' if signal["side"] == 'BUY' else 'SHORT'
                    if pos['side'] == new_side and abs(pos['size']) > 0:
                        print(f"⏸️ \033[1mSKIPPED\033[0m: Already in a {pos['side']} position of size {pos['size']} for {signal['symbol']}.")
                    else:
                        print(f"🚀 \033[1mPLACING TRADE\033[0m: {signal}")
                        try:
                            result = execute_trade(signal)
                            print("Hyperliquid trade result:", result)
                            if result and result.get("main_order") and result["main_order"].get("status") == "ok":
                                print("✅ \033[1mTrade placed successfully on Hyperliquid.\033[0m")
                                if result.get("sl_order_id"):
                                    print(f"🛑 Stop loss order ID: {result['sl_order_id']}")
                                if result.get("tp_order_id"):
                                    print(f"🎯 Take profit order ID: {result['tp_order_id']}")
                                # Only send notification if trade is placed
                                notification_service.send_notification(
                                    title=f"{side} | R/R {rr:.1f} | BTCUSD",  # Side and risk/reward in preview
                                    message=f"{side} trade placed at {entry_price} (SL: {stop_loss}, TP: {take_profit}, R/R: {rr:.1f})",
                                    priority=1
                                )
                                print(f"[Pushover] Notification sent.")
                            else:
                                print("❌ \033[1mTrade failed or was not accepted by Hyperliquid.\033[0m")
                        except Exception as e:
                            print(f"❌ \033[1mError placing trade on Hyperliquid: {e}\033[0m")
                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
            # --- End Hyperliquid trade execution ---
        else:
            print(f"Pull: No signal detected (last trigger: {trigger_reason})")

        time.sleep(30) 