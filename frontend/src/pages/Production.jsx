import { useState, useEffect } from 'react';
import { api } from '../api';
import { Plus, Trash2, X, Check } from 'lucide-react';

export default function Production() {
  const [records, setRecords] = useState([]);
  const [products, setProducts] = useState([]);
  const [materials, setMaterials] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ product_id: '', raw_material_id: '', quantity_produced: '', raw_material_used: '', wastage: '', date: '' });

  useEffect(() => { loadAll(); }, []);

  useEffect(() => {
    const h = () => loadAll();
    window.addEventListener('production-refresh', h);
    return () => window.removeEventListener('production-refresh', h);
  }, []);

  async function loadAll() {
    const [r, p, m] = await Promise.all([api.getProductions(), api.getProducts(), api.getMaterials()]);
    setRecords(r);
    setProducts(p);
    setMaterials(m);
  }

  async function save() {
    await api.createProduction({
      product_id: Number(form.product_id),
      raw_material_id: Number(form.raw_material_id),
      quantity_produced: Number(form.quantity_produced),
      raw_material_used: Number(form.raw_material_used),
      wastage: Number(form.wastage) || 0,
      date: form.date || undefined,
    });
    setShowForm(false);
    setForm({ product_id: '', raw_material_id: '', quantity_produced: '', raw_material_used: '', wastage: '', date: '' });
    loadAll();
  }

  async function remove(id) {
    if (!confirm('Delete this production record?')) return;
    await api.deleteProduction(id);
    loadAll();
  }

  const totalProduced = records.reduce((s, x) => s + x.quantity_produced, 0);
  const totalWastage = records.reduce((s, x) => s + x.wastage, 0);
  const totalRM = records.reduce((s, x) => s + x.raw_material_used, 0);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Production</h1>
          <p className="text-gray-500 text-sm">Log production runs & track wastage</p>
        </div>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
          <Plus size={16} /> Log Production
        </button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border p-4 text-center">
          <p className="text-sm text-gray-500">Total Produced</p>
          <p className="text-2xl font-bold text-blue-600">{totalProduced.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-xl border p-4 text-center">
          <p className="text-sm text-gray-500">Raw Material Used</p>
          <p className="text-2xl font-bold text-gray-700">{totalRM.toLocaleString()} kg</p>
        </div>
        <div className="bg-white rounded-xl border p-4 text-center">
          <p className="text-sm text-gray-500">Total Wastage</p>
          <p className="text-2xl font-bold text-red-500">{totalWastage.toLocaleString()} kg ({totalRM ? (totalWastage / totalRM * 100).toFixed(1) : 0}%)</p>
        </div>
      </div>

      {/* Form */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">Log Production</h2>
              <button onClick={() => setShowForm(false)}><X size={20} /></button>
            </div>
            <div className="space-y-3">
              <select className="w-full border rounded-lg px-3 py-2 text-sm" value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })}>
                <option value="">Select Product</option>
                {products.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.variant})</option>)}
              </select>
              <select className="w-full border rounded-lg px-3 py-2 text-sm" value={form.raw_material_id} onChange={(e) => setForm({ ...form, raw_material_id: e.target.value })}>
                <option value="">Select Raw Material</option>
                {materials.map((m) => <option key={m.id} value={m.id}>{m.name} (Stock: {m.current_stock} {m.unit})</option>)}
              </select>
              <div className="grid grid-cols-3 gap-3">
                <input type="number" className="border rounded-lg px-3 py-2 text-sm" placeholder="Qty Produced" value={form.quantity_produced} onChange={(e) => setForm({ ...form, quantity_produced: e.target.value })} />
                <input type="number" className="border rounded-lg px-3 py-2 text-sm" placeholder="RM Used (kg)" value={form.raw_material_used} onChange={(e) => setForm({ ...form, raw_material_used: e.target.value })} />
                <input type="number" className="border rounded-lg px-3 py-2 text-sm" placeholder="Wastage (kg)" value={form.wastage} onChange={(e) => setForm({ ...form, wastage: e.target.value })} />
              </div>
              <input type="date" className="w-full border rounded-lg px-3 py-2 text-sm" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
              <button onClick={save} className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 flex items-center justify-center gap-2">
                <Check size={16} /> Log Production
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Date</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Product</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Raw Material</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Qty Produced</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">RM Used</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Wastage</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Wastage %</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600">Actions</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r) => (
              <tr key={r.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-3">{new Date(r.date).toLocaleDateString()}</td>
                <td className="px-4 py-3 font-medium">{r.product_name}</td>
                <td className="px-4 py-3">{r.raw_material_name}</td>
                <td className="px-4 py-3 text-right">{r.quantity_produced}</td>
                <td className="px-4 py-3 text-right">{r.raw_material_used} kg</td>
                <td className="px-4 py-3 text-right text-red-500">{r.wastage} kg</td>
                <td className="px-4 py-3 text-right">{r.wastage_pct}%</td>
                <td className="px-4 py-3 text-center">
                  <button onClick={() => remove(r.id)} className="text-gray-400 hover:text-red-600"><Trash2 size={16} /></button>
                </td>
              </tr>
            ))}
            {records.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No production records yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
