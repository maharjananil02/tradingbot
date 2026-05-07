import logging
from datetime import date
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from config import get_settings
from models.tables import Position, Trade
from utils.calculations import calculate_unrealized_pnl, calculate_unrealized_pnl_pct
from utils.validators import nepal_today

logger = logging.getLogger(__name__)
settings = get_settings()


class PositionManager:
    """Manages positions and trailing stop-loss logic."""

    def open_position(
        self,
        db: Session,
        symbol: str,
        entry_price: float,
        quantity: int,
        stop_loss_pct: float = 0.05,
        entry_signal: str = "",
        is_paper: bool = False,
    ) -> Position:
        """Open a new position."""
        stop_loss = round(entry_price * (1 - stop_loss_pct), 2)

        position = Position(
            symbol=symbol,
            entry_price=entry_price,
            entry_date=nepal_today(),
            quantity=quantity,
            current_price=entry_price,
            base_price=entry_price,
            stop_loss=stop_loss,
            initial_stop_loss=stop_loss,
            entry_signal=entry_signal,
            status="OPEN",
            is_paper=is_paper,
        )
        db.add(position)
        db.commit()
        db.refresh(position)
        logger.info(f"Opened position: {symbol} @ {entry_price} x{quantity}, SL={stop_loss}")
        return position

    def update_price(self, db: Session, position: Position, current_price: float) -> dict:
        """Update position price and check trailing stop-loss.

        Returns dict with action taken:
            {"action": "none"} - no action
            {"action": "milestone", "new_sl": ..., "milestone": ...} - SL updated
            {"action": "stop_loss_hit", "exit_price": ...} - position closed
            {"action": "stop_loss_warning"} - approaching SL
        """
        position.current_price = current_price
        position.unrealized_pnl = calculate_unrealized_pnl(
            position.entry_price, current_price, position.quantity
        )

        result = {"action": "none"}

        # Check trailing stop-loss trigger
        gain_from_base = (current_price - position.base_price) / position.base_price

        if gain_from_base >= settings.TRAILING_SL_TRIGGER_PCT:
            # 10% gain from base price - move stop loss up
            new_base = round(current_price * (1 - settings.TRAILING_SL_LOCK_PCT), 2)
            old_sl = position.stop_loss

            if new_base > position.stop_loss:
                position.base_price = new_base
                position.stop_loss = new_base
                position.milestone_count += 1

                result = {
                    "action": "milestone",
                    "old_sl": old_sl,
                    "new_sl": new_base,
                    "milestone": position.milestone_count,
                    "locked_profit_per_share": round(new_base - position.entry_price, 2),
                    "total_locked_profit": round(
                        (new_base - position.entry_price) * position.quantity, 2
                    ),
                }
                logger.info(
                    f"Milestone #{position.milestone_count} for {position.symbol}: "
                    f"SL moved {old_sl} -> {new_base}"
                )

        # Check if stop loss hit
        if current_price <= position.stop_loss and position.status == "OPEN":
            result = self._close_position(
                db, position, current_price, "STOP_LOSS_HIT"
            )

        # Check hard stop loss (-10% from entry)
        hard_loss = (current_price - position.entry_price) / position.entry_price
        if hard_loss <= -settings.HARD_STOP_LOSS_PCT and position.status == "OPEN":
            result = self._close_position(
                db, position, current_price, "HARD_STOP_LOSS"
            )

        # Check time-based stop (max holding days)
        days_held = (nepal_today() - position.entry_date).days
        if days_held >= settings.MAX_HOLDING_DAYS and position.status == "OPEN":
            result = self._close_position(
                db, position, current_price, "TIME_STOP"
            )

        # Warning if approaching stop loss (within 1%)
        if position.status == "OPEN":
            distance_to_sl = (current_price - position.stop_loss) / current_price
            if 0 < distance_to_sl <= 0.01:
                result = {
                    "action": "stop_loss_warning",
                    "current_price": current_price,
                    "stop_loss": position.stop_loss,
                    "distance_pct": round(distance_to_sl * 100, 2),
                }

        db.commit()
        return result

    def _close_position(
        self, db: Session, position: Position, exit_price: float, reason: str
    ) -> dict:
        """Close a position and record the trade."""
        # Guard against double-close
        if position.status == "CLOSED":
            logger.warning(f"Attempted to close already-closed position {position.symbol} (id={position.id})")
            return {"action": "none"}

        position.status = "CLOSED"
        position.exit_price = exit_price
        position.exit_date = nepal_today()
        position.exit_reason = reason
        position.realized_pnl = round(
            (exit_price - position.entry_price) * position.quantity, 2
        )

        # Record trade
        duration = (nepal_today() - position.entry_date).days
        pnl = position.realized_pnl
        pnl_pct = round(
            ((exit_price - position.entry_price) / position.entry_price) * 100, 2
        )

        if pnl > 0:
            trade_result = "WINNER"
        elif pnl < 0:
            trade_result = "LOSER"
        else:
            trade_result = "BREAKEVEN"

        trade = Trade(
            position_id=position.id,
            symbol=position.symbol,
            entry_date=position.entry_date,
            entry_price=position.entry_price,
            quantity=position.quantity,
            exit_date=nepal_today(),
            exit_price=exit_price,
            duration_days=duration,
            entry_signal=position.entry_signal,
            exit_signal=reason,
            profit_loss=pnl,
            profit_loss_pct=pnl_pct,
            result=trade_result,
            is_paper=position.is_paper,
        )
        db.add(trade)

        logger.info(
            f"Closed {position.symbol}: {position.entry_price} -> {exit_price} "
            f"({pnl_pct:+.1f}%) [{reason}]"
        )

        return {
            "action": "stop_loss_hit",
            "exit_price": exit_price,
            "reason": reason,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "result": trade_result,
        }

    def get_open_positions(self, db: Session, is_paper: bool = False) -> List[Position]:
        """Get all open positions."""
        return (
            db.query(Position)
            .filter(Position.status == "OPEN", Position.is_paper == is_paper)
            .all()
        )

    def get_position(self, db: Session, position_id: int) -> Optional[Position]:
        return db.query(Position).filter(Position.id == position_id).first()

    def get_closed_positions(
        self, db: Session, is_paper: bool = False, limit: int = 50
    ) -> List[Position]:
        return (
            db.query(Position)
            .filter(Position.status == "CLOSED", Position.is_paper == is_paper)
            .order_by(Position.exit_date.desc())
            .limit(limit)
            .all()
        )

    def get_next_milestone_price(self, position: Position) -> float:
        """Calculate the price at which next trailing SL trigger occurs."""
        return round(
            position.base_price * (1 + settings.TRAILING_SL_TRIGGER_PCT), 2
        )

    def get_position_summary(self, position: Position) -> dict:
        """Get detailed summary of a position."""
        days_held = (nepal_today() - position.entry_date).days
        unrealized_pct = calculate_unrealized_pnl_pct(
            position.entry_price, position.current_price or position.entry_price
        )

        return {
            "id": position.id,
            "symbol": position.symbol,
            "entry_price": position.entry_price,
            "entry_date": str(position.entry_date),
            "quantity": position.quantity,
            "current_price": position.current_price,
            "base_price": position.base_price,
            "stop_loss": position.stop_loss,
            "unrealized_pnl": position.unrealized_pnl,
            "unrealized_pnl_pct": round(unrealized_pct, 2),
            "days_held": days_held,
            "milestone_count": position.milestone_count,
            "next_milestone_price": self.get_next_milestone_price(position),
            "status": "WINNING" if (position.unrealized_pnl or 0) > 0 else "LOSING",
            "is_paper": position.is_paper,
        }


position_manager = PositionManager()
