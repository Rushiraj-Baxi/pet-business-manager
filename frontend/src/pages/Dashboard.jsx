import { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area,
} from 'recharts';
import { TrendingUp, TrendingDown, Package, IndianRupee, Percent, Upload, CheckCircle, XCircle, Trash2, Receipt, FolderOpen, FileText, X, RefreshCw } from 'lucide-react';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

function StatCard({ title, value, icon: Icon, color = 'blue', sub }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    red: 'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
  };
  return (
    <div className="bg-white rounded-xl shadow-sm border p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
          {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
        </div>
        <div className={`p-3 rounded-lg ${colors[color]}`}>
          <Icon size={22} />
        </div>
      </div>
    </div>
  );
}

function DynamicChart({ chart, days, onDelete }) {
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.getChartData(chart.data_source, days).then((d) => {
      let filtered = d;
      if (chart.config?.filter_type) {
        filtered = d.filter((row) => row.type === chart.config.filter_type);
      }
      // For non-time-series data with too many items, keep top 12
      const isTimeSeries = chart.data_source === 'daily_trend';
      if (!isTimeSeries && filtered.length > 12) {
        const key = chart.config?.data_key || 'revenue';
        const sorted = [...filtered].sort((a, b) => (b[key] || 0) - (a[key] || 0));
        filtered = sorted.slice(0, 12);
      }
      setChartData(filtered);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [chart.data_source, chart.config?.filter_type, days]);

  if (loading) return <div className="bg-white rounded-xl shadow-sm border p-5"><p className="text-gray-400 text-sm py-12 text-center">Loading chart...</p></div>;

  const cfg = chart.config || {};
  const dataKey = cfg.data_key || 'revenue';
  const secondKey = cfg.second_data_key;
  const color1 = cfg.color || '#3b82f6';
  const color2 = cfg.second_color || '#10b981';
  const nameKey = cfg.name_key || 'name';
  const showLegend = cfg.show_legend !== false;

  const noData = !chartData || chartData.length === 0;

  const renderInner = () => {
    if (noData) return <p className="text-gray-400 text-sm py-12 text-center">No data available</p>;

    if (chart.chart_type === 'pie') {
      // Limit pie to top 8 items, group rest as "Others"
      const sorted = [...chartData].sort((a, b) => (b[dataKey] || 0) - (a[dataKey] || 0));
      const top = sorted.slice(0, 8);
      const rest = sorted.slice(8);
      const pieData = rest.length > 0
        ? [...top, { [nameKey]: 'Others', [dataKey]: rest.reduce((s, r) => s + (r[dataKey] || 0), 0) }]
        : top;
      return (
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={100} dataKey={dataKey} nameKey={nameKey}
              label={({ [nameKey]: n, percent }) => percent > 0.03 ? `${n} (${(percent * 100).toFixed(0)}%)` : ''}>
              {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
            <Tooltip formatter={(v) => Number(v).toLocaleString('en-IN')} />
            {showLegend && <Legend />}
          </PieChart>
        </ResponsiveContainer>
      );
    }

    if (chart.chart_type === 'line') {
      return (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={nameKey} tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip formatter={(v) => Number(v).toLocaleString('en-IN')} />
            {showLegend && <Legend />}
            <Line type="monotone" dataKey={dataKey} stroke={color1} name={dataKey} strokeWidth={2} />
            {secondKey && <Line type="monotone" dataKey={secondKey} stroke={color2} name={secondKey} strokeWidth={2} />}
          </LineChart>
        </ResponsiveContainer>
      );
    }

    if (chart.chart_type === 'area') {
      return (
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={nameKey} tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip formatter={(v) => Number(v).toLocaleString('en-IN')} />
            {showLegend && <Legend />}
            <Area type="monotone" dataKey={dataKey} stroke={color1} fill={color1} fillOpacity={0.15} name={dataKey} />
            {secondKey && <Area type="monotone" dataKey={secondKey} stroke={color2} fill={color2} fillOpacity={0.15} name={secondKey} />}
          </AreaChart>
        </ResponsiveContainer>
      );
    }

    // Default: bar
    return (
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={nameKey} tick={{ fontSize: 11 }} />
          <YAxis />
          <Tooltip formatter={(v) => Number(v).toLocaleString('en-IN')} />
          {showLegend && <Legend />}
          <Bar dataKey={dataKey} fill={color1} name={dataKey} radius={[4, 4, 0, 0]} />
          {secondKey && <Bar dataKey={secondKey} fill={color2} name={secondKey} radius={[4, 4, 0, 0]} />}
        </BarChart>
      </ResponsiveContainer>
    );
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-700">{chart.title}</h3>
        <button onClick={() => onDelete(chart.id)} className="text-gray-300 hover:text-red-500 transition-colors" title="Delete chart">
          <Trash2 size={16} />
        </button>
      </div>
      {renderInner()}
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [days, setDays] = useState(30);
  const [productType, setProductType] = useState('');
  const [variant, setVariant] = useState('');
  const [variants, setVariants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [importResult, setImportResult] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [customCharts, setCustomCharts] = useState([]);
  const fileRef = useRef(null);
  const invoiceRef = useRef(null);
  const [invoiceModal, setInvoiceModal] = useState(false);
  const [invoiceType, setInvoiceType] = useState('sales');
  const [invoiceFiles, setInvoiceFiles] = useState([]);
  const [invoiceUploading, setInvoiceUploading] = useState(false);
  const [invoiceProgress, setInvoiceProgress] = useState('');
  const [invoiceCurrent, setInvoiceCurrent] = useState(0);
  const [invoiceResult, setInvoiceResult] = useState(null);
  const [failedFiles, setFailedFiles] = useState([]);
  const [retryingFailed, setRetryingFailed] = useState(false);

  useEffect(() => {
    load();
    loadCharts();
  }, [days, productType, variant]);

  useEffect(() => {
    api.getProducts(productType || undefined).then((prods) => {
      const vs = [...new Set(prods.map((p) => p.variant))];
      setVariants(vs);
    });
  }, [productType]);

  // Listen for AI-triggered refreshes
  useEffect(() => {
    function onRefresh() { load(); loadCharts(); }
    window.addEventListener('dashboard-refresh', onRefresh);
    return () => window.removeEventListener('dashboard-refresh', onRefresh);
  }, [days, productType, variant]);

  async function load() {
    setLoading(true);
    try {
      const params = { days: String(days) };
      if (productType) params.product_type = productType;
      if (variant) params.variant = variant;
      const d = await api.getDashboard(params);
      setData(d);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }

  async function loadCharts() {
    try {
      const charts = await api.getCharts('dashboard');
      setCustomCharts(charts);
    } catch (e) {
      console.error(e);
    }
  }

  async function deleteCustomChart(id) {
    if (!confirm('Delete this chart?')) return;
    await api.deleteChart(id);
    setCustomCharts((prev) => prev.filter((c) => c.id !== id));
  }

  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setImportResult(null);
    try {
      const res = await api.uploadFile(file);
      setImportResult(res.import || { type: 'none', imported: 0, errors: ['No import data returned'] });
      // Refresh dashboard after import
      await load();
    } catch (err) {
      setImportResult({ type: 'error', imported: 0, errors: [err.message] });
    }
    setUploading(false);
    e.target.value = '';
  }

  function handleInvoiceFilesSelect(e) {
    const files = Array.from(e.target.files || []);
    setInvoiceFiles(files);
    e.target.value = '';
  }

  async function _uploadBatch(files, totalLabel, allResults) {
    for (let i = 0; i < files.length; i++) {
      const batch = [files[i]];
      setInvoiceCurrent(i + 1);
      setInvoiceProgress(`AI is reading invoice ${i + 1} of ${files.length} (${totalLabel})...`);

      try {
        const result = await api.uploadInvoices(batch, invoiceType);
        allResults.processed += result.processed || 0;
        allResults.total_imported += result.total_imported || 0;
        allResults.total_skipped += result.total_skipped || 0;
        const fileResults = result.file_results || [];
        for (let i = 0; i < fileResults.length; i++) {
          const fr = fileResults[i];
          // Match back to file by filename for retry tracking
          const matchedFile = batch.find(f => f.name === fr.filename) || batch[i];
          fr._file = matchedFile;
          allResults.file_results.push(fr);
        }
        if (fileResults.some(fr => fr.status === 'failed')) {
          allResults.failed += fileResults.filter(fr => fr.status === 'failed').length;
        }
      } catch (err) {
        // If entire batch fails, mark all as failed
        for (const file of batch) {
          allResults.failed += 1;
          allResults.file_results.push({
            filename: file.name,
            status: 'failed',
            imported: 0,
            errors: [err.message],
            _file: file,
          });
        }
      }

      setInvoiceResult({ ...allResults });
    }
  }

  async function handleInvoiceUpload() {
    if (invoiceFiles.length === 0) return;
    setInvoiceUploading(true);
    setInvoiceCurrent(0);
    setInvoiceResult(null);
    setFailedFiles([]);

    const totalFiles = invoiceFiles.length;
    const allResults = {
      total_files: totalFiles,
      processed: 0,
      failed: 0,
      total_imported: 0,
      total_skipped: 0,
      file_results: [],
    };

    // Initial pass
    await _uploadBatch(invoiceFiles, `pass 1 of ${totalFiles}`, allResults);

    // Auto-retry failed ones up to 3 times
    for (let attempt = 2; attempt <= 4; attempt++) {
      const failedFrs = allResults.file_results.filter(fr => fr.status === 'failed' && fr._file);
      if (failedFrs.length === 0) break;

      setInvoiceProgress(`Retrying ${failedFrs.length} failed invoice(s) — attempt ${attempt - 1}/3...`);

      // Remove old failed entries before retry
      const failedFileSet = new Set(failedFrs.map(fr => fr._file));
      allResults.file_results = allResults.file_results.filter(fr => !failedFileSet.has(fr._file));
      allResults.failed = allResults.file_results.filter(fr => fr.status === 'failed').length;
      allResults.processed = allResults.file_results.filter(fr => fr.status !== 'failed').length;

      await _uploadBatch([...failedFileSet], `retry ${attempt - 1}/3`, allResults);
    }

    // Sort: failed first, then success
    allResults.file_results.sort((a, b) => {
      if (a.status === 'failed' && b.status !== 'failed') return -1;
      if (a.status !== 'failed' && b.status === 'failed') return 1;
      return 0;
    });

    // Track still-failed files for manual retry
    const stillFailed = allResults.file_results.filter(fr => fr.status === 'failed' && fr._file);
    setFailedFiles(stillFailed.map(fr => fr._file));

    setInvoiceResult({ ...allResults });
    setInvoiceProgress('');
    setInvoiceUploading(false);
    if (allResults.total_imported > 0) {
      await load();
    }
  }

  async function handleRetryFailed() {
    if (failedFiles.length === 0) return;
    setRetryingFailed(true);
    setInvoiceCurrent(0);

    const prevResult = { ...invoiceResult };
    // Remove old failed entries for these files
    const retrySet = new Set(failedFiles);
    prevResult.file_results = prevResult.file_results.filter(fr => !retrySet.has(fr._file));
    prevResult.failed = prevResult.file_results.filter(fr => fr.status === 'failed').length;

    await _uploadBatch(failedFiles, `retry ${failedFiles.length} file(s)`, prevResult);

    prevResult.file_results.sort((a, b) => {
      if (a.status === 'failed' && b.status !== 'failed') return -1;
      if (a.status !== 'failed' && b.status === 'failed') return 1;
      return 0;
    });

    const stillFailed = prevResult.file_results.filter(fr => fr.status === 'failed' && fr._file);
    setFailedFiles(stillFailed.map(fr => fr._file));
    setInvoiceResult({ ...prevResult });
    setInvoiceProgress('');
    setRetryingFailed(false);
    if (prevResult.total_imported > 0) {
      await load();
    }
  }

  if (loading && !data) return <div className="p-8 text-gray-400">Loading dashboard...</div>;
  if (!data) return <div className="p-8 text-red-500">Failed to load dashboard data</div>;

  const fmt = (n) => '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 });

  const preformData = data.sales_by_variant.filter((v) => v.type === 'preform');
  const rawCapData = data.sales_by_variant.filter((v) => v.type === 'cap');

  // Group cap data: show top 10 by revenue, merge rest into "Others"
  const sortedCaps = [...rawCapData].sort((a, b) => b.revenue - a.revenue);
  const topCaps = sortedCaps.slice(0, 10);
  const otherCaps = sortedCaps.slice(10);
  const capData = otherCaps.length > 0
    ? [...topCaps, {
        variant: 'Others',
        type: 'cap',
        quantity: otherCaps.reduce((s, c) => s + c.quantity, 0),
        revenue: otherCaps.reduce((s, c) => s + c.revenue, 0),
        taxable: otherCaps.reduce((s, c) => s + (c.taxable || 0), 0),
      }]
    : topCaps;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
          <p className="text-gray-500 text-sm">Overview of your PET Preforms & Caps business</p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <input type="file" ref={fileRef} onChange={handleUpload} accept=".xlsx,.xls,.csv" className="hidden" />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
          >
            <Upload size={16} /> {uploading ? 'AI is importing...' : 'Import Excel'}
          </button>
          <button
            onClick={() => { setInvoiceModal(true); setInvoiceResult(null); setInvoiceFiles([]); }}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
          >
            <FolderOpen size={16} /> Import Invoices
          </button>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="border rounded-lg px-3 py-2 text-sm bg-white"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={180}>Last 6 months</option>
            <option value={365}>Last 1 year</option>
          </select>
          <select
            value={productType}
            onChange={(e) => { setProductType(e.target.value); setVariant(''); }}
            className="border rounded-lg px-3 py-2 text-sm bg-white"
          >
            <option value="">All Products</option>
            <option value="preform">Preforms</option>
            <option value="cap">Caps</option>
            <option value="bottle">Bottles</option>
          </select>
          {productType && (
            <select
              value={variant}
              onChange={(e) => setVariant(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm bg-white"
            >
              <option value="">All {productType === 'preform' ? 'Grams' : 'Colors'}</option>
              {variants.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Import Result Banner */}
      {importResult && (
        <div className={`rounded-xl border p-4 ${
          importResult.imported > 0 ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {importResult.imported > 0 ? (
                <CheckCircle size={20} className="text-green-600" />
              ) : (
                <XCircle size={20} className="text-red-600" />
              )}
              <span className="font-semibold">
                {importResult.imported > 0
                  ? `Successfully imported ${importResult.imported} ${importResult.type} records!`
                  : `Import failed: ${importResult.errors?.[0] || 'Unknown error'}`
                }
              </span>
              {importResult.skipped > 0 && (
                <span className="text-sm text-gray-500">({importResult.skipped} rows skipped)</span>
              )}
            </div>
            <button onClick={() => setImportResult(null)} className="text-gray-400 hover:text-gray-600">✕</button>
          </div>
          {importResult.details && importResult.details.length > 0 && (
            <div className="mt-2 max-h-32 overflow-y-auto text-sm text-gray-600 space-y-0.5">
              {importResult.details.slice(0, 20).map((d, i) => <div key={i}>• {d}</div>)}
              {importResult.details.length > 20 && <div className="text-gray-400">...and {importResult.details.length - 20} more</div>}
            </div>
          )}
          {importResult.errors && importResult.errors.length > 0 && importResult.imported > 0 && (
            <div className="mt-2 text-sm text-red-600">
              {importResult.errors.slice(0, 5).map((e, i) => <div key={i}>⚠ {e}</div>)}
            </div>
          )}
        </div>
      )}

      {/* Stats Cards - Row 1: Sales & Tax */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Taxable Sales" value={fmt(data.total_taxable)} icon={Receipt} color="green" sub="Before tax" />
        <StatCard title="GST (Tax)" value={fmt(data.total_tax)} icon={Receipt} color="yellow" sub="Tax amount" />
        <StatCard title="Revenue (incl. Tax)" value={fmt(data.total_revenue)} icon={IndianRupee} color="blue" sub="After tax" />
        <StatCard title="Units Sold" value={data.total_units_sold.toLocaleString()} icon={Package} color="green"
          sub={data.sales_by_variant ? (() => {
            const byType = {};
            (data.sales_by_variant || []).forEach(v => { byType[v.type] = (byType[v.type] || 0) + v.quantity; });
            return Object.entries(byType).map(([t, q]) => `${t}: ${q.toLocaleString()}`).join(' | ');
          })() : undefined}
        />
      </div>

      {/* Stats Cards - Row 2: Profit & Operations */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Gross Profit" value={fmt(data.gross_profit)} icon={TrendingUp} color="green" />
        <StatCard title="Net Profit" value={fmt(data.net_profit)} icon={TrendingUp} color="purple" />
        <StatCard title="Wastage" value={`${data.wastage_pct}%`} icon={Percent} color="yellow" sub={`${data.total_wastage_kg} kg wasted`} />
        <StatCard title="Expenses" value={fmt(data.expenses)} icon={TrendingDown} color="red" />
      </div>



      {/* Charts Row 1 - Sales Trend & Sales by Product */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <h3 className="font-semibold text-gray-700 mb-4">Sales Trend (Daily)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data.daily_trend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis />
              <Tooltip formatter={(v) => '₹' + Number(v).toLocaleString('en-IN')} />
              <Legend />
              <Area type="monotone" dataKey="taxable" stroke="#10b981" fill="#10b981" fillOpacity={0.1} name="Taxable (Before Tax)" />
              <Area type="monotone" dataKey="revenue" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.1} name="Revenue (With Tax)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl shadow-sm border p-5">
          <h3 className="font-semibold text-gray-700 mb-4">Sales by Product</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.sales_by_product}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis />
              <Tooltip formatter={(v) => '₹' + Number(v).toLocaleString('en-IN')} />
              <Legend />
              <Bar dataKey="taxable" fill="#10b981" name="Taxable (₹)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="revenue" fill="#3b82f6" name="Revenue with Tax (₹)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2 - By Preform Gram & By Cap Color */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <h3 className="font-semibold text-gray-700 mb-4">Sales by Preform Gram</h3>
          {preformData.length === 0 ? (
            <p className="text-gray-400 text-sm py-12 text-center">No preform sales data</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={preformData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="variant" tick={{ fontSize: 12 }} />
                <YAxis />
                <Tooltip formatter={(v) => '₹' + Number(v).toLocaleString('en-IN')} />
                <Legend />
                <Bar dataKey="taxable" fill="#8b5cf6" name="Taxable (₹)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="revenue" fill="#06b6d4" name="Revenue with Tax (₹)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-sm border p-5">
          <h3 className="font-semibold text-gray-700 mb-4">Sales by Cap Color {otherCaps.length > 0 && <span className="text-xs text-gray-400 font-normal">(Top 10 + {otherCaps.length} others)</span>}</h3>
          {capData.length === 0 ? (
            <p className="text-gray-400 text-sm py-12 text-center">No cap sales data</p>
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(300, capData.length * 30)}>
              <BarChart data={capData} layout="vertical" margin={{ left: 10, right: 30 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tickFormatter={(v) => v >= 1000 ? '₹' + (v / 1000).toFixed(0) + 'k' : '₹' + v} />
                <YAxis type="category" dataKey="variant" tick={{ fontSize: 11 }} width={120} />
                <Tooltip formatter={(v) => '₹' + Number(v).toLocaleString('en-IN')} />
                <Bar dataKey="revenue" fill="#8b5cf6" name="Revenue (₹)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* AI-Created Custom Charts */}
      {customCharts.length > 0 && (
        <>
          <div className="flex items-center gap-2 mt-2">
            <h2 className="text-lg font-semibold text-gray-700">Custom Charts</h2>
            <span className="text-xs text-gray-400">(created via AI Chat)</span>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {customCharts.map((chart) => (
              <DynamicChart key={chart.id} chart={chart} days={days} onDelete={deleteCustomChart} />
            ))}
          </div>
        </>
      )}

      {/* Invoice Upload Modal */}
      {invoiceModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b">
              <div>
                <h2 className="text-xl font-bold text-gray-800">Import Invoices (AI-Powered)</h2>
                <p className="text-sm text-gray-500 mt-1">Upload PDF or image invoices — AI will read and auto-import data</p>
              </div>
              <button onClick={() => setInvoiceModal(false)} className="text-gray-400 hover:text-gray-600">
                <X size={24} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-5">
              {/* Invoice Type Selection */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Invoice Type</label>
                <div className="flex gap-3">
                  <button
                    onClick={() => setInvoiceType('sales')}
                    className={`flex-1 py-3 px-4 rounded-xl border-2 text-sm font-medium transition-all ${
                      invoiceType === 'sales'
                        ? 'border-green-500 bg-green-50 text-green-700'
                        : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                    }`}
                  >
                    <div className="font-bold">Sales / Output Invoice</div>
                    <div className="text-xs mt-1 opacity-75">Invoices where YOU sold goods to customers</div>
                  </button>
                  <button
                    onClick={() => setInvoiceType('purchase')}
                    className={`flex-1 py-3 px-4 rounded-xl border-2 text-sm font-medium transition-all ${
                      invoiceType === 'purchase'
                        ? 'border-orange-500 bg-orange-50 text-orange-700'
                        : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                    }`}
                  >
                    <div className="font-bold">Purchase / Input Invoice</div>
                    <div className="text-xs mt-1 opacity-75">Invoices where YOU bought materials/goods</div>
                  </button>
                </div>
              </div>

              {/* File Selection */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Select Invoice Files</label>
                <input
                  type="file"
                  ref={invoiceRef}
                  onChange={handleInvoiceFilesSelect}
                  accept=".pdf,.png,.jpg,.jpeg,.bmp,.tiff"
                  multiple
                  className="hidden"
                />
                <button
                  onClick={() => invoiceRef.current?.click()}
                  className="w-full py-8 border-2 border-dashed rounded-xl text-gray-500 hover:border-blue-400 hover:text-blue-500 transition-colors text-center"
                >
                  <FolderOpen size={32} className="mx-auto mb-2 opacity-60" />
                  <div className="text-sm font-medium">Click to select PDF or image files</div>
                  <div className="text-xs mt-1 opacity-60">Supports: PDF, PNG, JPG, BMP, TIFF — select multiple files</div>
                </button>
              </div>

              {/* Selected Files List */}
              {invoiceFiles.length > 0 && (
                <div>
                  <div className="text-sm font-semibold text-gray-700 mb-2">{invoiceFiles.length} file(s) selected</div>
                  <div className="max-h-40 overflow-y-auto space-y-1 bg-gray-50 rounded-lg p-3">
                    {invoiceFiles.map((f, i) => (
                      <div key={i} className="flex items-center gap-2 text-sm text-gray-600">
                        <FileText size={14} className="text-gray-400 shrink-0" />
                        <span className="truncate">{f.name}</span>
                        <span className="text-xs text-gray-400 shrink-0">({(f.size / 1024).toFixed(0)} KB)</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Progress Bar */}
              {invoiceUploading && (
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full shrink-0"></div>
                    <span className="text-sm text-blue-700 font-medium">{invoiceProgress}</span>
                  </div>
                  <div className="w-full bg-blue-100 rounded-full h-3 overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all duration-500 ease-out"
                      style={{ width: `${(invoiceCurrent / invoiceFiles.length) * 100}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-blue-600">
                    <span>{invoiceCurrent} of {invoiceFiles.length} processed</span>
                    <span>{Math.round((invoiceCurrent / invoiceFiles.length) * 100)}%</span>
                  </div>
                </div>
              )}

              {/* Results */}
              {invoiceResult && (
                <div className={`rounded-xl border p-4 ${
                  invoiceResult.total_imported > 0 ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                }`}>
                  <div className="flex items-center gap-2 mb-3">
                    {invoiceResult.total_imported > 0 ? (
                      <CheckCircle size={20} className="text-green-600" />
                    ) : (
                      <XCircle size={20} className="text-red-600" />
                    )}
                    <span className="font-semibold text-sm">
                      {invoiceResult.total_imported > 0
                        ? `Imported ${invoiceResult.total_imported} records from ${invoiceResult.processed} invoice(s)`
                        : `No data could be imported`
                      }
                      {invoiceResult.failed > 0 && ` — ${invoiceResult.failed} file(s) failed`}
                    </span>
                  </div>
                  <div className="max-h-48 overflow-y-auto space-y-2">
                    {invoiceResult.file_results?.map((fr, i) => (
                      <div key={i} className={`text-sm p-2 rounded-lg ${
                        fr.status === 'success' ? 'bg-green-100' : fr.status === 'failed' ? 'bg-red-100' : 'bg-gray-100'
                      }`}>
                        <div className="font-medium flex items-center gap-2">
                          {fr.status === 'success' ? '✅' : fr.status === 'failed' ? '❌' : '⚠️'}
                          {fr.filename}
                          {fr.invoice_no && <span className="text-xs text-gray-500">#{fr.invoice_no}</span>}
                          {fr.party && <span className="text-xs text-gray-500">— {fr.party}</span>}
                        </div>
                        {fr.details?.length > 0 && (
                          <div className="mt-1 text-xs text-gray-600 space-y-0.5">
                            {fr.details.slice(0, 5).map((d, j) => <div key={j}>• {d}</div>)}
                            {fr.details.length > 5 && <div className="text-gray-400">...and {fr.details.length - 5} more</div>}
                          </div>
                        )}
                        {fr.errors?.length > 0 && (
                          <div className="mt-1 text-xs text-red-600">
                            {fr.errors.map((e, j) => <div key={j}>⚠ {e}</div>)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Retry Failed Button */}
              {failedFiles.length > 0 && !invoiceUploading && !retryingFailed && (
                <button
                  onClick={handleRetryFailed}
                  className="w-full py-3 rounded-xl font-semibold text-white text-sm bg-red-600 hover:bg-red-700 transition-colors flex items-center justify-center gap-2"
                >
                  <RefreshCw size={16} /> Retry {failedFiles.length} Failed Invoice(s)
                </button>
              )}

              {/* Upload Button */}
              <button
                onClick={handleInvoiceUpload}
                disabled={invoiceFiles.length === 0 || invoiceUploading || retryingFailed}
                className={`w-full py-3 rounded-xl font-semibold text-white text-sm transition-colors ${
                  invoiceType === 'sales'
                    ? 'bg-green-600 hover:bg-green-700 disabled:bg-green-300'
                    : 'bg-orange-600 hover:bg-orange-700 disabled:bg-orange-300'
                }`}
              >
                {invoiceUploading || retryingFailed
                  ? 'AI is reading invoices...'
                  : `Upload & Import ${invoiceFiles.length || ''} ${invoiceType === 'sales' ? 'Sales' : 'Purchase'} Invoice(s)`
                }
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
