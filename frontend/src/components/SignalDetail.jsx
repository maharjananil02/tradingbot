import { useState, useEffect, useRef, useCallback } from 'react';
import { X, Download, TrendingUp, TrendingDown, Check, AlertTriangle, Activity } from 'lucide-react';
import { getSignalTrace, getPricePrediction } from '../utils/api';
import { createChart, CandlestickSeries, LineSeries } from 'lightweight-charts';

function IndicatorRow({ label, triggered, children }) {
  return (
    <div className={`p-3 rounded-lg border ${triggered ? 'border-emerald-500/40 bg-emerald-500/5' : 'border-slate-700/50 bg-slate-800/30'}`}>
      <div className="flex items-center gap-2 mb-2">
        {triggered ? <Check className="w-4 h-4 text-emerald-400" /> : <X className="w-4 h-4 text-slate-500" />}
        <span className={`text-sm font-semibold ${triggered ? 'text-emerald-400' : 'text-slate-400'}`}>{label}</span>
        {triggered && <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">TRIGGERED</span>}
      </div>
      <div className="text-xs text-slate-300 space-y-1">{children}</div>
    </div>
  );
}

export default function SignalDetail({ symbol, onClose }) {
  const [trace, setTrace] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('analysis');
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [traceRes, predRes] = await Promise.all([
          getSignalTrace(symbol),
          getPricePrediction(symbol, 7),
        ]);
        setTrace(traceRes.data);
        setPrediction(predRes.data);
      } catch (err) {
        console.error('Failed to load signal detail:', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [symbol]);

  const initChart = useCallback(() => {
    if (!chartContainerRef.current || !prediction) return;

    // Clean up existing chart
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: '#0f172a' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      crosshair: { mode: 0 },
      timeScale: {
        borderColor: '#334155',
        timeVisible: false,
      },
      rightPriceScale: { borderColor: '#334155' },
    });

    // Historical candles
    const historyData = prediction.history.map(c => ({
      time: c.date,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });
    candleSeries.setData(historyData);

    // Predicted candles (different colors)
    const predData = prediction.predictions.map(c => ({
      time: c.date,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    const predSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#3b82f6',
      downColor: '#f59e0b',
      borderUpColor: '#3b82f6',
      borderDownColor: '#f59e0b',
      wickUpColor: '#3b82f6',
      wickDownColor: '#f59e0b',
    });
    predSeries.setData(predData);

    // Divider line at prediction start
    if (trace?.signal) {
      const sl = trace.signal.stop_loss;
      const t1 = trace.signal.target_1;
      const t2 = trace.signal.target_2;

      candleSeries.createPriceLine({ price: sl, color: '#ef4444', lineWidth: 1, lineStyle: 2, title: 'SL' });
      candleSeries.createPriceLine({ price: t1, color: '#10b981', lineWidth: 1, lineStyle: 2, title: 'T1' });
      candleSeries.createPriceLine({ price: t2, color: '#22d3ee', lineWidth: 1, lineStyle: 2, title: 'T2' });
    }

    chart.timeScale().fitContent();
    chartRef.current = chart;

    const resizeHandler = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', resizeHandler);
    return () => window.removeEventListener('resize', resizeHandler);
  }, [prediction, trace]);

  useEffect(() => {
    if (tab === 'chart') {
      const cleanup = initChart();
      return () => { if (cleanup) cleanup(); };
    }
    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [tab, initChart]);

  const handleDownload = async () => {
    if (!chartContainerRef.current) return;
    try {
      const { toPng } = await import('html-to-image');
      const dataUrl = await toPng(chartContainerRef.current, {
        backgroundColor: '#0f172a',
        pixelRatio: 2,
      });
      const link = document.createElement('a');
      link.download = `${symbol}_prediction_${new Date().toISOString().split('T')[0]}.png`;
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  const ind = trace?.indicators;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-slate-900 rounded-2xl border border-slate-700/50 w-full max-w-4xl max-h-[90vh] overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/50">
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-blue-400" />
            <h2 className="text-xl font-bold">{symbol}</h2>
            {trace?.verdict && (
              <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                trace.verdict === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-600/20 text-slate-400'
              }`}>
                {trace.verdict}
              </span>
            )}
            {trace && <span className="text-slate-500 text-sm">Rs.{trace.current_price?.toLocaleString()}</span>}
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-slate-800 rounded-lg transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-700/50">
          <button
            onClick={() => setTab('analysis')}
            className={`px-6 py-3 text-sm font-medium transition-colors ${tab === 'analysis' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-slate-400 hover:text-white'}`}
          >
            Signal Analysis
          </button>
          <button
            onClick={() => setTab('chart')}
            className={`px-6 py-3 text-sm font-medium transition-colors ${tab === 'chart' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-slate-400 hover:text-white'}`}
          >
            7-Day Prediction Chart
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-130px)] p-6">
          {loading ? (
            <div className="text-center py-16 text-slate-500">Loading analysis...</div>
          ) : tab === 'analysis' && ind ? (
            <div className="space-y-4">
              {/* Summary */}
              {trace.signal && (
                <div className={`p-4 rounded-xl border ${trace.signal.type === 'BUY' ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
                  <div className="flex items-center gap-2 mb-2">
                    {trace.signal.type === 'BUY' ? <TrendingUp className="w-5 h-5 text-emerald-400" /> : <TrendingDown className="w-5 h-5 text-red-400" />}
                    <span className="font-bold text-lg">{trace.signal.type} Signal</span>
                    <span className="text-slate-400">— {trace.signal.confidence}% confidence</span>
                  </div>
                  <p className="text-sm text-slate-300 mb-3">{trace.signal.reason}</p>
                  <div className="grid grid-cols-4 gap-3 text-sm">
                    <div><span className="text-slate-500 block">Entry</span><span className="font-mono">Rs.{trace.signal.entry_price}</span></div>
                    <div><span className="text-slate-500 block">Stop Loss</span><span className="font-mono text-red-400">Rs.{trace.signal.stop_loss}</span></div>
                    <div><span className="text-slate-500 block">Target 2</span><span className="font-mono text-emerald-400">Rs.{trace.signal.target_2}</span></div>
                    <div><span className="text-slate-500 block">R:R</span><span className="font-mono text-blue-400">1:{trace.signal.risk_reward_ratio}</span></div>
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2 mt-2">
                <span className="text-sm text-slate-400">Confirmations:</span>
                <span className={`font-bold ${trace.buy_confirmations >= 2 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {trace.buy_confirmations} / 5
                </span>
                <span className="text-xs text-slate-500">(need ≥ 2)</span>
              </div>

              {/* Indicator Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <IndicatorRow label="Volume Filter" triggered={ind.volume.surge}>
                  <div className="flex justify-between"><span>Current Volume:</span><span className="font-mono">{ind.volume.current?.toLocaleString()}</span></div>
                  <div className="flex justify-between"><span>20-day Average:</span><span className="font-mono">{ind.volume.avg_20d?.toLocaleString()}</span></div>
                  <div className="flex justify-between"><span>Volume Surge (&gt;1.2x):</span><span className={ind.volume.surge ? 'text-emerald-400' : 'text-slate-500'}>{ind.volume.surge ? 'YES' : 'NO'}</span></div>
                  <div className="flex justify-between"><span>Liquidity (avg &gt;100):</span><span className={ind.volume.liquid ? 'text-emerald-400' : 'text-red-400'}>{ind.volume.liquid ? 'PASS' : 'FAIL'}</span></div>
                </IndicatorRow>

                <IndicatorRow label="SMA Crossover" triggered={ind.sma.triggered}>
                  <div className="flex justify-between"><span>SMA 20:</span><span className="font-mono">{ind.sma.sma20}</span></div>
                  <div className="flex justify-between"><span>SMA 50:</span><span className="font-mono">{ind.sma.sma50}</span></div>
                  <div className="flex justify-between"><span>Price &gt; SMA20:</span><span className={ind.sma.price_above_sma20 ? 'text-emerald-400' : 'text-slate-500'}>{ind.sma.price_above_sma20 ? 'YES' : 'NO'}</span></div>
                  <div className="flex justify-between"><span>SMA20 &gt; SMA50:</span><span className={ind.sma.sma20_above_sma50 ? 'text-emerald-400' : 'text-slate-500'}>{ind.sma.sma20_above_sma50 ? 'YES' : 'NO'}</span></div>
                  <div className="flex justify-between"><span>Fresh Crossover (3d):</span><span className={ind.sma.fresh_crossover ? 'text-emerald-400 font-bold' : 'text-slate-500'}>{ind.sma.fresh_crossover ? 'YES' : 'NO'}</span></div>
                </IndicatorRow>

                <IndicatorRow label="RSI Oversold Bounce" triggered={ind.rsi.triggered}>
                  <div className="flex justify-between"><span>Current RSI:</span><span className={`font-mono ${ind.rsi.current < 30 ? 'text-emerald-400' : ind.rsi.current > 70 ? 'text-red-400' : ''}`}>{ind.rsi.current}</span></div>
                  <div className="flex justify-between"><span>Previous RSI:</span><span className="font-mono">{ind.rsi.previous}</span></div>
                  <div className="flex justify-between"><span>Was &lt;30 &amp; bouncing:</span><span className={ind.rsi.oversold_bounce ? 'text-emerald-400 font-bold' : 'text-slate-500'}>{ind.rsi.oversold_bounce ? 'YES' : 'NO'}</span></div>
                </IndicatorRow>

                <IndicatorRow label="MACD Crossover" triggered={ind.macd.triggered}>
                  <div className="flex justify-between"><span>MACD Line:</span><span className="font-mono">{ind.macd.macd_line}</span></div>
                  <div className="flex justify-between"><span>Signal Line:</span><span className="font-mono">{ind.macd.signal_line}</span></div>
                  <div className="flex justify-between"><span>Prev MACD:</span><span className="font-mono">{ind.macd.prev_macd}</span></div>
                  <div className="flex justify-between"><span>Prev Signal:</span><span className="font-mono">{ind.macd.prev_signal}</span></div>
                  <div className="flex justify-between"><span>Bullish Crossover:</span><span className={ind.macd.bullish_crossover ? 'text-emerald-400 font-bold' : 'text-slate-500'}>{ind.macd.bullish_crossover ? 'YES' : 'NO'}</span></div>
                </IndicatorRow>

                <IndicatorRow label="Chart Patterns" triggered={ind.patterns.triggered}>
                  <div className="flex justify-between"><span>Double Bottom:</span><span className={ind.patterns.double_bottom ? 'text-emerald-400 font-bold' : 'text-slate-500'}>{ind.patterns.double_bottom ? 'DETECTED' : 'NO'}</span></div>
                  <div className="flex justify-between"><span>Breakout (20d high + vol):</span><span className={ind.patterns.breakout ? 'text-emerald-400 font-bold' : 'text-slate-500'}>{ind.patterns.breakout ? 'DETECTED' : 'NO'}</span></div>
                </IndicatorRow>

                <IndicatorRow label="ATR (Volatility)" triggered={false}>
                  <div className="flex justify-between"><span>ATR (14):</span><span className="font-mono">{ind.atr.value}</span></div>
                  <div className="flex justify-between"><span>Used for:</span><span>Stop Loss &amp; Target calculation</span></div>
                </IndicatorRow>
              </div>
            </div>
          ) : tab === 'chart' && prediction ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded-sm bg-emerald-500" />
                    <span className="text-slate-400">Historical (up)</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded-sm bg-red-500" />
                    <span className="text-slate-400">Historical (down)</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded-sm bg-blue-500" />
                    <span className="text-slate-400">Predicted (up)</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded-sm bg-amber-500" />
                    <span className="text-slate-400">Predicted (down)</span>
                  </div>
                </div>
                <button
                  onClick={handleDownload}
                  className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Download Chart
                </button>
              </div>

              <div ref={chartContainerRef} className="rounded-xl overflow-hidden border border-slate-700/50" />

              {/* Prediction table */}
              <div className="mt-4">
                <h4 className="text-sm font-semibold text-slate-400 mb-2">Predicted Prices</h4>
                <div className="grid grid-cols-7 gap-2">
                  {prediction.predictions.map((p, i) => {
                    const change = ((p.close - prediction.current_price) / prediction.current_price * 100).toFixed(1);
                    const isUp = p.close >= p.open;
                    return (
                      <div key={i} className={`p-2 rounded-lg border text-center text-xs ${isUp ? 'border-blue-500/30 bg-blue-500/5' : 'border-amber-500/30 bg-amber-500/5'}`}>
                        <div className="text-slate-500 mb-1">{new Date(p.date + 'T00:00:00').toLocaleDateString('en', { weekday: 'short', month: 'short', day: 'numeric' })}</div>
                        <div className="font-mono font-semibold">{p.close}</div>
                        <div className={`mt-0.5 ${parseFloat(change) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {parseFloat(change) >= 0 ? '+' : ''}{change}%
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs text-slate-500 mt-2">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Predictions are based on technical indicators (SMA, RSI, ATR, Bollinger Bands). Not financial advice.</span>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
