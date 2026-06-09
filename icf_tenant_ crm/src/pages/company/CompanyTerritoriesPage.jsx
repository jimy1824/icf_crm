import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Map, Plus, Trash2 } from 'lucide-react';
import {
  getTerritories, createTerritory, updateTerritory, deleteTerritory,
  getTerritoryAdvisors, assignAdvisorToTerritory, removeAdvisorFromTerritory,
  getEmployees,
} from '../../api/company.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import ConfirmModal from '../../components/ui/ConfirmModal.jsx';
import { useAuth } from '../../hooks/useAuth.js';

function TerritoryRow({ territory, canManage, onDelete }) {
  const [expanded, setExpanded] = useState(false);
  const qc = useQueryClient();

  const { data: advisors, isLoading: advisorsLoading } = useQuery({
    queryKey: ['territory-advisors', territory.id],
    queryFn: () => getTerritoryAdvisors(territory.id),
    enabled: expanded,
  });

  const { data: employeeData } = useQuery({
    queryKey: ['company-employees', 1, 100, '', '', ''],
    queryFn: () => getEmployees({ page: 1, page_size: 100 }),
    enabled: expanded && canManage,
  });

  const assignMutation = useMutation({
    mutationFn: (advisor_id) => assignAdvisorToTerritory(territory.id, advisor_id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['territory-advisors', territory.id] }),
  });

  const removeMutation = useMutation({
    mutationFn: (advisorId) => removeAdvisorFromTerritory(territory.id, advisorId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['territory-advisors', territory.id] }),
  });

  const employees = employeeData?.results ?? [];
  const assignedAdvisorIds = new Set((advisors ?? []).map((a) => a.advisor?.id));

  return (
    <>
      <tr className="hover:bg-gray-50/60 dark:hover:bg-gray-800/60 cursor-pointer" onClick={() => setExpanded((e) => !e)}>
        <td className="td font-medium text-gray-900 dark:text-white text-xs">{territory.name}</td>
        <td className="td text-xs text-gray-500">{territory.region ?? '—'}</td>
        <td className="td text-xs text-gray-500">{territory.advisor_count ?? 0}</td>
        <td className="td text-xs text-gray-500">{territory.lead_count ?? 0}</td>
        <td className="td"><Badge status={territory.is_active ? 'active' : 'inactive'} showDot /></td>
        <td className="td">
          {canManage && (
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(territory); }}
              className="text-red-500 hover:text-red-600 p-1"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={6} className="bg-gray-50 dark:bg-gray-800/40 px-6 py-4">
            <p className="text-xs font-medium text-gray-600 dark:text-gray-300 mb-2">Advisors in this territory</p>
            {advisorsLoading ? (
              <div className="skeleton h-3 w-48 rounded" />
            ) : (
              <div className="flex flex-wrap gap-2">
                {(advisors ?? []).map((a) => (
                  <span key={a.id} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-xs">
                    {a.advisor_name ?? a.advisor?.email ?? 'Unknown'}
                    {canManage && (
                      <button
                        onClick={() => removeMutation.mutate(a.advisor?.id ?? a.advisor_id)}
                        className="text-gray-400 hover:text-red-500 ml-0.5"
                      >×</button>
                    )}
                  </span>
                ))}
                {(advisors ?? []).length === 0 && (
                  <span className="text-xs text-gray-400">No advisors assigned.</span>
                )}
              </div>
            )}
            {canManage && (
              <select
                className="mt-3 text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800"
                defaultValue=""
                onChange={(e) => {
                  if (e.target.value) {
                    assignMutation.mutate(Number(e.target.value));
                    e.target.value = '';
                  }
                }}
              >
                <option value="">+ Assign advisor…</option>
                {employees
                  .filter((emp) => !assignedAdvisorIds.has(emp.user?.id))
                  .map((emp) => (
                    <option key={emp.id} value={emp.user?.id}>{emp.full_name}</option>
                  ))}
              </select>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function CreateTerritoryModal({ onClose, onCreate }) {
  const [form, setForm] = useState({ name: '', region: '', description: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) { setError('Name is required.'); return; }
    setSaving(true);
    try {
      await createTerritory(form);
      onCreate();
    } catch {
      setError('Failed to create territory.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl w-full max-w-sm p-6">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-4">New Territory</h2>
        {error && <p className="text-xs text-red-600 mb-3">{error}</p>}
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="label">Name</label>
            <input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} className="input" />
          </div>
          <div>
            <label className="label">Region <span className="text-gray-400">(optional)</span></label>
            <input value={form.region} onChange={(e) => setForm((f) => ({ ...f, region: e.target.value }))} className="input" />
          </div>
          <div>
            <label className="label">Description <span className="text-gray-400">(optional)</span></label>
            <textarea value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} className="input h-20 resize-none" />
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="btn-secondary btn-sm">Cancel</button>
            <button type="submit" className="btn-primary btn-sm" disabled={saving}>
              {saving ? 'Creating…' : 'Create Territory'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function CompanyTerritoriesPage() {
  const { isFirmAdmin } = useAuth();
  const canManage = isFirmAdmin();
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ['company-territories'],
    queryFn: () => getTerritories(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => deleteTerritory(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['company-territories'] });
      setConfirmDelete(null);
    },
  });

  const territories = data?.results ?? data ?? [];

  return (
    <div>
      <PageHeader
        title="Territories"
        subtitle="Manage firm coverage areas and advisor assignments"
        icon={Map}
        actions={
          canManage && (
            <button onClick={() => setShowCreate(true)} className="btn-primary btn-sm">
              <Plus className="w-3.5 h-3.5" />
              New Territory
            </button>
          )
        }
      />

      <div className="card overflow-hidden mt-5">
        <table className="w-full">
          <thead>
            <tr>
              <th className="th">Territory</th>
              <th className="th hidden md:table-cell">Region</th>
              <th className="th hidden md:table-cell">Advisors</th>
              <th className="th hidden md:table-cell">Leads</th>
              <th className="th">Status</th>
              <th className="th w-10" />
            </tr>
          </thead>
          <tbody>
            {isLoading && [1, 2, 3].map((i) => (
              <tr key={i}>
                {[1, 2, 3, 4, 5, 6].map((j) => (
                  <td key={j} className="td"><div className="skeleton h-3 rounded w-full max-w-[120px]" /></td>
                ))}
              </tr>
            ))}
            {!isLoading && territories.map((t) => (
              <TerritoryRow
                key={t.id}
                territory={t}
                canManage={canManage}
                onDelete={setConfirmDelete}
              />
            ))}
            {!isLoading && territories.length === 0 && (
              <tr>
                <td colSpan={6} className="td py-10 text-center text-sm text-gray-400">
                  No territories yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <CreateTerritoryModal
          onClose={() => setShowCreate(false)}
          onCreate={() => {
            setShowCreate(false);
            qc.invalidateQueries({ queryKey: ['company-territories'] });
          }}
        />
      )}

      {confirmDelete && (
        <ConfirmModal
          title="Delete Territory"
          message={`Delete "${confirmDelete.name}"? This action cannot be undone.`}
          confirmLabel="Delete"
          danger
          onConfirm={() => deleteMutation.mutate(confirmDelete.id)}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </div>
  );
}
