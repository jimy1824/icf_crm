import { Link } from 'react-router-dom';
import { ShieldOff } from 'lucide-react';

export default function AccessDeniedPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-brand-900 flex items-center justify-center p-4">
      <div className="text-center max-w-sm">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-danger-600/20 border border-danger-500/20 mb-6">
          <ShieldOff className="w-8 h-8 text-danger-400" />
        </div>
        <h1 className="text-2xl font-bold text-white mb-3">Access Denied</h1>
        <p className="text-gray-400 text-sm leading-relaxed mb-8">
          This workspace is for authorized advisors and firm admins only.
        </p>
        <Link to="/login" className="btn-primary">Back to Login</Link>
      </div>
    </div>
  );
}
