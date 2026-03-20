import { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import { Send, Upload, Trash2, Bot, User, FileText, CheckCircle2, RefreshCw } from 'lucide-react';

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [actionBanner, setActionBanner] = useState(null);
  const endRef = useRef(null);
  const fileRef = useRef(null);

  useEffect(() => { loadHistory(); }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  async function loadHistory() {
    const h = await api.getChatHistory();
    setMessages(h);
  }

  async function send() {
    if (!input.trim() && !uploadResult) return;
    let msg = input.trim();
    if (uploadResult) {
      msg = msg ? `${msg}\n\n[Uploaded file: ${uploadResult.original_filename}]\nData: ${JSON.stringify(uploadResult.preview || uploadResult.text || uploadResult.extracted_text || uploadResult, null, 2).slice(0, 3000)}` : `I uploaded a file: ${uploadResult.original_filename}. Here is the extracted data:\n${JSON.stringify(uploadResult.preview || uploadResult.text || uploadResult.extracted_text || uploadResult, null, 2).slice(0, 3000)}\n\nPlease analyze this data and suggest how to import it into the system.`;
    }
    setMessages((prev) => [...prev, { role: 'user', message: msg, timestamp: new Date().toISOString() }]);
    setInput('');
    setUploadResult(null);
    setLoading(true);
    setActionBanner(null);
    try {
      const res = await api.sendChat(msg);
      setMessages((prev) => [...prev, { role: 'assistant', message: res.message, timestamp: new Date().toISOString() }]);
      if (res.actions_performed) {
        const successes = (res.action_results || []).filter(r => r.ok).length;
        const failures = (res.action_results || []).filter(r => !r.ok).length;
        const affected = res.affected_pages || [];
        setActionBanner({ successes, failures, results: res.action_results || [], affected });
        // Dispatch refresh events so other pages auto-refresh when navigated to
        for (const page of affected) {
          window.dispatchEvent(new CustomEvent(`${page}-refresh`));
        }
        // Auto-hide banner after 15 seconds
        setTimeout(() => setActionBanner(null), 15000);
      }
    } catch (e) {
      setMessages((prev) => [...prev, { role: 'assistant', message: `Error: ${e.message}`, timestamp: new Date().toISOString() }]);
    }
    setLoading(false);
  }

  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setLoading(true);
    try {
      const result = await api.uploadFile(file);
      setUploadResult(result);
      setMessages((prev) => [...prev, { role: 'system', message: `📎 File "${result.original_filename}" uploaded & processed (${result.type}). ${result.row_count ? `${result.row_count} rows found.` : ''} Type a message to analyze it with AI.`, timestamp: new Date().toISOString() }]);
    } catch (e) {
      setMessages((prev) => [...prev, { role: 'system', message: `Upload failed: ${e.message}`, timestamp: new Date().toISOString() }]);
    }
    setLoading(false);
    e.target.value = '';
  }

  async function clearAll() {
    if (!confirm('Clear all chat history?')) return;
    await api.clearChat();
    setMessages([]);
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b bg-white flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">AI Assistant</h1>
          <p className="text-gray-500 text-sm">Ask about your business, upload files for data import</p>
        </div>
        <button onClick={clearAll} className="text-gray-400 hover:text-red-500 flex items-center gap-1 text-sm"><Trash2 size={16} /> Clear</button>
      </div>

      {/* Action banner */}
      {actionBanner && (
        <div className="mx-6 mt-2 bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm">
          <div className="flex items-center gap-2 text-green-700 font-medium">
            <CheckCircle2 size={18} />
            {actionBanner.successes} action{actionBanner.successes !== 1 ? 's' : ''} performed!
            {actionBanner.failures > 0 && <span className="text-red-600">({actionBanner.failures} failed)</span>}
            <button onClick={() => setActionBanner(null)} className="ml-auto text-green-500 hover:text-green-700">✕</button>
          </div>
          <div className="mt-1 text-green-600 text-xs space-y-0.5">
            {actionBanner.results.map((r, i) => (
              <div key={i}>{r.ok ? '✅' : '❌'} {r.detail}</div>
            ))}
          </div>
          {actionBanner.affected && actionBanner.affected.length > 0 && (
            <div className="mt-2 text-xs text-blue-600">
              Updated pages: {actionBanner.affected.map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(', ')} — data will refresh automatically.
            </div>
          )}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin">
        {messages.length === 0 && (
          <div className="text-center py-20">
            <Bot size={48} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-400 text-lg">Ask me anything about your business!</p>
            <div className="mt-4 flex flex-wrap gap-2 justify-center">
              {[
                "What's my best selling product?",
                "How much profit did I make this month?",
                "Add a new product: 25g preform, sell ₹3, cost ₹2, stock 1000",
                "Record a sale of 500 units of 25g preform to ABC Corp",
                "Add raw material PET Resin, 5000 kg at ₹85/kg",
                "What's my current stock levels?",
              ].map((q) => (
                <button key={q} onClick={() => { setInput(q); }} className="text-sm bg-blue-50 text-blue-600 px-3 py-1.5 rounded-lg hover:bg-blue-100">{q}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : ''}`}>
            {m.role !== 'user' && (
              <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${m.role === 'assistant' ? 'bg-blue-100' : 'bg-gray-100'}`}>
                {m.role === 'assistant' ? <Bot size={16} className="text-blue-600" /> : <FileText size={16} className="text-gray-500" />}
              </div>
            )}
            <div className={`max-w-[70%] rounded-xl px-4 py-3 text-sm ${
              m.role === 'user' ? 'bg-blue-600 text-white' :
              m.role === 'system' ? 'bg-amber-50 text-amber-800 border border-amber-200' :
              'bg-white border shadow-sm text-gray-800'
            }`}>
              <div className="whitespace-pre-wrap">{m.message}</div>
              <div className={`text-xs mt-1 ${m.role === 'user' ? 'text-blue-200' : 'text-gray-400'}`}>
                {new Date(m.timestamp).toLocaleTimeString()}
              </div>
            </div>
            {m.role === 'user' && (
              <div className="shrink-0 w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                <User size={16} className="text-white" />
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
              <Bot size={16} className="text-blue-600" />
            </div>
            <div className="bg-white border shadow-sm rounded-xl px-4 py-3">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Upload indicator */}
      {uploadResult && (
        <div className="mx-6 mb-2 bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 text-sm text-amber-700 flex items-center gap-2">
          <FileText size={16} /> 📎 {uploadResult.original_filename} ready — ask AI to analyze it
          <button onClick={() => setUploadResult(null)} className="ml-auto text-amber-500 hover:text-red-500">✕</button>
        </div>
      )}

      {/* Input */}
      <div className="px-6 py-4 border-t bg-white">
        <div className="flex gap-3 items-end">
          <input type="file" ref={fileRef} onChange={handleUpload} accept=".xlsx,.xls,.csv,.pdf,.png,.jpg,.jpeg" className="hidden" />
          <button onClick={() => fileRef.current?.click()} className="shrink-0 p-2.5 rounded-lg border text-gray-500 hover:bg-gray-50 hover:text-blue-600" title="Upload file">
            <Upload size={20} />
          </button>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about sales, profits, stock, wastage... or upload a file"
            rows={1}
            className="flex-1 border rounded-lg px-4 py-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button onClick={send} disabled={loading} className="shrink-0 p-2.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}
