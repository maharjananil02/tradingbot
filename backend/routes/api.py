from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from models.database import get_db
from models.tables import Position, Trade, Performance
from utils.validators import nepal_today
from models.schemas import (
    PositionSchema, PositionCreate, PositionUpdate,
    TradeSchema, TradeUpdate, PortfolioSummary,
    PerformanceSchema, RiskMetrics, SignalSchema,
)
from services.position_manager import position_manager
from services.signal_generator import signal_generator
from services.risk_manager import risk_manager
from services.data_fetcher import data_fetcher
from config import get_settings

router = APIRouter(prefix="/api", tags=["trading"])
settings = get_settings()


# --- Nepal Time ---

@router.get("/time")
def get_nepal_time():
    """Get current Nepal time (Asia/Kathmandu UTC+5:45)."""
    from utils.validators import nepal_now, is_market_open
    now = nepal_now()
    return {
        "datetime": now.isoformat(),
        "time": now.strftime("%I:%M:%S %p"),
        "date": now.strftime("%Y-%m-%d"),
        "day": now.strftime("%A"),
        "is_market_open": is_market_open(),
    }


# --- Dashboard ---

@router.get("/dashboard", response_model=PortfolioSummary)
def get_dashboard(db: Session = Depends(get_db)):
    """Get portfolio dashboard summary."""
    positions = position_manager.get_open_positions(db)
    total_invested = sum(p.entry_price * p.quantity for p in positions)
    position_value = sum((p.current_price or p.entry_price) * p.quantity for p in positions)
    unrealized_pnl = position_value - total_invested

    # Today's P&L
    today_trades = db.query(Trade).filter(Trade.exit_date == nepal_today()).all()
    today_pnl = sum(t.profit_loss or 0 for t in today_trades)

    # Calculate total portfolio value
    cash = settings.PAPER_TRADING_CAPITAL - total_invested
    total_value = cash + position_value

    # Win rate
    all_trades = db.query(Trade).filter(Trade.exit_date.isnot(None)).all()
    total_trades = len(all_trades)
    winners = len([t for t in all_trades if (t.profit_loss or 0) > 0])
    win_rate = (winners / total_trades * 100) if total_trades > 0 else 0

    return PortfolioSummary(
        total_value=round(total_value, 2),
        total_invested=round(total_invested, 2),
        total_unrealized_pnl=round(unrealized_pnl, 2),
        total_unrealized_pnl_pct=round(
            (unrealized_pnl / total_invested * 100) if total_invested > 0 else 0, 2
        ),
        today_pnl=round(today_pnl, 2),
        today_pnl_pct=round(
            (today_pnl / total_value * 100) if total_value > 0 else 0, 2
        ),
        cash_available=round(cash, 2),
        open_positions=len(positions),
        win_rate=round(win_rate, 1),
        total_trades=total_trades,
    )


# --- Positions ---

@router.get("/positions", response_model=List[PositionSchema])
def get_positions(is_paper: bool = False, db: Session = Depends(get_db)):
    """Get all open positions."""
    positions = position_manager.get_open_positions(db, is_paper)
    result = []
    for p in positions:
        summary = position_manager.get_position_summary(p)
        schema = PositionSchema(
            id=p.id,
            symbol=p.symbol,
            entry_price=p.entry_price,
            entry_date=p.entry_date,
            quantity=p.quantity,
            current_price=p.current_price,
            base_price=p.base_price,
            stop_loss=p.stop_loss,
            initial_stop_loss=p.initial_stop_loss,
            entry_signal=p.entry_signal,
            status=p.status,
            unrealized_pnl=p.unrealized_pnl or 0,
            realized_pnl=p.realized_pnl or 0,
            milestone_count=p.milestone_count or 0,
            is_paper=p.is_paper,
            days_held=summary["days_held"],
            next_milestone_price=summary["next_milestone_price"],
        )
        result.append(schema)
    return result


