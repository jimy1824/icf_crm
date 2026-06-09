import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Briefcase, Clock, Mail, MapPin, Phone, User } from 'lucide-react';
import { clientsApi } from '../../api/clients.js';
import { financialsApi } from '../../api/financials.js';
import { documentsApi } from '../../api/documents.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { PageSpinner, SkeletonCard } from '../../components/ui/Spinner.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';
import { format } from 'date-fns';

const TABS = ['Overview', 'Financial Profile', 'Goals', 'Documents', 'Communications', 'Timeline'];

function InfoRow({ label, value }) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-2.5 py-1.5">
      <span className="text-xs text-gray-400 w-28 flex-shrink-0">{label}</span>
      <span className="text-xs text-gray-800 dark:text-gray-200 font-medium">{value}</span>
    </div>
  );
}

function NetWorthCard({ profile, loading }) {
  if (loading) return <SkeletonCard />;
  if (!profile) return null;
  return (
    <div className="card p-5 border-l-4 border-brand-500">
      <p className="text-xs text-gray-400 mb-1">Net Worth (from backend — BRU-27)</p>
      <p className="text-2xl font-bold text-brand-600 dark:text-brand-400">
        {profile.net_worth != null
          ? new Intl.NumberFormat('en-US', { style: 'currency', currency: profile.currency ?? 'USD', maximumFractionDigits: 0 }).format(profile.net_worth)
          : '—'}
      </p>
      {profile.as_of_date && (
        <p className="text-[10px] text-gray-400 mt-1">as of {profile.as_of_date}</p>
      )}
    </div>
  );
}

function OverviewTab({ client, profile, profileLoading }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <div className="card p-5">
        <h3 className="section-title mb-3">Contact Info</h3>
        {[
          { icon: Mail,   label: 'Email',   value: client.email },
          { icon: Phone,  label: 'Phone',   value: client.phone },
          { icon: MapPin, label: 'Location', value: [client.city, client.state].filter(Boolean).join(', ') },
          { icon: User,   label: 'Advisor',  value: client.assigned_advisor_name },
          { icon: Briefcase, label: 'Household', value: client.household_name },
        ].map(({ icon: Icon, label, value }) => value ? (
          <div key={label} className="flex items-center gap-2.5 py-1.5">
            <Icon className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
            <div>
              <p className="text-[10px] text-gray-400">{label}</p>
              <p className="text-xs text-gray-800 dark:text-gray-200">{value}</p>
            </div>
          </div>
        ) : null)}
        <div className="pt-3 mt-2 border-t border-gray-100 dark:border-gray-800 space-y-1.5">
          <Badge status={client.kyc_status ?? 'pending'} showDot />
        </div>
      </div>

      <div className="space-y-4">
        <NetWorthCard profile={profile} loading={profileLoading} />
        {profile && (
          <div className="card p-5">
            <h3 className="section-title mb-3">Financial Summary</h3>
            <InfoRow label="Annual Income"
              value={profile.annual_income != null ? `$${Number(profile.annual_income).toLocaleString()}` : null} />
            <InfoRow label="Total Assets"
              value={profile.total_assets != null ? `$${Number(profile.total_assets).toLocaleString()}` : null} />
            <InfoRow label="Total Liabilities"
              value={profile.total_liabilities != null ? `$${Number(profile.total_liabilities).toLocaleString()}` : null} />
            <InfoRow label="Risk Tolerance" value={profile.risk_tolerance} />
            <InfoRow label="Employment"     value={profile.employment_status} />
          </div>
        )}
      </div>

      <div className="card p-5">
        <h3 className="section-title mb-3">Quick Actions</h3>
        <div className="space-y-2">
          <Link to={`/clients/${client.id}/financial-profile`} className="btn-outline btn-sm w-full justify-center">
            Financial Profile
          </Link>
          <Link to={`/clients/${client.id}/goals`} className="btn-outline btn-sm w-full justify-center">
            Goals
          </Link>
          <Link to={`/clients/${client.id}/documents`} className="btn-outline btn-sm w-full justify-center">
            Documents / KYC
          </Link>
          <Link to={`/clients/${client.id}/communications`} className="btn-outline btn-sm w-full justify-center">
            Communications
          </Link>
        </div>
      </div>
    </div>
  );
}

