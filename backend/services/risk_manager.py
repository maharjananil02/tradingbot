import logging
import numpy as np
from typing import List, Optional
from sqlalchemy.orm import Session

from config import get_settings
from models.tables import Position, Trade, Performance
from models.schemas import RiskMetrics

logger = logging.getLogger(__name__)
settings = get_settings()


class RiskManager:
    """Manages portfolio risk calculations and enforcement."""

    def check_can_open_position(
        self, db: Session, portfolio_value: float, entry_price: float,
        quantity: int, symbol: str, is_paper: bool = False
    ) -> tuple[bool, str]:
        """Check if a new position can be opened based on risk rules."""
        open_positions = (
            db.query(Position)
            .filter(Position.status == "OPEN", Position.is_paper == is_paper)
            .all()
        )

        # Max positions check
        if len(open_positions) >= settings.MAX_POSITIONS:
            return False, f"Max positions ({settings.MAX_POSITIONS}) reached"

        # Max position size check
        position_value = entry_price * quantity
        if position_value > portfolio_value * settings.MAX_POSITION_PCT:
            return False, f"Position exceeds {settings.MAX_POSITION_PCT*100}% of portfolio"

        # Sector concentration check
        stock_sector = self._get_stock_sector(db, symbol)
        if stock_sector:
            sector_value = sum(
                (p.current_price or p.entry_price) * p.quantity
                for p in open_positions
                if self._get_stock_sector(db, p.symbol) == stock_sector
            )
            if (sector_value + position_value) > portfolio_value * settings.MAX_SECTOR_CONCENTRATION:
                return False, f"Sector concentration exceeds {settings.MAX_SECTOR_CONCENTRATION*100}%"

        # Drawdown check
        drawdown = self.calculate_current_drawdown(db, portfolio_value, is_paper)
        if drawdown >= settings.MAX_DRAWDOWN_PAUSE_PCT:
            return False, f"Trading paused: drawdown {drawdown*100:.1f}% exceeds limit"

        return True, "OK"

    def calculate_risk_metrics(self, db: Session, is_paper: bool = False) -> RiskMetrics:
        """Calculate comprehensive risk metrics."""
        trades = (
            db.query(Trade)
            .filter(Trade.is_paper == is_paper, Trade.exit_date.isnot(None))
            .all()
        )

        if not trades:
            return RiskMetrics(
                sharpe_ratio=0, max_drawdown=0, max_drawdown_pct=0,
                value_at_risk=0, profit_factor=0, win_rate=0,
                avg_win=0, avg_loss=0, total_trades=0,
                winning_trades=0, losing_trades=0,
            )

        pnls = [t.profit_loss or 0 for t in trades]
        pnl_pcts = [t.profit_loss_pct or 0 for t in trades]

        winners = [p for p in pnls if p > 0]
        losers = [p for p in pnls if p < 0]

        total = len(trades)
        win_count = len(winners)
        loss_count = len(losers)
        win_rate = win_count / total if total > 0 else 0

        avg_win = np.mean(winners) if winners else 0
        avg_loss = abs(np.mean(losers)) if losers else 0

        gross_profit = sum(winners) if winners else 0
        gross_loss = abs(sum(losers)) if losers else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Sharpe ratio (annualized, risk-free = 5%)
        if len(pnl_pcts) > 1:
            mean_return = np.mean(pnl_pcts)
            std_return = np.std(pnl_pcts)
            sharpe = (mean_return - 0.02) / std_return if std_return > 0 else 0
        else:
            sharpe = 0

        # Max drawdown
        cumulative = np.cumsum(pnls)
        peak = np.maximum.accumulate(cumulative)
        drawdowns = peak - cumulative
        max_dd = np.max(drawdowns) if len(drawdowns) > 0 else 0
        max_dd_pct = (max_dd / (peak[np.argmax(drawdowns)] if np.argmax(drawdowns) < len(peak) and peak[np.argmax(drawdowns)] > 0 else 1)) if max_dd > 0 else 0

        # Value at Risk (95% confidence)
        var_95 = np.percentile(pnls, 5) if len(pnls) > 5 else 0

        return RiskMetrics(
            sharpe_ratio=round(float(sharpe), 2),
            max_drawdown=round(float(max_dd), 2),
            max_drawdown_pct=round(float(max_dd_pct * 100), 2),
            value_at_risk=round(float(var_95), 2),
            profit_factor=round(float(profit_factor), 2),
            win_rate=round(float(win_rate * 100), 1),
            avg_win=round(float(avg_win), 2),
            avg_loss=round(float(avg_loss), 2),
            total_trades=total,
            winning_trades=win_count,
            losing_trades=loss_count,
        )

    def calculate_current_drawdown(
        self, db: Session, portfolio_value: float, is_paper: bool = False
    ) -> float:
        """Calculate current drawdown from peak portfolio value."""
        performances = (
            db.query(Performance)
            .filter(Performance.is_paper == is_paper)
            .order_by(Performance.date.desc())
            .limit(252)
            .all()
        )

        if not performances:
            return 0.0

        values = [p.portfolio_value for p in reversed(performances)]
        values.append(portfolio_value)
        peak = max(values)

        if peak <= 0:
            return 0.0

        return (peak - portfolio_value) / peak

    def check_daily_loss_limit(
        self, db: Session, today_pnl: float, portfolio_value: float
    ) -> bool:
        """Check if daily loss limit has been exceeded."""
        if portfolio_value <= 0:
            return True
        daily_loss_pct = abs(today_pnl) / portfolio_value
        return today_pnl < 0 and daily_loss_pct >= settings.DAILY_LOSS_LIMIT_PCT

    def _get_stock_sector(self, db: Session, symbol: str) -> Optional[str]:
        from models.tables import Stock
        stock = db.query(Stock).filter(Stock.symbol == symbol).first()
        return stock.sector if stock else None


risk_manager = RiskManager()
