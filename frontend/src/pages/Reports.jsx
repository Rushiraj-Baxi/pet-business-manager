import { useState, useEffect } from 'react';
import { api } from '../api';
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import {
  TrendingUp, TrendingDown, Users, Package, IndianRupee, AlertTriangle,
  Factory, FileText, ArrowUpRight, ArrowDownRight, Minus, ChevronDown, ChevronUp
} from 'lucide-react';

const TABS = [
  { id: 'monthly', label: 'Monthly Sales' },
  { id: 'top', label: 'Top Performers' },
  { id: 'fy', label: 'FY Comparison' },
  { id: 'customers', label: 'Customers' },
  { id: 'gst', label: 'GST Report' },
  { id: 'financial', label: 'P&L / Balance Sheet' },
  { id: 'purchases', label: 'Purchase Breakdown' },
  { id: 'rates', label: 'Rate Trends' },
  { id: 'projections', label: 'Projections' },
  { id: 'wastage', label: 'Wastage' },
  { id: 'machines', label: 'Machines' },
  { id: 'planning', label: 'Production Planning' },
];

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];
const fmt = (n) => n != null ? `₹${Number(n).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}` : '—';
const fmtD = (n) => n != null ? `₹${Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '—';
const pct = (n) => n != null ? `${n > 0 ? '+' : ''}${n}%` : '—';

function StatCard({ label, value, sub, trend, icon: Icon }) {
  const trendColor = trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-600' : 'text-gray-500';
  const TIcon = trend > 0 ? ArrowUpRight : trend < 0 ? ArrowDownRight : Minus;
  return (
    <div className="bg-white rounded-xl shadow-sm border p-4">
      <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
        {Icon && <Icon size={14} />} {label}
      </div>
      <div className="text-xl font-bold text-gray-900">{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
      {trend != null && (
        <div className={`flex items-center gap-1 text-xs mt-1 ${trendColor}`}>
          <TIcon size={12} /> {pct(trend)}
        </div>
      )}
    </div>
  );
}

function CollapsibleSection({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="bg-white rounded-xl shadow-sm border">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between p-4 text-left font-semibold text-gray-900 hover:bg-gray-50">
        {title}
        {open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
      </button>
      {open && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
}

// ─── Monthly Sales Tab ──────────────────────────────────────────
function MonthlySales() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.getReport('monthly-sales?months=12').then(setData).finally(() => setLoading(false)); }, []);
  if (loading) return <Loader />;
  if (!data.length) return <Empty msg="No sales data yet" />;

  const chartData = data.map(m => ({ month: m.month, revenue: m.total_revenue, qty: m.total_qty }));
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm border p-4">
        <h3 className="font-semibold mb-3">Revenue Trend</h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip formatter={(v) => fmt(v)} />
            <Area type="monotone" dataKey="revenue" fill="#3b82f6" fillOpacity={0.2} stroke="#3b82f6" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      {data.map(m => (
        <CollapsibleSection key={m.month} title={`${m.month} — ${fmt(m.total_revenue)} (${m.total_qty} units)`} defaultOpen={false}>
          <table className="w-full text-sm">
            <thead><tr className="text-left text-gray-500 border-b"><th className="pb-2">Product</th><th>Type</th><th className="text-right">Qty</th><th className="text-right">Revenue</th><th className="text-right">Taxable</th></tr></thead>
            <tbody>
              {m.products.map((p, i) => (
                <tr key={i} className="border-b last:border-0"><td className="py-1.5">{p.name}</td><td className="capitalize">{p.type}</td><td className="text-right">{p.qty.toLocaleString()}</td><td className="text-right">{fmt(p.revenue)}</td><td className="text-right">{fmt(p.taxable)}</td></tr>
              ))}
            </tbody>
          </table>
        </CollapsibleSection>
      ))}
    </div>
  );
}

// ─── Top Performers Tab ──────────────────────────────────────────
function TopPerformers() {
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.getReport('top-performers?days=90').then(setData).finally(() => setLoading(false)); }, []);
  if (loading) return <Loader />;

  return (
    <div className="space-y-6">
      {Object.entries(data).map(([type, products]) => (
        <div key={type} className="bg-white rounded-xl shadow-sm border p-4">
          <h3 className="font-semibold mb-3 capitalize">{type}s — Top 5</h3>
          <div className="space-y-2">
            {products.map((p, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-sm ${i === 0 ? 'bg-yellow-500' : i === 1 ? 'bg-gray-400' : i === 2 ? 'bg-amber-700' : 'bg-gray-300'}`}>{i + 1}</div>
                <div className="flex-1">
                  <div className="font-medium text-sm">{p.name}</div>
                  <div className="text-xs text-gray-500">{p.variant} — {p.quantity.toLocaleString()} units</div>
                </div>
                <div className="font-semibold text-sm">{fmt(p.revenue)}</div>
              </div>
            ))}
            {!products.length && <div className="text-sm text-gray-400">No data</div>}
          </div>
        </div>
      ))}
      {!Object.keys(data).length && <Empty msg="No sales data yet" />}
    </div>
  );
}

