import { useState } from 'react';
import { runBacktest } from '../utils/api';
import { Play, Loader } from 'lucide-react';
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
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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
          </div>
          <div className="mt-4 flex items-center gap-4">
            <button
              type="submit" disabled={loading}
              className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
            >
              {loading ? <Loader className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {loading ? 'Running...' : 'Run Backtest'}
            </button>
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
