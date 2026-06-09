import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Search, Ticket, X } from 'lucide-react';
import { tenantsApi } from '../../api/tenants.js';
import { supportApi } from '../../api/support.js';

export default function CommandPalette({ open, onClose }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState({ tenants: [], tickets: [] });
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (open) {
      setQuery('');
      setResults({ tenants: [], tickets: [] });
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    function handler(e) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (open) onClose();
      }
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  const search = useCallback(async (q) => {
    if (!q.trim()) { setResults({ tenants: [], tickets: [] }); return; }
    setLoading(true);
    try {
      const [tenants, tickets] = await Promise.allSettled([
        tenantsApi.list(),
        supportApi.listTickets({ status: '' }),
      ]);
      const tList = tenants.status === 'fulfilled' ? tenants.value ?? [] : [];
      const tkList = tickets.status === 'fulfilled'
        ? (tickets.value?.results ?? tickets.value ?? []) : [];
      const low = q.toLowerCase();
      setResults({
        tenants: tList.filter((t) =>
          t.firm_name.toLowerCase().includes(low) ||
          (t.company_email ?? '').toLowerCase().includes(low)
        ).slice(0, 4),
        tickets: tkList.filter((t) =>
          (t.subject ?? '').toLowerCase().includes(low)
        ).slice(0, 4),
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => search(query), 300);
    return () => clearTimeout(t);
  }, [query, search]);

  function go(path) {
    navigate(path);
    onClose();
  }

  const hasResults = results.tenants.length + results.tickets.length > 0;

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl bg-white dark:bg-gray-900 rounded-2xl shadow-modal border border-gray-100 dark:border-gray-700 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-gray-100 dark:border-gray-700">
          <Search className="w-4 h-4 text-gray-400 flex-shrink-0" />
          <input
            ref={inputRef}
            className="flex-1 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 outline-none bg-transparent"
            placeholder="Search tenants, tickets, users…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {query && (
            <button onClick={() => setQuery('')} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
              <X className="w-4 h-4" />
            </button>
          )}
          <kbd className="px-1.5 py-0.5 text-xs font-medium text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-600">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto divide-y divide-gray-50 dark:divide-gray-800">
          {loading && (
            <div className="flex items-center justify-center py-8 text-sm text-gray-400">
              Searching…
            </div>
          )}

          {!loading && !hasResults && query && (
            <div className="py-10 text-center text-sm text-gray-400">
              No results for <span className="font-medium text-gray-600 dark:text-gray-300">"{query}"</span>
            </div>
          )}

          {!loading && !query && (
            <div className="py-8 text-center text-sm text-gray-400">
              Start typing to search across the platform…
            </div>
          )}

          {results.tenants.length > 0 && (
            <div>
              <p className="px-4 py-2 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                Tenants
              </p>
              {results.tenants.map((t) => (
                <button
                  key={t.id}
                  className="flex items-center gap-3 w-full px-4 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-800 text-left transition-colors"
                  onClick={() => go(`/tenants/${t.id}`)}
                >
                  <div className="w-7 h-7 rounded-lg bg-brand-50 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
                    <Building2 className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{t.firm_name}</p>
                    <p className="text-xs text-gray-400 truncate">{t.company_email || t.subdomain || '—'}</p>
                  </div>
                  <span className={`ml-auto badge text-xs ${
                    t.status === 'active'
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800'
                      : 'bg-gray-100 text-gray-500 border border-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:border-gray-600'
                  }`}>{t.status}</span>
                </button>
              ))}
            </div>
          )}

          {results.tickets.length > 0 && (
            <div>
              <p className="px-4 py-2 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                Support Tickets
              </p>
              {results.tickets.map((t) => (
                <button
                  key={t.id}
                  className="flex items-center gap-3 w-full px-4 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-800 text-left transition-colors"
                  onClick={() => go(`/support/${t.id}`)}
                >
                  <div className="w-7 h-7 rounded-lg bg-violet-50 dark:bg-violet-900/30 flex items-center justify-center flex-shrink-0">
                    <Ticket className="w-3.5 h-3.5 text-violet-600 dark:text-violet-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{t.subject}</p>
                    <p className="text-xs text-gray-400">#{t.id} · {t.priority || 'normal'}</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-gray-100 dark:border-gray-700 flex items-center gap-4 text-xs text-gray-400">
          <span><kbd className="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-[10px]">↵</kbd> to select</span>
          <span><kbd className="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-[10px]">↑↓</kbd> to navigate</span>
          <span><kbd className="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-[10px]">ESC</kbd> to close</span>
        </div>
      </div>
    </div>
  );
}
