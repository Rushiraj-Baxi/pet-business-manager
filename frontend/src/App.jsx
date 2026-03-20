import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { LayoutDashboard, Package, Layers, ShoppingCart, Factory, BarChart3, MessageSquare, Trash2, Wallet, FileText } from 'lucide-react';
import { useState } from 'react';
import { api } from './api';
import PasswordGate from './components/PasswordGate';
import Dashboard from './pages/Dashboard';
import Products from './pages/Products';
import Materials from './pages/Materials';
import Sales from './pages/Sales';
import Production from './pages/Production';
import Analytics from './pages/Analytics';
import Chat from './pages/Chat';
import CostsLiabilities from './pages/CostsLiabilities';
import Reports from './pages/Reports';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/products', icon: Package, label: 'Products' },
  { to: '/materials', icon: Layers, label: 'Raw Materials' },
  { to: '/sales', icon: ShoppingCart, label: 'Sales' },
  { to: '/costs', icon: Wallet, label: 'Costs & Liabilities' },
  { to: '/production', icon: Factory, label: 'Production' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/reports', icon: FileText, label: 'Reports' },
  { to: '/chat', icon: MessageSquare, label: 'AI Chat' },
];

export default function App() {
  const [clearing, setClearing] = useState(false);

  async function handleClearAll() {
    if (!confirm('⚠️ This will permanently delete ALL data (products, sales, materials, production, expenses, charts, and chat history).\n\nAre you sure?')) return;
    if (!confirm('This cannot be undone. Type OK to confirm.\n\nReally delete everything?')) return;
    setClearing(true);
    try {
      await api.clearAllData();
      window.location.reload();
    } catch (e) {
      alert('Failed to clear data: ' + e.message);
    }
    setClearing(false);
  }

  return (
    <PasswordGate>
    <BrowserRouter>
      <div className="flex h-screen">
        {/* Sidebar */}
        <aside className="w-64 bg-slate-900 text-white flex flex-col shrink-0">
          <div className="p-5 border-b border-slate-700">
            <h1 className="text-xl font-bold">📊 ANI Enterprises</h1>
            <p className="text-slate-400 text-xs mt-1">Preforms & Caps Manager</p>
          </div>
          <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
            {navItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                    isActive ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                  }`
                }
              >
                <Icon size={18} />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="p-4 border-t border-slate-700 space-y-3">
            <button
              onClick={handleClearAll}
              disabled={clearing}
              className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-xs text-red-400 hover:bg-red-900/30 hover:text-red-300 transition-colors disabled:opacity-50"
            >
              <Trash2 size={14} /> {clearing ? 'Clearing...' : 'Clear All Data'}
            </button>
            <div className="text-xs text-slate-500">
              v1.0 — Local Installation
            </div>
          </div>
        </aside>

        {/* Main area */}
        <main className="flex-1 overflow-y-auto bg-gray-50">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/products" element={<Products />} />
            <Route path="/materials" element={<Materials />} />
            <Route path="/sales" element={<Sales />} />
            <Route path="/costs" element={<CostsLiabilities />} />
            <Route path="/production" element={<Production />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/chat" element={<Chat />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
    </PasswordGate>
  );
}
