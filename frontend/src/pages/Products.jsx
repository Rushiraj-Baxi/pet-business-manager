import { useState, useEffect } from 'react';
import { api } from '../api';
import { Plus, Trash2, Edit3, X, Check } from 'lucide-react';

export default function Products() {
  const [products, setProducts] = useState([]);
  const [filter, setFilter] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState({ name: '', type: 'preform', variant: '', sell_price: '', cost_price: '', stock: '' });

  useEffect(() => { load(); }, [filter]);

  useEffect(() => {
    const h = () => load();
    window.addEventListener('products-refresh', h);
    return () => window.removeEventListener('products-refresh', h);
  }, [filter]);

  async function load() {
    const data = await api.getProducts(filter || undefined);
    setProducts(data);
  }

  async function save() {
    const payload = {
      ...form,
      sell_price: Number(form.sell_price),
      cost_price: Number(form.cost_price),
      stock: Number(form.stock),
    };
    if (editId) {
      await api.updateProduct(editId, { name: form.name, sell_price: payload.sell_price, cost_price: payload.cost_price, stock: payload.stock });
    } else {
      await api.createProduct(payload);
    }
    setShowForm(false);
    setEditId(null);
    setForm({ name: '', type: 'preform', variant: '', sell_price: '', cost_price: '', stock: '' });
    load();
  }

  async function remove(id) {
    if (!confirm('Delete this product?')) return;
    await api.deleteProduct(id);
    load();
  }

  function startEdit(p) {
    setEditId(p.id);
    setForm({ name: p.name, type: p.type, variant: p.variant, sell_price: p.sell_price, cost_price: p.cost_price, stock: p.stock });
    setShowForm(true);
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Products</h1>
          <p className="text-gray-500 text-sm">Manage preforms & caps</p>
        </div>
        <div className="flex gap-3">
          <select value={filter} onChange={(e) => setFilter(e.target.value)} className="border rounded-lg px-3 py-2 text-sm bg-white">
            <option value="">All Types</option>
            <option value="preform">Preforms</option>
            <option value="cap">Caps</option>
          </select>
          <button onClick={() => { setShowForm(true); setEditId(null); setForm({ name: '', type: 'preform', variant: '', sell_price: '', cost_price: '', stock: '' }); }} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
            <Plus size={16} /> Add Product
          </button>
        </div>
      </div>

      {/* Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">{editId ? 'Edit Product' : 'Add Product'}</h2>
              <button onClick={() => setShowForm(false)}><X size={20} /></button>
            </div>
            <div className="space-y-3">
              <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Product Name (e.g., Preform 18g)" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              {!editId && (
                <>
                  <select className="w-full border rounded-lg px-3 py-2 text-sm" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                    <option value="preform">Preform</option>
                    <option value="cap">Cap</option>
                  </select>
                  <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder={form.type === 'preform' ? 'Gram weight (e.g., 18g)' : 'Color (e.g., Red)'} value={form.variant} onChange={(e) => setForm({ ...form, variant: e.target.value })} />
                </>
              )}
              <div className="grid grid-cols-3 gap-3">
                <input type="number" className="border rounded-lg px-3 py-2 text-sm" placeholder="Sell Price (₹)" value={form.sell_price} onChange={(e) => setForm({ ...form, sell_price: e.target.value })} />
                <input type="number" className="border rounded-lg px-3 py-2 text-sm" placeholder="Cost Price (₹)" value={form.cost_price} onChange={(e) => setForm({ ...form, cost_price: e.target.value })} />
                <input type="number" className="border rounded-lg px-3 py-2 text-sm" placeholder="Stock" value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })} />
              </div>
              <button onClick={save} className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 flex items-center justify-center gap-2">
                <Check size={16} /> {editId ? 'Update' : 'Create'}
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
              <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Type</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Variant</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Sell Price</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Cost Price</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Stock</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600">Actions</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{p.name}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${p.type === 'preform' ? 'bg-blue-100 text-blue-700' : 'bg-pink-100 text-pink-700'}`}>
                    {p.type}
                  </span>
                </td>
                <td className="px-4 py-3">{p.variant}</td>
                <td className="px-4 py-3 text-right">₹{p.sell_price.toLocaleString('en-IN')}</td>
                <td className="px-4 py-3 text-right">₹{p.cost_price.toLocaleString('en-IN')}</td>
                <td className="px-4 py-3 text-right">
                  <span className={p.stock <= 10 ? 'text-red-600 font-bold' : ''}>{p.stock}</span>
                </td>
                <td className="px-4 py-3 text-center">
                  <button onClick={() => startEdit(p)} className="text-gray-400 hover:text-blue-600 mr-2"><Edit3 size={16} /></button>
                  <button onClick={() => remove(p.id)} className="text-gray-400 hover:text-red-600"><Trash2 size={16} /></button>
                </td>
              </tr>
            ))}
            {products.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No products yet. Add your first product!</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
