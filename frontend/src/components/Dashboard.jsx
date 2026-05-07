import { useEffect } from 'react';
import useStore from '../hooks/useStore';
import {
  TrendingUp, TrendingDown, DollarSign, BarChart3,
  Target, Activity,
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

function StatCard({ title, value, change, icon: Icon, color = 'text-emerald-400' }) {
  const isPositive = change >= 0;
  return (
    <div className="bg-surface rounded-xl p-5 border border-slate-700/50 hover:border-slate-600 transition-all hover:scale-[1.02]">
      <div className="flex items-center justify-between mb-3">
        <span className="text-slate-400 text-sm">{title}</span>
        <Icon className={`w-5 h-5 ${color}`} />
      </div>
      <div className="text-2xl font-bold font-mono">{value}</div>
      {change !== undefined && (
        <div className={`flex items-center mt-1 text-sm ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
          {isPositive ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
          {isPositive ? '+' : ''}{typeof change === 'number' ? change.toFixed(2) : change}%
        </div>
      )}
    </div>
  );
}

function PositionsTable({ positions }) {
  if (!positions.length) {
    return (
      <div className="text-center text-slate-500 py-8">
        No open positions. Add one to get started.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-slate-400 border-b border-slate-700">
            <th className="text-left py-3 px-2">Symbol</th>
            <th className="text-right py-3 px-2">Qty</th>
            <th className="text-right py-3 px-2">Entry</th>
            <th className="text-right py-3 px-2">Current</th>
            <th className="text-right py-3 px-2">P&L</th>
            <th className="text-right py-3 px-2">Gain%</th>
            <th className="text-right py-3 px-2">SL</th>
            <th className="text-right py-3 px-2">Days</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => {
            const gainPct = ((p.current_price - p.entry_price) / p.entry_price * 100);
            const isWinning = p.unrealized_pnl >= 0;
            return (
              <tr key={p.id} className="border-b border-slate-800 hover:bg-slate-800/50">
                <td className="py-3 px-2 font-semibold text-white">{p.symbol}</td>
                <td className="text-right py-3 px-2 font-mono">{p.quantity}</td>
                <td className="text-right py-3 px-2 font-mono">₨{p.entry_price?.toLocaleString()}</td>
                <td className="text-right py-3 px-2 font-mono">₨{p.current_price?.toLocaleString()}</td>
                <td className={`text-right py-3 px-2 font-mono font-semibold ${isWinning ? 'text-emerald-400' : 'text-red-400'}`}>
                  ₨{p.unrealized_pnl?.toLocaleString()}
                </td>
                <td className={`text-right py-3 px-2 font-mono ${isWinning ? 'text-emerald-400' : 'text-red-400'}`}>
                  {gainPct >= 0 ? '+' : ''}{gainPct.toFixed(1)}%
                </td>
                <td className="text-right py-3 px-2 font-mono text-yellow-400">₨{p.stop_loss?.toLocaleString()}</td>
                <td className="text-right py-3 px-2 font-mono text-slate-400">{p.days_held}d</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function Dashboard() {
  const {
    dashboard, fetchDashboard, dashboardLoading,
    positions, fetchPositions,
    signals, fetchSignals,
    performance, fetchPerformance,
    alerts, fetchAlerts,
  } = useStore();

  useEffect(() => {
    fetchDashboard();
    fetchPositions();
    fetchSignals();
    fetchPerformance(30);
    fetchAlerts();

    const interval = setInterval(() => {
      fetchDashboard();
      fetchPositions();
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  const d = dashboard || {};

  // Sector breakdown mock (from positions)
  const sectorData = positions.reduce((acc, p) => {
    const sector = p.entry_signal || 'Unknown';
    const existing = acc.find(s => s.name === sector);
    if (existing) {
      existing.value += (p.current_price || p.entry_price) * p.quantity;
    } else {
      acc.push({ name: sector, value: (p.current_price || p.entry_price) * p.quantity });
    }
    return acc;
  }, []);

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Portfolio Value"
          value={`₨${(d.total_value || 0).toLocaleString()}`}
          change={d.total_unrealized_pnl_pct}
          icon={DollarSign}
        />
        <StatCard
          title="Today's P&L"
          value={`₨${(d.today_pnl || 0).toLocaleString()}`}
          change={d.today_pnl_pct}
          icon={Activity}
          color="text-cyan-400"
        />
        <StatCard
          title="Win Rate"
          value={`${(d.win_rate || 0).toFixed(1)}%`}
          icon={Target}
          color="text-blue-400"
        />
        <StatCard
          title="Open Positions"
          value={d.open_positions || 0}
          icon={BarChart3}
          color="text-purple-400"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Performance Chart */}
        <div className="lg:col-span-2 bg-surface rounded-xl p-5 border border-slate-700/50">
          <h3 className="text-lg font-semibold mb-4">Portfolio Performance</h3>
          {performance.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={performance}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 12 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Line type="monotone" dataKey="portfolio_value" stroke="#10b981" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-slate-500">
              No performance data yet. Start trading to see your chart.
            </div>
          )}
        </div>

        {/* Sector Breakdown */}
        <div className="bg-surface rounded-xl p-5 border border-slate-700/50">
          <h3 className="text-lg font-semibold mb-4">Allocation</h3>
          {sectorData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={sectorData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {sectorData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-slate-500">
              No positions to display.
            </div>
          )}
        </div>
      </div>

      {/* Holdings Table */}
      <div className="bg-surface rounded-xl p-5 border border-slate-700/50">
        <h3 className="text-lg font-semibold mb-4">Open Holdings</h3>
        <PositionsTable positions={positions} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Today's Signals */}
        <div className="bg-surface rounded-xl p-5 border border-slate-700/50">
          <h3 className="text-lg font-semibold mb-4">Today's Signals</h3>
          {signals.length > 0 ? (
            <div className="space-y-3">
              {signals.slice(0, 5).map((s, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700/30">
                  <div>
                    <span className="font-semibold text-white">{s.symbol}</span>
                    <span className={`ml-2 px-2 py-0.5 rounded text-xs font-bold ${s.signal_type === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                      {s.signal_type}
                    </span>
                    <p className="text-xs text-slate-400 mt-1">{s.reason}</p>
                  </div>
                  <div className="text-right">
                    <div className="font-mono text-sm">₨{s.entry_price?.toLocaleString()}</div>
                    <div className="text-xs text-slate-400">{s.confidence?.toFixed(0)}% conf</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center text-slate-500 py-8">No signals today.</div>
          )}
        </div>

        {/* Recent Alerts */}
        <div className="bg-surface rounded-xl p-5 border border-slate-700/50">
          <h3 className="text-lg font-semibold mb-4">Recent Alerts</h3>
          {alerts.length > 0 ? (
            <div className="space-y-3 max-h-[400px] overflow-y-auto">
              {alerts.slice(0, 5).map((a, i) => (
                <div key={i} className={`p-3 rounded-lg border ${a.is_read ? 'bg-slate-800/30 border-slate-700/20' : 'bg-slate-800/50 border-slate-600/30'}`}>
                  <div className="flex justify-between items-start">
                    <span className="font-semibold text-sm">{a.title || a.alert_type}</span>
                    <span className="text-xs text-slate-500">{new Date(a.created_at).toLocaleTimeString()}</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">{a.message}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center text-slate-500 py-8">No alerts yet.</div>
          )}
        </div>
      </div>
    </div>
  );
}
