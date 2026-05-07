import { useEffect, useState } from 'react';
import useStore from '../hooks/useStore';
import { Pencil, Trash2, X, Check, Star } from 'lucide-react';

export default function TradeJournal() {
  const { trades, tradeStats, fetchTrades, tradesLoading, updateTrade, deleteTrade } = useStore();
  const [editId, setEditId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [error, setError] = useState('');

  useEffect(() => {
    fetchTrades();
  }, []);

  const stats = tradeStats || {};

  const handleEdit = (trade) => {
    setEditId(trade.id);
    setEditForm({
      entry_price: trade.entry_price,
      exit_price: trade.exit_price,
      quantity: trade.quantity,
      entry_signal: trade.entry_signal || '',
      exit_signal: trade.exit_signal || '',
      notes: trade.notes || '',
      rating: trade.rating || 0,
    });
    setError('');
  };

  const handleSave = async () => {
    try {
      setError('');
      await updateTrade(editId, editForm);
      setEditId(null);
      fetchTrades();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update trade');
    }
  };

  const handleDelete = async (id, symbol) => {
    if (!confirm(`Delete trade for ${symbol}? This cannot be undone.`)) return;
    try {
      await deleteTrade(id);
      fetchTrades();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete trade');
    }
  };

  const renderStars = (rating, editable = false) => {
    return (
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((s) => (
          <Star
            key={s}
            className={`w-3.5 h-3.5 ${s <= (rating || 0) ? 'fill-yellow-400 text-yellow-400' : 'text-slate-600'} ${editable ? 'cursor-pointer hover:text-yellow-400' : ''}`}
            onClick={editable ? () => setEditForm({ ...editForm, rating: s === editForm.rating ? 0 : s }) : undefined}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Trade Journal</h2>

      {/* Stats Summary */}
      {stats.total_trades > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {[
            { label: 'Total Trades', value: stats.total_trades, color: 'text-slate-200' },
            { label: 'Win Rate', value: `${stats.win_rate}%`, color: 'text-emerald-400' },
            { label: 'Total P&L', value: `₨${stats.total_pnl?.toLocaleString()}`, color: stats.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400' },
            { label: 'Avg P&L', value: `₨${stats.avg_pnl?.toLocaleString()}`, color: stats.avg_pnl >= 0 ? 'text-emerald-400' : 'text-red-400' },
            { label: 'Best Trade', value: `₨${stats.best_trade?.toLocaleString()}`, color: 'text-emerald-400' },
            { label: 'Worst Trade', value: `₨${stats.worst_trade?.toLocaleString()}`, color: 'text-red-400' },
          ].map((s, i) => (
            <div key={i} className="bg-surface rounded-xl p-4 border border-slate-700/50">
              <div className="text-slate-400 text-xs mb-1">{s.label}</div>
              <div className={`text-lg font-bold font-mono ${s.color}`}>{s.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Signal Performance */}
      {stats.signal_performance && Object.keys(stats.signal_performance).length > 0 && (
        <div className="bg-surface rounded-xl p-5 border border-slate-700/50">
          <h3 className="text-lg font-semibold mb-4">Signal Performance</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(stats.signal_performance).map(([signal, data]) => (
              <div key={signal} className="p-3 bg-slate-800/50 rounded-lg border border-slate-700/30">
                <div className="font-semibold text-sm">{signal}</div>
                <div className="flex justify-between text-xs text-slate-400 mt-2">
                  <span>Trades: {data.total}</span>
                  <span className="text-emerald-400">Win: {data.win_rate}%</span>
                  <span className={data.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                    ₨{data.pnl?.toLocaleString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trades Table */}
      <div className="bg-surface rounded-xl p-5 border border-slate-700/50">
        <h3 className="text-lg font-semibold mb-4">Trade History</h3>
        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}
        {tradesLoading ? (
          <div className="text-center py-8 text-slate-500">Loading trades...</div>
        ) : trades.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-slate-700">
                  <th className="text-left py-3 px-2">#</th>
                  <th className="text-left py-3 px-2">Symbol</th>
                  <th className="text-left py-3 px-2">Entry</th>
                  <th className="text-left py-3 px-2">Exit</th>
                  <th className="text-right py-3 px-2">Entry ₨</th>
                  <th className="text-right py-3 px-2">Exit ₨</th>
                  <th className="text-right py-3 px-2">Qty</th>
                  <th className="text-right py-3 px-2">P&L</th>
                  <th className="text-right py-3 px-2">P&L%</th>
                  <th className="text-right py-3 px-2">Days</th>
                  <th className="text-left py-3 px-2">Signal</th>
                  <th className="text-left py-3 px-2">Exit Reason</th>
                  <th className="text-center py-3 px-2">Rating</th>
                  <th className="text-center py-3 px-2">Result</th>
                  <th className="text-center py-3 px-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t, i) => (
                  editId === t.id ? (
                    <tr key={t.id} className="border-b border-slate-800 bg-slate-800/70">
                      <td className="py-3 px-2 text-slate-500">{t.trade_number || i + 1}</td>
                      <td className="py-3 px-2 font-semibold text-white">{t.symbol}</td>
                      <td className="py-3 px-2 text-slate-400 text-xs">{t.entry_date}</td>
                      <td className="py-3 px-2 text-slate-400 text-xs">{t.exit_date || '-'}</td>
                      <td className="py-2 px-1">
                        <input
                          type="number" step="0.01"
                          value={editForm.entry_price}
                          onChange={(e) => setEditForm({ ...editForm, entry_price: parseFloat(e.target.value) || 0 })}
                          className="w-20 bg-slate-900 border border-slate-600 rounded px-2 py-1 text-xs text-right font-mono focus:border-emerald-500 outline-none"
                        />
                      </td>
                      <td className="py-2 px-1">
                        <input
                          type="number" step="0.01"
                          value={editForm.exit_price}
                          onChange={(e) => setEditForm({ ...editForm, exit_price: parseFloat(e.target.value) || 0 })}
                          className="w-20 bg-slate-900 border border-slate-600 rounded px-2 py-1 text-xs text-right font-mono focus:border-emerald-500 outline-none"
                        />
                      </td>
                      <td className="py-2 px-1">
                        <input
                          type="number" min="1"
                          value={editForm.quantity}
                          onChange={(e) => setEditForm({ ...editForm, quantity: parseInt(e.target.value) || 0 })}
                          className="w-16 bg-slate-900 border border-slate-600 rounded px-2 py-1 text-xs text-right font-mono focus:border-emerald-500 outline-none"
                        />
                      </td>
                      <td className="text-right py-3 px-2 font-mono text-slate-500" colSpan={2}>
                        auto-calculated
                      </td>
                      <td className="text-right py-3 px-2 font-mono text-slate-400">{t.duration_days}d</td>
                      <td className="py-2 px-1">
                        <input
                          type="text"
                          value={editForm.entry_signal}
                          onChange={(e) => setEditForm({ ...editForm, entry_signal: e.target.value })}
                          className="w-24 bg-slate-900 border border-slate-600 rounded px-2 py-1 text-xs focus:border-emerald-500 outline-none"
                          placeholder="Signal"
                        />
                      </td>
                      <td className="py-2 px-1">
                        <input
                          type="text"
                          value={editForm.exit_signal}
                          onChange={(e) => setEditForm({ ...editForm, exit_signal: e.target.value })}
                          className="w-24 bg-slate-900 border border-slate-600 rounded px-2 py-1 text-xs focus:border-emerald-500 outline-none"
                          placeholder="Reason"
                        />
                      </td>
                      <td className="py-3 px-2">{renderStars(editForm.rating, true)}</td>
                      <td className="text-center py-3 px-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                          t.result === 'WINNER' ? 'bg-emerald-500/20 text-emerald-400' :
                          t.result === 'LOSER' ? 'bg-red-500/20 text-red-400' :
                          'bg-slate-600/20 text-slate-400'
                        }`}>
                          {t.result}
                        </span>
                      </td>
                      <td className="text-center py-3 px-2">
                        <div className="flex gap-1 justify-center">
                          <button
                            onClick={handleSave}
                            className="p-1.5 bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/40 rounded transition-colors"
                            title="Save"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => { setEditId(null); setError(''); }}
                            className="p-1.5 bg-slate-600/20 text-slate-400 hover:bg-slate-600/40 rounded transition-colors"
                            title="Cancel"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    <tr key={t.id} className="border-b border-slate-800 hover:bg-slate-800/50 group">
                      <td className="py-3 px-2 text-slate-500">{t.trade_number || i + 1}</td>
                      <td className="py-3 px-2 font-semibold text-white">{t.symbol}</td>
                      <td className="py-3 px-2 text-slate-400 text-xs">{t.entry_date}</td>
                      <td className="py-3 px-2 text-slate-400 text-xs">{t.exit_date || '-'}</td>
                      <td className="text-right py-3 px-2 font-mono">₨{t.entry_price?.toLocaleString()}</td>
                      <td className="text-right py-3 px-2 font-mono">
                        {t.exit_price ? `₨${t.exit_price?.toLocaleString()}` : '-'}
                      </td>
                      <td className="text-right py-3 px-2 font-mono text-slate-400">{t.quantity}</td>
                      <td className={`text-right py-3 px-2 font-mono font-bold ${(t.profit_loss || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        ₨{t.profit_loss?.toLocaleString()}
                      </td>
                      <td className={`text-right py-3 px-2 font-mono ${(t.profit_loss_pct || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {t.profit_loss_pct >= 0 ? '+' : ''}{t.profit_loss_pct?.toFixed(1)}%
                      </td>
                      <td className="text-right py-3 px-2 font-mono text-slate-400">{t.duration_days}d</td>
                      <td className="py-3 px-2 text-xs text-slate-400">{t.entry_signal || '-'}</td>
                      <td className="py-3 px-2 text-xs text-slate-400">{t.exit_signal || '-'}</td>
                      <td className="py-3 px-2">{renderStars(t.rating)}</td>
                      <td className="text-center py-3 px-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                          t.result === 'WINNER' ? 'bg-emerald-500/20 text-emerald-400' :
                          t.result === 'LOSER' ? 'bg-red-500/20 text-red-400' :
                          'bg-slate-600/20 text-slate-400'
                        }`}>
                          {t.result}
                        </span>
                      </td>
                      <td className="text-center py-3 px-2">
                        <div className="flex gap-1 justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => handleEdit(t)}
                            className="p-1.5 bg-blue-600/20 text-blue-400 hover:bg-blue-600/40 rounded transition-colors"
                            title="Edit"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDelete(t.id, t.symbol)}
                            className="p-1.5 bg-red-600/20 text-red-400 hover:bg-red-600/40 rounded transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-slate-500">
            No completed trades yet. Close a position to record a trade.
          </div>
        )}

        {/* Notes section for editing */}
        {editId && (
          <div className="mt-4 p-4 bg-slate-800/50 rounded-lg border border-slate-700/30">
            <label className="block text-xs text-slate-400 mb-1">Trade Notes</label>
            <textarea
              value={editForm.notes}
              onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
              className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none resize-none"
              rows={3}
              placeholder="Add your notes about this trade..."
            />
          </div>
        )}
      </div>
    </div>
  );
}
