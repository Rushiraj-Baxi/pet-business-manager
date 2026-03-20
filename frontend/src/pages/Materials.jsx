import { useState, useEffect } from 'react';
import { api } from '../api';
import { Plus, Trash2, X, Check, ShoppingBag } from 'lucide-react';

export default function Materials() {
  const [materials, setMaterials] = useState([]);
  const [purchases, setPurchases] = useState([]);
  const [tab, setTab] = useState('materials');
  const [showForm, setShowForm] = useState(false);
  const [formType, setFormType] = useState('material');
  const [matForm, setMatForm] = useState({ name: '', unit: 'kg', current_stock: '', price_per_unit: '', reorder_level: '' });
  const [purForm, setPurForm] = useState({ raw_material_id: '', quantity: '', price_per_unit: '', supplier: '', date: '' });

  useEffect(() => { loadAll(); }, []);

  useEffect(() => {
    const h = () => loadAll();
    window.addEventListener('materials-refresh', h);
    return () => window.removeEventListener('materials-refresh', h);
  }, []);

  async function loadAll() {
    const [m, p] = await Promise.all([api.getMaterials(), api.getPurchases()]);
    setMaterials(m);
    setPurchases(p);
  }

  async function saveMaterial() {
    await api.createMaterial({
      ...matForm,
      current_stock: Number(matForm.current_stock),
      price_per_unit: Number(matForm.price_per_unit),
      reorder_level: Number(matForm.reorder_level),
    });
    setShowForm(false);
    loadAll();
  }

  async function savePurchase() {
    await api.createPurchase({
      raw_material_id: Number(purForm.raw_material_id),
      quantity: Number(purForm.quantity),
      price_per_unit: Number(purForm.price_per_unit),
      supplier: purForm.supplier,
      date: purForm.date || undefined,
    });
    setShowForm(false);
    loadAll();
  }

  async function remove(id) {
    if (!confirm('Delete this material?')) return;
    await api.deleteMaterial(id);
    loadAll();
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Raw Materials</h1>
          <p className="text-gray-500 text-sm">Track inventory & purchases</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => { setFormType('material'); setShowForm(true); }} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
            <Plus size={16} /> Add Material
          </button>
          <button onClick={() => { setFormType('purchase'); setShowForm(true); }} className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700">
            <ShoppingBag size={16} /> Record Purchase
          </button>
        </div>
      </div>

      {/* Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">{formType === 'material' ? 'Add Material' : 'Record Purchase'}</h2>
              <button onClick={() => setShowForm(false)}><X size={20} /></button>
            </div>
            {formType === 'material' ? (
              <div className="space-y-3">
                <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Material Name (e.g., PET Resin)" value={matForm.name} onChange={(e) => setMatForm({ ...matForm, name: e.target.value })} />
                <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Unit (kg, liters, etc.)" value={matForm.unit} onChange={(e) => setMatForm({ ...matForm, unit: e.target.value })} />
                <div className="grid grid-cols-3 gap-3">
                  <input type="number" className="border rounded-lg px-3 py-2 text-sm" placeholder="Stock" value={matForm.current_stock} onChange={(e) => setMatForm({ ...matForm, current_stock: e.target.value })} />
                  <input type="number" className="border rounded-lg px-3 py-2 text-sm" placeholder="Price/Unit" value={matForm.price_per_unit} onChange={(e) => setMatForm({ ...matForm, price_per_unit: e.target.value })} />
                  <input type="number" className="border rounded-lg px-3 py-2 text-sm" placeholder="Reorder Level" value={matForm.reorder_level} onChange={(e) => setMatForm({ ...matForm, reorder_level: e.target.value })} />
                </div>
                <button onClick={saveMaterial} className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 flex items-center justify-center gap-2">
                  <Check size={16} /> Create
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <select className="w-full border rounded-lg px-3 py-2 text-sm" value={purForm.raw_material_id} onChange={(e) => setPurForm({ ...purForm, raw_material_id: e.target.value })}>
                  <option value="">Select Material</option>
                  {materials.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
                <div className="grid grid-cols-2 gap-3">
                  <input type="number" className="border rounded-lg px-3 py-2 text-sm" placeholder="Quantity" value={purForm.quantity} onChange={(e) => setPurForm({ ...purForm, quantity: e.target.value })} />
                  <input type="number" className="border rounded-lg px-3 py-2 text-sm" placeholder="Price per Unit" value={purForm.price_per_unit} onChange={(e) => setPurForm({ ...purForm, price_per_unit: e.target.value })} />
                </div>
                <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Supplier Name" value={purForm.supplier} onChange={(e) => setPurForm({ ...purForm, supplier: e.target.value })} />
                <input type="date" className="w-full border rounded-lg px-3 py-2 text-sm" value={purForm.date} onChange={(e) => setPurForm({ ...purForm, date: e.target.value })} />
                <button onClick={savePurchase} className="w-full bg-green-600 text-white py-2 rounded-lg text-sm hover:bg-green-700 flex items-center justify-center gap-2">
                  <Check size={16} /> Record Purchase
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2">
        <button onClick={() => setTab('materials')} className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === 'materials' ? 'bg-blue-600 text-white' : 'bg-white border text-gray-600'}`}>Materials</button>
        <button onClick={() => setTab('purchases')} className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === 'purchases' ? 'bg-blue-600 text-white' : 'bg-white border text-gray-600'}`}>Purchase History</button>
      </div>

      {tab === 'materials' ? (
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Stock</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Price/Unit</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Reorder Level</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Value</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Status</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody>
              {materials.map((m) => (
                <tr key={m.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{m.name}</td>
                  <td className="px-4 py-3 text-right">{m.current_stock} {m.unit}</td>
                  <td className="px-4 py-3 text-right">₹{m.price_per_unit.toLocaleString('en-IN')}</td>
                  <td className="px-4 py-3 text-right">{m.reorder_level} {m.unit}</td>
                  <td className="px-4 py-3 text-right">₹{(m.current_stock * m.price_per_unit).toLocaleString('en-IN')}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${m.current_stock <= m.reorder_level ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
                      {m.current_stock <= m.reorder_level ? 'Low' : 'OK'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button onClick={() => remove(m.id)} className="text-gray-400 hover:text-red-600"><Trash2 size={16} /></button>
                  </td>
                </tr>
              ))}
              {materials.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No materials yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Date</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Material</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Quantity</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Price/Unit</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Total</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Supplier</th>
              </tr>
            </thead>
            <tbody>
              {purchases.map((p) => (
                <tr key={p.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3">{new Date(p.date).toLocaleDateString()}</td>
                  <td className="px-4 py-3">{materials.find((m) => m.id === p.raw_material_id)?.name || '-'}</td>
                  <td className="px-4 py-3 text-right">{p.quantity}</td>
                  <td className="px-4 py-3 text-right">₹{p.price_per_unit.toLocaleString('en-IN')}</td>
                  <td className="px-4 py-3 text-right">₹{p.total_price.toLocaleString('en-IN')}</td>
                  <td className="px-4 py-3">{p.supplier || '-'}</td>
                </tr>
              ))}
              {purchases.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No purchases recorded yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
