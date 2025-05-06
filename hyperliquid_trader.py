import example_utils
from hyperliquid.utils import constants
from hyperliquid.utils.error import ServerError
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def round_price(price, symbol=None):
    """Round price to avoid floating point issues. For BTC, use whole numbers."""
    if symbol and symbol.upper() == "BTC":
        return round(float(price))
    return round(float(price), 1)

def setup_exchange(max_retries=3, retry_delay=5):
    """Setup exchange connection with retry logic"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to Hyperliquid (attempt {attempt + 1}/{max_retries})")
            address, info, exchange = example_utils.setup(base_url=constants.TESTNET_API_URL, skip_ws=True)
            logger.info("Successfully connected to Hyperliquid")
            return address, info, exchange
        except ServerError as e:
            if e.status_code == 502:
                if attempt < max_retries - 1:
                    logger.warning(f"Hyperliquid API temporarily unavailable (502). Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
            logger.error(f"Failed to connect to Hyperliquid: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to Hyperliquid: {str(e)}")
            raise

# Setup once at module load with retry logic
address, info, exchange = setup_exchange()

def execute_trade(signal):
    """
    Executes a trade on Hyperliquid based on the provided signal dict.
    signal = {
        "side": "BUY" or "SELL",
        "symbol": "BTC" or "ETH",
        "size": float,
        "order_type": "market" or "limit",
        "limit_price": float (optional, required for limit),
        "stop_loss": float (optional),
        "take_profit": float (optional)
    }
    """
    try:
        is_buy = signal["side"].upper() == "BUY"
        symbol = signal["symbol"]
        size = signal["size"]
        
        # Execute main order
        if signal["order_type"] == "market":
            # For market orders, we'll use a very aggressive limit price to ensure execution
            current_price = 94000  # Approximate current BTC price
            limit_price = round_price(current_price * 1.1 if is_buy else current_price * 0.9, symbol)
            result = exchange.order(symbol, is_buy, size, limit_price, {"limit": {"tif": "Gtc"}})
            logger.info("Market order result: %s", result)
        elif signal["order_type"] == "limit":
            limit_price = signal.get("limit_price")
            if limit_price is None:
                raise ValueError("Limit price must be provided for limit orders.")
            limit_price = round_price(limit_price, symbol)
            result = exchange.order(symbol, is_buy, size, limit_price, {"limit": {"tif": "Gtc"}})
            logger.info("Limit order result: %s", result)
        else:
            raise ValueError("Unknown order type: {}".format(signal["order_type"]))
        
        if result.get("status") != "ok":
            logger.error("❌ Main order failed, not placing SL/TP")
            return result
        
        # Place stop loss if provided
        sl_order_id = None
        if "stop_loss" in signal and signal["stop_loss"] is not None:
            sl_trigger = round_price(signal["stop_loss"], symbol)
            # For a long, order price should be even lower; for a short, even higher
            if is_buy:
                sl_order_price = round_price(sl_trigger * 0.99, symbol)  # 1% below trigger
            else:
                sl_order_price = round_price(sl_trigger * 1.01, symbol)  # 1% above trigger
            logger.info(f"Attempting to place stop loss order: trigger={sl_trigger}, order_price={sl_order_price}")
            stop_order_type = {
                "trigger": {
                    "triggerPx": sl_trigger,
                    "isMarket": True,
                    "tpsl": "sl"
                }
            }
            sl_result = exchange.order(
                symbol,
                not is_buy,  # Opposite side of main order
                size,
                sl_order_price,
                stop_order_type,
                reduce_only=True
            )
            logger.info("Stop loss order result: %s", sl_result)
            if sl_result.get("status") == "ok" and "resting" in sl_result["response"]["data"]["statuses"][0]:
                sl_order_id = sl_result["response"]["data"]["statuses"][0]["resting"]["oid"]
            elif "error" in sl_result["response"]["data"]["statuses"][0]:
                logger.error(f"Stop loss order error: {sl_result['response']['data']['statuses'][0]['error']}")
        
        # Place take profit if provided
        tp_order_id = None
        if "take_profit" in signal and signal["take_profit"] is not None:
            tp_trigger = round_price(signal["take_profit"], symbol)
            # For a long, order price should be even higher; for a short, even lower
            if is_buy:
                tp_order_price = round_price(tp_trigger * 1.01, symbol)  # 1% above trigger
            else:
                tp_order_price = round_price(tp_trigger * 0.99, symbol)  # 1% below trigger
            logger.info(f"Attempting to place take profit order: trigger={tp_trigger}, order_price={tp_order_price}")
            tp_order_type = {
                "trigger": {
                    "triggerPx": tp_trigger,
                    "isMarket": True,
                    "tpsl": "tp"
                }
            }
            tp_result = exchange.order(
                symbol,
                not is_buy,  # Opposite side of main order
                size,
                tp_order_price,
                tp_order_type,
                reduce_only=True
            )
            logger.info("Take profit order result: %s", tp_result)
            if tp_result.get("status") == "ok" and "resting" in tp_result["response"]["data"]["statuses"][0]:
                tp_order_id = tp_result["response"]["data"]["statuses"][0]["resting"]["oid"]
            elif "error" in tp_result["response"]["data"]["statuses"][0]:
                logger.error(f"Take profit order error: {tp_result['response']['data']['statuses'][0]['error']}")
        
        return {
            "main_order": result,
            "sl_order_id": sl_order_id,
            "tp_order_id": tp_order_id
        }
    except ServerError as e:
        logger.error(f"Hyperliquid API error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error executing trade: {str(e)}")
        raise

def cancel_order(symbol, order_id):
    """
    Cancels an order on Hyperliquid by its order ID.
    """
    try:
        result = exchange.cancel(symbol, order_id)
        logger.info(f"Cancel order result for {order_id}: %s", result)
        return result
    except ServerError as e:
        logger.error(f"Error canceling order {order_id}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error canceling order {order_id}: {str(e)}")
        raise 