@router.post("/positions", response_model=PositionSchema)
def create_position(data: PositionCreate, db: Session = Depends(get_db)):
    """Open a new position."""
    # Risk check
    portfolio_value = settings.PAPER_TRADING_CAPITAL
    can_open, reason = risk_manager.check_can_open_position(
        db, portfolio_value, data.entry_price, data.quantity,
        data.symbol, data.is_paper,
    )
    if not can_open:
        raise HTTPException(status_code=400, detail=reason)

    pos = position_manager.open_position(
        db, data.symbol, data.entry_price, data.quantity,
        data.stop_loss_pct, data.entry_signal or "", data.is_paper,
    )
    summary = position_manager.get_position_summary(pos)
    return PositionSchema(
        id=pos.id,
        symbol=pos.symbol,
        entry_price=pos.entry_price,
        entry_date=pos.entry_date,
        quantity=pos.quantity,
        current_price=pos.current_price,
        base_price=pos.base_price,
        stop_loss=pos.stop_loss,
        initial_stop_loss=pos.initial_stop_loss,
        entry_signal=pos.entry_signal,
        status=pos.status,
        unrealized_pnl=0,
        realized_pnl=0,
        milestone_count=0,
        is_paper=pos.is_paper,
        days_held=0,
        next_milestone_price=summary["next_milestone_price"],
    )


@router.delete("/positions/{position_id}")
def close_position(position_id: int, exit_price: float, db: Session = Depends(get_db)):
    """Manually close a position."""
    pos = position_manager.get_position(db, position_id)
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    if pos.status == "CLOSED":
        raise HTTPException(status_code=400, detail="Position already closed")

    # Force close directly instead of going through update_price to avoid side-effects
    from services.position_manager import PositionManager
    result = position_manager._close_position(db, pos, exit_price, "MANUAL_CLOSE")
    db.commit()

    return {"message": "Position closed", "pnl": pos.realized_pnl}


# --- Signals ---

@router.get("/signals", response_model=List[SignalSchema])
def get_signals(target_date: str = None, db: Session = Depends(get_db)):
    """Get trading signals for a given date."""
    from models.tables import Signal
    query_date = date.fromisoformat(target_date) if target_date else nepal_today()
    signals = (
        db.query(Signal)
        .filter(Signal.date == query_date)
        .order_by(Signal.confidence.desc())
        .all()
    )
    return signals


@router.post("/signals/generate", response_model=List[SignalSchema])
def generate_signals(db: Session = Depends(get_db)):
    """Manually trigger signal generation."""
    signals = signal_generator.generate_all_signals(db, settings.PAPER_TRADING_CAPITAL)
    return signals


# --- Trades (Journal) ---

@router.get("/trades", response_model=List[TradeSchema])
def get_trades(
    is_paper: bool = False, limit: int = 50, db: Session = Depends(get_db)
):
    """Get trade journal entries."""
    trades = (
        db.query(Trade)
        .filter(Trade.is_paper == is_paper)
        .order_by(Trade.exit_date.desc())
        .limit(limit)
        .all()
    )
    return trades


@router.get("/trades/stats")
def get_trade_stats(is_paper: bool = False, db: Session = Depends(get_db)):
    """Get trade statistics and insights."""
    trades = (
        db.query(Trade)
        .filter(Trade.is_paper == is_paper, Trade.exit_date.isnot(None))
        .all()
    )
    if not trades:
        return {"message": "No completed trades yet"}

    pnls = [t.profit_loss or 0 for t in trades]
    winners = [t for t in trades if (t.profit_loss or 0) > 0]
    losers = [t for t in trades if (t.profit_loss or 0) < 0]

    # Signal analysis
    signal_stats = {}
    for t in trades:
        sig = t.entry_signal or "Unknown"
        if sig not in signal_stats:
            signal_stats[sig] = {"total": 0, "wins": 0, "pnl": 0}
        signal_stats[sig]["total"] += 1
        signal_stats[sig]["pnl"] += t.profit_loss or 0
        if (t.profit_loss or 0) > 0:
            signal_stats[sig]["wins"] += 1

    for sig in signal_stats:
        s = signal_stats[sig]
        s["win_rate"] = round(s["wins"] / s["total"] * 100, 1) if s["total"] > 0 else 0
        s["pnl"] = round(s["pnl"], 2)

    # Duration analysis
    durations = [t.duration_days or 0 for t in trades]

    return {
        "total_trades": len(trades),
        "winning_trades": len(winners),
        "losing_trades": len(losers),
        "win_rate": round(len(winners) / len(trades) * 100, 1),
        "total_pnl": round(sum(pnls), 2),
        "avg_pnl": round(sum(pnls) / len(trades), 2),
        "best_trade": round(max(pnls), 2),
        "worst_trade": round(min(pnls), 2),
        "avg_duration_days": round(sum(durations) / len(durations), 1) if durations else 0,
        "signal_performance": signal_stats,
    }


