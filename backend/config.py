import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./nepse_bot.db"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = "maharjananil02@gmail.com"
    SMTP_PASSWORD: str = "jrtp oiop lvoa uxcv"
    ALERT_EMAIL_TO: str = "maharjananil02@gmail.com"

    # App
    SECRET_KEY: str = "change-this-to-a-random-secret-key"
    DEBUG: bool = True
    PAPER_TRADING_CAPITAL: float = 1000000.0

    # NEPSE Data Source
    NEPSE_DATA_URL: str = "https://www.sharesansar.com"

    # Risk parameters
    RISK_PER_TRADE: float = 0.02
    MAX_POSITIONS: int = 10
    MAX_POSITION_PCT: float = 0.25
    TRAILING_SL_TRIGGER_PCT: float = 0.10
    TRAILING_SL_LOCK_PCT: float = 0.05
    HARD_STOP_LOSS_PCT: float = 0.10
    MAX_DRAWDOWN_ALERT_PCT: float = 0.08
    MAX_DRAWDOWN_PAUSE_PCT: float = 0.10
    DAILY_LOSS_LIMIT_PCT: float = 0.05
    MAX_SECTOR_CONCENTRATION: float = 0.50
    MIN_HOLDING_DAYS: int = 2
    MAX_HOLDING_DAYS: int = 60

    # Auto-execution
    AUTO_EXECUTE_PAPER: bool = True  # Auto-execute BUY signals in paper trading
    AUTO_EXECUTE_MIN_CONFIDENCE: float = 65.0  # Minimum confidence to auto-execute

    # Market hours (Nepal Time)
    MARKET_OPEN_HOUR: int = 11
    MARKET_OPEN_MINUTE: int = 0
    MARKET_CLOSE_HOUR: int = 15
    MARKET_CLOSE_MINUTE: int = 0


# Runtime state (toggled via API)
_runtime_state = {
    "auto_execute_enabled": True,
}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
