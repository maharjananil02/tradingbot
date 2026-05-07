from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, Boolean, Text, Enum as SAEnum
)
from sqlalchemy.sql import func
from models.database import Base
import enum


class SignalType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    EXIT = "EXIT"


class PositionStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class TradeResult(str, enum.Enum):
    WINNER = "WINNER"
    LOSER = "LOSER"
    BREAKEVEN = "BREAKEVEN"


class AlertType(str, enum.Enum):
    MARKET_OPEN = "MARKET_OPEN"
    MARKET_CLOSE = "MARKET_CLOSE"
    PRICE_MILESTONE = "PRICE_MILESTONE"
    STOP_LOSS_WARNING = "STOP_LOSS_WARNING"
    STOP_LOSS_HIT = "STOP_LOSS_HIT"
    MID_DAY_UPDATE = "MID_DAY_UPDATE"
    RISK_ALERT = "RISK_ALERT"
    SIGNAL = "SIGNAL"
    NEWS = "NEWS"


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(200))
    sector = Column(String(100))
    listing_date = Column(Date)
    isin = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())


class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float, nullable=False)
    volume = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    signal_type = Column(String(10), nullable=False)
    confidence = Column(Float, nullable=False)
    reason = Column(Text)
    entry_price = Column(Float)
    stop_loss = Column(Float)
    target_1 = Column(Float)
    target_2 = Column(Float)
    target_3 = Column(Float)
    suggested_quantity = Column(Integer)
    risk_reward_ratio = Column(Float)
    actual_outcome = Column(String(20))
    created_at = Column(DateTime, server_default=func.now())


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    entry_price = Column(Float, nullable=False)
    entry_date = Column(Date, nullable=False)
    quantity = Column(Integer, nullable=False)
    current_price = Column(Float)
    base_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    initial_stop_loss = Column(Float, nullable=False)
    entry_signal = Column(String(50))
    status = Column(String(10), default=PositionStatus.OPEN.value)
    exit_price = Column(Float)
    exit_date = Column(Date)
    exit_reason = Column(String(100))
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    milestone_count = Column(Integer, default=0)
    is_paper = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    trade_number = Column(Integer)
    position_id = Column(Integer, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    entry_date = Column(Date, nullable=False)
    entry_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    exit_date = Column(Date)
    exit_price = Column(Float)
    duration_days = Column(Integer)
    entry_signal = Column(String(100))
    exit_signal = Column(String(100))
    profit_loss = Column(Float)
    profit_loss_pct = Column(Float)
    result = Column(String(20))
    notes = Column(Text)
    rating = Column(Integer)
    is_paper = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(30), nullable=False)
    title = Column(String(200))
    message = Column(Text, nullable=False)
    symbol = Column(String(20))
    is_read = Column(Boolean, default=False)
    sent_telegram = Column(Boolean, default=False)
    sent_email = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class Performance(Base):
    __tablename__ = "performance"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)
    portfolio_value = Column(Float, nullable=False)
    daily_pnl = Column(Float)
    daily_pnl_pct = Column(Float)
    total_pnl = Column(Float)
    total_pnl_pct = Column(Float)
    win_rate = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    open_positions = Column(Integer)
    total_trades = Column(Integer)
    is_paper = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    action = Column(String(10), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    commission = Column(Float, default=0.0)
    total_cost = Column(Float, nullable=False)
    balance_after = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class PaperPosition(Base):
    __tablename__ = "paper_positions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    quantity = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)
    current_price = Column(Float)
    unrealized_pnl = Column(Float, default=0.0)
    status = Column(String(10), default=PositionStatus.OPEN.value)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
