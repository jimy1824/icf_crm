import { Link } from 'react-router-dom';
import { ShieldOff } from 'lucide-react';

export default function AccessDeniedPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-brand-900 flex items-center justify-center p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-red-600/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full bg-brand-600/10 blur-3xl" />
      </div>

      <div className="relative text-center max-w-sm">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-red-600/20 border border-red-500/20 mb-6">
          <ShieldOff className="w-8 h-8 text-red-400" />
        </div>
        <h1 className="text-2xl font-bold text-white mb-3">Access Denied</h1>
        <p className="text-gray-400 text-sm leading-relaxed mb-8">
          The Super Panel is restricted to authorised platform operators —
          Super Admin, Support, and Compliance Officer roles only.
          Your account does not have operator access.
        </p>
        <Link
          to="/login"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 text-white
                     text-sm font-semibold hover:bg-brand-700 transition-colors"
        >
          Back to Login
        </Link>
      </div>
    </div>
  );
}
