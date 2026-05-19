import sys
sys.path.insert(0, '.')
from models.database import SessionLocal
from models.tables import Price
from datetime import date, timedelta
from utils.technical_indicators import calculate_sma, calculate_rsi, calculate_macd, calculate_volume_sma

db = SessionLocal()
symbol = 'BHL'
start_date = date(2025, 12, 1)
end_date = date(2026, 5, 7)
sma_long = 50
sma_short = 20
initial_capital = 1000000.0
risk_per_trade = 0.02
min_confirmations = 1

warmup_days = max(sma_long, 60) + 10
warmup_start = start_date - timedelta(days=int(warmup_days * 1.5))

prices = db.query(Price).filter(Price.symbol == symbol, Price.date >= warmup_start, Price.date <= end_date).order_by(Price.date).all()
closes = [p.close for p in prices]
dates = [p.date for p in prices]
volumes = [p.volume or 0 for p in prices]

sma_short_arr = calculate_sma(closes, sma_short)
sma_long_arr = calculate_sma(closes, sma_long)
rsi = calculate_rsi(closes, 14)
macd_data = calculate_macd(closes)
vol_sma = calculate_volume_sma(volumes, 20)

cash = initial_capital
positions = {}
trades = []

for i in range(sma_long, len(closes)):
    current_price = closes[i]
    current_date = dates[i]
    if current_date < start_date:
        continue

    if symbol in positions:
        pos = positions[symbol]
        gain = (current_price - pos['base_price']) / pos['base_price']
        if gain >= 0.10:
            new_base = current_price * 0.95
            if new_base > pos['stop_loss']:
                pos['base_price'] = new_base
                pos['stop_loss'] = new_base
                print(f"  [{current_date}] Trailing stop adjusted to {pos['stop_loss']:.2f}")
        if current_price <= pos['stop_loss']:
            pnl = (current_price - pos['entry_price']) * pos['quantity']
            print(f"SELL [{current_date}] price={current_price} qty={pos['quantity']} entry={pos['entry_price']} pnl={pnl:.2f} reason=STOP_LOSS")
            cash += current_price * pos['quantity']
            trades.append({'exit': current_date, 'pnl': pnl, 'reason': 'STOP_LOSS', 'entry': pos['entry_date'], 'entry_price': pos['entry_price'], 'exit_price': current_price, 'qty': pos['quantity']})
            del positions[symbol]
        elif (current_date - pos['entry_date']).days >= 60:
            pnl = (current_price - pos['entry_price']) * pos['quantity']
            print(f"SELL [{current_date}] price={current_price} qty={pos['quantity']} entry={pos['entry_price']} pnl={pnl:.2f} reason=TIME_STOP")
            cash += current_price * pos['quantity']
            trades.append({'exit': current_date, 'pnl': pnl, 'reason': 'TIME_STOP', 'entry': pos['entry_date'], 'entry_price': pos['entry_price'], 'exit_price': current_price, 'qty': pos['quantity']})
            del positions[symbol]

    if symbol not in positions and cash > current_price:
        c1=c2=c3=c4=False
        if sma_short_arr[i] is not None and sma_long_arr[i] is not None and sma_short_arr[i] > sma_long_arr[i]:
            for j in range(max(1,i-2),i+1):
                if sma_short_arr[j-1] is not None and sma_long_arr[j-1] is not None and sma_short_arr[j-1] <= sma_long_arr[j-1] and sma_short_arr[j] > sma_long_arr[j]:
                    c1=True; break
        if rsi[i] is not None and rsi[i-1] is not None and rsi[i-1] < 30 and rsi[i] > rsi[i-1] and rsi[i] < 35:
            c2=True
        if i > 0 and macd_data['macd'][i-1] <= macd_data['signal'][i-1] and macd_data['macd'][i] > macd_data['signal'][i]:
            c3=True
        if vol_sma[i] is not None and vol_sma[i] > 0 and volumes[i] > vol_sma[i] * 1.2:
            c4=True
        confirmations = sum([c1,c2,c3,c4])
        signals_fired = [s for s,v in [('SMA',c1),('RSI',c2),('MACD',c3),('VOL',c4)] if v]
        if confirmations >= min_confirmations:
            risk_amt = cash * risk_per_trade
            stop_loss = current_price * 0.95
            loss_per_share = current_price - stop_loss
            quantity = max(1, int(risk_amt / loss_per_share))
            cost = current_price * quantity
            if cost <= cash:
                positions[symbol] = {'entry_price': current_price, 'entry_date': current_date, 'quantity': quantity, 'stop_loss': stop_loss, 'base_price': current_price}
                cash -= cost
                print(f"BUY  [{current_date}] price={current_price} qty={quantity} cost={cost:.2f} stop={stop_loss:.2f} signals={signals_fired} sma20={sma_short_arr[i]:.2f} sma50={sma_long_arr[i]:.2f} rsi={rsi[i]:.1f} cash_left={cash:.2f}")

# Close remaining
if symbol in positions:
    pos = positions[symbol]
    last = closes[-1]
    pnl = (last - pos['entry_price']) * pos['quantity']
    print(f"SELL [{end_date}] price={last} qty={pos['quantity']} entry={pos['entry_price']} pnl={pnl:.2f} reason=END_OF_BACKTEST")
    cash += last * pos['quantity']
    trades.append({'exit': end_date, 'pnl': pnl, 'reason': 'END', 'entry': pos['entry_date'], 'entry_price': pos['entry_price'], 'exit_price': last, 'qty': pos['quantity']})

print()
print('=== SUMMARY ===')
print(f'Initial Capital: {initial_capital}')
print(f'Final Cash: {cash:.2f}')
print(f'Total Return: {cash - initial_capital:.2f} ({((cash-initial_capital)/initial_capital)*100:.2f}%)')
print(f'Total Trades: {len(trades)}')
wins = [t for t in trades if t['pnl'] > 0]
losses = [t for t in trades if t['pnl'] <= 0]
print(f'Wins: {len(wins)}, Losses: {len(losses)}')
