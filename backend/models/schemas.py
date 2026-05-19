from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class StockSchema(BaseModel):
    symbol: str
    name: Optional[str] = None
    sector: Optional[str] = None
    model_config = {"from_attributes": True}


class PriceSchema(BaseModel):
    symbol: str
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    volume: Optional[int] = None
    model_config = {"from_attributes": True}


class SignalSchema(BaseModel):
    id: Optional[int] = None
    symbol: str
    date: date
    signal_type: str
    confidence: float
    reason: Optional[str] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    target_3: Optional[float] = None
    suggested_quantity: Optional[int] = None
    risk_reward_ratio: Optional[float] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class PositionSchema(BaseModel):
    id: Optional[int] = None
    symbol: str
    entry_price: float
    entry_date: date
    quantity: int
    current_price: Optional[float] = None
    base_price: float
    stop_loss: float
    initial_stop_loss: float
    entry_signal: Optional[str] = None
    status: str = "OPEN"
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    milestone_count: int = 0
    is_paper: bool = False
    days_held: Optional[int] = None
    next_milestone_price: Optional[float] = None
    model_config = {"from_attributes": True}


class PositionCreate(BaseModel):
    symbol: str
    entry_price: float
    quantity: int
    stop_loss_pct: float = 0.05
    entry_signal: Optional[str] = None
    is_paper: bool = False


class TradeSchema(BaseModel):
    id: Optional[int] = None
    trade_number: Optional[int] = None
    position_id: Optional[int] = None
    symbol: str
    entry_date: date
    entry_price: float
    quantity: int
    exit_date: Optional[date] = None
    exit_price: Optional[float] = None
    duration_days: Optional[int] = None
    entry_signal: Optional[str] = None
    exit_signal: Optional[str] = None
    profit_loss: Optional[float] = None
    profit_loss_pct: Optional[float] = None
    result: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = None
    is_paper: bool = False
    model_config = {"from_attributes": True}


class TradeUpdate(BaseModel):
    notes: Optional[str] = None
    rating: Optional[int] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    quantity: Optional[int] = None
    entry_signal: Optional[str] = None
    exit_signal: Optional[str] = None
    result: Optional[str] = None


class PositionUpdate(BaseModel):
    stop_loss: Optional[float] = None
    entry_price: Optional[float] = None
    quantity: Optional[int] = None
    entry_signal: Optional[str] = None


class AlertSchema(BaseModel):
    id: Optional[int] = None
    alert_type: str
    title: Optional[str] = None
    message: str
    symbol: Optional[str] = None
    is_read: bool = False
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class PortfolioSummary(BaseModel):
    total_value: float
    total_invested: float
    total_unrealized_pnl: float
    total_unrealized_pnl_pct: float
    today_pnl: float
    today_pnl_pct: float
    cash_available: float
    open_positions: int
    win_rate: float
    total_trades: int


class PerformanceSchema(BaseModel):
    date: date
    portfolio_value: float
    daily_pnl: Optional[float] = None
    daily_pnl_pct: Optional[float] = None
    total_pnl: Optional[float] = None
    total_pnl_pct: Optional[float] = None
    win_rate: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    model_config = {"from_attributes": True}


class RiskMetrics(BaseModel):
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    value_at_risk: float
    profit_factor: float
    win_rate: float
    avg_win: float
    avg_loss: float
    total_trades: int
    winning_trades: int
    losing_trades: int


class BacktestRequest(BaseModel):
    symbols: List[str]
    start_date: date
    end_date: date
    initial_capital: float = 100000.0
    risk_per_trade: float = 0.02
    sma_short: int = 20
    sma_long: int = 50
    rsi_period: int = 14
    strategy: str = "trend_following"
    min_confirmations: int = 1


class BacktestResult(BaseModel):
    total_return: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    avg_holding_days: float
    best_trade: float
    worst_trade: float
    equity_curve: List[dict]
    trades: List[dict]
    monthly_returns: List[dict]
