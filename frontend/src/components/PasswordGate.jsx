import { useState, useEffect } from 'react';
import { Lock } from 'lucide-react';

const HASH = '4b5e15af13502e020fe344860f11a4aff626ca4e13490bc6f4d51fa8d2b552c6';

async function sha256(text) {
  const data = new TextEncoder().encode(text);
  const buf = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
}

export default function PasswordGate({ children }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const token = sessionStorage.getItem('ani_auth');
    if (token === 'authenticated') setAuthenticated(true);
    setChecking(false);
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const hash = await sha256(password);
    if (hash === HASH) {
      sessionStorage.setItem('ani_auth', 'authenticated');
      setAuthenticated(true);
    } else {
      setError('Incorrect password');
      setPassword('');
    }
  }

  if (checking) return null;
  if (authenticated) return children;

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="bg-slate-800 rounded-2xl shadow-2xl p-8 w-full max-w-sm border border-slate-700">
        <div className="flex flex-col items-center mb-6">
          <div className="bg-blue-600 p-3 rounded-full mb-4">
            <Lock size={28} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">ANI Enterprises</h1>
          <p className="text-slate-400 text-sm mt-1">Enter password to continue</p>
        </div>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Password"
            autoFocus
            className="w-full px-4 py-3 rounded-lg bg-slate-700 border border-slate-600 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
          <button
            type="submit"
            className="w-full mt-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
          >
            Unlock
          </button>
        </form>
      </div>
    </div>
  );
}
