import { useEffect, useState } from 'react';
import { getSettings, toggleAutoExecute, resetAllData, fetchPriceHistory } from '../utils/api';
import { AlertTriangle, RotateCcw, Database, Download } from 'lucide-react';

export default function Settings() {
  const [settings, setSettings] = useState(null);
  const [toggling, setToggling] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [resetStep, setResetStep] = useState(0); // 0=hidden, 1=first confirm, 2=type confirm
  const [confirmText, setConfirmText] = useState('');
  const [resetting, setResetting] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [fetchResult, setFetchResult] = useState(null);

  useEffect(() => {
    getSettings().then(({ data }) => setSettings(data)).catch(console.error);
  }, []);

  const handleToggleAutoExec = async () => {
    setToggling(true);
    try {
      const newValue = !settings.auto_execute_enabled;
      await toggleAutoExecute(newValue);
      setSettings({ ...settings, auto_execute_enabled: newValue });
    } catch (err) {
      console.error('Toggle error:', err);
    } finally {
      setToggling(false);
    }
  };

  const handleReset = async () => {
    if (confirmText !== 'RESET') return;
    setResetting(true);
    try {
      await resetAllData();
      setResetStep(0);
      setConfirmText('');
      // Reload to reflect fresh state
      window.location.reload();
    } catch (err) {
      alert(err.response?.data?.detail || 'Reset failed');
    } finally {
      setResetting(false);
    }
  };

  const handleFetchHistory = async () => {
    setFetching(true);
    setFetchResult(null);
    try {
      const { data } = await fetchPriceHistory(100);
      setFetchResult(data);
    } catch (err) {
      setFetchResult({ error: err.response?.data?.detail || 'Fetch failed' });
    } finally {
      setFetching(false);
    }
  };

  if (!settings) {
    return <div className="text-center py-16 text-slate-500">Loading settings...</div>;
  }

  const sections = [
    {
      title: 'Risk Management',
      items: [
        { label: 'Risk Per Trade', value: `${(settings.risk_per_trade * 100).toFixed(0)}%` },
        { label: 'Max Positions', value: settings.max_positions },
        { label: 'Max Position Size', value: `${(settings.max_position_pct * 100).toFixed(0)}%` },
        { label: 'Hard Stop Loss', value: `${(settings.hard_stop_loss_pct * 100).toFixed(0)}%` },
        { label: 'Max Sector Concentration', value: `${(settings.max_sector_concentration * 100).toFixed(0)}%` },
      ],
    },
    {
      title: 'Trailing Stop Loss',
      items: [
        { label: 'Trigger (gain %)', value: `${(settings.trailing_sl_trigger_pct * 100).toFixed(0)}%` },
        { label: 'Lock (profit %)', value: `${(settings.trailing_sl_lock_pct * 100).toFixed(0)}%` },
      ],
    },
    {
      title: 'Drawdown Controls',
      items: [
        { label: 'Alert At', value: `${(settings.max_drawdown_alert_pct * 100).toFixed(0)}%` },
        { label: 'Pause Trading At', value: `${(settings.max_drawdown_pause_pct * 100).toFixed(0)}%` },
        { label: 'Daily Loss Limit', value: `${(settings.daily_loss_limit_pct * 100).toFixed(0)}%` },
      ],
    },
    {
      title: 'Holding Period',
      items: [
        { label: 'Minimum Days', value: `${settings.min_holding_days} days` },
        { label: 'Maximum Days', value: `${settings.max_holding_days} days` },
      ],
    },
    {
      title: 'Market Hours (Nepal Time)',
      items: [
        { label: 'Market Open', value: settings.market_hours?.open },
        { label: 'Market Close', value: settings.market_hours?.close },
      ],
    },
    {
      title: 'Capital',
      items: [
        { label: 'Paper Trading Capital', value: `₨${settings.paper_trading_capital?.toLocaleString()}` },
      ],
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Settings</h2>
        <p className="text-slate-400 text-sm mt-1">
          Strategy parameters and risk management configuration.
          Edit <code className="text-xs bg-slate-800 px-1 py-0.5 rounded">config.py</code> to change these values.
        </p>
      </div>

      {/* Auto-Execution Toggle */}
      <div className="bg-surface rounded-xl p-5 border border-slate-700/50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
              Auto-Execute Paper Trades
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Automatically open paper positions when BUY signals with ≥{settings.auto_execute_min_confidence}% confidence are generated.
            </p>
          </div>
          <button
            onClick={handleToggleAutoExec}
            disabled={toggling}
            className={`relative inline-flex h-7 w-14 items-center rounded-full transition-colors ${
              settings.auto_execute_enabled ? 'bg-green-600' : 'bg-slate-600'
            }`}
          >
            <span
              className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                settings.auto_execute_enabled ? 'translate-x-8' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {sections.map((section, i) => (
          <div key={i} className="bg-surface rounded-xl p-5 border border-slate-700/50">
            <h3 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">
              {section.title}
            </h3>
            <div className="space-y-3">
              {section.items.map((item, j) => (
                <div key={j} className="flex justify-between items-center">
                  <span className="text-sm text-slate-400">{item.label}</span>
                  <span className="font-mono text-sm font-semibold text-white">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Data Management */}
      <div className="bg-surface rounded-xl p-5 border border-slate-700/50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <Database className="w-4 h-4" /> Price Data Management
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Fetch 100 days of historical price data from ShareSansar for top 50 stocks.
              Required for signal generation (minimum 50 days needed). Daily prices are added automatically during market hours.
            </p>
          </div>
          <button
            onClick={handleFetchHistory}
            disabled={fetching}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600/20 text-blue-400 hover:bg-blue-600/40 border border-blue-600/30 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className={`w-4 h-4 ${fetching ? 'animate-bounce' : ''}`} />
            {fetching ? 'Fetching...' : 'Fetch Price History'}
          </button>
        </div>
        {fetchResult && (
          <div className={`mt-3 p-3 rounded-lg text-sm ${
            fetchResult.error
              ? 'bg-red-500/10 border border-red-500/30 text-red-400'
              : 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
          }`}>
            {fetchResult.error
              ? fetchResult.error
              : `${fetchResult.message} — ${fetchResult.saved} price records saved`
            }
          </div>
        )}
      </div>

      {/* Danger Zone - Reset */}
      <div className="bg-red-900/10 border border-red-700/30 rounded-xl p-5">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-red-400 uppercase tracking-wider flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" /> Danger Zone
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Reset everything and start fresh. This will permanently delete all positions, trades, signals, alerts, and performance history. Price data is preserved so you can generate signals immediately.
            </p>
          </div>
          <button
            onClick={() => setResetStep(1)}
            className="flex items-center gap-2 px-4 py-2 bg-red-600/20 text-red-400 hover:bg-red-600/40 border border-red-600/30 rounded-lg text-sm font-medium transition-colors"
          >
            <RotateCcw className="w-4 h-4" /> Reset All Data
          </button>
        </div>

        {/* Step 1: First confirmation */}
        {resetStep === 1 && (
          <div className="mt-4 p-4 bg-red-950/50 rounded-lg border border-red-700/40">
            <p className="text-red-300 text-sm font-semibold mb-3">
              Are you sure? This will delete ALL data:
            </p>
            <ul className="text-xs text-red-300/80 space-y-1 mb-4 ml-4 list-disc">
              <li>All open & closed positions</li>
              <li>All trade history & journal entries</li>
              <li>All signals & alerts</li>
              <li>All performance records</li>
              <li>Portfolio reset to ₨{settings.paper_trading_capital?.toLocaleString()}</li>
            </ul>
            <p className="text-xs text-emerald-400/80 mb-4">✓ Price history will be preserved</p>
            <div className="flex gap-2">
              <button
                onClick={() => setResetStep(2)}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Yes, I want to reset
              </button>
              <button
                onClick={() => { setResetStep(0); setConfirmText(''); }}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-sm font-medium transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Type RESET to confirm */}
        {resetStep === 2 && (
          <div className="mt-4 p-4 bg-red-950/50 rounded-lg border border-red-700/40">
            <p className="text-red-300 text-sm mb-3">
              Type <code className="bg-red-900/50 px-2 py-0.5 rounded font-bold text-red-200">RESET</code> to confirm:
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="Type RESET"
                className="bg-slate-900 border border-red-600/50 rounded-lg px-3 py-2 text-sm text-red-300 focus:border-red-400 outline-none w-40 font-mono"
                autoFocus
              />
              <button
                onClick={handleReset}
                disabled={confirmText !== 'RESET' || resetting}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  confirmText === 'RESET'
                    ? 'bg-red-600 hover:bg-red-500 text-white'
                    : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                }`}
              >
                {resetting ? 'Resetting...' : 'Confirm Reset'}
              </button>
              <button
                onClick={() => { setResetStep(0); setConfirmText(''); }}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-sm font-medium transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Disclaimer */}
      <div className="bg-yellow-900/20 border border-yellow-700/30 rounded-xl p-5">
        <h4 className="text-yellow-400 font-semibold mb-2">Disclaimer</h4>
        <p className="text-sm text-yellow-200/70">
          This trading bot is for educational and paper trading purposes only.
          It does not constitute financial advice. Use at your own risk.
          Past performance is not indicative of future results.
          The bot does not execute real trades on your behalf.
        </p>
      </div>
    </div>
  );
}
