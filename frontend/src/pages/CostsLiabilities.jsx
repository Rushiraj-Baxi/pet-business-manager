import { useState, useEffect } from 'react';
import { api } from '../api';
import { Plus, Trash2, Save, X, IndianRupee, AlertTriangle } from 'lucide-react';

export default function CostsLiabilities() {
  const [entries, setEntries] = useState([]);
  const [editingEntry, setEditingEntry] = useState(null);
  const [editAmount, setEditAmount] = useState('');
  const [newEntry, setNewEntry] = useState(null);

  useEffect(() => { load(); }, []);

  useEffect(() => {
    const h = () => load();
    window.addEventListener('costs-refresh', h);
    return () => window.removeEventListener('costs-refresh', h);
  }, []);

  async function load() {
    try {
      setEntries(await api.getBusinessEntries());
    } catch (e) {
      console.error(e);
    }
  }

  async function saveEntry(id) {
    await api.updateBusinessEntry(id, { amount: Number(editAmount) });
    setEditingEntry(null);
    load();
  }

  async function addEntry() {
    if (!newEntry?.label) return;
    await api.createBusinessEntry({ category: newEntry.category, label: newEntry.label, amount: Number(newEntry.amount || 0) });
    setNewEntry(null);
    load();
  }

  async function removeEntry(id) {
    if (!confirm('Delete this entry?')) return;
    await api.deleteBusinessEntry(id);
    load();
  }

  const fmt = (n) => '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 });

  const costs = entries.filter(e => e.category === 'cost');
  const liabilities = entries.filter(e => e.category === 'liability');
  const totalCosts = costs.reduce((s, e) => s + e.amount, 0);
  const totalLiabilities = liabilities.reduce((s, e) => s + e.amount, 0);

  function renderTable(items, category, title, totalColor = 'text-gray-700') {
    return (
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-gray-800">{title}</h2>
          <button
            onClick={() => setNewEntry({ category, label: '', amount: '' })}
            className="flex items-center gap-1 text-blue-600 hover:text-blue-700 text-sm font-medium"
          >
            <Plus size={16} /> Add New
          </button>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b">
              <th className="text-left py-3 text-gray-500 font-medium">{category === 'cost' ? 'Cost Item' : 'Liability'}</th>
              <th className="text-right py-3 text-gray-500 font-medium">Amount</th>
              <th className="w-24"></th>
            </tr>
          </thead>
          <tbody>
            {items.map(e => (
              <tr key={e.id} className="border-b hover:bg-gray-50 transition-colors">
                <td className="py-3 text-gray-700 font-medium">{e.label}</td>
                <td className="py-3 text-right">
                  {editingEntry === e.id ? (
                    <input
                      type="number"
                      className="border rounded-lg px-3 py-1.5 w-40 text-right text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      value={editAmount}
                      onChange={ev => setEditAmount(ev.target.value)}
                      autoFocus
                      onKeyDown={ev => { if (ev.key === 'Enter') saveEntry(e.id); if (ev.key === 'Escape') setEditingEntry(null); }}
                    />
                  ) : (
                    <span
                      className="font-semibold cursor-pointer hover:text-blue-600 transition-colors"
                      onClick={() => { setEditingEntry(e.id); setEditAmount(e.amount); }}
                      title="Click to edit"
                    >
                      {fmt(e.amount)}
                    </span>
                  )}
                </td>
                <td className="py-3 text-right">
                  {editingEntry === e.id ? (
                    <span className="flex gap-2 justify-end">
                      <button onClick={() => saveEntry(e.id)} className="text-green-600 hover:text-green-700" title="Save"><Save size={16} /></button>
                      <button onClick={() => setEditingEntry(null)} className="text-gray-400 hover:text-gray-600" title="Cancel"><X size={16} /></button>
                    </span>
                  ) : (
                    <button onClick={() => removeEntry(e.id)} className="text-gray-300 hover:text-red-500 transition-colors" title="Delete"><Trash2 size={16} /></button>
                  )}
                </td>
              </tr>
            ))}
            {newEntry?.category === category && (
              <tr className="border-b bg-blue-50">
                <td className="py-3">
                  <input
                    className="border rounded-lg px-3 py-1.5 text-sm w-full focus:ring-2 focus:ring-blue-500"
                    placeholder={category === 'cost' ? 'e.g. PET Resin Cost' : 'e.g. Supplier Payables'}
                    value={newEntry.label}
                    onChange={ev => setNewEntry({...newEntry, label: ev.target.value})}
                    autoFocus
                    onKeyDown={ev => { if (ev.key === 'Enter' && newEntry.label) addEntry(); if (ev.key === 'Escape') setNewEntry(null); }}
                  />
                </td>
                <td className="py-3">
                  <input
                    type="number"
                    className="border rounded-lg px-3 py-1.5 text-sm w-full text-right focus:ring-2 focus:ring-blue-500"
                    placeholder="0"
                    value={newEntry.amount}
                    onChange={ev => setNewEntry({...newEntry, amount: ev.target.value})}
                    onKeyDown={ev => { if (ev.key === 'Enter' && newEntry.label) addEntry(); if (ev.key === 'Escape') setNewEntry(null); }}
                  />
                </td>
                <td className="py-3 text-right">
                  <span className="flex gap-2 justify-end">
                    <button onClick={addEntry} className="text-green-600 hover:text-green-700"><Save size={16} /></button>
                    <button onClick={() => setNewEntry(null)} className="text-gray-400 hover:text-gray-600"><X size={16} /></button>
                  </span>
                </td>
              </tr>
            )}
            {items.length === 0 && !newEntry && (
              <tr><td colSpan={3} className="py-8 text-center text-gray-400">No {category === 'cost' ? 'costs' : 'liabilities'} added yet. Click "Add New" to create one.</td></tr>
            )}
          </tbody>
          {items.length > 0 && (
            <tfoot>
              <tr className="border-t-2 border-gray-300">
                <td className="py-3 font-bold text-gray-700">Total</td>
                <td className={`py-3 text-right font-bold text-lg ${totalColor}`}>
                  {fmt(items.reduce((s, e) => s + e.amount, 0))}
                </td>
                <td></td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Costs & Liabilities</h1>
        <p className="text-gray-500 text-sm">Track operating costs, supplier payables, loans, and other liabilities</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Operating Costs</p>
              <p className="text-2xl font-bold mt-1">{fmt(totalCosts)}</p>
            </div>
            <div className="p-3 rounded-lg bg-yellow-50 text-yellow-600"><IndianRupee size={22} /></div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Liabilities</p>
              <p className="text-2xl font-bold mt-1 text-red-600">{fmt(totalLiabilities)}</p>
            </div>
            <div className="p-3 rounded-lg bg-red-50 text-red-600"><AlertTriangle size={22} /></div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Outflow</p>
              <p className="text-2xl font-bold mt-1">{fmt(totalCosts + totalLiabilities)}</p>
            </div>
            <div className="p-3 rounded-lg bg-purple-50 text-purple-600"><IndianRupee size={22} /></div>
          </div>
        </div>
      </div>

      {/* Tables Side by Side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {renderTable(costs, 'cost', 'Operating Costs', 'text-gray-700')}
        {renderTable(liabilities, 'liability', 'Liabilities', 'text-red-600')}
      </div>
    </div>
  );
}
