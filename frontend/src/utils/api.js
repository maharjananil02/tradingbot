import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Dashboard
export const getDashboard = () => api.get('/dashboard');

// Positions
export const getPositions = (isPaper = false) =>
  api.get(`/positions?is_paper=${isPaper}`);
export const createPosition = (data) => api.post('/positions', data);
export const updatePosition = (id, data) => api.put(`/positions/${id}`, data);
export const closePosition = (id, exitPrice) =>
  api.delete(`/positions/${id}?exit_price=${exitPrice}`);

// Signals
export const getSignals = (date = null) =>
  api.get(`/signals${date ? `?target_date=${date}` : ''}`);
export const generateSignals = () => api.post('/signals/generate');

// Trades
export const getTrades = (isPaper = false, limit = 50) =>
  api.get(`/trades?is_paper=${isPaper}&limit=${limit}`);
export const getTradeStats = (isPaper = false) =>
  api.get(`/trades/stats?is_paper=${isPaper}`);
export const updateTrade = (id, data) => api.put(`/trades/${id}`, data);
export const deleteTrade = (id) => api.delete(`/trades/${id}`);

// Risk
export const getRiskMetrics = (isPaper = false) =>
  api.get(`/risk?is_paper=${isPaper}`);

// Performance
export const getPerformance = (days = 30, isPaper = false) =>
  api.get(`/performance?days=${days}&is_paper=${isPaper}`);

// Alerts
export const getAlerts = (limit = 20) => api.get(`/alerts?limit=${limit}`);
export const markAlertRead = (id) => api.put(`/alerts/${id}/read`);

// Market Data
export const getMarketStocks = () => api.get('/market/stocks');
export const getLivePrices = () => api.get('/market/live');
export const getMarketSummary = () => api.get('/market/summary');
export const getTopGainers = () => api.get('/market/gainers');
export const getTopLosers = () => api.get('/market/losers');
export const fetchPriceHistory = (days = 100, mode = 'all') =>
  api.post(`/market/fetch-history?days=${days}&mode=${mode}`);

// Backtest
export const runBacktest = (params) => api.post('/backtest', params);

// Settings
export const getSettings = () => api.get('/settings');
export const toggleAutoExecute = (enabled) =>
  api.put(`/settings/auto-execute?enabled=${enabled}`);
export const resetAllData = () => api.post('/settings/reset');

// Health
export const getHealth = () => axios.get('/health');

export default api;

