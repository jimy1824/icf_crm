import { useState } from 'react';
import { AlertCircle, X } from 'lucide-react';

export default function ErrorAlert({ error, className = '' }) {
  const [dismissed, setDismissed] = useState(false);
  if (!error || dismissed) return null;
  const msg = error?.message || error?.data?.detail || String(error);
  return (
    <div className={`flex items-start gap-3 px-4 py-3 rounded-xl bg-danger-50 dark:bg-danger-900/20 border border-danger-100 dark:border-danger-800 text-danger-700 dark:text-danger-400 ${className}`}>
      <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
      <p className="text-sm flex-1">{msg}</p>
      <button onClick={() => setDismissed(true)} className="text-danger-400 hover:text-danger-600">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
