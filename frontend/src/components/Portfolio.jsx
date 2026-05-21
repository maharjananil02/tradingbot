import { useEffect, useState } from 'react';
import useStore from '../hooks/useStore';
import { createPosition, closePosition, manualSync } from '../utils/api';
import { Plus, X, AlertTriangle, Pencil, Check, RefreshCw } from 'lucide-react';

export default function Portfolio() {
  const { positions, fetchPositions, riskMetrics, fetchRisk, updatePosition } = useStore();
  const [showAdd, setShowAdd] = useState(false);
  const [editId, setEditId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [form, setForm] = useState({
    symbol: '', entry_price: '', quantity: '', stop_loss_pct: '5', is_paper: false
  });
  const [error, setError] = useState('');
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [nextRefresh, setNextRefresh] = useState(10);
  const [isSyncing, setIsSyncing] = useState(false);

  const handleManualSync = async () => {
    setIsSyncing(true);
    try {
      await manualSync();
      fetchPositions();
      fetchRisk();
      setLastRefresh(new Date());
      setNextRefresh(10);
      alert('Manual sync completed successfully');
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to sync manually');
    } finally {
      setIsSyncing(false);
    }
  };

  const getNextBotRun = () => {
    const now = new Date();
    const nepal = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kathmandu' }));
    const h = nepal.getHours(), m = nepal.getMinutes(), day = nepal.getDay();
    const isTradingDay = day >= 0 && day <= 4; // Sun-Thu
    if (isTradingDay && h >= 11 && h < 15) {
      // During market hours - next run is next minute
      const next = new Date(nepal);
      next.setMinutes(m + 1, 0, 0);
      return next.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } else if (isTradingDay && h === 15 && m < 1) {
      return 'Today 3:01 PM (final sync)';
    } else if (isTradingDay && h < 11) {
      return 'Today 11:00 AM';
    } else {
      // After hours or non-trading day - find next trading day
      let daysAhead = 1;
      for (let i = 1; i <= 7; i++) {
        const nextDay = (day + i) % 7;
        if (nextDay >= 0 && nextDay <= 4) { daysAhead = i; break; }
      }
      const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      return `${dayNames[(day + daysAhead) % 7]} 11:00 AM`;
    }
  };

  const isMarketOpen = () => {
    const now = new Date();
    const nepal = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kathmandu' }));
    const h = nepal.getHours(), m = nepal.getMinutes(), day = nepal.getDay();
    const isTradingDay = day >= 0 && day <= 4; // Sun-Thu
    const timeInMinutes = h * 60 + m;
    // Market: 11:00 (660) to 15:01 (901) — includes 1 min after close for final sync
    return isTradingDay && timeInMinutes >= 660 && timeInMinutes <= 901;
  };

  useEffect(() => {
    fetchPositions();
    fetchRisk();
    setLastRefresh(new Date());
    setNextRefresh(10);
    const interval = setInterval(() => {
      if (isMarketOpen()) {
        fetchPositions();
        fetchRisk();
        setLastRefresh(new Date());
      }
      setNextRefresh(10);
    }, 10000);
    const countdown = setInterval(() => {
      setNextRefresh(prev => prev > 0 ? prev - 1 : 0);
    }, 1000);
    return () => { clearInterval(interval); clearInterval(countdown); };
  }, []);

  const handleAddPosition = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await createPosition({
        symbol: form.symbol.toUpperCase(),
        entry_price: parseFloat(form.entry_price),
        quantity: parseInt(form.quantity),
        stop_loss_pct: parseFloat(form.stop_loss_pct) / 100,
        is_paper: form.is_paper,
      });
      setShowAdd(false);
      setForm({ symbol: '', entry_price: '', quantity: '', stop_loss_pct: '5', is_paper: false });
      fetchPositions();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add position');
    }
  };

  const handleClose = async (id, currentPrice) => {
    if (!confirm('Close this position?')) return;
    try {
      await closePosition(id, currentPrice);
      fetchPositions();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to close position');
    }
  };

  const handleEditPosition = (p) => {
    setEditId(p.id);
    setEditForm({
      stop_loss: p.stop_loss,
      entry_price: p.entry_price,
      quantity: p.quantity,
      entry_signal: p.entry_signal || '',
    });
  };

  const handleSavePosition = async () => {
    try {
      await updatePosition(editId, editForm);
      setEditId(null);
      fetchPositions();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update position');
    }
  };

  const rm = riskMetrics || {};

  return (
    <div className="space-y-6">
      {/* Risk Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {[
          { label: 'Sharpe Ratio', value: rm.sharpe_ratio?.toFixed(2) || '0', color: 'text-cyan-400' },
          { label: 'Max Drawdown', value: `${rm.max_drawdown_pct?.toFixed(1) || '0'}%`, color: 'text-red-400' },
          { label: 'Win Rate', value: `${rm.win_rate?.toFixed(1) || '0'}%`, color: 'text-emerald-400' },
          { label: 'Profit Factor', value: rm.profit_factor?.toFixed(2) || '0', color: 'text-blue-400' },
          { label: 'Avg Win', value: `₨${rm.avg_win?.toLocaleString() || '0'}`, color: 'text-emerald-400' },
          { label: 'Avg Loss', value: `₨${rm.avg_loss?.toLocaleString() || '0'}`, color: 'text-red-400' },
        ].map((m, i) => (
          <div key={i} className="bg-surface rounded-xl p-4 border border-slate-700/50">
            <div className="text-slate-400 text-xs mb-1">{m.label}</div>
            <div className={`text-xl font-bold font-mono ${m.color}`}>{m.value}</div>
          </div>
        ))}
      </div>

      {/* Positions */}
      <div className="bg-surface rounded-xl p-5 border border-slate-700/50">
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-semibold">Positions</h3>
            <span className="text-xs text-slate-500">Last updated: {lastRefresh.toLocaleTimeString()} • Next refresh: {nextRefresh}s • Bot next listen: {getNextBotRun()}</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleManualSync}
              disabled={isSyncing}
              className="flex items-center gap-1 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:opacity-70 rounded-lg text-sm font-medium transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} /> {isSyncing ? 'Syncing...' : 'Sync Bot'}
            </button>
            <button
              onClick={() => setShowAdd(!showAdd)}
              className="flex items-center gap-1 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium transition-colors"
            >
              <Plus className="w-4 h-4" /> Add Position
            </button>
          </div>
        </div>

        {/* Add Position Form */}
        {showAdd && (
          <form onSubmit={handleAddPosition} className="mb-6 p-4 bg-slate-800/50 rounded-lg border border-slate-700/30">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <input
                type="text" placeholder="Symbol (e.g. NABIL)" required
                value={form.symbol}
                onChange={(e) => setForm({ ...form, symbol: e.target.value })}
                className="bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none"
              />
              <input
                type="number" placeholder="Entry Price" required step="0.01"
                value={form.entry_price}
                onChange={(e) => setForm({ ...form, entry_price: e.target.value })}
                className="bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none"
              />
              <input
                type="number" placeholder="Quantity" required min="1"
                value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                className="bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none"
              />
              <input
                type="number" placeholder="SL %" step="0.1" min="1" max="20"
                value={form.stop_loss_pct}
                onChange={(e) => setForm({ ...form, stop_loss_pct: e.target.value })}
                className="bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none"
              />
              <div className="flex gap-2">
                <button type="submit" className="flex-1 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium transition-colors">
                  Add
                </button>
                <button type="button" onClick={() => setShowAdd(false)} className="px-3 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            <label className="flex items-center gap-2 mt-3 text-sm text-slate-400">
              <input type="checkbox" checked={form.is_paper} onChange={(e) => setForm({ ...form, is_paper: e.target.checked })} className="rounded" />
              Paper Trade (virtual money)
            </label>
            {error && (
              <div className="mt-2 flex items-center gap-2 text-red-400 text-sm">
                <AlertTriangle className="w-4 h-4" /> {error}
              </div>
            )}
          </form>
        )}

        {/* Positions Table */}
        {positions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-slate-700">
                  <th className="text-left py-3 px-2">Symbol</th>
                  <th className="text-right py-3 px-2">Qty</th>
                  <th className="text-right py-3 px-2">Entry</th>
                  <th className="text-right py-3 px-2">Current</th>
                  <th className="text-right py-3 px-2">P&L</th>
                  <th className="text-right py-3 px-2">Stop Loss</th>
                  <th className="text-right py-3 px-2">Next Target</th>
                  <th className="text-right py-3 px-2">Milestones</th>
                  <th className="text-right py-3 px-2">Days</th>
                  <th className="text-center py-3 px-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p) => {
                  const gainPct = ((p.current_price - p.entry_price) / p.entry_price * 100);
                  const isWinning = p.unrealized_pnl >= 0;
                  const isEditing = editId === p.id;
                  return (
                    <tr key={p.id} className={`border-b border-slate-800 ${isEditing ? 'bg-slate-800/70' : 'hover:bg-slate-800/50'} group`}>
                      <td className="py-3 px-2">
                        <span className="font-semibold text-white">{p.symbol}</span>
                        {p.is_paper && <span className="ml-1 text-xs text-yellow-500">(Paper)</span>}
                      </td>
                      <td className="text-right py-3 px-2 font-mono">
                        {isEditing ? (
                          <input type="number" min="1" value={editForm.quantity}
                            onChange={(e) => setEditForm({ ...editForm, quantity: parseInt(e.target.value) || 0 })}
                            className="w-16 bg-slate-900 border border-slate-600 rounded px-2 py-1 text-xs text-right font-mono focus:border-emerald-500 outline-none"
                          />
                        ) : p.quantity}
                      </td>
                      <td className="text-right py-3 px-2 font-mono">
                        {isEditing ? (
                          <input type="number" step="0.01" value={editForm.entry_price}
                            onChange={(e) => setEditForm({ ...editForm, entry_price: parseFloat(e.target.value) || 0 })}
                            className="w-20 bg-slate-900 border border-slate-600 rounded px-2 py-1 text-xs text-right font-mono focus:border-emerald-500 outline-none"
                          />
                        ) : `₨${p.entry_price?.toLocaleString()}`}
                      </td>
                      <td className="text-right py-3 px-2 font-mono">₨{p.current_price?.toLocaleString()}</td>
                      <td className={`text-right py-3 px-2 font-mono font-bold ${isWinning ? 'text-emerald-400' : 'text-red-400'}`}>
                        {gainPct >= 0 ? '+' : ''}{gainPct.toFixed(1)}%
                        <div className="text-xs font-normal">₨{p.unrealized_pnl?.toLocaleString()}</div>
                      </td>
                      <td className="text-right py-3 px-2 font-mono text-yellow-400">
                        {isEditing ? (
                          <input type="number" step="0.01" value={editForm.stop_loss}
                            onChange={(e) => setEditForm({ ...editForm, stop_loss: parseFloat(e.target.value) || 0 })}
                            className="w-20 bg-slate-900 border border-yellow-600 rounded px-2 py-1 text-xs text-right font-mono text-yellow-400 focus:border-yellow-400 outline-none"
                          />
                        ) : `₨${p.stop_loss?.toLocaleString()}`}
                      </td>
                      <td className="text-right py-3 px-2 font-mono text-blue-400">₨{p.next_milestone_price?.toLocaleString()}</td>
                      <td className="text-right py-3 px-2">
                        {p.milestone_count > 0 && (
                          <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded text-xs font-bold">
                            {p.milestone_count}x
                          </span>
                        )}
                      </td>
                      <td className="text-right py-3 px-2 font-mono text-slate-400">{p.days_held}d</td>
                      <td className="text-center py-3 px-2">
                        <div className="flex gap-1 justify-center">
                          {isEditing ? (
                            <>
                              <button onClick={handleSavePosition}
                                className="p-1.5 bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/40 rounded transition-colors" title="Save">
                                <Check className="w-3.5 h-3.5" />
                              </button>
                              <button onClick={() => setEditId(null)}
                                className="p-1.5 bg-slate-600/20 text-slate-400 hover:bg-slate-600/40 rounded transition-colors" title="Cancel">
                                <X className="w-3.5 h-3.5" />
                              </button>
                            </>
                          ) : (
                            <>
                              <button onClick={() => handleEditPosition(p)}
                                className="p-1.5 bg-blue-600/20 text-blue-400 hover:bg-blue-600/40 rounded opacity-0 group-hover:opacity-100 transition-all" title="Edit">
                                <Pencil className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => handleClose(p.id, p.current_price)}
                                className="px-3 py-1 bg-red-600/20 text-red-400 hover:bg-red-600/40 rounded text-xs font-medium transition-colors"
                              >
                                Close
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center text-slate-500 py-8">
            No open positions. Click "Add Position" to start tracking.
          </div>
        )}
      </div>
    </div>
  );
}
