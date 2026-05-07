import pytest
from utils.technical_indicators import (
    calculate_sma, calculate_rsi, calculate_macd,
    calculate_ema, calculate_bollinger_bands,
    detect_double_bottom, is_breakout,
)


class TestSMA:
    def test_basic_sma(self):
        prices = [10, 20, 30, 40, 50]
        result = calculate_sma(prices, 3)
        assert result[-1] == pytest.approx(40.0)
        assert result[-2] == pytest.approx(30.0)

    def test_sma_insufficient_data(self):
        prices = [10, 20]
        result = calculate_sma(prices, 5)
        assert all(v is None for v in result)


class TestRSI:
    def test_rsi_range(self):
        prices = list(range(100, 130)) + list(range(130, 100, -1))
        rsi = calculate_rsi(prices, 14)
        valid = [r for r in rsi if r is not None]
        for r in valid:
            assert 0 <= r <= 100

    def test_rsi_overbought(self):
        # Steadily rising prices should give high RSI
        prices = list(range(100, 150))
        rsi = calculate_rsi(prices, 14)
        assert rsi[-1] > 70

    def test_rsi_oversold(self):
        # Steadily falling prices should give low RSI
        prices = list(range(150, 100, -1))
        rsi = calculate_rsi(prices, 14)
        assert rsi[-1] < 30


class TestMACD:
    def test_macd_structure(self):
        prices = list(range(100, 150))
        result = calculate_macd(prices)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result
        assert len(result["macd"]) == len(prices)


class TestSignalGeneration:
    def test_sma_buy_signal(self):
        """SMA20 > SMA50 should indicate bullish trend."""
        # Create uptrending data
        prices = list(range(100, 200, 2))
        sma_20 = calculate_sma(prices, 20)
        sma_50 = calculate_sma(prices, min(50, len(prices)))

        if sma_20[-1] is not None and sma_50[-1] is not None:
            assert sma_20[-1] > sma_50[-1]  # SMA20 should be above SMA50 in uptrend

    def test_breakout_detection(self):
        # Normal prices then a breakout
        prices = [100] * 20 + [120]
        volumes = [1000] * 20 + [2000]
        assert is_breakout(prices, volumes, 20) is True

    def test_no_breakout(self):
        prices = [100] * 21
        volumes = [1000] * 21
        assert is_breakout(prices, volumes, 20) is False
