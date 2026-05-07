import { useState, useEffect } from 'react';
import useStore from './hooks/useStore';
import Dashboard from './components/Dashboard';
import Portfolio from './components/Portfolio';
import Signals from './components/Signals';
import Alerts from './components/Alerts';
import TradeJournal from './components/TradeJournal';
import Backtest from './components/Backtest';
import Settings from './components/Settings';
import {
  LayoutDashboard, Briefcase, TrendingUp, Bell,
  BookOpen, FlaskConical, SettingsIcon, Activity,
} from 'lucide-react';

const TABS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'portfolio', label: 'Portfolio', icon: Briefcase },
  { id: 'signals', label: 'Signals', icon: TrendingUp },
  { id: 'alerts', label: 'Alerts', icon: Bell },
  { id: 'journal', label: 'Trade Journal', icon: BookOpen },
  { id: 'backtest', label: 'Backtest', icon: FlaskConical },
  { id: 'settings', label: 'Settings', icon: SettingsIcon },
];

function App() {
  const { activeTab, setActiveTab, alerts } = useStore();
  const [nepalTime, setNepalTime] = useState('');
  const [isMarketOpen, setIsMarketOpen] = useState(false);

  useEffect(() => {
    const fetchTime = async () => {
      try {
        const res = await fetch('/api/time');
        const data = await res.json();
        setNepalTime(data.time);
        setIsMarketOpen(data.is_market_open);
      } catch {
        // Fallback: compute Nepal time from UTC
        const now = new Date();
        const utc = now.getTime() + now.getTimezoneOffset() * 60000;
        const npt = new Date(utc + 5.75 * 3600000);
        setNepalTime(npt.toLocaleTimeString('en-US', { hour12: true }));
        const h = npt.getHours();
        setIsMarketOpen(h >= 11 && h < 15 && npt.getDay() !== 0 && npt.getDay() !== 6);
      }
    };
    fetchTime();
    const timer = setInterval(fetchTime, 5000);
    return () => clearInterval(timer);
  }, []);

  const unreadAlerts = alerts.filter(a => !a.is_read).length;

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard': return <Dashboard />;
      case 'portfolio': return <Portfolio />;
      case 'signals': return <Signals />;
      case 'alerts': return <Alerts />;
      case 'journal': return <TradeJournal />;
      case 'backtest': return <Backtest />;
      case 'settings': return <Settings />;
      default: return <Dashboard />;
    }
  };

  // Simple market open check (Nepal time approximation)
  const isMarketHours = isMarketOpen;

  return (
    <div className="min-h-screen bg-background">
      {/* Top Bar */}
      <header className="bg-surface border-b border-slate-700/50 px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="w-6 h-6 text-emerald-400" />
            <h1 className="text-xl font-bold">
              NEPSE <span className="text-emerald-400">Trading Bot</span>
            </h1>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isMarketHours ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
              <span className="text-sm text-slate-400">
                {isMarketHours ? 'Market Open' : 'Market Closed'}
              </span>
            </div>
            <span className="text-sm font-mono text-slate-400" title="Nepal Time (NPT)">
              🇳🇵 {nepalTime || '--:--:-- --'}
            </span>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-56 min-h-[calc(100vh-57px)] bg-surface/50 border-r border-slate-700/30 p-3">
          <nav className="space-y-1">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  activeTab === id
                    ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-600/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
                {id === 'alerts' && unreadAlerts > 0 && (
                  <span className="ml-auto px-1.5 py-0.5 bg-red-500 text-white text-xs rounded-full">
                    {unreadAlerts}
                  </span>
                )}
              </button>
            ))}
          </nav>

          {/* Bot Status */}
          <div className="mt-8 p-3 bg-slate-800/30 rounded-lg border border-slate-700/30">
            <div className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Bot Status</div>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Scheduler</span>
                <span className="text-emerald-400">Active</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Mode</span>
                <span className="text-yellow-400">Paper</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Version</span>
                <span className="text-slate-300">1.0.0</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6 overflow-y-auto max-h-[calc(100vh-57px)]">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}

export default App;
