import { AlertCircle, X } from 'lucide-react';
import { useState } from 'react';

export default function ErrorAlert({ error, className = '' }) {
  const [dismissed, setDismissed] = useState(false);
  if (!error || dismissed) return null;

  const msg = error?.data?.detail
    || (Array.isArray(error?.data) ? error.data.join(' · ') : null)
    || error?.message
    || 'An unexpected error occurred.';

  return (
    <div className={`flex items-start gap-3 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 ${className}`} role="alert">
      <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
      <p className="text-sm text-red-700 dark:text-red-400 flex-1">{msg}</p>
      <button onClick={() => setDismissed(true)} className="text-red-400 hover:text-red-600 dark:hover:text-red-300 transition-colors">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