function TimelineTab({ client }) {
  const { data: timeline } = useQuery({
    queryKey: ['client-timeline', client.id],
    queryFn: () => clientsApi.getTimeline(client.id),
  });
  const entries = timeline?.results ?? timeline ?? [];

  return (
    <div className="card p-5">
      <h3 className="section-title mb-4 flex items-center gap-2">
        <Clock className="w-4 h-4 text-gray-400" /> Activity Timeline
      </h3>
      <div className="space-y-0">
        {entries.map((e, i) => (
          <div key={e.id ?? i} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div className="w-6 h-6 rounded-full bg-brand-50 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
                <Clock className="w-3 h-3 text-brand-400" />
              </div>
              {i < entries.length - 1 && <div className="w-px flex-1 bg-gray-100 dark:bg-gray-800 mt-1" />}
            </div>
            <div className="pb-4 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-xs font-medium text-gray-800 dark:text-gray-200">{e.actor ?? e.created_by ?? 'System'}</span>
                <span className="text-[10px] text-gray-400">{e.created_at?.slice(0,16).replace('T',' ')}</span>
                {e.is_private && <span className="text-[10px] font-medium text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded-full">Private</span>}
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-300">{e.body ?? e.description ?? e.note}</p>
            </div>
          </div>
        ))}
        {entries.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-8">No activity yet.</p>
        )}
      </div>
    </div>
  );
}

function DocumentsTab({ client }) {
  const { data } = useQuery({
    queryKey: ['documents', client.id],
    queryFn: () => documentsApi.list({ client: client.id }),
  });
  const docs = data?.results ?? data ?? [];

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800">
        <h3 className="section-title">Documents & KYC</h3>
        <Link to={`/clients/${client.id}/documents`} className="text-xs text-brand-600 font-medium">
          Manage Documents →
        </Link>
      </div>
      <table className="w-full">
        <thead><tr>
          <th className="th">Name</th>
          <th className="th">Type</th>
          <th className="th">Status</th>
          <th className="th hidden md:table-cell">Uploaded</th>
        </tr></thead>
        <tbody>
          {docs.slice(0, 8).map((d) => (
            <tr key={d.id} className="hover:bg-gray-50/60 dark:hover:bg-gray-800/60">
              <td className="td text-xs">{d.file_name ?? d.name}</td>
              <td className="td text-xs text-gray-500">{d.document_type}</td>
              <td className="td"><Badge status={d.kyc_status ?? d.status ?? 'pending'} /></td>
              <td className="td hidden md:table-cell text-xs text-gray-400">{d.uploaded_at?.slice(0,10)}</td>
            </tr>
          ))}
          {docs.length === 0 && (
            <tr><td colSpan={4} className="td text-center text-sm text-gray-400 py-6">No documents uploaded yet.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default function ClientDetailPage() {
  const { id } = useParams();
  const [tab, setTab] = useState('Overview');

  const { data: client, isLoading, error } = useQuery({
    queryKey: ['client', id],
    queryFn: () => clientsApi.get(id),
  });

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ['financial-profile', id],
    queryFn: () => financialsApi.getProfile(id),
    enabled: !!client,
  });

  if (isLoading) return <PageSpinner />;
  if (error) return <ErrorAlert error={error} />;
  if (!client) return null;

  const name = client.full_name ?? `${client.first_name} ${client.last_name}`;

  return (
    <div>
      <PageHeader
        crumbs={[{ label: 'Clients', to: '/clients' }, { label: name }]}
        title={name}
        subtitle={client.email}
        actions={
          <div className="flex items-center gap-2">
            <Link to={`/clients/${id}/edit`} className="btn-outline btn-sm">Edit</Link>
            <Link to={`/clients/${id}/financial-profile`} className="btn-primary btn-sm">Financial Profile</Link>
          </div>
        }
      />

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 dark:border-gray-700 mb-5 overflow-x-auto">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors
              ${tab === t
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'}`}>
            {t}
          </button>
        ))}
      </div>

      {tab === 'Overview' && <OverviewTab client={client} profile={profile} profileLoading={profileLoading} />}
      {tab === 'Financial Profile' && (
        <div className="text-center py-12">
          <Link to={`/clients/${id}/financial-profile`} className="btn-primary">Open Full Financial Profile</Link>
        </div>
      )}
      {tab === 'Goals' && (
        <div className="text-center py-12">
          <Link to={`/clients/${id}/goals`} className="btn-primary">Open Goals</Link>
        </div>
      )}
      {tab === 'Documents' && <DocumentsTab client={client} />}
      {tab === 'Communications' && (
        <div className="text-center py-12">
          <Link to={`/clients/${id}/communications`} className="btn-primary">Open Communications</Link>
        </div>
      )}
      {tab === 'Timeline' && <TimelineTab client={client} />}
    </div>
  );
}