// ─── FY Comparison Tab ───────────────────────────────────────────
function FYComparison() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.getReport('fy-comparison').then(setData).finally(() => setLoading(false)); }, []);
  if (loading) return <Loader />;
  if (!data) return <Empty msg="No data" />;

  const metrics = [
    { key: 'revenue', label: 'Revenue', icon: IndianRupee },
    { key: 'units_sold', label: 'Units Sold', icon: Package },
    { key: 'gross_profit', label: 'Gross Profit', icon: TrendingUp },
    { key: 'net_profit', label: 'Net Profit', icon: TrendingUp },
    { key: 'expenses', label: 'Expenses', icon: IndianRupee },
    { key: 'purchases', label: 'Purchases', icon: IndianRupee },
    { key: 'units_produced', label: 'Units Produced', icon: Factory },
    { key: 'wastage_kg', label: 'Wastage (kg)', icon: AlertTriangle },
  ];

  const chartBarData = metrics.map(m => ({
    name: m.label,
    [data.current_fy]: data.current[m.key],
    [data.previous_fy]: data.previous[m.key],
  }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {metrics.map(m => (
          <StatCard
            key={m.key}
            label={m.label}
            value={['revenue', 'gross_profit', 'net_profit', 'expenses', 'purchases', 'cogs'].includes(m.key) ? fmt(data.current[m.key]) : data.current[m.key]?.toLocaleString()}
            sub={`Prev: ${['revenue', 'gross_profit', 'net_profit', 'expenses', 'purchases', 'cogs'].includes(m.key) ? fmt(data.previous[m.key]) : data.previous[m.key]?.toLocaleString()}`}
            trend={data.growth[m.key]}
            icon={m.icon}
          />
        ))}
      </div>
      <div className="bg-white rounded-xl shadow-sm border p-4">
        <h3 className="font-semibold mb-3">{data.current_fy} vs {data.previous_fy}</h3>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={chartBarData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" height={60} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip formatter={(v) => v?.toLocaleString()} />
            <Legend />
            <Bar dataKey={data.current_fy} fill="#3b82f6" />
            <Bar dataKey={data.previous_fy} fill="#94a3b8" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ─── Customers Tab ───────────────────────────────────────────────
function CustomersTab() {
  const [analysis, setAnalysis] = useState(null);
  const [loyalty, setLoyalty] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([api.getReport('customer-analysis?days=365'), api.getReport('customer-loyalty')])
      .then(([a, l]) => { setAnalysis(a); setLoyalty(l); })
      .finally(() => setLoading(false));
  }, []);
  if (loading) return <Loader />;

  return (
    <div className="space-y-6">
      {/* Overall customer rankings */}
      <div className="bg-white rounded-xl shadow-sm border p-4">
        <h3 className="font-semibold mb-3">Top Customers by Revenue</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-gray-500 border-b"><th className="pb-2">#</th><th>Customer</th><th className="text-right">Orders</th><th className="text-right">Qty</th><th className="text-right">Revenue</th><th>Products</th></tr></thead>
            <tbody>
              {(analysis?.overall || []).slice(0, 15).map((c, i) => (
                <tr key={i} className="border-b last:border-0"><td className="py-1.5 font-medium">{i + 1}</td><td>{c.customer}</td><td className="text-right">{c.orders}</td><td className="text-right">{c.total_qty.toLocaleString()}</td><td className="text-right font-medium">{fmt(c.total_revenue)}</td><td className="text-xs text-gray-500">{c.products.slice(0, 3).join(', ')}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Top customer per product */}
      {analysis?.top_per_product && Object.keys(analysis.top_per_product).length > 0 && (
        <CollapsibleSection title="Top Customer Per Product" defaultOpen={false}>
          <div className="space-y-4">
            {Object.entries(analysis.top_per_product).map(([product, custs]) => (
              <div key={product}>
                <div className="font-medium text-sm mb-1">{product}</div>
                <div className="pl-3 space-y-1">
                  {custs.map((c, i) => (
                    <div key={i} className="flex justify-between text-sm text-gray-600">
                      <span>{i + 1}. {c.customer}</span>
                      <span>{c.orders} orders — {fmt(c.total_revenue)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Customer loyalty */}
      <div className="bg-white rounded-xl shadow-sm border p-4">
        <h3 className="font-semibold mb-3">Customer Loyalty & Duration</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-gray-500 border-b"><th className="pb-2">Customer</th><th>First Order</th><th>Last Order</th><th>Duration</th><th className="text-right">Orders</th><th className="text-right">Avg Value</th><th className="text-right">Total</th></tr></thead>
            <tbody>
              {loyalty.slice(0, 20).map((c, i) => (
                <tr key={i} className="border-b last:border-0">
                  <td className="py-1.5 font-medium">{c.customer}</td>
                  <td className="text-gray-500">{c.first_order}</td>
                  <td className="text-gray-500">{c.last_order}</td>
                  <td><span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-xs">{c.duration_label}</span></td>
                  <td className="text-right">{c.total_orders}</td>
                  <td className="text-right">{fmt(c.avg_order_value)}</td>
                  <td className="text-right font-medium">{fmt(c.total_revenue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── GST Report Tab ──────────────────────────────────────────────
function GSTReport() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.getReport('gst-report?months=12').then(setData).finally(() => setLoading(false)); }, []);
  if (loading) return <Loader />;
  if (!data) return <Empty msg="No data" />;

  const hasBreakdown = data.totals.igst > 0 || data.totals.sgst > 0 || data.totals.cgst > 0;

  return (
    <div className="space-y-6">
      <div className={`grid grid-cols-2 ${hasBreakdown ? 'md:grid-cols-5' : 'md:grid-cols-3'} gap-3`}>
        <StatCard label="Taxable Amount" value={fmt(data.totals.taxable)} icon={IndianRupee} />
        <StatCard label="Total GST" value={fmt(data.totals.total_gst)} icon={IndianRupee} />
        {hasBreakdown && <StatCard label="IGST" value={fmt(data.totals.igst)} icon={IndianRupee} />}
        {hasBreakdown && <StatCard label="SGST" value={fmt(data.totals.sgst)} icon={IndianRupee} />}
        {hasBreakdown && <StatCard label="CGST" value={fmt(data.totals.cgst)} icon={IndianRupee} />}
        {!hasBreakdown && <StatCard label="Invoice Value" value={fmt(data.totals.total_invoice)} icon={IndianRupee} />}
      </div>
      {!hasBreakdown && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
          GST breakdown (IGST/SGST/CGST) is not available for older sales. Total GST is derived from Invoice Value − Taxable Amount. New sales with GST fields will show the full breakdown.
        </div>
      )}
      <div className="bg-white rounded-xl shadow-sm border p-4">
        <h3 className="font-semibold mb-3">Monthly GST</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data.monthly}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip formatter={(v) => fmtD(v)} />
            <Legend />
            {hasBreakdown ? (
              <>
                <Bar dataKey="igst" fill="#3b82f6" name="IGST" stackId="gst" />
                <Bar dataKey="sgst" fill="#10b981" name="SGST" stackId="gst" />
                <Bar dataKey="cgst" fill="#f59e0b" name="CGST" stackId="gst" />
              </>
            ) : (
              <Bar dataKey="total_gst" fill="#8b5cf6" name="Total GST" radius={[4, 4, 0, 0]} />
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="bg-white rounded-xl shadow-sm border p-4">
        <h3 className="font-semibold mb-3">Monthly Detail</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-gray-500 border-b">
              <th className="pb-2">Month</th><th className="text-right">Sales</th><th className="text-right">Taxable</th>
              {hasBreakdown && <><th className="text-right">IGST</th><th className="text-right">SGST</th><th className="text-right">CGST</th></>}
              <th className="text-right">Total GST</th><th className="text-right">Invoice Value</th>
            </tr></thead>
            <tbody>
              {data.monthly.map((m, i) => (
                <tr key={i} className="border-b last:border-0">
                  <td className="py-1.5">{m.month}</td>
                  <td className="text-right">{m.sales_count}</td>
                  <td className="text-right">{fmtD(m.taxable)}</td>
                  {hasBreakdown && <><td className="text-right">{fmtD(m.igst)}</td><td className="text-right">{fmtD(m.sgst)}</td><td className="text-right">{fmtD(m.cgst)}</td></>}
                  <td className="text-right font-medium">{fmtD(m.total_gst)}</td>
                  <td className="text-right">{fmtD(m.invoice_value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Financial Statements Tab ─────────────────────────────────────
function FinancialStatements() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.getReport('financial-statements').then(setData).finally(() => setLoading(false)); }, []);
  if (loading) return <Loader />;
  if (!data) return <Empty msg="No data" />;

  const { pnl, balance_sheet, ledger } = data;
  return (
    <div className="space-y-6">
      {/* P&L */}
      <div className="bg-white rounded-xl shadow-sm border p-5">
        <h3 className="font-bold text-lg mb-4">Profit & Loss Statement</h3>
        <div className="space-y-2 text-sm">
          <Row label="Revenue" value={fmtD(pnl.revenue)} bold />
          <Row label="Less: COGS" value={`(${fmtD(pnl.cogs)})`} indent />
          <div className="border-t my-2" />
          <Row label="Gross Profit" value={fmtD(pnl.gross_profit)} bold color={pnl.gross_profit >= 0 ? 'green' : 'red'} />
          <div className="mt-3 mb-1 font-medium text-gray-500">Operating Expenses</div>
          {Object.entries(pnl.expenses).map(([cat, amt]) => (
            <Row key={cat} label={cat} value={fmtD(amt)} indent />
          ))}
          <Row label="Total Expenses" value={`(${fmtD(pnl.total_expenses)})`} indent bold />
          <div className="border-t my-2" />
          <Row label="Net Profit" value={fmtD(pnl.net_profit)} bold color={pnl.net_profit >= 0 ? 'green' : 'red'} />
          <Row label="Net Margin" value={`${pnl.net_margin_pct}%`} indent />
        </div>
      </div>

      {/* Balance Sheet */}
      <div className="bg-white rounded-xl shadow-sm border p-5">
        <h3 className="font-bold text-lg mb-4">Balance Sheet Summary</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="font-semibold text-green-700 mb-2">Assets</div>
            <Row label="Product Inventory" value={fmtD(balance_sheet.assets.product_inventory)} indent />
            <Row label="Material Inventory" value={fmtD(balance_sheet.assets.material_inventory)} indent />
            <div className="border-t my-2" />
            <Row label="Total Assets" value={fmtD(balance_sheet.assets.total_assets)} bold />
          </div>
          <div>
            <div className="font-semibold text-red-700 mb-2">Liabilities</div>
            {balance_sheet.liabilities.items.map((l, i) => (
              <Row key={i} label={l.label} value={fmtD(l.amount)} indent />
            ))}
            <div className="border-t my-2" />
            <Row label="Total Liabilities" value={fmtD(balance_sheet.liabilities.total_liabilities)} bold />
            <div className="mt-4 font-semibold text-blue-700 mb-2">Equity</div>
            <Row label="Retained Earnings" value={fmtD(balance_sheet.equity.retained_earnings)} indent />
          </div>
        </div>
      </div>

      {/* Ledger */}
      <div className="bg-white rounded-xl shadow-sm border p-4">
        <h3 className="font-bold text-lg mb-3">Monthly Ledger</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-gray-500 border-b"><th className="pb-2">Month</th><th className="text-right">Sales</th><th className="text-right">Purchases</th><th className="text-right">Expenses</th><th className="text-right">Net</th></tr></thead>
            <tbody>
              {ledger.map((l, i) => (
                <tr key={i} className="border-b last:border-0">
                  <td className="py-1.5">{l.month}</td>
                  <td className="text-right text-green-700">{fmtD(l.sales)}</td>
                  <td className="text-right text-red-600">{fmtD(l.purchases)}</td>
                  <td className="text-right text-red-600">{fmtD(l.expenses)}</td>
                  <td className={`text-right font-medium ${l.net >= 0 ? 'text-green-700' : 'text-red-600'}`}>{fmtD(l.net)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, bold, indent, color }) {
  return (
    <div className={`flex justify-between py-0.5 ${indent ? 'pl-4' : ''} ${bold ? 'font-semibold' : ''}`}>
      <span className="text-gray-700">{label}</span>
      <span className={color === 'green' ? 'text-green-700' : color === 'red' ? 'text-red-600' : ''}>{value}</span>
    </div>
  );
}

// ─── Purchase Breakdown Tab ──────────────────────────────────────
function PurchaseBreakdown() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.getReport('purchase-breakdown?days=365').then(setData).finally(() => setLoading(false)); }, []);
  if (loading) return <Loader />;
  if (!data) return <Empty msg="No purchase data" />;

  const pieData = data.by_category.map((c, i) => ({ name: c.category, value: c.total_cost, fill: COLORS[i % COLORS.length] }));
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <h3 className="font-semibold mb-3">By Category</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(v) => fmt(v)} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <h3 className="font-semibold mb-3">Category Summary</h3>
          <div className="space-y-3">
            {data.by_category.map((c, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                <div className="flex-1">
                  <div className="font-medium text-sm capitalize">{c.category.replace('_', ' ')}</div>
                  <div className="text-xs text-gray-500">{c.purchases} purchases — {c.materials.length} materials</div>
                </div>
                <div className="font-semibold text-sm">{fmt(c.total_cost)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="bg-white rounded-xl shadow-sm border p-4">
        <h3 className="font-semibold mb-3">By Material</h3>
        <table className="w-full text-sm">
          <thead><tr className="text-left text-gray-500 border-b"><th className="pb-2">Material</th><th>Category</th><th className="text-right">Qty</th><th>Unit</th><th className="text-right">Avg Rate</th><th className="text-right">Total Cost</th></tr></thead>
          <tbody>
            {data.by_material.map((m, i) => (
              <tr key={i} className="border-b last:border-0"><td className="py-1.5">{m.name}</td><td className="capitalize text-gray-500">{m.category.replace('_', ' ')}</td><td className="text-right">{m.total_qty.toLocaleString()}</td><td>{m.unit}</td><td className="text-right">{fmtD(m.avg_rate)}</td><td className="text-right font-medium">{fmt(m.total_cost)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Rate Trends Tab ─────────────────────────────────────────────
function RateTrends() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.getReport('rate-trends?days=365').then(setData).finally(() => setLoading(false)); }, []);
  if (loading) return <Loader />;
  if (!data) return <Empty msg="No data" />;

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="bg-white rounded-xl shadow-sm border p-4">
        <h3 className="font-semibold mb-3">Rate Changes Summary</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {data.summary.map((s, i) => (
            <div key={i} className="p-3 rounded-lg border bg-gray-50">
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded ${s.type === 'purchase' ? 'bg-orange-100 text-orange-700' : 'bg-blue-100 text-blue-700'}`}>{s.type}</span>
                <span className="font-medium text-sm">{s.name}</span>
              </div>
              <div className="flex items-center gap-2 mt-2 text-sm">
                <span className="text-gray-500">{fmtD(s.first_rate)}</span>
                <span>→</span>
                <span className="font-medium">{fmtD(s.latest_rate)}</span>
                <span className={`text-xs font-medium ${s.change_pct > 0 ? 'text-red-600' : s.change_pct < 0 ? 'text-green-600' : 'text-gray-500'}`}>{pct(s.change_pct)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Purchase rate charts */}
      {Object.entries(data.purchase_trends).map(([name, entries]) => (
        <CollapsibleSection key={name} title={`Purchase: ${name}`} defaultOpen={false}>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={entries}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Line type="monotone" dataKey="rate" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </CollapsibleSection>
      ))}

      {/* Sale rate charts */}
      {Object.entries(data.sale_trends).map(([name, entries]) => (
        <CollapsibleSection key={name} title={`Sale: ${name}`} defaultOpen={false}>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={entries}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Line type="monotone" dataKey="rate" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </CollapsibleSection>
      ))}
    </div>
  );
}

// ─── Projections Tab ─────────────────────────────────────────────
function Projections() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.getReport('projections').then(setData).finally(() => setLoading(false)); }, []);
  if (loading) return <Loader />;
  if (!data) return <Empty msg="No data" />;

  const chartData = [
    ...data.historical.map(h => ({ month: h.month, revenue: h.revenue, type: 'actual' })),
    ...data.projections.map(p => ({ month: p.month, projected: p.projected_revenue, type: 'projected' })),
  ];
  // Merge for combined chart
  const merged = {};
  data.historical.forEach(h => { merged[h.month] = { month: h.month, actual: h.revenue }; });
  data.projections.forEach(p => { merged[p.month] = { ...merged[p.month], month: p.month, projected: p.projected_revenue }; });
  const mergedData = Object.values(merged).sort((a, b) => a.month.localeCompare(b.month));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {data.projections.map((p, i) => (
          <StatCard key={i} label={p.month} value={fmt(p.projected_revenue)} sub={`~${p.projected_units.toLocaleString()} units`} icon={TrendingUp} />
        ))}
      </div>
      <div className="bg-white rounded-xl shadow-sm border p-4">
        <h3 className="font-semibold mb-3">Revenue: Actual vs Projected</h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={mergedData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip formatter={(v) => fmt(v)} />
            <Legend />
            <Area type="monotone" dataKey="actual" fill="#3b82f6" fillOpacity={0.2} stroke="#3b82f6" strokeWidth={2} name="Actual" />
            <Area type="monotone" dataKey="projected" fill="#10b981" fillOpacity={0.2} stroke="#10b981" strokeWidth={2} strokeDasharray="5 5" name="Projected" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ─── Wastage Tab ─────────────────────────────────────────────────
function WastageTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.getReport('wastage-analysis?days=90').then(setData).finally(() => setLoading(false)); }, []);
  if (loading) return <Loader />;
  if (!data) return <Empty msg="No production data" />;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Total RM Used" value={`${data.summary.total_rm_used} kg`} icon={Package} />
        <StatCard label="Total Wastage" value={`${data.summary.total_wastage} kg`} icon={AlertTriangle} />
        <StatCard label="Overall Wastage %" value={`${data.summary.overall_pct}%`} icon={TrendingDown} />
      </div>
      <div className="bg-white rounded-xl shadow-sm border p-4">
        <h3 className="font-semibold mb-3">Wastage Trend</h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={data.daily_trend}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Line type="monotone" dataKey="wastage_pct" stroke="#ef4444" strokeWidth={2} name="Wastage %" />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <h3 className="font-semibold mb-3">By Product</h3>
          {data.by_product.map((p, i) => (
            <div key={i} className="flex justify-between py-1.5 border-b last:border-0 text-sm">
              <span>{p.name}</span>
              <span className="font-medium">{p.wastage_pct}% ({p.total_wastage} kg)</span>
            </div>
          ))}
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <h3 className="font-semibold mb-3">By Material</h3>
          {data.by_material.map((m, i) => (
            <div key={i} className="flex justify-between py-1.5 border-b last:border-0 text-sm">
              <span>{m.name}</span>
              <span className="font-medium">{m.wastage_pct}% ({m.total_wastage} kg)</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Machines Tab ────────────────────────────────────────────────
function MachinesTab() {
  const [machines, setMachines] = useState([]);
  const [efficiency, setEfficiency] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ name: '', machine_type: '', capacity_per_hour: '', status: 'active' });
  const [showForm, setShowForm] = useState(false);

  const load = () => {
    Promise.all([api.getMachines(), api.getReport('machine-efficiency?days=30')])
      .then(([m, e]) => { setMachines(m); setEfficiency(e); })
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    await api.createMachine({ name: form.name, machine_type: form.machine_type, capacity_per_hour: parseInt(form.capacity_per_hour) || 0, status: form.status });
    setForm({ name: '', machine_type: '', capacity_per_hour: '', status: 'active' });
    setShowForm(false);
    load();
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this machine?')) return;
    await api.deleteMachine(id);
    load();
  };

  if (loading) return <Loader />;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="font-semibold">Machines ({machines.length})</h3>
        <button onClick={() => setShowForm(!showForm)} className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">+ Add Machine</button>
      </div>
      {showForm && (
        <form onSubmit={handleAdd} className="bg-white rounded-xl border p-4 flex flex-wrap gap-3 items-end">
          <div><label className="text-xs text-gray-500">Name</label><input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="block w-40 border rounded px-2 py-1.5 text-sm" required /></div>
          <div><label className="text-xs text-gray-500">Type</label><input value={form.machine_type} onChange={e => setForm({ ...form, machine_type: e.target.value })} className="block w-40 border rounded px-2 py-1.5 text-sm" placeholder="injection_molding" /></div>
          <div><label className="text-xs text-gray-500">Capacity/hr</label><input type="number" value={form.capacity_per_hour} onChange={e => setForm({ ...form, capacity_per_hour: e.target.value })} className="block w-28 border rounded px-2 py-1.5 text-sm" /></div>
          <div><label className="text-xs text-gray-500">Status</label><select value={form.status} onChange={e => setForm({ ...form, status: e.target.value })} className="block border rounded px-2 py-1.5 text-sm"><option value="active">Active</option><option value="maintenance">Maintenance</option><option value="inactive">Inactive</option></select></div>
          <button type="submit" className="px-4 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700">Add</button>
        </form>
      )}

      {/* Efficiency cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {efficiency.filter(e => e.id !== null).map((m) => (
          <div key={m.id} className="bg-white rounded-xl shadow-sm border p-4">
            <div className="flex justify-between items-start">
              <div>
                <div className="font-semibold">{m.name}</div>
                <div className="text-xs text-gray-500">{m.type || 'General'}</div>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded ${m.status === 'active' ? 'bg-green-100 text-green-700' : m.status === 'maintenance' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-500'}`}>{m.status}</span>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-3 text-sm">
              <div><span className="text-gray-500">Produced</span><div className="font-semibold">{m.total_produced.toLocaleString()}</div></div>
              <div><span className="text-gray-500">Hours Run</span><div className="font-semibold">{m.total_hours}</div></div>
              <div><span className="text-gray-500">Efficiency</span><div className="font-semibold">{m.efficiency_pct || 0}%</div></div>
              <div><span className="text-gray-500">Wastage</span><div className="font-semibold">{m.wastage_pct || 0}%</div></div>
            </div>
            <button onClick={() => handleDelete(m.id)} className="mt-3 text-xs text-red-500 hover:text-red-700">Delete</button>
          </div>
        ))}
      </div>
      {!machines.length && <Empty msg="No machines added yet" />}
    </div>
  );
}

// ─── Production Planning Tab ─────────────────────────────────────
function ProductionPlanning() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.getReport('production-planning').then(setData).finally(() => setLoading(false)); }, []);
  if (loading) return <Loader />;
  if (!data) return <Empty msg="No products yet" />;

  const urgencyColor = { critical: 'bg-red-100 text-red-700', high: 'bg-orange-100 text-orange-700', medium: 'bg-yellow-100 text-yellow-700', normal: 'bg-green-100 text-green-700' };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm border p-4">
        <h3 className="font-semibold mb-3">Production Suggestions</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-gray-500 border-b"><th className="pb-2">Product</th><th>Type</th><th className="text-right">Stock</th><th className="text-right">30d Demand</th><th className="text-right">Avg Monthly</th><th className="text-right">Days of Stock</th><th className="text-right">Suggested Qty</th><th>Urgency</th><th className="text-right">Wastage %</th></tr></thead>
            <tbody>
              {data.suggestions.map((s, i) => (
                <tr key={i} className="border-b last:border-0">
                  <td className="py-2 font-medium">{s.product}</td>
                  <td className="capitalize">{s.type}</td>
                  <td className="text-right">{s.current_stock.toLocaleString()}</td>
                  <td className="text-right">{s.demand_30d.toLocaleString()}</td>
                  <td className="text-right">{s.demand_avg_monthly.toLocaleString()}</td>
                  <td className="text-right">{s.days_of_stock ?? '∞'}</td>
                  <td className="text-right font-semibold">{s.suggested_production.toLocaleString()}</td>
                  <td><span className={`text-xs px-2 py-0.5 rounded ${urgencyColor[s.urgency]}`}>{s.urgency}</span></td>
                  <td className="text-right">{s.wastage_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border p-4">
        <h3 className="font-semibold mb-3">Material Availability</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {data.material_status.map((m, i) => (
            <div key={i} className={`p-3 rounded-lg border ${m.needs_reorder ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'}`}>
              <div className="font-medium text-sm">{m.name}</div>
              <div className="text-xs text-gray-500 capitalize">{m.category.replace('_', ' ')}</div>
              <div className="flex justify-between mt-1 text-sm">
                <span>Stock: {m.stock} {m.unit}</span>
                {m.needs_reorder && <span className="text-red-600 text-xs font-medium">REORDER</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Helpers ─────────────────────────────────────────────────────
function Loader() {
  return <div className="flex items-center justify-center h-40"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>;
}
function Empty({ msg }) {
  return <div className="text-center text-gray-400 py-12">{msg}</div>;
}

// ─── Main Reports Page ───────────────────────────────────────────
export default function Reports() {
  const [tab, setTab] = useState('monthly');

  const TabContent = {
    monthly: MonthlySales,
    top: TopPerformers,
    fy: FYComparison,
    customers: CustomersTab,
    gst: GSTReport,
    financial: FinancialStatements,
    purchases: PurchaseBreakdown,
    rates: RateTrends,
    projections: Projections,
    wastage: WastageTab,
    machines: MachinesTab,
    planning: ProductionPlanning,
  }[tab];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Reports & Analytics</h2>
      <div className="flex flex-wrap gap-1.5 mb-6">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${tab === t.id ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border hover:bg-gray-50'}`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <TabContent />
    </div>
  );
}
