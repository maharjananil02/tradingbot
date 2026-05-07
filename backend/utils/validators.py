from datetime import datetime, time, timezone, timedelta
from config import get_settings

settings = get_settings()

# Nepal timezone: UTC+5:45
NPT = timezone(timedelta(hours=5, minutes=45))


def nepal_now() -> datetime:
    """Get current datetime in Nepal Time (Asia/Kathmandu, UTC+5:45)."""
    return datetime.now(NPT)


def nepal_today():
    """Get today's date in Nepal Time."""
    return nepal_now().date()


# NEPSE holidays (update yearly)
NEPSE_HOLIDAYS_2026 = [
    "2026-01-01", "2026-01-14", "2026-01-29", "2026-02-19",
    "2026-03-08", "2026-03-29", "2026-04-14", "2026-05-01",
    "2026-05-26", "2026-09-03", "2026-10-02", "2026-10-15",
    "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23",
    "2026-10-24", "2026-11-05", "2026-12-25",
]


def is_market_open() -> bool:
    """Check if NEPSE market is currently open (Nepal Time)."""
    now = nepal_now()

    # Weekend check (Saturday is 5, Sunday is 6 - Nepal has Saturday as weekend)
    if now.weekday() in (5, 6):  # Saturday, Sunday
        return False

    # Holiday check
    today_str = now.strftime("%Y-%m-%d")
    if today_str in NEPSE_HOLIDAYS_2026:
        return False

    # Time check
    market_open = time(settings.MARKET_OPEN_HOUR, settings.MARKET_OPEN_MINUTE)
    market_close = time(settings.MARKET_CLOSE_HOUR, settings.MARKET_CLOSE_MINUTE)
    current_time = now.time()

    return market_open <= current_time <= market_close


def is_trading_day() -> bool:
    """Check if today is a trading day (Nepal Time)."""
    now = nepal_now()
    if now.weekday() in (5, 6):
        return False
    today_str = now.strftime("%Y-%m-%d")
    return today_str not in NEPSE_HOLIDAYS_2026


def validate_symbol(symbol: str) -> str:
    """Validate and normalize stock symbol."""
    return symbol.strip().upper()


def validate_quantity(quantity: int) -> int:
    """Validate quantity is positive."""
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    return quantity


def validate_price(price: float) -> float:
    """Validate price is positive."""
    if price <= 0:
        raise ValueError("Price must be positive")
    return price
