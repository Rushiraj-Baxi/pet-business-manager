import React, { useState, useEffect, useMemo } from 'react';
import { api } from '../api';
import { Plus, Trash2, X, Check, ChevronUp, ChevronDown, Search, Pencil, Download } from 'lucide-react';
import * as XLSX from 'xlsx';

export default function Sales() {
  const [sales, setSales] = useState([]);
  const [products, setProducts] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editSale, setEditSale] = useState(null);
  const [filters, setFilters] = useState({ product_type: '', variant: '', start_date: '', end_date: '' });
  const [form, setForm] = useState({ product_id: '', quantity: '', price_per_unit: '', customer: '', date: '' });
  const [editForm, setEditForm] = useState({});
  const [sortCol, setSortCol] = useState('date');
  const [sortDir, setSortDir] = useState('desc');
  const [searchText, setSearchText] = useState('');

  useEffect(() => { loadProducts(); }, []);
  useEffect(() => { load(); }, [filters]);

  useEffect(() => {
    const h = () => { load(); loadProducts(); };
    window.addEventListener('sales-refresh', h);
    return () => window.removeEventListener('sales-refresh', h);
  }, [filters]);

  async function loadProducts() {
    setProducts(await api.getProducts());
  }

  async function load() {
    const params = {};
    if (filters.product_type) params.product_type = filters.product_type;
    if (filters.variant) params.variant = filters.variant;
    if (filters.start_date) params.start_date = filters.start_date;
    if (filters.end_date) params.end_date = filters.end_date;
    setSales(await api.getSales(params));
  }

  async function save() {
    await api.createSale({
      product_id: Number(form.product_id),
      quantity: Number(form.quantity),
      price_per_unit: Number(form.price_per_unit),
      customer: form.customer,
      date: form.date || undefined,
    });
    setShowForm(false);
    setForm({ product_id: '', quantity: '', price_per_unit: '', customer: '', date: '' });
    load();
    loadProducts();
  }

  async function remove(id) {
    if (!confirm('Delete this sale?')) return;
    await api.deleteSale(id);
    load();
    loadProducts();
  }

  function startEdit(s) {
    setEditSale(s);
    setEditForm({
      quantity: s.quantity,
      price_per_unit: s.price_per_unit,
      customer: s.customer || '',
      date: s.date ? s.date.split('T')[0] : '',
      invoice_no: s.invoice_no || '',
      taxable_amount: s.taxable_amount || 0,
    });
  }

  async function saveEdit() {
    const updates = {};
    if (Number(editForm.quantity) !== editSale.quantity) updates.quantity = Number(editForm.quantity);
    if (Number(editForm.price_per_unit) !== editSale.price_per_unit) updates.price_per_unit = Number(editForm.price_per_unit);
    if (editForm.customer !== (editSale.customer || '')) updates.customer = editForm.customer;
    if (editForm.invoice_no !== (editSale.invoice_no || '')) updates.invoice_no = editForm.invoice_no;
    if (Number(editForm.taxable_amount) !== (editSale.taxable_amount || 0)) updates.taxable_amount = Number(editForm.taxable_amount);
    const editDate = editForm.date || '';
    const saleDate = editSale.date ? editSale.date.split('T')[0] : '';
    if (editDate !== saleDate) updates.date = editForm.date;
    if (Object.keys(updates).length === 0) { setEditSale(null); return; }
    await api.updateSale(editSale.id, updates);
    setEditSale(null);
    load();
    loadProducts();
  }

  function autoFillPrice(pid) {
    const p = products.find((x) => x.id === Number(pid));
    if (p) setForm({ ...form, product_id: pid, price_per_unit: p.sell_price });
    else setForm({ ...form, product_id: pid });
  }

  const variants = [...new Set(products.filter((p) => !filters.product_type || p.type === filters.product_type).map((p) => p.variant))];

  // Filter by search text
  const filtered = useMemo(() => {
    if (!searchText.trim()) return sales;
    const q = searchText.toLowerCase();
    return sales.filter((s) =>
      (s.product_name || '').toLowerCase().includes(q) ||
      (s.customer || '').toLowerCase().includes(q) ||
      (s.invoice_no || '').toLowerCase().includes(q) ||
      (s.product_type || '').toLowerCase().includes(q) ||
      (s.product_variant || '').toLowerCase().includes(q)
    );
  }, [sales, searchText]);

  // Sort
  const sorted = useMemo(() => {
    const arr = [...filtered];
    arr.sort((a, b) => {
      let va = a[sortCol], vb = b[sortCol];
      if (sortCol === 'date') { va = va || ''; vb = vb || ''; }
      if (typeof va === 'string') { va = va.toLowerCase(); vb = (vb || '').toLowerCase(); }
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return arr;
  }, [filtered, sortCol, sortDir]);



  function handleSort(col) {
    if (sortCol === col) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    else { setSortCol(col); setSortDir('asc'); }
  }

  function SortIcon({ col }) {
    if (sortCol !== col) return <ChevronUp size={12} className="text-gray-300" />;
    return sortDir === 'asc' ? <ChevronUp size={12} className="text-blue-600" /> : <ChevronDown size={12} className="text-blue-600" />;
  }

  const totalRevenue = filtered.reduce((s, x) => s + x.total_price, 0);
  const totalTaxable = filtered.reduce((s, x) => s + (x.taxable_amount || 0), 0);
  const totalTax = totalRevenue - totalTaxable;
  const totalQty = filtered.reduce((s, x) => s + x.quantity, 0);

  function downloadExcel() {
    const rows = sorted.map((s) => ({
      Date: s.date ? new Date(s.date).toLocaleDateString() : '',
      Invoice: s.invoice_no || '',
      Product: s.product_name,
      Type: s.product_type,
      Variant: s.product_variant,
      Qty: s.quantity,
      'Price/Unit': s.price_per_unit,
      'Taxable Amt': s.taxable_amount || 0,
      'Total (with Tax)': s.total_price,
      Customer: s.customer || '',
    }));
    rows.push({ Date: '', Invoice: '', Product: '', Type: '', Variant: 'TOTALS', Qty: totalQty, 'Price/Unit': '', 'Taxable Amt': totalTaxable, 'Total (with Tax)': totalRevenue, Customer: '' });
    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Sales');
    XLSX.writeFile(wb, `Sales_${new Date().toISOString().slice(0, 10)}.xlsx`);
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Sales</h1>
          <p className="text-gray-500 text-sm">Record & track all sales</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={downloadExcel} className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700">
            <Download size={16} /> Download Excel
          </button>
          <button onClick={() => setShowForm(true)} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
            <Plus size={16} /> Record Sale
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap items-end">
        <div>
          <label className="text-xs text-gray-500 mb-1 block">Type</label>
          <select value={filters.product_type} onChange={(e) => setFilters({ ...filters, product_type: e.target.value, variant: '' })} className="border rounded-lg px-3 py-2 text-sm bg-white">
            <option value="">All</option>
            <option value="preform">Preforms</option>
            <option value="cap">Caps</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 mb-1 block">Variant</label>
          <select value={filters.variant} onChange={(e) => setFilters({ ...filters, variant: e.target.value })} className="border rounded-lg px-3 py-2 text-sm bg-white">
            <option value="">All</option>
            {variants.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 mb-1 block">From</label>
          <input type="date" value={filters.start_date} onChange={(e) => setFilters({ ...filters, start_date: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="text-xs text-gray-500 mb-1 block">To</label>
          <input type="date" value={filters.end_date} onChange={(e) => setFilters({ ...filters, end_date: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" />
        </div>
        <div className="flex-1 min-w-[200px]">
          <label className="text-xs text-gray-500 mb-1 block">Search</label>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input value={searchText} onChange={(e) => setSearchText(e.target.value)} placeholder="Product, customer, invoice..." className="w-full border rounded-lg pl-8 pr-3 py-2 text-sm" />
          </div>
        </div>
      </div>
      <div className="text-sm text-gray-500 text-right">
        <span className="font-semibold text-gray-800">{totalQty}</span> units | <span className="font-semibold text-gray-800">₹{totalTaxable.toLocaleString('en-IN', {maximumFractionDigits: 0})}</span> taxable | <span className="font-semibold text-blue-700">₹{totalRevenue.toLocaleString('en-IN', {maximumFractionDigits: 0})}</span> with tax
      </div>

      {/* Form */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">Record Sale</h2>
              <button onClick={() => setShowForm(false)}><X size={20} /></button>
            </div>
            <div className="space-y-3">
              <select className="w-full border rounded-lg px-3 py-2 text-sm" value={form.product_id} onChange={(e) => autoFillPrice(e.target.value)}>
                <option value="">Select Product</option>
                {products.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.type} - {p.variant}) [Stock: {p.stock}]</option>)}
              </select>
              <div className="grid grid-cols-2 gap-3">
                <input type="number" className="border rounded-lg px-3 py-2 text-sm" placeholder="Quantity" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} />
                <input type="number" className="border rounded-lg px-3 py-2 text-sm" placeholder="Price/Unit (₹)" value={form.price_per_unit} onChange={(e) => setForm({ ...form, price_per_unit: e.target.value })} />
              </div>
              <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Customer Name" value={form.customer} onChange={(e) => setForm({ ...form, customer: e.target.value })} />
              <input type="date" className="w-full border rounded-lg px-3 py-2 text-sm" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
              <button onClick={save} className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 flex items-center justify-center gap-2">
                <Check size={16} /> Record Sale
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editSale && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">Edit Sale</h2>
              <button onClick={() => setEditSale(null)}><X size={20} /></button>
            </div>
            <div className="text-sm text-gray-500 mb-3">Product: <span className="font-medium text-gray-800">{editSale.product_name}</span></div>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Quantity</label>
                  <input type="number" className="w-full border rounded-lg px-3 py-2 text-sm" value={editForm.quantity} onChange={(e) => setEditForm({ ...editForm, quantity: e.target.value })} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Price/Unit (₹)</label>
                  <input type="number" className="w-full border rounded-lg px-3 py-2 text-sm" value={editForm.price_per_unit} onChange={(e) => setEditForm({ ...editForm, price_per_unit: e.target.value })} />
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Taxable Amount (₹)</label>
                <input type="number" className="w-full border rounded-lg px-3 py-2 text-sm" value={editForm.taxable_amount} onChange={(e) => setEditForm({ ...editForm, taxable_amount: e.target.value })} />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Customer</label>
                <input className="w-full border rounded-lg px-3 py-2 text-sm" value={editForm.customer} onChange={(e) => setEditForm({ ...editForm, customer: e.target.value })} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Invoice No</label>
                  <input className="w-full border rounded-lg px-3 py-2 text-sm" value={editForm.invoice_no} onChange={(e) => setEditForm({ ...editForm, invoice_no: e.target.value })} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Date</label>
                  <input type="date" className="w-full border rounded-lg px-3 py-2 text-sm" value={editForm.date} onChange={(e) => setEditForm({ ...editForm, date: e.target.value })} />
                </div>
              </div>
              <button onClick={saveEdit} className="w-full bg-green-600 text-white py-2 rounded-lg text-sm hover:bg-green-700 flex items-center justify-center gap-2">
                <Check size={16} /> Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border overflow-x-auto">
        <table className="w-full text-sm min-w-[1050px]">
          <thead className="bg-gray-50 border-b">
            <tr>
              {[
                { key: 'date', label: 'Date', align: 'left' },
                { key: 'invoice_no', label: 'Invoice', align: 'left' },
                { key: 'product_name', label: 'Product', align: 'left' },
                { key: 'product_type', label: 'Type', align: 'left' },
                { key: 'product_variant', label: 'Variant', align: 'left' },
                { key: 'quantity', label: 'Qty', align: 'right' },
                { key: 'price_per_unit', label: 'Price/Unit', align: 'right' },
                { key: 'taxable_amount', label: 'Taxable Amt', align: 'right' },
                { key: 'total_price', label: 'Total (with Tax)', align: 'right' },
                { key: 'customer', label: 'Customer', align: 'left' },
              ].map((col) => (
                <th key={col.key} className={`text-${col.align} px-4 py-3 font-medium text-gray-600 cursor-pointer select-none hover:bg-gray-100`} onClick={() => handleSort(col.key)}>
                  <span className="inline-flex items-center gap-1">{col.label} <SortIcon col={col.key} /></span>
                </th>
              ))}
              <th className="text-center px-4 py-3 font-medium text-gray-600">Actions</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((s, idx) => {
              const prevInvoice = idx > 0 ? (sorted[idx - 1].invoice_no || '') : null;
              const currInvoice = s.invoice_no || '';
              const isNewGroup = idx > 0 && currInvoice !== prevInvoice;
              return (
                <tr key={s.id} className={`hover:bg-gray-50 ${isNewGroup ? 'border-t-[3px] border-gray-300' : 'border-b border-gray-100'}`}>
                  <td className="px-4 py-3">{new Date(s.date).toLocaleDateString()}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{s.invoice_no || '-'}</td>
                  <td className="px-4 py-3 font-medium">{s.product_name}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${s.product_type === 'preform' ? 'bg-blue-100 text-blue-700' : 'bg-pink-100 text-pink-700'}`}>{s.product_type}</span>
                  </td>
                  <td className="px-4 py-3">{s.product_variant}</td>
                  <td className="px-4 py-3 text-right">{s.quantity}</td>
                  <td className="px-4 py-3 text-right">₹{s.price_per_unit.toLocaleString('en-IN')}</td>
                  <td className="px-4 py-3 text-right">₹{(s.taxable_amount || 0).toLocaleString('en-IN')}</td>
                  <td className="px-4 py-3 text-right font-medium text-blue-700">₹{s.total_price.toLocaleString('en-IN')}</td>
                  <td className="px-4 py-3">{s.customer || '-'}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <button onClick={() => startEdit(s)} className="text-gray-400 hover:text-blue-600"><Pencil size={15} /></button>
                      <button onClick={() => remove(s.id)} className="text-gray-400 hover:text-red-600"><Trash2 size={15} /></button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && (
              <tr><td colSpan={11} className="px-4 py-8 text-center text-gray-400">No sales recorded yet.</td></tr>
            )}
          </tbody>
          {filtered.length > 0 && (
            <tfoot className="bg-gray-50 border-t-2 border-gray-300">
              <tr>
                <td colSpan={5} className="px-4 py-3 font-bold text-gray-700">Totals</td>
                <td className="px-4 py-3 text-right font-bold text-gray-700">{totalQty.toLocaleString('en-IN')}</td>
                <td className="px-4 py-3"></td>
                <td className="px-4 py-3 text-right font-bold text-gray-700">₹{totalTaxable.toLocaleString('en-IN', {maximumFractionDigits: 0})}</td>
                <td className="px-4 py-3 text-right font-bold text-blue-700">₹{totalRevenue.toLocaleString('en-IN', {maximumFractionDigits: 0})}</td>
                <td colSpan={2} className="px-4 py-3 text-right text-sm text-gray-500">Tax: ₹{totalTax.toLocaleString('en-IN', {maximumFractionDigits: 0})}</td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  );
}
