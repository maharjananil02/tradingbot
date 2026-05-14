"""Trace how a signal is calculated for a given stock."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import SessionLocal
from models.tables import Signal, Price
from utils.validators import nepal_today
from utils.technical_indicators import (
    calculate_sma, calculate_rsi, calculate_macd,
    calculate_volume_sma, calculate_atr, detect_double_bottom, is_breakout,
)

symbol = sys.argv[1] if len(sys.argv) > 1 else "SAHAS"
db = SessionLocal()

# Check signal
sig = db.query(Signal).filter(Signal.symbol == symbol).order_by(Signal.date.desc()).first()
if sig:
    print(f"=== {symbol} Signal ({sig.date}) ===")
    print(f"Type: {sig.signal_type} | Confidence: {sig.confidence}%")
    print(f"Reason: {sig.reason}")
    print(f"Entry: {sig.entry_price} | SL: {sig.stop_loss}")
    print(f"T1: {sig.target_1} | T2: {sig.target_2} | T3: {sig.target_3}")
    print(f"Qty: {sig.suggested_quantity} | R:R: {sig.risk_reward_ratio}")
else:
    print(f"No signal found for {symbol}")

# Trace indicators
print(f"\n=== INDICATOR BREAKDOWN ===")
prices = db.query(Price).filter(Price.symbol == symbol).order_by(Price.date.desc()).limit(200).all()[::-1]
print(f"Price records: {len(prices)}")

if len(prices) >= 50:
    closes = [p.close for p in prices]
    volumes = [p.volume or 0 for p in prices]
    highs = [p.high or p.close for p in prices]
    lows = [p.low or p.close for p in prices]

    print(f"Current price: Rs.{closes[-1]} (date: {prices[-1].date})")
    print(f"Current volume: {volumes[-1]:,}")

    # 1. Volume filter
    vol_sma = calculate_volume_sma(volumes, 20)
    avg_vol = vol_sma[-1] or 0
    surge = volumes[-1] > avg_vol * 1.2 if avg_vol > 0 else False
    print(f"\n1. VOLUME FILTER")
    print(f"   20d avg volume: {avg_vol:,.0f}")
    print(f"   Current volume: {volumes[-1]:,}")
    print(f"   Volume surge (>1.2x avg): {'YES' if surge else 'NO'}")
    print(f"   Passes liquidity (avg>100): {'YES' if avg_vol >= 100 else 'NO - FILTERED OUT'}")

    # 2. SMA Trend
    sma20 = calculate_sma(closes, 20)
    sma50 = calculate_sma(closes, 50)
    print(f"\n2. TREND FOLLOWING (SMA Crossover)")
    print(f"   SMA20: {sma20[-1]:.2f}")
    print(f"   SMA50: {sma50[-1]:.2f}")
    print(f"   Price > SMA20: {'YES' if closes[-1] > sma20[-1] else 'NO'}")
    print(f"   SMA20 > SMA50: {'YES' if sma20[-1] > sma50[-1] else 'NO'}")
    fresh_cross = False
    for i in range(-3, 0):
        if (sma20[i-1] is not None and sma50[i-1] is not None
                and sma20[i-1] <= sma50[i-1] and sma20[i] > sma50[i]):
            fresh_cross = True
            break
    print(f"   Fresh bullish crossover (3d): {'YES -> SIGNAL' if fresh_cross else 'NO'}")

    # 3. RSI
    rsi = calculate_rsi(closes, 14)
    curr_rsi = rsi[-1]
    prev_rsi = rsi[-2]
    oversold_bounce = curr_rsi < 35 and prev_rsi < 30 and curr_rsi > prev_rsi
    print(f"\n3. RSI (Oversold Bounce)")
    print(f"   Current RSI: {curr_rsi:.1f}")
    print(f"   Previous RSI: {prev_rsi:.1f}")
    print(f"   Was <30 & bouncing up & still <35: {'YES -> SIGNAL' if oversold_bounce else 'NO'}")

    # 4. MACD
    macd = calculate_macd(closes)
    macd_line = macd["macd"]
    signal_line = macd["signal"]
    bullish_cross = macd_line[-2] <= signal_line[-2] and macd_line[-1] > signal_line[-1]
    print(f"\n4. MACD (Bullish Crossover)")
    print(f"   MACD line: {macd_line[-1]:.3f} (prev: {macd_line[-2]:.3f})")
    print(f"   Signal line: {signal_line[-1]:.3f} (prev: {signal_line[-2]:.3f})")
    print(f"   Bullish crossover: {'YES -> SIGNAL' if bullish_cross else 'NO'}")

    # 5. Patterns
    dbl_bottom = detect_double_bottom(closes)
    breakout = is_breakout(closes, volumes, 20)
    print(f"\n5. PATTERNS")
    print(f"   Double bottom: {'YES -> SIGNAL' if dbl_bottom else 'NO'}")
    print(f"   Breakout (20d high + volume): {'YES -> SIGNAL' if breakout else 'NO'}")

    # Count confirming signals
    buy_count = sum([fresh_cross, oversold_bounce, bullish_cross, dbl_bottom, breakout])
    print(f"\n=== VERDICT ===")
    print(f"Buy confirmations: {buy_count} (need >= 2)")
    print(f"Volume surge bonus: {'YES (+8%)' if surge else 'NO'}")
    if buy_count >= 2:
        print(f"RESULT: BUY signal generated")
    else:
        print(f"RESULT: NO signal (insufficient confirmations)")

    # ATR stop loss
    atr = calculate_atr(highs, lows, closes, 14)
    if atr[-1]:
        print(f"\nATR(14): {atr[-1]:.2f}")
        print(f"ATR-based SL: Rs.{closes[-1] - atr[-1]*2:.2f} ({(atr[-1]*2/closes[-1]*100):.1f}% below entry)")
        rr = (atr[-1]*3) / (atr[-1]*2) if atr[-1]*2 > 0 else 0
        print(f"Risk:Reward ratio: 1:{rr:.1f}")

db.close()
