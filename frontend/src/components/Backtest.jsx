import { useState } from 'react';
import { runBacktest } from '../utils/api';
import { Play, Loader, Download, FileText } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar,
} from 'recharts';

export default function Backtest() {
  const [form, setForm] = useState({
    symbols: 'NABIL,NLIC,SCB,HBL,SBI',
    start_date: '2026-01-01',
    end_date: '2026-05-07',
    initial_capital: 1000000,
    risk_per_trade: 0.02,
    sma_short: 20,
    sma_long: 50,
    rsi_period: 14,
    strategy: 'trend_following',
    min_confirmations: 1,
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const downloadCSV = () => {
    if (!result?.trades?.length) return;
    const headers = ['Symbol','Entry Date','Exit Date','Entry Price','Exit Price','Quantity','P&L','P&L %','Days','Exit Reason'];
    const rows = result.trades.map(t => [
      t.symbol, t.entry_date, t.exit_date, t.entry_price, t.exit_price,
      t.quantity, t.pnl, t.pnl_pct, t.duration, t.exit_reason
    ]);
    const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url;
    a.download = `backtest_${form.symbols.replace(/,/g,'_')}_${form.start_date}_${form.end_date}.csv`;
    a.click(); URL.revokeObjectURL(url);
  };

  const downloadReport = () => {
    if (!result) return;
    const symbols = Array.isArray(form.symbols) ? form.symbols.join(', ') : form.symbols;
    const W = 60;
    const hr = '='.repeat(W);
    const hr2 = '-'.repeat(W);
    const center = (s) => s.padStart(Math.floor((W + s.length) / 2)).padEnd(W);

    const outcome = result.total_return >= 0 ? 'PROFIT' : 'LOSS';
    const lines = [
      hr,
      center('NEPSE BACKTEST REPORT'),
      center('Nepal Stock Exchange Trading Simulator'),
      hr,
      '',
      '  WHAT IS THIS REPORT?',
      '  This report simulates how a trading strategy would have',
      '  performed on real historical stock prices — WITHOUT using',
      '  real money. Think of it as a "practice run" in the past.',
      '',
      hr2,
      '  TEST SETTINGS',
      hr2,
      `  Stock(s)          : ${symbols}`,
      `  Period Tested     : ${form.start_date}  to  ${form.end_date}`,
      `  Starting Money    : NPR ${Number(form.initial_capital).toLocaleString()}`,
      `  Risk Per Trade    : ${(form.risk_per_trade * 100).toFixed(1)}% of available cash`,
      `  Strategy          : ${form.strategy}`,
      `  SMA Short / Long  : ${form.sma_short} days / ${form.sma_long} days`,
      `  Min Signals Needed: ${form.min_confirmations} (out of 4 possible)`,
      '',
      hr2,
      '  FINAL RESULT',
      hr2,
      `  Starting Money    : NPR ${Number(form.initial_capital).toLocaleString()}`,
      `  Ending Money      : NPR ${(Number(form.initial_capital) + result.total_return).toLocaleString()}`,
      `  Net ${outcome.padEnd(12)}  : NPR ${result.total_return?.toLocaleString()} (${result.total_return_pct}%)`,
      '',
      `  Total Trades Made : ${result.total_trades}`,
      `  Profitable Trades : ${result.winning_trades}  (WIN)`,
      `  Loss Trades       : ${result.losing_trades}  (LOSS)`,
      `  Win Rate          : ${result.win_rate}% — out of every 10 trades, ~${Math.round(result.win_rate/10)} were profitable`,
      '',
      `  Average Profit on a Win   : NPR ${result.avg_win?.toLocaleString()}`,
      `  Average Loss on a Loss    : NPR ${result.avg_loss?.toLocaleString()}`,
      `  Profit Factor             : ${result.profit_factor}  (above 1.0 = profitable overall)`,
      `  Sharpe Ratio              : ${result.sharpe_ratio}  (above 1.0 = good risk-adjusted return)`,
      `  Biggest Single-Day Drawdown: ${result.max_drawdown_pct}%`,
      `  Average Days Held/Trade   : ${result.avg_holding_days} days`,
      `  Best Trade Return         : ${result.best_trade}%`,
      `  Worst Trade Return        : ${result.worst_trade}%`,
      '',
    ];

    result.trades?.forEach((t, i) => {
      const won = t.pnl >= 0;
      const totalInvested = t.entry_price * t.quantity;
      lines.push(hr);
      lines.push(`  TRADE #${i + 1}  —  ${t.symbol}  —  ${won ? '✔ PROFIT' : '✘ LOSS'}`);
      lines.push(hr);
      lines.push('');
      lines.push('  WHY DID THE BOT BUY?');
      (t.entry_signals || []).forEach(sig => lines.push(`    • ${sig}`));
      lines.push('');
      lines.push('  PURCHASE DETAILS');
      lines.push(`    Date Bought       : ${t.entry_date}`);
      lines.push(`    Price Per Share   : NPR ${t.entry_price}`);
      lines.push(`    Shares Bought     : ${t.quantity}`);
      lines.push(`    Total Invested    : NPR ${totalInvested.toLocaleString()}`);
      lines.push(`    Stop Loss Set At  : NPR ${(t.entry_price * 0.95).toFixed(2)}  ← Auto-sell if price drops here`);
      lines.push('');
      lines.push('  DAY-BY-DAY PRICE MOVEMENT WHILE HOLDING');
      lines.push('  ' + '-'.repeat(56));
      lines.push('  Date          Price       Change     Unrealized P&L  Note');
      lines.push('  ' + '-'.repeat(56));
      (t.daily_log || []).forEach(day => {
        const priceStr = `NPR ${day.price}`.padEnd(12);
        const chgStr = `${day.change_pct >= 0 ? '+' : ''}${day.change_pct}%`.padEnd(10);
        const pnlStr = `NPR ${day.unrealized_pnl?.toLocaleString()}`.padEnd(16);
        lines.push(`  ${day.date}  ${priceStr}  ${chgStr}  ${pnlStr}  ${day.note || ''}`);
      });
      lines.push('');
      lines.push('  SALE DETAILS');
      lines.push(`    Date Sold         : ${t.exit_date}`);
      lines.push(`    Price Per Share   : NPR ${t.exit_price}`);
      lines.push(`    Reason for Selling: ${
        t.exit_reason === 'STOP_LOSS' ? 'Stop Loss triggered — price fell to the safety level' :
        t.exit_reason === 'TIME_STOP' ? 'Time limit reached — held for 60 days max' :
        'Backtest period ended'
      }`);
      lines.push('');
      lines.push('  PROFIT / LOSS CALCULATION');
      lines.push(`    Bought  ${t.quantity} shares × NPR ${t.entry_price}  =  NPR ${totalInvested.toLocaleString()}`);
      lines.push(`    Sold    ${t.quantity} shares × NPR ${t.exit_price}   =  NPR ${(t.exit_price * t.quantity).toLocaleString()}`);
      lines.push(`    Net P&L : NPR ${t.pnl?.toLocaleString()}  (${t.pnl_pct}%)`);
      lines.push(`    Held for ${t.duration} days`);
      lines.push('');
    });

    lines.push(hr);
    lines.push('  GLOSSARY — WHAT DO THESE TERMS MEAN?');
    lines.push(hr2);
    lines.push('  Stop Loss   : A safety rule. If the price drops 5% below buy price,');
    lines.push('                the bot automatically sells to limit your loss.');
    lines.push('  Trailing Stop: When a trade is profitable by 10%+, the stop loss');
    lines.push('                moves up to lock in some of the profit.');
    lines.push('  SMA (20/50) : Average price over last 20 or 50 days. When the');
    lines.push('                short average crosses above the long one = buy signal.');
    lines.push('  RSI         : Measures if a stock is oversold (beaten down too much).');
    lines.push('                RSI below 30 = stock may bounce back = buy signal.');
    lines.push('  MACD        : Compares two moving averages. When they cross = signal.');
    lines.push('  Volume Spike: More shares traded than usual = strong market interest.');
    lines.push('  Win Rate    : % of trades that made money.');
    lines.push('  Profit Factor: Total profits divided by total losses. >1 = good.');
    lines.push('  Sharpe Ratio: Return relative to risk. Higher = better.');
    lines.push('');
    lines.push(hr);
    lines.push(`  Generated on : ${new Date().toLocaleString()}`);
    lines.push('  DISCLAIMER   : This is a simulation. Past performance does not');
    lines.push('                 guarantee future results. Not financial advice.');
    lines.push(hr);

    const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url;
    a.download = `backtest_report_${symbols.replace(/,\s*/g,'_')}_${form.start_date}.txt`;
    a.click(); URL.revokeObjectURL(url);
  };

  const handleRun = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const params = {
        ...form,
        symbols: form.symbols.split(',').map(s => s.trim()),
        initial_capital: parseFloat(form.initial_capital),
        risk_per_trade: parseFloat(form.risk_per_trade),
        sma_short: parseInt(form.sma_short),
        sma_long: parseInt(form.sma_long),
        rsi_period: parseInt(form.rsi_period),
        min_confirmations: parseInt(form.min_confirmations),
      };
      const { data } = await runBacktest(params);
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Backtest failed. Make sure you have historical data.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Backtesting Engine</h2>

      {/* Parameters Form */}
      <div className="bg-surface rounded-xl p-5 border border-slate-700/50">
        <h3 className="text-lg font-semibold mb-4">Test Parameters</h3>
        <form onSubmit={handleRun}>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Symbols (comma-separated)</label>
              <input
                type="text" value={form.symbols}
                onChange={e => setForm({ ...form, symbols: e.target.value })}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Start Date</label>
              <input
                type="date" value={form.start_date}
                onChange={e => setForm({ ...form, start_date: e.target.value })}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">End Date</label>
              <input
                type="date" value={form.end_date}
                onChange={e => setForm({ ...form, end_date: e.target.value })}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Strategy</label>
              <select
                value={form.strategy}
                onChange={e => setForm({ ...form, strategy: e.target.value })}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none"
              >
                <option value="trend_following">Trend Following</option>
                <option value="mean_reversion">Mean Reversion</option>
                <option value="momentum">Momentum</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Initial Capital (₨)</label>
              <input
                type="number" value={form.initial_capital}
                onChange={e => setForm({ ...form, initial_capital: e.target.value })}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Risk Per Trade</label>
              <input
                type="number" step="0.01" value={form.risk_per_trade}
                onChange={e => setForm({ ...form, risk_per_trade: e.target.value })}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">SMA Short</label>
              <input
                type="number" value={form.sma_short}
                onChange={e => setForm({ ...form, sma_short: e.target.value })}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">SMA Long</label>
              <input
                type="number" value={form.sma_long}
                onChange={e => setForm({ ...form, sma_long: e.target.value })}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Min Confirmations (1–4)</label>
              <input
                type="number" min="1" max="4" value={form.min_confirmations}
                onChange={e => setForm({ ...form, min_confirmations: e.target.value })}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none"
              />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-4 flex-wrap">
            <button
              type="submit" disabled={loading}
              className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
            >
              {loading ? <Loader className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {loading ? 'Running...' : 'Run Backtest'}
            </button>
            {result && (
              <>
                <button
                  type="button" onClick={downloadCSV}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-700 hover:bg-emerald-600 rounded-lg text-sm font-medium transition-colors"
                >
                  <Download className="w-4 h-4" /> Download CSV
                </button>
                <button
                  type="button" onClick={downloadReport}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-600 hover:bg-slate-500 rounded-lg text-sm font-medium transition-colors"
                >
                  <FileText className="w-4 h-4" /> Download Report
                </button>
              </>
            )}
            {error && <span className="text-red-400 text-sm">{error}</span>}
          </div>
        </form>
      </div>

      {/* Results */}
      {result && (
        <>
          {/* Summary Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {[
              { label: 'Total Return', value: `₨${result.total_return?.toLocaleString()}`, sub: `${result.total_return_pct}%`, color: result.total_return >= 0 ? 'text-emerald-400' : 'text-red-400' },
              { label: 'Total Trades', value: result.total_trades, sub: `${result.winning_trades}W / ${result.losing_trades}L`, color: 'text-slate-200' },
              { label: 'Win Rate', value: `${result.win_rate}%`, color: 'text-emerald-400' },
              { label: 'Profit Factor', value: result.profit_factor, color: 'text-blue-400' },
              { label: 'Sharpe Ratio', value: result.sharpe_ratio, color: 'text-cyan-400' },
              { label: 'Max Drawdown', value: `${result.max_drawdown_pct}%`, color: 'text-red-400' },
            ].map((m, i) => (
              <div key={i} className="bg-surface rounded-xl p-4 border border-slate-700/50">
                <div className="text-slate-400 text-xs mb-1">{m.label}</div>
                <div className={`text-xl font-bold font-mono ${m.color}`}>{m.value}</div>
                {m.sub && <div className="text-xs text-slate-500 mt-1">{m.sub}</div>}
              </div>
            ))}
          </div>

          {/* Equity Curve */}
          <div className="bg-surface rounded-xl p-5 border border-slate-700/50">
            <h3 className="text-lg font-semibold mb-4">Equity Curve</h3>
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={result.equity_curve?.filter((_, i) => i % Math.max(1, Math.floor(result.equity_curve.length / 200)) === 0)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 12 }} />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
                <Line type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Monthly Returns */}
          {result.monthly_returns?.length > 0 && (
            <div className="bg-surface rounded-xl p-5 border border-slate-700/50">
              <h3 className="text-lg font-semibold mb-4">Monthly Returns</h3>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={result.monthly_returns}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="month" stroke="#64748b" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 12 }} />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
                  <Bar dataKey="pnl" fill="#10b981" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Trade List */}
          {result.trades?.length > 0 && (
            <div className="bg-surface rounded-xl p-5 border border-slate-700/50">
              <h3 className="text-lg font-semibold mb-4">Backtest Trades ({result.trades.length})</h3>
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-surface">
                    <tr className="text-slate-400 border-b border-slate-700">
                      <th className="text-left py-2 px-2">Symbol</th>
                      <th className="text-left py-2 px-2">Entry</th>
                      <th className="text-left py-2 px-2">Exit</th>
                      <th className="text-right py-2 px-2">Entry ₨</th>
                      <th className="text-right py-2 px-2">Exit ₨</th>
                      <th className="text-right py-2 px-2">P&L</th>
                      <th className="text-right py-2 px-2">P&L%</th>
                      <th className="text-right py-2 px-2">Days</th>
                      <th className="text-left py-2 px-2">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.map((t, i) => (
                      <tr key={i} className="border-b border-slate-800">
                        <td className="py-2 px-2 font-semibold">{t.symbol}</td>
                        <td className="py-2 px-2 text-xs text-slate-400">{t.entry_date}</td>
                        <td className="py-2 px-2 text-xs text-slate-400">{t.exit_date}</td>
                        <td className="text-right py-2 px-2 font-mono">₨{t.entry_price?.toLocaleString()}</td>
                        <td className="text-right py-2 px-2 font-mono">₨{t.exit_price?.toLocaleString()}</td>
                        <td className={`text-right py-2 px-2 font-mono font-bold ${t.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          ₨{t.pnl?.toLocaleString()}
                        </td>
                        <td className={`text-right py-2 px-2 font-mono ${t.pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {t.pnl_pct}%
                        </td>
                        <td className="text-right py-2 px-2 text-slate-400">{t.duration}d</td>
                        <td className="py-2 px-2 text-xs text-slate-400">{t.exit_reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