@router.get("/trades/{trade_id}", response_model=TradeSchema)
def get_trade(trade_id: int, db: Session = Depends(get_db)):
    """Get a single trade by ID."""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.put("/trades/{trade_id}", response_model=TradeSchema)
def update_trade(trade_id: int, data: TradeUpdate, db: Session = Depends(get_db)):
    """Update a trade entry."""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(trade, field, value)

    # Recalculate P&L if prices or quantity changed
    if any(f in update_data for f in ("entry_price", "exit_price", "quantity")):
        ep = trade.entry_price
        xp = trade.exit_price or ep
        qty = trade.quantity
        trade.profit_loss = round((xp - ep) * qty, 2)
        trade.profit_loss_pct = round(((xp - ep) / ep) * 100, 2) if ep else 0
        if trade.profit_loss > 0:
            trade.result = "WINNER"
        elif trade.profit_loss < 0:
            trade.result = "LOSER"
        else:
            trade.result = "BREAKEVEN"

    db.commit()
    db.refresh(trade)
    return trade


@router.delete("/trades/{trade_id}")
def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    """Delete a trade entry."""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    db.delete(trade)
    db.commit()
    return {"message": "Trade deleted"}


@router.put("/positions/{position_id}", response_model=PositionSchema)
def update_position(position_id: int, data: PositionUpdate, db: Session = Depends(get_db)):
    """Update an open position."""
    pos = position_manager.get_position(db, position_id)
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    if pos.status == "CLOSED":
        raise HTTPException(status_code=400, detail="Cannot edit closed position")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pos, field, value)

    db.commit()
    db.refresh(pos)
    summary = position_manager.get_position_summary(pos)
    return PositionSchema(
        id=pos.id,
        symbol=pos.symbol,
        entry_price=pos.entry_price,
        entry_date=pos.entry_date,
        quantity=pos.quantity,
        current_price=pos.current_price,
        base_price=pos.base_price,
        stop_loss=pos.stop_loss,
        initial_stop_loss=pos.initial_stop_loss,
        entry_signal=pos.entry_signal,
        status=pos.status,
        unrealized_pnl=pos.unrealized_pnl or 0,
        realized_pnl=pos.realized_pnl or 0,
        milestone_count=pos.milestone_count or 0,
        is_paper=pos.is_paper,
        days_held=summary["days_held"],
        next_milestone_price=summary["next_milestone_price"],
    )


# --- Risk ---

@router.get("/risk", response_model=RiskMetrics)
def get_risk_metrics(is_paper: bool = False, db: Session = Depends(get_db)):
    """Get current risk metrics."""
    return risk_manager.calculate_risk_metrics(db, is_paper)


# --- Performance ---

@router.get("/performance", response_model=List[PerformanceSchema])
def get_performance(days: int = 30, is_paper: bool = False, db: Session = Depends(get_db)):
    """Get performance history."""
    performances = (
        db.query(Performance)
        .filter(Performance.is_paper == is_paper)
        .order_by(Performance.date.desc())
        .limit(days)
        .all()
    )
    return list(reversed(performances))


# --- Alerts ---

@router.get("/alerts")
def get_alerts(limit: int = 20, db: Session = Depends(get_db)):
    """Get recent alerts."""
    from models.tables import Alert
    alerts = (
        db.query(Alert)
        .order_by(Alert.created_at.desc())
        .limit(limit)
        .all()
    )
    return alerts


@router.put("/alerts/{alert_id}/read")
def mark_alert_read(alert_id: int, db: Session = Depends(get_db)):
    """Mark an alert as read."""
    from models.tables import Alert
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    db.commit()
    return {"message": "Alert marked as read"}


# --- Market Data ---

@router.get("/market/stocks")
async def get_stocks():
    """Get all NEPSE stocks."""
    return await data_fetcher.fetch_all_stocks()


@router.get("/market/live")
async def get_live_prices():
    """Get live market prices."""
    return await data_fetcher.fetch_live_prices()


@router.get("/market/summary")
async def get_market_summary():
    """Get NEPSE market summary."""
    return await data_fetcher.fetch_market_summary()


@router.get("/market/gainers")
async def get_top_gainers():
    """Get top gainers."""
    return await data_fetcher.fetch_top_gainers()


@router.get("/market/losers")
async def get_top_losers():
    """Get top losers."""
    return await data_fetcher.fetch_top_losers()


