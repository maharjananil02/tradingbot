import { create } from 'zustand';
import {
  getDashboard,
  getPositions,
  getSignals,
  getTrades,
  getTradeStats,
  getRiskMetrics,
  getPerformance,
  getAlerts,
  updateTrade,
  deleteTrade,
  updatePosition,
} from '../utils/api';

const useStore = create((set, get) => ({
  // Dashboard
  dashboard: null,
  dashboardLoading: false,
  fetchDashboard: async () => {
    set({ dashboardLoading: true });
    try {
      const { data } = await getDashboard();
      set({ dashboard: data });
    } catch (err) {
      console.error('Dashboard error:', err);
    } finally {
      set({ dashboardLoading: false });
    }
  },

  // Positions
  positions: [],
  positionsLoading: false,
  fetchPositions: async (isPaper = false) => {
    set({ positionsLoading: true });
    try {
      const { data } = await getPositions(isPaper);
      set({ positions: data });
    } catch (err) {
      console.error('Positions error:', err);
    } finally {
      set({ positionsLoading: false });
    }
  },

  // Signals
  signals: [],
  signalsLoading: false,
  fetchSignals: async (date = null) => {
    set({ signalsLoading: true });
    try {
      const { data } = await getSignals(date);
      set({ signals: data });
    } catch (err) {
      console.error('Signals error:', err);
    } finally {
      set({ signalsLoading: false });
    }
  },

  // Trades
  trades: [],
  tradeStats: null,
  tradesLoading: false,
  fetchTrades: async (isPaper = false) => {
    set({ tradesLoading: true });
    try {
      const [tradesRes, statsRes] = await Promise.all([
        getTrades(isPaper),
        getTradeStats(isPaper),
      ]);
      set({ trades: tradesRes.data, tradeStats: statsRes.data });
    } catch (err) {
      console.error('Trades error:', err);
    } finally {
      set({ tradesLoading: false });
    }
  },
  updateTrade: async (id, data) => {
    const { data: updated } = await updateTrade(id, data);
    set((state) => ({
      trades: state.trades.map((t) => (t.id === id ? updated : t)),
    }));
    return updated;
  },
  deleteTrade: async (id) => {
    await deleteTrade(id);
    set((state) => ({
      trades: state.trades.filter((t) => t.id !== id),
    }));
  },
  updatePosition: async (id, data) => {
    const { data: updated } = await updatePosition(id, data);
    set((state) => ({
      positions: state.positions.map((p) => (p.id === id ? updated : p)),
    }));
    return updated;
  },

  // Risk
  riskMetrics: null,
  riskLoading: false,
  fetchRisk: async (isPaper = false) => {
    set({ riskLoading: true });
    try {
      const { data } = await getRiskMetrics(isPaper);
      set({ riskMetrics: data });
    } catch (err) {
      console.error('Risk error:', err);
    } finally {
      set({ riskLoading: false });
    }
  },

  // Performance
  performance: [],
  performanceLoading: false,
  fetchPerformance: async (days = 30, isPaper = false) => {
    set({ performanceLoading: true });
    try {
      const { data } = await getPerformance(days, isPaper);
      set({ performance: data });
    } catch (err) {
      console.error('Performance error:', err);
    } finally {
      set({ performanceLoading: false });
    }
  },

  // Alerts
  alerts: [],
  alertsLoading: false,
  fetchAlerts: async () => {
    set({ alertsLoading: true });
    try {
      const { data } = await getAlerts();
      set({ alerts: data });
    } catch (err) {
      console.error('Alerts error:', err);
    } finally {
      set({ alertsLoading: false });
    }
  },

  // Active tab
  activeTab: 'dashboard',
  setActiveTab: (tab) => set({ activeTab: tab }),
}));

export default useStore;
