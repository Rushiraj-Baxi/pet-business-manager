// In dev, Vite proxy handles /api → backend. In production, use full backend URL.
const BASE = import.meta.env.VITE_API_URL || '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export const api = {
  // Products
  getProducts: (type) => request(`/products${type ? `?type=${type}` : ''}`),
  createProduct: (data) => request('/products', { method: 'POST', body: JSON.stringify(data) }),
  updateProduct: (id, data) => request(`/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteProduct: (id) => request(`/products/${id}`, { method: 'DELETE' }),

  // Materials
  getMaterials: () => request('/materials'),
  createMaterial: (data) => request('/materials', { method: 'POST', body: JSON.stringify(data) }),
  updateMaterial: (id, data) => request(`/materials/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteMaterial: (id) => request(`/materials/${id}`, { method: 'DELETE' }),
  getPurchases: () => request('/materials/purchases'),
  createPurchase: (data) => request('/materials/purchases', { method: 'POST', body: JSON.stringify(data) }),

  // Sales
  getSales: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/sales${q ? `?${q}` : ''}`);
  },
  createSale: (data) => request('/sales', { method: 'POST', body: JSON.stringify(data) }),
  deleteSale: (id) => request(`/sales/${id}`, { method: 'DELETE' }),
  getSalesTrends: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/sales/trends${q ? `?${q}` : ''}`);
  },

  // Production
  getProductions: () => request('/production'),
  createProduction: (data) => request('/production', { method: 'POST', body: JSON.stringify(data) }),
  deleteProduction: (id) => request(`/production/${id}`, { method: 'DELETE' }),

  // Analytics
  getDashboard: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/analytics/dashboard${q ? `?${q}` : ''}`);
  },
  getProfit: (days = 30) => request(`/analytics/profit?days=${days}`),
  getStock: () => request('/analytics/stock'),
  getChartData: (dataSource, days = 30) => request(`/analytics/chart-data/${dataSource}?days=${days}`),

  // Chat
  sendChat: (message) => request('/chat', { method: 'POST', body: JSON.stringify({ message }) }),
  getChatHistory: () => request('/chat/history'),
  clearChat: () => request('/chat/clear', { method: 'POST' }),
  clearAllData: () => request('/clear-all', { method: 'POST' }),

  // Charts
  getCharts: (page) => request(`/charts${page ? `?page=${page}` : ''}`),
  createChart: (data) => request('/charts', { method: 'POST', body: JSON.stringify(data) }),
  updateChart: (id, data) => request(`/charts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteChart: (id) => request(`/charts/${id}`, { method: 'DELETE' }),

  // Business Entries (costs & liabilities)
  getBusinessEntries: () => request('/business-entries'),
  updateBusinessEntry: (id, data) => request(`/business-entries/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  createBusinessEntry: (data) => request('/business-entries', { method: 'POST', body: JSON.stringify(data) }),
  deleteBusinessEntry: (id) => request(`/business-entries/${id}`, { method: 'DELETE' }),

  // Upload
  uploadFile: async (file) => {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${BASE}/upload`, { method: 'POST', body: fd });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
  },

  // Reports
  getReport: (endpoint) => request(`/reports/${endpoint}`),

  // Machines
  getMachines: () => request('/machines'),
  createMachine: (data) => request('/machines', { method: 'POST', body: JSON.stringify(data) }),
  updateMachine: (id, data) => request(`/machines/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteMachine: (id) => request(`/machines/${id}`, { method: 'DELETE' }),

  // Invoice Folder Upload
  uploadInvoices: async (files, invoiceType) => {
    const fd = new FormData();
    for (const file of files) {
      fd.append('files', file);
    }
    fd.append('invoice_type', invoiceType);
    const res = await fetch(`${BASE}/invoices/upload`, { method: 'POST', body: fd });
    if (!res.ok) throw new Error('Invoice upload failed');
    return res.json();
  },
};
