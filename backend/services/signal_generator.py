import logging
from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session

from config import get_settings
from models.tables import Signal, Price, Stock
from utils.validators import nepal_today
from utils.technical_indicators import (
    calculate_sma, calculate_rsi, calculate_macd,
    find_support_resistance, detect_double_bottom, is_breakout,
    calculate_volume_sma, calculate_atr,
)
from utils.calculations import calculate_position_size, calculate_risk_reward

logger = logging.getLogger(__name__)
settings = get_settings()


class SignalGenerator:
    """Generates trading signals based on technical analysis."""

    def generate_signals_for_stock(
        self, db: Session, symbol: str, portfolio_value: float = 100000.0
    ) -> Optional[Signal]:
        """Generate trading signal for a single stock.
        
        Only generates a signal when at least 2 indicators agree,
        volume confirms, and individual indicator confidence is high.
        """
        prices = (
            db.query(Price)
            .filter(Price.symbol == symbol)
            .order_by(Price.date.desc())
            .limit(200)
            .all()
        )[::-1]

        if len(prices) < 50:
            return None

        closes = [p.close for p in prices]
        volumes = [p.volume or 0 for p in prices]
        highs = [p.high or p.close for p in prices]
        lows = [p.low or p.close for p in prices]

        # ── Volume filter: skip low-volume / illiquid stocks ──
        vol_sma = calculate_volume_sma(volumes, 20)
        current_volume = volumes[-1]
        avg_volume = vol_sma[-1]
        if avg_volume is None or avg_volume < 100:
            return None  # Skip illiquid stocks

        volume_surge = current_volume > avg_volume * 1.2 if avg_volume > 0 else False

        signals = []

        # A. Trend-Following Signal (fresh crossover only)
        trend_signal = self._check_trend_following(closes)
        if trend_signal:
            signals.append(trend_signal)

        # B. Momentum Signal (RSI extreme zones)
        rsi_signal = self._check_rsi(closes)
        if rsi_signal:
            signals.append(rsi_signal)

        # C. MACD Signal (crossover only)
        macd_signal = self._check_macd(closes)
        if macd_signal:
            signals.append(macd_signal)

        # D. Pattern-based (breakout, double bottom only)
        pattern_signal = self._check_patterns(closes, volumes)
        if pattern_signal:
            signals.append(pattern_signal)

        if not signals:
            return None

        # ── Require at least 2 confirming indicators ──
        buy_signals = [s for s in signals if s["type"] == "BUY"]
        sell_signals = [s for s in signals if s["type"] == "SELL"]

        if len(buy_signals) >= 2:
            confidence = sum(s["confidence"] for s in buy_signals) / len(buy_signals)
            reasons = ", ".join(s["reason"] for s in buy_signals)
            signal_type = "BUY"
            # Boost for volume confirmation
            if volume_surge:
                confidence = min(confidence + 8, 95)
                reasons += ", Volume Surge"
            # Boost for 3+ confirming signals
            if len(buy_signals) >= 3:
                confidence = min(confidence + 5, 95)
        elif len(sell_signals) >= 2:
            confidence = sum(s["confidence"] for s in sell_signals) / len(sell_signals)
            reasons = ", ".join(s["reason"] for s in sell_signals)
            signal_type = "SELL"
            if len(sell_signals) >= 3:
                confidence = min(confidence + 5, 95)
        else:
            # Only 1 indicator fired — not enough confirmation
            return None

        current_price = closes[-1]

        # ── ATR-based stop loss (volatility-adjusted) ──
        atr = calculate_atr(highs, lows, closes, 14)
        atr_value = atr[-1]
        if atr_value and atr_value > 0:
            stop_loss = round(current_price - (atr_value * 2), 2)
            target_1 = round(current_price + (atr_value * 2), 2)
            target_2 = round(current_price + (atr_value * 3), 2)
            target_3 = round(current_price + (atr_value * 4), 2)
        else:
            stop_loss = round(current_price * 0.95, 2)
            target_1 = round(current_price * 1.05, 2)
            target_2 = round(current_price * 1.10, 2)
            target_3 = round(current_price * 1.15, 2)

        qty = calculate_position_size(portfolio_value, current_price, stop_loss)
        rr = calculate_risk_reward(current_price, stop_loss, target_2)

        # ── Skip if risk-reward is poor ──
        if rr is not None and rr < 1.5:
            return None

        signal = Signal(
            symbol=symbol,
            date=nepal_today(),
            signal_type=signal_type,
            confidence=round(confidence, 1),
            reason=reasons,
            entry_price=current_price,
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            suggested_quantity=qty,
            risk_reward_ratio=rr,
        )

        return signal

    def generate_all_signals(
        self, db: Session, portfolio_value: float = 100000.0
    ) -> List[Signal]:
        """Generate signals for all stocks."""
        stocks = db.query(Stock).all()
        today = nepal_today()
        generated = []

        for stock in stocks:
            # Skip if signal already generated today
            existing = (
                db.query(Signal)
                .filter(Signal.symbol == stock.symbol, Signal.date == today)
                .first()
            )
            if existing:
                continue

            try:
                signal = self.generate_signals_for_stock(db, stock.symbol, portfolio_value)
                if signal and signal.confidence >= 70:
                    db.add(signal)
                    generated.append(signal)
            except Exception as e:
                logger.error(f"Error generating signal for {stock.symbol}: {e}")

        if generated:
            db.commit()

        return generated

    def _check_trend_following(self, closes: List[float]) -> Optional[dict]:
        """SMA Crossover: Only signal on FRESH crossover (within last 3 days)."""
        sma_20 = calculate_sma(closes, 20)
        sma_50 = calculate_sma(closes, 50)

        if sma_20[-1] is None or sma_50[-1] is None:
            return None

        current = closes[-1]

        # Buy: Fresh bullish crossover (SMA20 crossed above SMA50 within last 3 days)
        if sma_20[-1] > sma_50[-1] and current > sma_20[-1]:
            for i in range(-3, 0):
                if (sma_20[i - 1] is not None and sma_50[i - 1] is not None and
                        sma_20[i - 1] <= sma_50[i - 1] and sma_20[i] > sma_50[i]):
                    return {
                        "type": "BUY",
                        "confidence": 75.0,
                        "reason": "SMA20/50 Bullish Crossover",
                    }
            # No fresh crossover — skip (was: weak "Uptrend" signal)
            return None

        # Sell: Fresh bearish crossover (SMA20 crossed below SMA50 within last 3 days)
        if sma_20[-1] < sma_50[-1] and current < sma_20[-1]:
            for i in range(-3, 0):
                if (sma_20[i - 1] is not None and sma_50[i - 1] is not None and
                        sma_20[i - 1] >= sma_50[i - 1] and sma_20[i] < sma_50[i]):
                    return {
                        "type": "SELL",
                        "confidence": 73.0,
                        "reason": "SMA20/50 Bearish Crossover",
                    }
            return None

        return None

    def _check_rsi(self, closes: List[float]) -> Optional[dict]:
        """RSI signal: Buy only on confirmed oversold bounce, sell on overbought reversal."""
        rsi = calculate_rsi(closes, 14)

        if rsi[-1] is None or rsi[-2] is None:
            return None

        current_rsi = rsi[-1]
        prev_rsi = rsi[-2]

        # Buy: RSI was below 30 and is now bouncing up (confirmed reversal)
        if current_rsi < 35 and prev_rsi < 30 and current_rsi > prev_rsi:
            return {
                "type": "BUY",
                "confidence": 72.0,
                "reason": f"RSI Oversold Bounce ({current_rsi:.1f})",
            }

        # Sell: RSI was above 70 and is now dropping (confirmed reversal)
        if current_rsi > 65 and prev_rsi > 70 and current_rsi < prev_rsi:
            return {
                "type": "SELL",
                "confidence": 70.0,
                "reason": f"RSI Overbought Reversal ({current_rsi:.1f})",
            }

        return None

    def _check_macd(self, closes: List[float]) -> Optional[dict]:
        """MACD signal: Buy on bullish crossover, sell on bearish."""
        macd = calculate_macd(closes)
        macd_line = macd["macd"]
        signal_line = macd["signal"]
        histogram = macd["histogram"]

        if len(macd_line) < 2:
            return None

        # Bullish crossover: MACD crosses above signal
        if (macd_line[-2] <= signal_line[-2] and macd_line[-1] > signal_line[-1]):
            return {
                "type": "BUY",
                "confidence": 68.0,
                "reason": "MACD Bullish Crossover",
            }

        # Bearish crossover
        if (macd_line[-2] >= signal_line[-2] and macd_line[-1] < signal_line[-1]):
            return {
                "type": "SELL",
                "confidence": 66.0,
                "reason": "MACD Bearish Crossover",
            }

        return None

    def _check_patterns(
        self, closes: List[float], volumes: List[int]
    ) -> Optional[dict]:
        """Pattern-based signals: breakout and double bottom only."""

        # Breakout signal (already requires volume > 1.5x average)
        if is_breakout(closes, volumes, 20):
            return {
                "type": "BUY",
                "confidence": 72.0,
                "reason": "Breakout above 20-day high on volume",
            }

        # Double bottom reversal pattern
        if detect_double_bottom(closes):
            return {
                "type": "BUY",
                "confidence": 68.0,
                "reason": "Double Bottom Pattern",
            }

        return None

    def get_todays_signals(self, db: Session) -> List[Signal]:
        """Get all signals generated today."""
        return (
            db.query(Signal)
            .filter(Signal.date == nepal_today())
            .order_by(Signal.confidence.desc())
            .all()
        )


signal_generator = SignalGenerator()
