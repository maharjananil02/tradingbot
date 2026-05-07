import asyncio
import logging
from datetime import date

from models.database import SessionLocal
from models.tables import Performance, Trade, Position
from services.position_manager import position_manager
from services.risk_manager import risk_manager
from services.alert_sender import alert_sender
from utils.validators import nepal_today
from config import get_settings
from utils.validators import is_trading_day

logger = logging.getLogger(__name__)
settings = get_settings()


async def market_close_task():
    """Run at 3:15 PM on trading days - summary and performance update."""
    if not is_trading_day():
        return

    logger.info("=== MARKET CLOSE TASK ===")
    db = SessionLocal()

    try:
        # Calculate portfolio value
        open_positions = position_manager.get_open_positions(db)
        position_value = sum(
            (p.current_price or p.entry_price) * p.quantity
            for p in open_positions
        )

        # Get today's trades
        today_trades = (
            db.query(Trade)
            .filter(Trade.exit_date == nepal_today())
            .all()
        )
        today_pnl = sum(t.profit_loss or 0 for t in today_trades)

        # Calculate total portfolio
        total_value = settings.PAPER_TRADING_CAPITAL + position_value + today_pnl
        today_pnl_pct = (today_pnl / total_value * 100) if total_value > 0 else 0

        # Get risk metrics
        metrics = risk_manager.calculate_risk_metrics(db)

        # Save performance record
        perf = Performance(
            date=nepal_today(),
            portfolio_value=round(total_value, 2),
            daily_pnl=round(today_pnl, 2),
            daily_pnl_pct=round(today_pnl_pct, 2),
            total_pnl=round(total_value - settings.PAPER_TRADING_CAPITAL, 2),
            total_pnl_pct=round(
                ((total_value - settings.PAPER_TRADING_CAPITAL) / settings.PAPER_TRADING_CAPITAL) * 100, 2
            ),
            win_rate=metrics.win_rate,
            sharpe_ratio=metrics.sharpe_ratio,
            max_drawdown=metrics.max_drawdown,
            open_positions=len(open_positions),
            total_trades=metrics.total_trades,
        )

        existing = db.query(Performance).filter(Performance.date == nepal_today()).first()
        if existing:
            for key, value in {
                "portfolio_value": perf.portfolio_value,
                "daily_pnl": perf.daily_pnl,
                "daily_pnl_pct": perf.daily_pnl_pct,
                "total_pnl": perf.total_pnl,
                "total_pnl_pct": perf.total_pnl_pct,
                "win_rate": perf.win_rate,
                "sharpe_ratio": perf.sharpe_ratio,
                "max_drawdown": perf.max_drawdown,
                "open_positions": perf.open_positions,
                "total_trades": perf.total_trades,
            }.items():
                setattr(existing, key, value)
        else:
            db.add(perf)

        db.commit()

        # Send market close alert
        message = alert_sender.format_market_close_alert(
            total_value, today_pnl, today_pnl_pct,
            len(open_positions), today_trades,
        )
        await alert_sender.send_alert("Market Close Summary", message, via_email=True)

        # Check risk alerts
        drawdown = risk_manager.calculate_current_drawdown(db, total_value)
        if drawdown >= settings.MAX_DRAWDOWN_ALERT_PCT:
            risk_msg = alert_sender.format_risk_alert(drawdown * 100, today_pnl)
            await alert_sender.send_alert("Risk Alert", risk_msg)

    except Exception as e:
        logger.error(f"Market close task error: {e}")
    finally:
        db.close()


def run_market_close():
    """Sync wrapper for scheduler."""
    asyncio.run(market_close_task())
