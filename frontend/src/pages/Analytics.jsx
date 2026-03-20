import { useState, useEffect } from 'react';
import { api } from '../api';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

export default function Analytics() {
  const [profit, setProfit] = useState([]);
  const [stock, setStock] = useState({ products: [], materials: [] });
  const [trends, setTrends] = useState([]);
  const [days, setDays] = useState(30);
  const [period, setPeriod] = useState('daily');

  useEffect(() => { load(); }, [days, period]);

  useEffect(() => {
    const h = () => load();
    window.addEventListener('analytics-refresh', h);
    return () => window.removeEventListener('analytics-refresh', h);
  }, [days, period]);

  async function load() {
    const [p, s, t] = await Promise.all([
      api.getProfit(days),
      api.getStock(),
      api.getSalesTrends({ period, days: String(days) }),
    ]);
    setProfit(p);
    setStock(s);
    setTrends(t);
  }

  const totalProfit = profit.reduce((s, x) => s + x.profit, 0);
  const totalRevenue = profit.reduce((s, x) => s + x.revenue, 0);
  const fmt = (n) => '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Analytics</h1>
          <p className="text-gray-500 text-sm">Detailed business insights & profit analysis</p>
        </div>
        <div className="flex gap-3">
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="border rounded-lg px-3 py-2 text-sm bg-white">
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
            <option value={365}>1 year</option>
          </select>
          <select value={period} onChange={(e) => setPeriod(e.target.value)} className="border rounded-lg px-3 py-2 text-sm bg-white">
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
      </div>

      {/* Sales Trend */}
      <div className="bg-white rounded-xl shadow-sm border p-5">
        <h3 className="font-semibold text-gray-700 mb-4">Sales Trend ({period})</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={trends}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="period" tick={{ fontSize: 11 }} />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip formatter={(v, name) => name === 'total_revenue' ? fmt(v) : v} />
            <Legend />
            <Line yAxisId="left" type="monotone" dataKey="total_quantity" stroke="#3b82f6" name="Units Sold" strokeWidth={2} />
            <Line yAxisId="right" type="monotone" dataKey="total_revenue" stroke="#10b981" name="Revenue" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Profit by Product */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <h3 className="font-semibold text-gray-700 mb-2">Profit by Product</h3>
          <p className="text-sm text-gray-400 mb-4">Total: {fmt(totalRevenue)} revenue, {fmt(totalProfit)} profit</p>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={profit}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis />
              <Tooltip formatter={(v) => fmt(v)} />
              <Legend />
              <Bar dataKey="revenue" fill="#3b82f6" name="Revenue" radius={[4, 4, 0, 0]} />
              <Bar dataKey="cost" fill="#ef4444" name="Cost" radius={[4, 4, 0, 0]} />
              <Bar dataKey="profit" fill="#10b981" name="Profit" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl shadow-sm border p-5">
          <h3 className="font-semibold text-gray-700 mb-4">Profit Margins</h3>
          {profit.length === 0 ? (
            <p className="text-gray-400 text-sm py-12 text-center">No data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={profit.filter((p) => p.profit > 0)}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={110}
                  dataKey="profit"
                  nameKey="name"
                  label={({ name, margin_pct }) => `${name} (${margin_pct}%)`}
                >
                  {profit.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v) => fmt(v)} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Stock Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <h3 className="font-semibold text-gray-700 mb-4">Finished Goods Stock</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={stock.products} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="stock" fill="#8b5cf6" name="Stock" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl shadow-sm border p-5">
          <h3 className="font-semibold text-gray-700 mb-4">Raw Material Stock</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={stock.materials} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="current_stock" fill="#f59e0b" name="Stock" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
