import { useState } from 'react';
import { Plus, X } from 'lucide-react';
import { plansApi } from '../../api/tenants.js';
import { useFetch } from '../../hooks/useFetch.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import { SkeletonRow } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';

function fmt(val) {
  return val === 0 ? '∞' : val;
}

const BLANK = { name: '', max_leads: 0, max_users: 0, max_storage_gb: 0, max_campaigns: 0 };

export default function PlanListPage() {
  const { data: plans, loading, error, refetch } = useFetch(() => plansApi.list());
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(BLANK);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  function set(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function cancel() {
    setShowForm(false);
    setForm(BLANK);
    setSaveError(null);
  }

  async function handleCreate(e) {
    e.preventDefault();
    setSaving(true); setSaveError(null);
    try {
      await plansApi.create({
        ...form,
        max_leads: Number(form.max_leads),
        max_users: Number(form.max_users),
        max_storage_gb: Number(form.max_storage_gb),
        max_campaigns: Number(form.max_campaigns),
      });
      cancel();
      refetch();
    } catch (err) { setSaveError(err); }
    finally { setSaving(false); }
  }

  return (
    <div>
      <PageHeader
        title="Subscription Plans"
        subtitle="Plans define resource limits for all tenants."
        actions={
          !showForm && (
            <button className="btn-primary" onClick={() => setShowForm(true)}>
              <Plus className="w-4 h-4" />
              New Plan
            </button>
          )
        }
      />

      {/* Inline create form */}
      {showForm && (
        <div className="card p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Create Plan</h2>
            <button onClick={cancel} className="btn-ghost p-1.5">
              <X className="w-4 h-4" />
            </button>
          </div>
          <ErrorAlert error={saveError} className="mb-4" />
          <form onSubmit={handleCreate}>
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-4">
              {[
                { key: 'name',           label: 'Plan Name',           type: 'text',   required: true },
                { key: 'max_leads',      label: 'Max Leads (0=∞)',     type: 'number' },
                { key: 'max_users',      label: 'Max Users (0=∞)',     type: 'number' },
                { key: 'max_storage_gb', label: 'Storage GB (0=∞)',    type: 'number' },
                { key: 'max_campaigns',  label: 'Max Campaigns (0=∞)', type: 'number' },
              ].map(({ key, label, type, required }) => (
                <div key={key} className="space-y-1.5">
                  <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">
                    {label}{required && <span className="text-red-400 ml-0.5">*</span>}
                  </label>
                  <input
                    type={type}
                    className="input"
                    min={type === 'number' ? 0 : undefined}
                    value={form[key]}
                    onChange={(e) => set(key, e.target.value)}
                    required={required}
                  />
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-3">
              <button type="button" className="btn-ghost" onClick={cancel}>Cancel</button>
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? <><Spinner size="sm" />Creating…</> : 'Create Plan'}
              </button>
            </div>
          </form>
        </div>
      )}

      <ErrorAlert error={error} className="mb-4" />

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50/60 dark:bg-gray-800/60">
            <tr>
              <th className="th">Name</th>
              <th className="th text-center">Max Leads</th>
              <th className="th text-center">Max Users</th>
              <th className="th text-center hidden md:table-cell">Storage GB</th>
              <th className="th text-center hidden md:table-cell">Max Campaigns</th>
            </tr>
          </thead>
          <tbody>
            {loading && [1, 2, 3].map((i) => <SkeletonRow key={i} cols={5} />)}
            {!loading && (plans ?? []).map((p) => (
              <tr key={p.id} className="hover:bg-gray-50/70 dark:hover:bg-gray-700/30 transition-colors">
                <td className="td font-medium text-gray-900 dark:text-white">{p.name}</td>
                <td className="td text-center text-gray-600 dark:text-gray-300">{fmt(p.max_leads)}</td>
                <td className="td text-center text-gray-600 dark:text-gray-300">{fmt(p.max_users)}</td>
                <td className="td text-center text-gray-600 dark:text-gray-300 hidden md:table-cell">{fmt(p.max_storage_gb)}</td>
                <td className="td text-center text-gray-600 dark:text-gray-300 hidden md:table-cell">{fmt(p.max_campaigns)}</td>
              </tr>
            ))}
            {!loading && (plans ?? []).length === 0 && (
              <tr>
                <td colSpan={5} className="td text-center text-gray-400 py-10">No plans configured yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