@router.post("/market/fetch-history")
async def fetch_history(
    days: int = 100,
    mode: str = "all",
    db: Session = Depends(get_db),
):
    """Fetch historical price data from ShareSansar.
    
    mode='all'  — fetch/update for ALL stocks (default)
    mode='gaps' — only stocks with fewer than 50 price records
    """
    from models.tables import Stock, Price
    from sqlalchemy import func

    if mode == "gaps":
        stocks_with_counts = (
            db.query(Stock.symbol, func.count(Price.id).label("cnt"))
            .outerjoin(Price, Stock.symbol == Price.symbol)
            .group_by(Stock.symbol)
            .having(func.count(Price.id) < 50)
            .order_by(func.count(Price.id).asc())
            .all()
        )
        symbols = [s.symbol for s in stocks_with_counts]
    else:
        # Fetch for all stocks
        stocks = db.query(Stock.symbol).all()
        symbols = [s.symbol for s in stocks]

    # If no stocks in DB yet (fresh install), discover and save them first
    if not symbols:
        stocks_data = await data_fetcher.fetch_all_stocks()
        if stocks_data:
            data_fetcher.save_stocks(db, stocks_data)
            symbols = [s["symbol"] for s in stocks_data]
        else:
            return {"message": "No stocks found. Check network connectivity.", "saved": 0}

    saved = await data_fetcher.fetch_and_save_history(db, symbols, days)
    return {
        "message": f"Fetched history for {len(symbols)} stocks",
        "symbols_count": len(symbols),
        "saved": saved,
    }


# --- Backtest ---

@router.post("/backtest")
def run_backtest(request: dict, db: Session = Depends(get_db)):
    """Run a backtest simulation."""
    from models.schemas import BacktestRequest
    from services.backtest_engine import backtest_engine

    req = BacktestRequest(**request)
    result = backtest_engine.run_backtest(db, req)
    return result


# --- Settings ---

@router.get("/settings")
def get_app_settings():
    """Get current app settings."""
    from config import _runtime_state
    return {
        "risk_per_trade": settings.RISK_PER_TRADE,
        "max_positions": settings.MAX_POSITIONS,
        "max_position_pct": settings.MAX_POSITION_PCT,
        "trailing_sl_trigger_pct": settings.TRAILING_SL_TRIGGER_PCT,
        "trailing_sl_lock_pct": settings.TRAILING_SL_LOCK_PCT,
        "hard_stop_loss_pct": settings.HARD_STOP_LOSS_PCT,
        "max_drawdown_alert_pct": settings.MAX_DRAWDOWN_ALERT_PCT,
        "max_drawdown_pause_pct": settings.MAX_DRAWDOWN_PAUSE_PCT,
        "daily_loss_limit_pct": settings.DAILY_LOSS_LIMIT_PCT,
        "max_sector_concentration": settings.MAX_SECTOR_CONCENTRATION,
        "min_holding_days": settings.MIN_HOLDING_DAYS,
        "max_holding_days": settings.MAX_HOLDING_DAYS,
        "paper_trading_capital": settings.PAPER_TRADING_CAPITAL,
        "auto_execute_paper": settings.AUTO_EXECUTE_PAPER,
        "auto_execute_enabled": _runtime_state.get("auto_execute_enabled", True),
        "auto_execute_min_confidence": settings.AUTO_EXECUTE_MIN_CONFIDENCE,
        "market_hours": {
            "open": f"{settings.MARKET_OPEN_HOUR}:{settings.MARKET_OPEN_MINUTE:02d}",
            "close": f"{settings.MARKET_CLOSE_HOUR}:{settings.MARKET_CLOSE_MINUTE:02d}",
        },
    }


@router.put("/settings/auto-execute")
def toggle_auto_execute(enabled: bool):
    """Toggle auto-execution of paper trading signals."""
    from config import _runtime_state
    _runtime_state["auto_execute_enabled"] = enabled
    return {"auto_execute_enabled": enabled}


@router.post("/settings/reset")
def reset_all_data(db: Session = Depends(get_db)):
    """Reset all trading data - fresh start. Keeps stocks and price history."""
    from models.tables import (
        Position, Trade, Signal, Alert, Performance,
        PaperTrade, PaperPosition,
    )

    db.query(Trade).delete()
    db.query(Position).delete()
    db.query(Signal).delete()
    db.query(Alert).delete()
    db.query(Performance).delete()
    db.query(PaperTrade).delete()
    db.query(PaperPosition).delete()
    db.commit()

    return {
        "message": "All trading data reset successfully. Price history preserved.",
        "capital": settings.PAPER_TRADING_CAPITAL,
    }
