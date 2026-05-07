from config import get_settings

settings = get_settings()


def calculate_unrealized_pnl(entry_price: float, current_price: float, quantity: int) -> float:
    return (current_price - entry_price) * quantity


def calculate_unrealized_pnl_pct(entry_price: float, current_price: float) -> float:
    if entry_price == 0:
        return 0.0
    return ((current_price - entry_price) / entry_price) * 100


def calculate_position_size(
    portfolio_value: float,
    entry_price: float,
    stop_loss_price: float,
    win_rate: float = 0.65,
    avg_win: float = 500.0,
    avg_loss: float = 300.0,
) -> int:
    """Calculate position size using Kelly Criterion with 2% risk per trade."""
    risk_per_trade = portfolio_value * settings.RISK_PER_TRADE
    loss_per_share = abs(entry_price - stop_loss_price)

    if loss_per_share == 0:
        return 0

    position_size = int(risk_per_trade / loss_per_share)
    max_size = int((portfolio_value * settings.MAX_POSITION_PCT) / entry_price)

    return min(position_size, max_size)


def calculate_commission(price: float, quantity: int, rate: float = 0.003) -> float:
    """Calculate broker commission (0.3% default for NEPSE)."""
    return price * quantity * rate


def calculate_risk_reward(
    entry_price: float, stop_loss: float, target: float
) -> float:
    """Calculate risk/reward ratio."""
    risk = abs(entry_price - stop_loss)
    reward = abs(target - entry_price)
    if risk == 0:
        return 0.0
    return round(reward / risk, 2)
