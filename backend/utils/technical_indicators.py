import numpy as np
import pandas as pd
from typing import List, Optional, Dict


def calculate_sma(prices: List[float], period: int) -> List[Optional[float]]:
    """Calculate Simple Moving Average."""
    if len(prices) < period:
        return [None] * len(prices)
    series = pd.Series(prices)
    sma = series.rolling(window=period).mean()
    return sma.tolist()


def calculate_ema(prices: List[float], period: int) -> List[Optional[float]]:
    """Calculate Exponential Moving Average."""
    if len(prices) < period:
        return [None] * len(prices)
    series = pd.Series(prices)
    ema = series.ewm(span=period, adjust=False).mean()
    return ema.tolist()


def calculate_rsi(prices: List[float], period: int = 14) -> List[Optional[float]]:
    """Calculate Relative Strength Index."""
    if len(prices) < period + 1:
        return [None] * len(prices)

    series = pd.Series(prices)
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.inf)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50.0)
    return rsi.tolist()


def calculate_macd(
    prices: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> Dict[str, List[Optional[float]]]:
    """Calculate MACD, Signal, and Histogram."""
    series = pd.Series(prices)
    ema_fast = series.ewm(span=fast_period, adjust=False).mean()
    ema_slow = series.ewm(span=slow_period, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line

    return {
        "macd": macd_line.tolist(),
        "signal": signal_line.tolist(),
        "histogram": histogram.tolist(),
    }


def calculate_bollinger_bands(
    prices: List[float], period: int = 20, num_std: float = 2.0
) -> Dict[str, List[Optional[float]]]:
    """Calculate Bollinger Bands."""
    series = pd.Series(prices)
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)

    return {
        "upper": upper.tolist(),
        "middle": sma.tolist(),
        "lower": lower.tolist(),
    }


def calculate_atr(
    highs: List[float], lows: List[float], closes: List[float], period: int = 14
) -> List[Optional[float]]:
    """Calculate Average True Range."""
    if len(highs) < 2:
        return [None] * len(highs)

    high = pd.Series(highs)
    low = pd.Series(lows)
    close = pd.Series(closes)
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr.tolist()


def calculate_volume_sma(volumes: List[int], period: int = 20) -> List[Optional[float]]:
    """Calculate volume SMA for volume analysis."""
    series = pd.Series(volumes, dtype=float)
    sma = series.rolling(window=period).mean()
    return sma.tolist()


def find_support_resistance(
    prices: List[float], window: int = 20
) -> Dict[str, Optional[float]]:
    """Find nearest support and resistance levels."""
    if len(prices) < window:
        return {"support": None, "resistance": None}

    current = prices[-1]
    recent = prices[-window:]
    high_52w = max(prices[-min(252, len(prices)):])
    low_52w = min(prices[-min(252, len(prices)):])

    # Simple support: recent low, resistance: recent high
    return {
        "support": min(recent),
        "resistance": max(recent),
        "high_52w": high_52w,
        "low_52w": low_52w,
    }


def detect_double_bottom(prices: List[float], tolerance: float = 0.03) -> bool:
    """Detect double bottom pattern."""
    if len(prices) < 20:
        return False

    recent = prices[-20:]
    min_idx = np.argmin(recent)

    # Look for second bottom
    for i in range(min_idx + 3, len(recent)):
        if abs(recent[i] - recent[min_idx]) / recent[min_idx] < tolerance:
            # Check if there's a peak between the two bottoms
            between = recent[min_idx:i]
            if len(between) > 2:
                peak = max(between)
                if (peak - recent[min_idx]) / recent[min_idx] > 0.03:
                    return True
    return False


def is_breakout(prices: List[float], volumes: List[int], period: int = 20) -> bool:
    """Detect breakout above period high on high volume."""
    if len(prices) < period + 1 or len(volumes) < period + 1:
        return False

    current_price = prices[-1]
    period_high = max(prices[-(period + 1):-1])
    avg_volume = np.mean(volumes[-(period + 1):-1])
    current_volume = volumes[-1]

    return current_price > period_high and current_volume > avg_volume * 1.5
