import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Mail, MessageSquare, User } from 'lucide-react';
import { getAdvisors } from '../api/portal.js';
import PageHeader from '../components/ui/PageHeader.jsx';
import EmptyState from '../components/ui/EmptyState.jsx';
import { PageSpinner } from '../components/ui/Spinner.jsx';

function AdvisorCard({ advisor, onMessage }) {
  const initials = `${advisor.first_name?.[0] ?? ''}${advisor.last_name?.[0] ?? ''}`.toUpperCase() || 'A';

  return (
    <div className="card p-6 flex flex-col sm:flex-row items-start sm:items-center gap-4">
      {/* Avatar */}
      <div className="w-14 h-14 rounded-full bg-brand-600 flex items-center justify-center text-white text-lg font-semibold flex-shrink-0">
        {initials}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white">
          {advisor.first_name} {advisor.last_name}
        </h3>
        {advisor.role && (
          <p className="text-sm text-gray-500 dark:text-gray-400 capitalize mt-0.5">
            {advisor.role.replace(/_/g, ' ')}
          </p>
        )}
        {advisor.email && (
          <a
            href={`mailto:${advisor.email}`}
            className="inline-flex items-center gap-1.5 text-sm text-brand-600 dark:text-brand-400 hover:underline mt-1"
          >
            <Mail className="w-3.5 h-3.5" />
            {advisor.email}
          </a>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          onClick={onMessage}
          className="btn-primary"
        >
          <MessageSquare className="w-4 h-4" />
          Send Message
        </button>
      </div>
    </div>
  );
}

export default function AdvisorPage() {
  const navigate = useNavigate();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['advisors'],
    queryFn: getAdvisors,
  });

  const advisors = data?.results ?? data ?? [];

  if (isLoading) return <PageSpinner />;

  return (
    <div>
      <PageHeader
        title="My Advisor"
        subtitle="Your assigned advisory team"
      />

      {isError ? (
        <div className="card p-6 text-center text-sm text-red-600 dark:text-red-400">
          Unable to load advisor information. Please try again later.
        </div>
      ) : advisors.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={User}
            title="No advisor assigned yet"
            description="Your advisor will be assigned soon. You'll receive a notification when this happens."
          />
        </div>
      ) : (
        <div className="space-y-4">
          {advisors.map((advisor) => (
            <AdvisorCard
              key={advisor.id}
              advisor={advisor}
              onMessage={() => navigate('/messages')}
            />
          ))}
        </div>
      )}

      {/* Info note */}
      <div className="mt-6 p-4 rounded-xl bg-brand-50 dark:bg-brand-900/20 border border-brand-100 dark:border-brand-800">
        <p className="text-sm text-brand-700 dark:text-brand-300">
          <strong>Note:</strong> Your advisor manages your financial plan and goals. Use the messaging system to communicate securely.
        </p>
      </div>
    </div>
  );
}
