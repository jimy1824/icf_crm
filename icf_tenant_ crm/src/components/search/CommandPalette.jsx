import { useEffect, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { Briefcase, Search, Users, X } from 'lucide-react';
import { setCommandPalette } from '../../store/uiSlice.js';
import { searchApi } from '../../api/search.js';
import { useDebounce } from '../../hooks/useDebounce.js';
import Spinner from '../ui/Spinner.jsx';

export default function CommandPalette() {
  const open = useSelector((s) => s.ui.commandPaletteOpen);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const debouncedQ = useDebounce(q, 300);

  useEffect(() => {
    if (open) { setQ(''); setResults([]); setTimeout(() => inputRef.current?.focus(), 50); }
  }, [open]);

  useEffect(() => {
    if (!debouncedQ.trim()) { setResults([]); return; }
    setLoading(true);
    searchApi.global(debouncedQ)
      .then((d) => setResults(d?.results ?? d ?? []))
      .catch(() => setResults([]))
      .finally(() => setLoading(false));
  }, [debouncedQ]);

  function close() { dispatch(setCommandPalette(false)); }

  function go(r) {
    close();
    if (r.type === 'lead')   navigate(`/leads/${r.id}`);
    if (r.type === 'client') navigate(`/clients/${r.id}`);
    if (r.type === 'campaign') navigate(`/campaigns/${r.id}`);
  }

  if (!open) return null;

  const IconFor = (type) => type === 'client' ? Briefcase : Users;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={close} />
      <div className="relative w-full max-w-lg bg-white dark:bg-gray-900 rounded-2xl shadow-modal border border-gray-100 dark:border-gray-800 overflow-hidden animate-fade-in">
        {/* Input */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-gray-100 dark:border-gray-800">
          <Search className="w-4.5 h-4.5 text-gray-400 flex-shrink-0" style={{ width: 18, height: 18 }} />
          <input
            ref={inputRef}
            className="flex-1 text-sm bg-transparent outline-none text-gray-900 dark:text-white placeholder:text-gray-400"
            placeholder="Search leads, clients, campaigns…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          {loading && <Spinner size="sm" className="text-brand-500" />}
          <button onClick={close} className="btn-ghost p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto py-2">
          {results.map((r) => {
            const Icon = IconFor(r.type);
            return (
              <button
                key={`${r.type}-${r.id}`}
                onClick={() => go(r)}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors group"
              >
                <div className="w-7 h-7 rounded-lg bg-brand-50 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
                  <Icon className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate group-hover:text-brand-600">
                    {r.name ?? r.title ?? r.subject}
                  </p>
                  <p className="text-xs text-gray-400 capitalize mt-0.5">{r.type}</p>
                </div>
              </button>
            );
          })}
          {!loading && q.length > 1 && results.length === 0 && (
            <p className="text-center text-sm text-gray-400 py-8">No results for "{q}"</p>
          )}
          {!q && (
            <p className="text-center text-xs text-gray-400 py-6">Type to search across leads, clients, and campaigns</p>
          )}
        </div>

        <div className="border-t border-gray-100 dark:border-gray-800 px-4 py-2 flex items-center gap-4">
          <span className="text-[10px] text-gray-400"><kbd className="font-mono bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">↵</kbd> select</span>
          <span className="text-[10px] text-gray-400"><kbd className="font-mono bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
}
