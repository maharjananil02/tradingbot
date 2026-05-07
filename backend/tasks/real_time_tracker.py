import asyncio
import logging
from datetime import date
from utils.validators import nepal_today

from models.database import SessionLocal
from services.data_fetcher import data_fetcher
from services.position_manager import position_manager
from services.alert_sender import alert_sender
from utils.validators import is_market_open

logger = logging.getLogger(__name__)


async def real_time_tracker_task():
    """Run every minute during market hours - update prices and check trailing SL."""
    if not is_market_open():
        return

    db = SessionLocal()
    try:
        # Fetch live prices
        prices_data = await data_fetcher.fetch_live_prices()
        if not prices_data:
            return

        # Build price lookup
        price_map = {}
        for p in prices_data:
            symbol = p.get("symbol", p.get("companyShortName", ""))
            ltp = p.get("lastTradedPrice", p.get("ltp", p.get("close", 0)))
            if symbol and ltp:
                price_map[symbol] = float(ltp)

        # Save to DB
        data_fetcher.save_prices(db, prices_data, nepal_today())

        # Update open positions
        open_positions = position_manager.get_open_positions(db)
        for pos in open_positions:
            current_price = price_map.get(pos.symbol)
            if current_price is None:
                continue

            result = position_manager.update_price(db, pos, current_price)

            if result["action"] == "milestone":
                message = alert_sender.format_milestone_alert(
                    pos.symbol, pos.entry_price, current_price,
                    result["old_sl"], result["new_sl"],
                    result["total_locked_profit"],
                )
                await alert_sender.send_alert("Profit Milestone", message)

            elif result["action"] == "stop_loss_hit":
                days = (nepal_today() - pos.entry_date).days
                message = alert_sender.format_stop_loss_hit(
                    pos.symbol, pos.entry_price, result["exit_price"],
                    result["pnl"], result["pnl_pct"], days,
                )
                await alert_sender.send_alert("Stop Loss Hit", message, via_email=True)

            elif result["action"] == "stop_loss_warning":
                message = alert_sender.format_stop_loss_warning(
                    pos.symbol, current_price,
                    result["stop_loss"], result["distance_pct"],
                )
                await alert_sender.send_alert("Stop Loss Warning", message)

        # Also update paper trading positions
        paper_positions = position_manager.get_open_positions(db, is_paper=True)
        for pos in paper_positions:
            current_price = price_map.get(pos.symbol)
            if current_price:
                position_manager.update_price(db, pos, current_price)

    except Exception as e:
        logger.error(f"Real-time tracker error: {e}")
    finally:
        db.close()


def run_real_time_tracker():
    """Sync wrapper for scheduler."""
    asyncio.run(real_time_tracker_task())
