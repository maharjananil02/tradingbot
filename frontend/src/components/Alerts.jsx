import { useEffect } from 'react';
import useStore from '../hooks/useStore';
import { markAlertRead } from '../utils/api';
import { Bell, CheckCircle, AlertTriangle, TrendingUp, Info } from 'lucide-react';

export default function Alerts() {
  const { alerts, fetchAlerts, alertsLoading } = useStore();

  useEffect(() => {
    fetchAlerts();
  }, []);

  const handleMarkRead = async (id) => {
    try {
      await markAlertRead(id);
      fetchAlerts();
    } catch (err) {
      console.error('Mark read error:', err);
    }
  };

  const getAlertIcon = (type) => {
    switch (type) {
      case 'PRICE_MILESTONE': return <TrendingUp className="w-5 h-5 text-emerald-400" />;
      case 'STOP_LOSS_HIT':
      case 'STOP_LOSS_WARNING':
      case 'RISK_ALERT': return <AlertTriangle className="w-5 h-5 text-red-400" />;
      case 'SIGNAL': return <Bell className="w-5 h-5 text-blue-400" />;
      default: return <Info className="w-5 h-5 text-slate-400" />;
    }
  };

  const getAlertBorder = (type) => {
    switch (type) {
      case 'PRICE_MILESTONE': return 'border-l-emerald-500';
      case 'STOP_LOSS_HIT':
      case 'STOP_LOSS_WARNING':
      case 'RISK_ALERT': return 'border-l-red-500';
      case 'SIGNAL': return 'border-l-blue-500';
      default: return 'border-l-slate-500';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Alerts</h2>
          <p className="text-slate-400 text-sm mt-1">
            Trading notifications, milestones, and risk warnings
          </p>
        </div>
        <span className="text-sm text-slate-400">
          {alerts.filter(a => !a.is_read).length} unread
        </span>
      </div>

      {alertsLoading ? (
        <div className="text-center py-16 text-slate-500">Loading alerts...</div>
      ) : alerts.length > 0 ? (
        <div className="space-y-3">
          {alerts.map((a, i) => (
            <div
              key={i}
              className={`bg-surface rounded-lg p-4 border border-slate-700/50 border-l-4 ${getAlertBorder(a.alert_type)} ${
                a.is_read ? 'opacity-60' : ''
              } hover:bg-slate-800/80 transition-colors`}
            >
              <div className="flex items-start gap-3">
                <div className="mt-0.5">{getAlertIcon(a.alert_type)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-start">
                    <h4 className="font-semibold text-sm">{a.title || a.alert_type}</h4>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500 whitespace-nowrap">
                        {a.created_at ? new Date(a.created_at).toLocaleString() : ''}
                      </span>
                      {!a.is_read && (
                        <button
                          onClick={() => handleMarkRead(a.id)}
                          className="text-slate-500 hover:text-emerald-400 transition-colors"
                          title="Mark as read"
                        >
                          <CheckCircle className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                  <p className="text-sm text-slate-300 mt-1 whitespace-pre-line">{a.message}</p>
                  {a.symbol && (
                    <span className="inline-block mt-2 px-2 py-0.5 bg-slate-700/50 rounded text-xs text-slate-300">
                      {a.symbol}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-surface rounded-xl p-12 border border-slate-700/50 text-center">
          <Bell className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <div className="text-slate-500 text-lg mb-2">No alerts yet</div>
          <p className="text-slate-600 text-sm">Alerts will appear when signals trigger, milestones are reached, or stop losses activate.</p>
        </div>
      )}
    </div>
  );
}
