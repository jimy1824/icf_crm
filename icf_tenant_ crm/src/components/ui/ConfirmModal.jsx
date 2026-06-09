import { AlertTriangle, X } from 'lucide-react';
import Spinner from './Spinner.jsx';

export default function ConfirmModal({ title, message, danger, onConfirm, onCancel, loading }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-modal border border-gray-100 dark:border-gray-800 w-full max-w-sm p-6 animate-fade-in">
        <div className="flex items-start gap-4">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${danger ? 'bg-danger-50 dark:bg-danger-900/30' : 'bg-brand-50 dark:bg-brand-900/30'}`}>
            <AlertTriangle className={`w-5 h-5 ${danger ? 'text-danger-600' : 'text-brand-600'}`} />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900 dark:text-white">{title}</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{message}</p>
          </div>
          <button onClick={onCancel} className="btn-ghost p-1.5">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onCancel} className="btn-outline">Cancel</button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={danger ? 'btn-danger' : 'btn-primary'}
          >
            {loading && <Spinner size="sm" />}
            {danger ? 'Confirm' : 'OK'}
          </button>
        </div>
      </div>
    </div>
  );
}
