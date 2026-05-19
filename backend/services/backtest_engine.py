import logging
import numpy as np
import pandas as pd
from datetime import date, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from models.tables import Price
from models.schemas import BacktestRequest, BacktestResult
from utils.technical_indicators import (
    calculate_sma, calculate_rsi, calculate_macd, calculate_volume_sma,
)
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BacktestEngine:
    """Backtests trading strategies against historical NEPSE data."""

    def run_backtest(self, db: Session, request: BacktestRequest) -> BacktestResult:
        """Run backtest for given parameters."""
        capital = request.initial_capital
        cash = capital
        positions = {}
        all_trades = []
        equity_curve = [{"date": str(request.start_date), "value": capital}]

        for symbol in [s.upper() for s in request.symbols]:
            # Load extra data before start_date for indicator warm-up
            warmup_days = max(request.sma_long, 60) + 10
            warmup_start = request.start_date - timedelta(days=int(warmup_days * 1.5))

            prices = (
                db.query(Price)
                .filter(
                    Price.symbol == symbol,
                    Price.date >= warmup_start,
                    Price.date <= request.end_date,
                )
                .order_by(Price.date)
                .all()
            )

            if len(prices) < 50:
                continue

            closes = [p.close for p in prices]
            dates = [p.date for p in prices]
            volumes = [p.volume or 0 for p in prices]

            # Pre-compute indicators
            sma_short = calculate_sma(closes, request.sma_short)
            sma_long = calculate_sma(closes, request.sma_long)
            rsi = calculate_rsi(closes, request.rsi_period)
            macd_data = calculate_macd(closes)
            vol_sma = calculate_volume_sma(volumes, 20)

            for i in range(request.sma_long, len(closes)):
                current_price = closes[i]
                current_date = dates[i]

                # Only trade within the requested date range
                if current_date < request.start_date:
                    continue

                # Check open positions for trailing stop / exit
                if symbol in positions:
                    pos = positions[symbol]
                    gain = (current_price - pos["base_price"]) / pos["base_price"]
                    change_from_entry = ((current_price - pos["entry_price"]) / pos["entry_price"]) * 100
                    unrealized_pnl = (current_price - pos["entry_price"]) * pos["quantity"]

                    day_note = ""

                    # Trailing stop update
                    if gain >= 0.10:
                        new_base = current_price * 0.95
                        if new_base > pos["stop_loss"]:
                            day_note = f"Trailing stop raised from {pos['stop_loss']:.2f} to {new_base:.2f} (price gained 10%+)"
                            pos["base_price"] = new_base
                            pos["stop_loss"] = new_base

                    # Log daily data
                    pos["daily_log"].append({
                        "date": str(current_date),
                        "price": current_price,
                        "change_pct": round(change_from_entry, 2),
                        "unrealized_pnl": round(unrealized_pnl, 2),
                        "stop_loss": round(pos["stop_loss"], 2),
                        "note": day_note,
                    })

                    # Stop loss check
                    if current_price <= pos["stop_loss"]:
                        pnl = (current_price - pos["entry_price"]) * pos["quantity"]
                        pnl_pct = ((current_price - pos["entry_price"]) / pos["entry_price"]) * 100
                        duration = (current_date - pos["entry_date"]).days
                        pos["daily_log"][-1]["note"] = f"SOLD - Stop loss hit at {pos['stop_loss']:.2f}"

                        all_trades.append({
                            "symbol": symbol,
                            "entry_date": str(pos["entry_date"]),
                            "entry_price": pos["entry_price"],
                            "exit_date": str(current_date),
                            "exit_price": current_price,
                            "quantity": pos["quantity"],
                            "pnl": round(pnl, 2),
                            "pnl_pct": round(pnl_pct, 2),
                            "duration": duration,
                            "exit_reason": "STOP_LOSS",
                            "entry_signals": pos["entry_signals"],
                            "daily_log": pos["daily_log"],
                        })
                        cash += current_price * pos["quantity"]
                        del positions[symbol]

                    # Time stop
                    elif (current_date - pos["entry_date"]).days >= 60:
                        pnl = (current_price - pos["entry_price"]) * pos["quantity"]
                        pnl_pct = ((current_price - pos["entry_price"]) / pos["entry_price"]) * 100
                        duration = (current_date - pos["entry_date"]).days
                        pos["daily_log"][-1]["note"] = "SOLD - Held for 60+ days (time limit)"

                        all_trades.append({
                            "symbol": symbol,
                            "entry_date": str(pos["entry_date"]),
                            "entry_price": pos["entry_price"],
                            "exit_date": str(current_date),
                            "exit_price": current_price,
                            "quantity": pos["quantity"],
                            "pnl": round(pnl, 2),
                            "pnl_pct": round(pnl_pct, 2),
                            "duration": duration,
                            "exit_reason": "TIME_STOP",
                            "entry_signals": pos["entry_signals"],
                            "daily_log": pos["daily_log"],
                        })
                        cash += current_price * pos["quantity"]
                        del positions[symbol]

                # Entry signals — require min_confirmations confirming indicators
                if symbol not in positions and cash > current_price:
                    buy_confirmations = 0
                    c1_sma = c2_rsi = c3_macd = c4_vol = False

                    # 1. SMA fresh crossover (within last 3 bars)
                    if (sma_short[i] is not None and sma_long[i] is not None
                            and sma_short[i] > sma_long[i] and current_price > sma_short[i]):
                        fresh = False
                        for j in range(max(1, i - 2), i + 1):
                            if (sma_short[j - 1] is not None and sma_long[j - 1] is not None
                                    and sma_short[j - 1] <= sma_long[j - 1]
                                    and sma_short[j] > sma_long[j]):
                                fresh = True
                                break
                        if fresh:
                            c1_sma = True
                            buy_confirmations += 1

                    # 2. RSI oversold bounce
                    if (rsi[i] is not None and rsi[i - 1] is not None
                            and rsi[i - 1] < 30 and rsi[i] > rsi[i - 1] and rsi[i] < 35):
                        c2_rsi = True
                        buy_confirmations += 1

                    # 3. MACD bullish crossover
                    if (i > 0
                            and macd_data["macd"][i - 1] <= macd_data["signal"][i - 1]
                            and macd_data["macd"][i] > macd_data["signal"][i]):
                        c3_macd = True
                        buy_confirmations += 1

                    # 4. Volume above average
                    if vol_sma[i] is not None and vol_sma[i] > 0 and volumes[i] > vol_sma[i] * 1.2:
                        c4_vol = True
                        buy_confirmations += 1

                    # Build list of which signals fired
                    signals_fired = []
                    if c1_sma: signals_fired.append("SMA Crossover")
                    if c2_rsi: signals_fired.append("RSI Oversold Bounce")
                    if c3_macd: signals_fired.append("MACD Crossover")
                    if c4_vol: signals_fired.append("Volume Spike")

                    # Need at least min_confirmations signals to enter
                    if buy_confirmations >= request.min_confirmations:
                        risk_per_trade = cash * request.risk_per_trade
                        stop_loss = current_price * 0.95
                        loss_per_share = current_price - stop_loss
                        quantity = max(1, int(risk_per_trade / loss_per_share))
                        cost = current_price * quantity

                        if cost <= cash:
                            positions[symbol] = {
                                "entry_price": current_price,
                                "entry_date": current_date,
                                "quantity": quantity,
                                "stop_loss": stop_loss,
                                "base_price": current_price,
                                "entry_signals": signals_fired,
                                "daily_log": [{
                                    "date": str(current_date),
                                    "price": current_price,
                                    "change_pct": 0.0,
                                    "unrealized_pnl": 0.0,
                                    "stop_loss": round(stop_loss, 2),
                                    "note": f"BOUGHT {quantity} shares @ NPR {current_price} | Signals: {', '.join(signals_fired)}",
                                }],
                            }
                            cash -= cost

                # Update equity curve
                position_value = sum(
                    closes[i] * p["quantity"]
                    for s, p in positions.items()
                    if s == symbol
                )
                total_value = cash + position_value
                equity_curve.append({
                    "date": str(current_date),
                    "value": round(total_value, 2),
                })

        # Close remaining positions at last price
        for symbol, pos in list(positions.items()):
            last_price_rec = (
                db.query(Price)
                .filter(Price.symbol == symbol)
                .order_by(Price.date.desc())
                .first()
            )
            if last_price_rec:
                last_price = last_price_rec.close
                pnl = (last_price - pos["entry_price"]) * pos["quantity"]
                pnl_pct = ((last_price - pos["entry_price"]) / pos["entry_price"]) * 100
                duration = (request.end_date - pos["entry_date"]).days

                pos["daily_log"].append({
                    "date": str(request.end_date),
                    "price": last_price,
                    "change_pct": round(pnl_pct, 2),
                    "unrealized_pnl": round(pnl, 2),
                    "stop_loss": round(pos["stop_loss"], 2),
                    "note": "SOLD - Backtest period ended",
                })
                all_trades.append({
                    "symbol": symbol,
                    "entry_date": str(pos["entry_date"]),
                    "entry_price": pos["entry_price"],
                    "exit_date": str(request.end_date),
                    "exit_price": last_price,
                    "quantity": pos["quantity"],
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "duration": duration,
                    "exit_reason": "END_OF_BACKTEST",
                    "entry_signals": pos.get("entry_signals", []),
                    "daily_log": pos.get("daily_log", []),
                })
                cash += last_price * pos["quantity"]

        # Calculate metrics
        return self._calculate_metrics(all_trades, equity_curve, capital, cash)

    def _calculate_metrics(
        self, trades: List[dict], equity_curve: List[dict],
        initial_capital: float, final_cash: float
    ) -> BacktestResult:
        """Calculate backtest performance metrics."""
        if not trades:
            return BacktestResult(
                total_return=0, total_return_pct=0, total_trades=0,
                winning_trades=0, losing_trades=0, win_rate=0,
                avg_win=0, avg_loss=0, profit_factor=0,
                sharpe_ratio=0, max_drawdown=0, max_drawdown_pct=0,
                avg_holding_days=0, best_trade=0, worst_trade=0,
                equity_curve=equity_curve, trades=trades, monthly_returns=[],
            )

        pnls = [t["pnl"] for t in trades]
        pnl_pcts = [t["pnl_pct"] for t in trades]
        winners = [p for p in pnls if p > 0]
        losers = [p for p in pnls if p < 0]

        total_return = final_cash - initial_capital
        total_return_pct = (total_return / initial_capital) * 100
        total_trades = len(trades)
        win_count = len(winners)
        loss_count = len(losers)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

        avg_win = float(np.mean(winners)) if winners else 0
        avg_loss = abs(float(np.mean(losers))) if losers else 0

        gross_profit = sum(winners) if winners else 0
        gross_loss = abs(sum(losers)) if losers else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Sharpe ratio
        if len(pnl_pcts) > 1:
            sharpe = float(np.mean(pnl_pcts)) / float(np.std(pnl_pcts)) if np.std(pnl_pcts) > 0 else 0
        else:
            sharpe = 0

        # Max drawdown
        values = [e["value"] for e in equity_curve]
        if values:
            peak = np.maximum.accumulate(values)
            drawdowns = (peak - values) / np.where(peak > 0, peak, 1)
            max_dd_pct = float(np.max(drawdowns)) * 100
            max_dd = float(np.max(peak - values))
        else:
            max_dd = 0
            max_dd_pct = 0

        durations = [t["duration"] for t in trades if t["duration"] is not None]
        avg_hold = float(np.mean(durations)) if durations else 0

        # Monthly returns
        monthly_returns = self._calculate_monthly_returns(trades)

        return BacktestResult(
            total_return=round(total_return, 2),
            total_return_pct=round(total_return_pct, 2),
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate=round(win_rate, 1),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            profit_factor=round(profit_factor, 2),
            sharpe_ratio=round(sharpe, 2),
            max_drawdown=round(max_dd, 2),
            max_drawdown_pct=round(max_dd_pct, 2),
            avg_holding_days=round(avg_hold, 1),
            best_trade=round(max(pnl_pcts) if pnl_pcts else 0, 2),
            worst_trade=round(min(pnl_pcts) if pnl_pcts else 0, 2),
            equity_curve=equity_curve,
            trades=trades,
            monthly_returns=monthly_returns,
        )

    def _calculate_monthly_returns(self, trades: List[dict]) -> List[dict]:
        """Group trades by month and calculate returns."""
        if not trades:
            return []

        monthly = {}
        for t in trades:
            month = t["exit_date"][:7] if t.get("exit_date") else t["entry_date"][:7]
            if month not in monthly:
                monthly[month] = {"month": month, "pnl": 0, "trades": 0, "wins": 0}
            monthly[month]["pnl"] += t["pnl"]
            monthly[month]["trades"] += 1
            if t["pnl"] > 0:
                monthly[month]["wins"] += 1

        result = []
        for month in sorted(monthly.keys()):
            m = monthly[month]
            m["pnl"] = round(m["pnl"], 2)
            m["win_rate"] = round(m["wins"] / m["trades"] * 100, 1) if m["trades"] > 0 else 0
            result.append(m)
        return result


backtest_engine = BacktestEngine()
