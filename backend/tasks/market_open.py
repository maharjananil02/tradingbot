import asyncio
import logging
from datetime import date
from utils.validators import nepal_today

from models.database import SessionLocal
from services.data_fetcher import data_fetcher
from services.signal_generator import signal_generator
from services.position_manager import position_manager
from services.risk_manager import risk_manager
from services.alert_sender import alert_sender
from utils.calculations import calculate_position_size
from utils.validators import is_trading_day
from config import get_settings, _runtime_state

logger = logging.getLogger(__name__)
settings = get_settings()


async def market_open_task():
    """Run at 11:00 AM on trading days - generate signals and send alerts."""
    if not is_trading_day():
        logger.info("Not a trading day, skipping market open task")
        return

    logger.info("=== MARKET OPEN TASK ===")
    db = SessionLocal()

    try:
        # Fetch latest stock data
        stocks_data = await data_fetcher.fetch_all_stocks()
        if stocks_data:
            data_fetcher.save_stocks(db, stocks_data)

        # Fetch live prices
        prices_data = await data_fetcher.fetch_live_prices()
        if prices_data:
            data_fetcher.save_prices(db, prices_data, nepal_today())

        # Generate signals
        signals = signal_generator.generate_all_signals(db)
        logger.info(f"Generated {len(signals)} signals")

        # Send market open alert
        if signals:
            message = alert_sender.format_market_open_alert(signals)
            await alert_sender.send_alert("Market Open Signals", message)

        # Auto-execute BUY signals in paper trading mode
        if settings.AUTO_EXECUTE_PAPER and _runtime_state.get("auto_execute_enabled", True):
            await _auto_execute_signals(db, signals)

    except Exception as e:
        logger.error(f"Market open task error: {e}")
    finally:
        db.close()


async def _auto_execute_signals(db, signals):
    """Automatically open paper positions for qualifying BUY signals."""
    buy_signals = [
        s for s in signals
        if s.signal_type == "BUY" and s.confidence >= settings.AUTO_EXECUTE_MIN_CONFIDENCE
    ]

    if not buy_signals:
        logger.info("No qualifying BUY signals for auto-execution")
        return

    # Calculate available capital
    open_positions = position_manager.get_open_positions(db, is_paper=True)
    invested = sum(p.entry_price * p.quantity for p in open_positions)
    cash = settings.PAPER_TRADING_CAPITAL - invested
    portfolio_value = cash + sum(
        (p.current_price or p.entry_price) * p.quantity for p in open_positions
    )

    executed = []
    for signal in buy_signals:
        # Skip if already have a position in this stock
        if any(p.symbol == signal.symbol for p in open_positions):
            logger.info(f"Skip {signal.symbol}: already in position")
            continue

        # Risk check
        entry = signal.entry_price
        sl = signal.stop_loss
        qty = signal.suggested_quantity or calculate_position_size(
            portfolio_value, entry, sl
        )

        if qty <= 0 or entry * qty > cash:
            logger.info(f"Skip {signal.symbol}: insufficient capital or zero qty")
            continue

        can_open, reason = risk_manager.check_can_open_position(
            db, portfolio_value, entry, qty, signal.symbol, is_paper=True
        )
        if not can_open:
            logger.info(f"Skip {signal.symbol}: {reason}")
            continue

        # Open paper position
        pos = position_manager.open_position(
            db, signal.symbol, entry, qty,
            stop_loss_pct=0.05,
            entry_signal=signal.reason or signal.signal_type,
            is_paper=True,
        )
        cash -= entry * qty
        open_positions.append(pos)
        executed.append(pos)
        logger.info(f"AUTO-EXECUTED: {signal.symbol} x{qty} @ ₨{entry} (paper)")

    # Send alert about auto-executed trades
    if executed:
        msg = f"🤖 <b>AUTO-EXECUTED {len(executed)} PAPER TRADES</b>\n\n"
        for p in executed:
            msg += f"• {p.symbol}: {p.quantity} shares @ ₨{p.entry_price:,.0f} | SL: ₨{p.stop_loss:,.0f}\n"
        msg += f"\nRemaining Cash: ₨{cash:,.0f}"
        await alert_sender.send_alert("Auto-Execution", msg)


def run_market_open():
    """Sync wrapper for scheduler."""
    asyncio.run(market_open_task())
