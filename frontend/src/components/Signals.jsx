import { useEffect, useState } from 'react';
import useStore from '../hooks/useStore';
import { generateSignals } from '../utils/api';
import { RefreshCw, TrendingUp, TrendingDown, Minus } from 'lucide-react';

export default function Signals() {
  const { signals, fetchSignals, signalsLoading } = useStore();
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    fetchSignals();
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await generateSignals();
      await fetchSignals();
    } catch (err) {
      console.error('Generate error:', err);
    } finally {
      setGenerating(false);
    }
  };

  const getSignalIcon = (type) => {
    switch (type) {
      case 'BUY': return <TrendingUp className="w-5 h-5 text-emerald-400" />;
      case 'SELL':
      case 'EXIT': return <TrendingDown className="w-5 h-5 text-red-400" />;
      default: return <Minus className="w-5 h-5 text-slate-400" />;
    }
  };

  const getSignalColor = (type) => {
    switch (type) {
      case 'BUY': return 'border-emerald-500/30 bg-emerald-500/5';
      case 'SELL':
      case 'EXIT': return 'border-red-500/30 bg-red-500/5';
      default: return 'border-slate-600/30 bg-slate-800/30';
    }
  };

  const getConfidenceColor = (conf) => {
    if (conf >= 75) return 'text-emerald-400';
    if (conf >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Trading Signals</h2>
          <p className="text-slate-400 text-sm mt-1">
            AI-generated signals based on SMA, RSI, MACD, and pattern analysis
          </p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${generating ? 'animate-spin' : ''}`} />
          {generating ? 'Generating...' : 'Generate Signals'}
        </button>
      </div>

      {signalsLoading ? (
        <div className="text-center py-16 text-slate-500">Loading signals...</div>
      ) : signals.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {signals.map((s, i) => (
            <div
              key={i}
              className={`rounded-xl p-5 border transition-all hover:scale-[1.02] ${getSignalColor(s.signal_type)}`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  {getSignalIcon(s.signal_type)}
                  <span className="text-lg font-bold">{s.symbol}</span>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                  s.signal_type === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
                }`}>
                  {s.signal_type}
                </span>
              </div>

              <p className="text-sm text-slate-300 mb-4">{s.reason}</p>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-slate-500">Entry</span>
                  <div className="font-mono font-semibold">₨{s.entry_price?.toLocaleString()}</div>
                </div>
                <div>
                  <span className="text-slate-500">Confidence</span>
                  <div className={`font-mono font-semibold ${getConfidenceColor(s.confidence)}`}>
                    {s.confidence?.toFixed(0)}%
                  </div>
                </div>
                <div>
                  <span className="text-slate-500">Stop Loss</span>
                  <div className="font-mono text-red-400">₨{s.stop_loss?.toLocaleString()}</div>
                </div>
                <div>
                  <span className="text-slate-500">R:R</span>
                  <div className="font-mono text-blue-400">1:{s.risk_reward_ratio}</div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-700/50">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Targets:</span>
                  <div className="space-x-3 font-mono">
                    <span className="text-emerald-400">T1: ₨{s.target_1?.toLocaleString()}</span>
                    <span className="text-emerald-300">T2: ₨{s.target_2?.toLocaleString()}</span>
                    <span className="text-emerald-200">T3: ₨{s.target_3?.toLocaleString()}</span>
                  </div>
                </div>
                {s.suggested_quantity && (
                  <div className="flex justify-between text-xs mt-1">
                    <span className="text-slate-500">Suggested Qty:</span>
                    <span className="font-mono">{s.suggested_quantity} shares</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-surface rounded-xl p-12 border border-slate-700/50 text-center">
          <div className="text-slate-500 text-lg mb-2">No signals today</div>
          <p className="text-slate-600 text-sm">Click "Generate Signals" to analyze stocks, or wait for the scheduled 11:00 AM scan.</p>
        </div>
      )}
    </div>
  );
}
