import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';
import {
  ArrowRight, Briefcase, Building2, CheckCircle, Clock,
  Mail, MapPin, MessageSquare, Phone, Plus, Send, Shield, User, UserPlus, X,
} from 'lucide-react';
import { leadsApi } from '../../api/leads.js';
import { financialsApi } from '../../api/financials.js';
import { documentsApi } from '../../api/documents.js';
import { communicationsApi } from '../../api/communications.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { PageSpinner, SkeletonCard, SkeletonRow } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';
import ConfirmModal from '../../components/ui/ConfirmModal.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';

const PIPELINE_STAGES = [
  'new', 'contacted', 'qualified', 'in_discussion', 'proposal_sent', 'closed_won', 'closed_lost',
];
const CLIENT_STATUSES = new Set(['client', 'former_client']);
const TABS = ['Overview', 'Financial Profile', 'Goals', 'Documents', 'Communications', 'Timeline'];

// ─────────────────────────────────────────────────────────────────────────────
// Shared helpers
// ─────────────────────────────────────────────────────────────────────────────

function Money({ value, currency = 'USD' }) {
  if (value == null) return <span className="text-gray-400">—</span>;
  return (
    <span className="font-semibold text-gray-900 dark:text-white">
      {new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(value)}
    </span>
  );
}

function FormField({ label, children }) {
  return (
    <div className="space-y-1.5">
      <label className="label">{label}</label>
      {children}
    </div>
  );
}

function InfoRow({ label, value }) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-2.5 py-1.5">
      <span className="text-xs text-gray-400 w-28 flex-shrink-0">{label}</span>
      <span className="text-xs text-gray-800 dark:text-gray-200 font-medium">{value}</span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Financial Profile tab
// ─────────────────────────────────────────────────────────────────────────────

function FinancialSummarySection({ profile, id }) {
  const qc = useQueryClient();
  const { register, handleSubmit } = useForm({
    defaultValues: {
      annual_income: profile?.annual_income ?? '',
      risk_tolerance: profile?.risk_tolerance ?? '',
      employment_status: profile?.employment_status ?? '',
      tax_bracket: profile?.tax_bracket ?? '',
      currency: profile?.currency ?? 'USD',
    },
  });

  const save = useMutation({
    mutationFn: (data) => profile
      ? financialsApi.updateProfile(id, data)
      : financialsApi.createProfile(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['financial-profile', id] }); toast.success('Profile saved'); },
    onError: (e) => toast.error(e.message),
  });

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      {/* Net worth card — read-only, backend-derived (BRU-27) */}
      <div className="card p-5 border-l-4 border-brand-500">
        <p className="text-xs text-gray-400 mb-1">Net Worth — derived by backend (BRU-27)</p>
        <div className="flex items-end gap-3">
          <span className="text-3xl font-bold text-brand-600 dark:text-brand-400">
            <Money value={profile?.net_worth} currency={profile?.currency} />
          </span>
          {profile?.as_of_date && <span className="text-xs text-gray-400 mb-1">as of {profile.as_of_date}</span>}
        </div>
        <div className="grid grid-cols-3 gap-3 mt-4">
          {[
            { label: 'Total Assets',      value: profile?.total_assets,       color: 'text-success-600' },
            { label: 'Total Liabilities', value: profile?.total_liabilities,  color: 'text-danger-600' },
            { label: 'Annual Income',     value: profile?.annual_income,      color: 'text-brand-600' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 text-center">
              <p className="text-[10px] text-gray-400 mb-1">{label}</p>
              <p className={`text-sm font-semibold ${color}`}><Money value={value} /></p>
            </div>
          ))}
        </div>
      </div>

      {/* Editable profile details */}
      <div className="card p-5">
        <h3 className="section-title mb-4">Profile Details</h3>
        <form onSubmit={handleSubmit((d) => save.mutate(d))} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Annual Income">
              <input type="number" className="input" step="1000" {...register('annual_income')} />
            </FormField>
            <FormField label="Currency">
              <select className="select" {...register('currency')}>
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="GBP">GBP</option>
                <option value="CAD">CAD</option>
              </select>
            </FormField>
            <FormField label="Risk Tolerance">
              <select className="select" {...register('risk_tolerance')}>
                <option value="">Select…</option>
                <option value="conservative">Conservative</option>
                <option value="moderate">Moderate</option>
                <option value="aggressive">Aggressive</option>
              </select>
            </FormField>
            <FormField label="Employment Status">
              <select className="select" {...register('employment_status')}>
                <option value="">Select…</option>
                <option value="employed">Employed</option>
                <option value="self_employed">Self-employed</option>
                <option value="retired">Retired</option>
                <option value="unemployed">Unemployed</option>
              </select>
            </FormField>
            <FormField label="Tax Bracket (%)">
              <input type="number" className="input" min="0" max="100" step="0.5" {...register('tax_bracket')} />
            </FormField>
          </div>
          <div className="flex justify-end">
            <button type="submit" className="btn-primary btn-sm" disabled={save.isPending}>
              {save.isPending && <Spinner size="sm" />}
              Save Profile
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function AccountsSection({ profile, id }) {
  const qc = useQueryClient();
  const { register, handleSubmit, reset } = useForm();

  const addAccount = useMutation({
    mutationFn: (data) => financialsApi.addAccount(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['financial-profile', id] }); toast.success('Account added'); reset(); },
    onError: (e) => toast.error(e.message),
  });
  const removeAccount = useMutation({
    mutationFn: (aid) => financialsApi.removeAccount(id, aid),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['financial-profile', id] }); toast.success('Account removed'); },
    onError: (e) => toast.error(e.message),
  });

  const accounts = profile?.accounts ?? [];

  return (
    <div className="space-y-5">
      <div className="card overflow-hidden">
        <div className="flex items-center gap-2 px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <Building2 className="w-4 h-4 text-gray-400" />
          <h3 className="section-title">Financial Accounts</h3>
        </div>
        <table className="w-full">
          <thead><tr>
            <th className="th">Account Name</th><th className="th">Type</th>
            <th className="th">Balance</th><th className="th hidden md:table-cell">Institution</th>
            <th className="th w-10" />
          </tr></thead>
          <tbody>
            {accounts.map((a) => (
              <tr key={a.id} className="hover:bg-gray-50/60 dark:hover:bg-gray-800/60">
                <td className="td text-sm">{a.name}</td>
                <td className="td text-xs text-gray-500">{a.account_type}</td>
                <td className="td text-sm font-medium"><Money value={a.balance} currency={a.currency} /></td>
                <td className="td hidden md:table-cell text-xs text-gray-400">{a.institution}</td>
                <td className="td">
                  <button onClick={() => removeAccount.mutate(a.id)} className="text-xs text-danger-600 hover:text-danger-700 font-medium">Remove</button>
                </td>
              </tr>
            ))}
            {accounts.length === 0 && (
              <tr><td colSpan={5} className="td text-center text-sm text-gray-400 py-6">No accounts added yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="card p-5">
        <h3 className="section-title mb-4">Add Account</h3>
        <form onSubmit={handleSubmit((d) => addAccount.mutate(d))} className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <FormField label="Name"><input className="input" {...register('name', { required: true })} placeholder="e.g. Checking" /></FormField>
          <FormField label="Type">
            <select className="select" {...register('account_type')}>
              <option value="checking">Checking</option><option value="savings">Savings</option>
              <option value="investment">Investment</option><option value="retirement">Retirement</option>
              <option value="real_estate">Real Estate</option><option value="other">Other</option>
            </select>
          </FormField>
          <FormField label="Balance"><input type="number" className="input" step="100" {...register('balance')} placeholder="0" /></FormField>
          <FormField label="Institution"><input className="input" {...register('institution')} placeholder="Bank name" /></FormField>
          <div className="col-span-full flex justify-end">
            <button type="submit" className="btn-primary btn-sm" disabled={addAccount.isPending}>
              {addAccount.isPending && <Spinner size="sm" />} Add Account
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function InsuranceSection({ profile, id }) {
  const qc = useQueryClient();
  const { register, handleSubmit, reset } = useForm();

  const addInsurance = useMutation({
    mutationFn: (data) => financialsApi.addInsurance(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['financial-profile', id] }); toast.success('Insurance added'); reset(); },
    onError: (e) => toast.error(e.message),
  });
  const removeInsurance = useMutation({
    mutationFn: (pid) => financialsApi.removeInsurance(id, pid),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['financial-profile', id] }); toast.success('Policy removed'); },
    onError: (e) => toast.error(e.message),
  });

  const policies = profile?.insurance_policies ?? [];

  return (
    <div className="space-y-5">
      <div className="card overflow-hidden">
        <div className="flex items-center gap-2 px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <Shield className="w-4 h-4 text-gray-400" />
          <h3 className="section-title">Insurance Policies</h3>
        </div>
        <table className="w-full">
          <thead><tr>
            <th className="th">Type</th><th className="th">Provider</th>
            <th className="th">Coverage</th><th className="th hidden md:table-cell">Premium /yr</th>
            <th className="th w-10" />
          </tr></thead>
          <tbody>
            {policies.map((p) => (
              <tr key={p.id} className="hover:bg-gray-50/60 dark:hover:bg-gray-800/60">
                <td className="td text-xs capitalize">{p.insurance_type?.replace(/_/g, ' ')}</td>
                <td className="td text-xs text-gray-500">{p.provider}</td>
                <td className="td text-sm font-medium"><Money value={p.coverage_amount} /></td>
                <td className="td hidden md:table-cell text-xs text-gray-400"><Money value={p.annual_premium} /></td>
                <td className="td">
                  <button onClick={() => removeInsurance.mutate(p.id)} className="text-xs text-danger-600 hover:text-danger-700 font-medium">Remove</button>
                </td>
              </tr>
            ))}
            {policies.length === 0 && (
              <tr><td colSpan={5} className="td text-center text-sm text-gray-400 py-6">No insurance policies yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="card p-5">
        <h3 className="section-title mb-4">Add Insurance Policy</h3>
        <form onSubmit={handleSubmit((d) => addInsurance.mutate(d))} className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <FormField label="Type">
            <select className="select" {...register('insurance_type')}>
              <option value="life">Life</option><option value="health">Health</option>
              <option value="disability">Disability</option><option value="long_term_care">Long-Term Care</option>
              <option value="auto">Auto</option><option value="home">Home</option><option value="other">Other</option>
            </select>
          </FormField>
          <FormField label="Provider"><input className="input" {...register('provider')} placeholder="Insurance co." /></FormField>
          <FormField label="Coverage Amount"><input type="number" className="input" step="1000" {...register('coverage_amount')} /></FormField>
          <FormField label="Annual Premium"><input type="number" className="input" step="100" {...register('annual_premium')} /></FormField>
          <div className="col-span-full flex justify-end">
            <button type="submit" className="btn-primary btn-sm" disabled={addInsurance.isPending}>
              {addInsurance.isPending && <Spinner size="sm" />} Add Policy
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const FP_SUBTABS = ['Summary', 'Accounts', 'Insurance'];

function FinancialProfileTab({ id }) {
  const [sub, setSub] = useState('Summary');

  const { data: profile, isLoading, error } = useQuery({
    queryKey: ['financial-profile', id],
    queryFn: () => financialsApi.getProfile(id),
  });

  if (isLoading) return <div className="py-8 flex justify-center"><Spinner /></div>;
  if (error && error.status !== 404) return <ErrorAlert error={error} />;

  return (
    <div>
      <div className="flex gap-1 border-b border-gray-200 dark:border-gray-700 mb-5">
        {FP_SUBTABS.map((t) => (
          <button key={t} onClick={() => setSub(t)}
            className={`px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors
              ${sub === t ? 'border-brand-600 text-brand-600' : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'}`}>
            {t}
          </button>
        ))}
      </div>
      {sub === 'Summary'   && <FinancialSummarySection profile={profile} id={id} />}
      {sub === 'Accounts'  && <AccountsSection profile={profile} id={id} />}
      {sub === 'Insurance' && <InsuranceSection profile={profile} id={id} />}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Goals tab
// ─────────────────────────────────────────────────────────────────────────────

const GOAL_TYPES = ['retirement','education','home_purchase','emergency_fund','debt_payoff','investment','other'];

function GoalProgress({ goal }) {
  const pct = goal.progress_pct ?? 0;
  const color = pct >= 70 ? 'bg-success-500' : pct >= 40 ? 'bg-warning-500' : 'bg-danger-500';
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
        <span>Progress</span>
        <span className="font-semibold">{pct}%</span>
      </div>
      <div className="h-2.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      {goal.current_value != null && goal.target_amount != null && (
        <div className="flex justify-between text-[10px] text-gray-400 mt-1">
          <span>${Number(goal.current_value).toLocaleString()} saved</span>
          <span>${Number(goal.target_amount).toLocaleString()} target</span>
        </div>
      )}
    </div>
  );
}

function MilestoneList({ goalId, id }) {
  const qc = useQueryClient();
  const { register, handleSubmit, reset } = useForm();

  const { data } = useQuery({
    queryKey: ['goal-milestones', goalId],
    queryFn: () => financialsApi.listMilestones(id, goalId),
  });
  const addMilestone = useMutation({
    mutationFn: (data) => financialsApi.addMilestone(id, goalId, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['goal-milestones', goalId] }); toast.success('Milestone added'); reset(); },
    onError: (e) => toast.error(e.message),
  });

  const milestones = data?.results ?? data ?? [];
  return (
    <div className="mt-3 space-y-2 pl-2 border-l-2 border-brand-100 dark:border-brand-900/40">
      {milestones.map((m) => (
        <div key={m.id} className="flex items-start gap-2">
          <CheckCircle className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${m.completed ? 'text-success-500' : 'text-gray-300'}`} />
          <div>
            <p className="text-xs text-gray-700 dark:text-gray-300">{m.title}</p>
            {m.due_date && <p className="text-[10px] text-gray-400">{m.due_date}</p>}
          </div>
        </div>
      ))}
      <form onSubmit={handleSubmit((d) => addMilestone.mutate(d))} className="flex gap-2 pt-1">
        <input className="input flex-1 text-xs h-7 py-1 px-2" {...register('title', { required: true })} placeholder="Add milestone…" />
        <input type="date" className="input h-7 py-1 px-2 text-xs w-32" {...register('due_date')} />
        <button type="submit" className="btn-primary btn-xs" disabled={addMilestone.isPending}>
          {addMilestone.isPending ? <Spinner size="sm" /> : <Plus className="w-3 h-3" />}
        </button>
      </form>
    </div>
  );
}

function GoalCard({ goal, id }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-gray-900 dark:text-white capitalize">
            {goal.goal_type?.replace(/_/g, ' ')}
          </p>
          {goal.title && <p className="text-xs text-gray-400 mt-0.5">{goal.title}</p>}
        </div>
        <Badge status={goal.status ?? 'on_track'} showDot />
      </div>
      <GoalProgress goal={goal} />
      {goal.target_date && <p className="text-[10px] text-gray-400 mt-2">Target: {goal.target_date}</p>}
      <button onClick={() => setExpanded(!expanded)} className="text-xs text-brand-600 mt-2 hover:text-brand-700">
        {expanded ? 'Hide milestones' : 'Show milestones'}
      </button>
      {expanded && <MilestoneList goalId={goal.id} id={id} />}
    </div>
  );
}

function GoalsTab({ id }) {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const { register, handleSubmit, reset } = useForm();

  const { data, isLoading } = useQuery({
    queryKey: ['goals', id],
    queryFn: () => financialsApi.listGoals(id),
  });
  const createGoal = useMutation({
    mutationFn: (data) => financialsApi.createGoal(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['goals', id] }); toast.success('Goal created'); reset(); setShowCreate(false); },
    onError: (e) => toast.error(e.message),
  });

  const goals = data?.results ?? data ?? [];
  if (isLoading) return <div className="py-8 flex justify-center"><Spinner /></div>;

  return (
    <div>
      <div className="flex justify-end mb-4">
        <button onClick={() => setShowCreate(!showCreate)} className="btn-primary btn-sm">
          <Plus className="w-3.5 h-3.5" /> New Goal
        </button>
      </div>

      {showCreate && (
        <div className="card p-5 mb-5">
          <h3 className="section-title mb-4">Create Goal</h3>
          <form onSubmit={handleSubmit((d) => createGoal.mutate(d))} className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="space-y-1.5">
              <label className="label">Goal Type</label>
              <select className="select" {...register('goal_type', { required: true })}>
                <option value="">Select type…</option>
                {GOAL_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="label">Title (optional)</label>
              <input className="input" {...register('title')} placeholder="e.g. Early retirement" />
            </div>
            <div className="space-y-1.5">
              <label className="label">Target Amount</label>
              <input type="number" className="input" step="1000" {...register('target_amount')} />
            </div>
            <div className="space-y-1.5">
              <label className="label">Target Date</label>
              <input type="date" className="input" {...register('target_date')} />
            </div>
            <div className="col-span-full flex justify-end gap-2">
              <button type="button" className="btn-outline btn-sm" onClick={() => setShowCreate(false)}>Cancel</button>
              <button type="submit" className="btn-primary btn-sm" disabled={createGoal.isPending}>
                {createGoal.isPending && <Spinner size="sm" />} Create Goal
              </button>
            </div>
          </form>
        </div>
      )}

      {goals.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {goals.map((g) => <GoalCard key={g.id} goal={g} id={id} />)}
        </div>
      ) : (
        <EmptyState
          icon={CheckCircle}
          title="No goals yet"
          subtitle="Create a financial goal to start tracking progress."
          action={<button onClick={() => setShowCreate(true)} className="btn-primary btn-sm">New Goal</button>}
        />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Documents tab
// ─────────────────────────────────────────────────────────────────────────────

function DocumentsTab({ id }) {
  const { data, isLoading } = useQuery({
    queryKey: ['documents', id],
    queryFn: () => documentsApi.list({ lead: id }),
  });
  const docs = data?.results ?? data ?? [];

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800">
        <h3 className="section-title">Documents & KYC</h3>
        <Link to={`/leads/${id}/documents`} className="text-xs text-brand-600 font-medium">
          Manage Documents →
        </Link>
      </div>
      <table className="w-full">
        <thead><tr>
          <th className="th">Name</th><th className="th">Type</th>
          <th className="th">Status</th><th className="th hidden md:table-cell">Uploaded</th>
        </tr></thead>
        <tbody>
          {isLoading && [1,2,3].map((i) => <SkeletonRow key={i} cols={4} />)}
          {!isLoading && docs.slice(0, 10).map((d) => (
            <tr key={d.id} className="hover:bg-gray-50/60 dark:hover:bg-gray-800/60">
              <td className="td text-xs">{d.file_name ?? d.name}</td>
              <td className="td text-xs text-gray-500">{d.document_type ?? d.doc_type}</td>
              <td className="td"><Badge status={d.kyc_status ?? d.status ?? 'pending'} /></td>
              <td className="td hidden md:table-cell text-xs text-gray-400">{d.uploaded_at?.slice(0,10)}</td>
            </tr>
          ))}
          {!isLoading && docs.length === 0 && (
            <tr><td colSpan={4} className="td text-center text-sm text-gray-400 py-6">No documents uploaded yet.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────────────
// Communications tab — 3-panel enterprise inbox
// ─────────────────────────────────────────────────────────────────────────────

const CHANNEL_ICON = { email: Mail, sms: MessageSquare, call: Phone };
const CHANNEL_META = {
  email: { color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300', dot: 'bg-blue-500' },
  sms:   { color: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300', dot: 'bg-green-500' },
  call:  { color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300', dot: 'bg-amber-500' },
};

function fmtTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diffDays = Math.floor((now - d) / 86400000);
  if (diffDays === 0) return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7)  return d.toLocaleDateString('en-US', { weekday: 'short' });
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function fmtFull(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
}

function ChBadge({ channel, size = 'sm' }) {
  const meta = CHANNEL_META[channel] ?? { color: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400' };
  return (
    <span className={`inline-flex items-center font-semibold uppercase tracking-wide rounded
      ${size === 'xs' ? 'text-[9px] px-1 py-px' : 'text-[10px] px-1.5 py-0.5'} ${meta.color}`}>
      {channel}
    </span>
  );
}

// ── Left panel: conversation list item ──────────────────────────────────────

function ConvItem({ msg, selected, onClick }) {
  const isOutbound = msg.direction === 'outbound';
  const preview = (msg.body_preview && msg.body_preview.trim())
    || (msg.body && msg.body.trim())
    || msg.subject
    || (msg.channel === 'call' ? 'Call log' : '—');
  const initials = isOutbound
    ? (msg.sent_by_name ?? 'Advisor').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : 'LD';

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-3 border-b border-gray-100 dark:border-gray-800 transition-colors
        flex items-start gap-2.5 group
        ${selected
          ? 'bg-brand-50 dark:bg-brand-900/20 border-l-2 border-l-brand-500'
          : 'hover:bg-gray-50 dark:hover:bg-gray-800/60 border-l-2 border-l-transparent'
        }`}
    >
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-[10px] font-bold mt-0.5
        ${isOutbound ? 'bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300' : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}>
        {initials}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-1 mb-0.5">
          <span className="text-xs font-semibold text-gray-800 dark:text-gray-200 truncate">
            {isOutbound ? (msg.sent_by_name ?? 'Advisor') : 'Lead'}
          </span>
          <span className="text-[10px] text-gray-400 flex-shrink-0">{fmtTime(msg.sent_at ?? msg.created_at)}</span>
        </div>
        <div className="flex items-center gap-1.5 mb-0.5">
          <ChBadge channel={msg.channel} size="xs" />
          <span className={`text-[10px] capitalize ${
            msg.direction === 'inbound'
              ? 'text-gray-400'
              : 'text-brand-500 dark:text-brand-400'
          }`}>
            {msg.direction === 'inbound' ? '← in' : '→ out'}
          </span>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 truncate leading-tight">{preview}</p>
      </div>
    </button>
  );
}

// ── Center panel: message timeline bubble ───────────────────────────────────

// ── Right panel: full message view ──────────────────────────────────────────

function MsgView({ msg }) {
  if (!msg) return (
    <div className="flex flex-col items-center justify-center h-full text-center p-8">
      <MessageSquare className="w-12 h-12 text-gray-200 dark:text-gray-700 mb-3" />
      <p className="text-sm font-medium text-gray-400">No message selected</p>
      <p className="text-xs text-gray-300 dark:text-gray-600 mt-1">Click a conversation on the left</p>
    </div>
  );

  const isOut   = msg.direction === 'outbound';
  const Icon    = CHANNEL_ICON[msg.channel] ?? MessageSquare;
  const isCall  = msg.channel === 'call';
  const cl      = msg.call_log;

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">

      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-start gap-3">
          <div className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0
            ${isOut ? 'bg-brand-100 dark:bg-brand-900/40' : 'bg-gray-100 dark:bg-gray-800'}`}>
            <Icon className={`w-4 h-4 ${isOut ? 'text-brand-600 dark:text-brand-400' : 'text-gray-500 dark:text-gray-400'}`} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-gray-800 dark:text-gray-100">
                {isOut ? (msg.sent_by_name ?? 'Advisor') : (msg.lead_name ?? 'Lead')}
              </span>
              <ChBadge channel={msg.channel} />
              <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full
                ${isOut
                  ? 'bg-brand-50 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400'
                  : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                }`}>
                {isOut ? 'Outbound' : 'Inbound'}
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">{fmtFull(msg.sent_at ?? msg.created_at)}</p>
          </div>
          <span className={`text-[10px] font-medium px-2 py-1 rounded-full capitalize flex-shrink-0
            ${msg.status === 'sent' || msg.status === 'delivered'
              ? 'bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400'
              : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
            }`}>
            {msg.status ?? 'unknown'}
          </span>
        </div>

        {msg.subject && (
          <p className="mt-3 text-base font-semibold text-gray-800 dark:text-gray-100 leading-snug">
            {msg.subject}
          </p>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {isCall ? (
          <div className="rounded-2xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 px-5 py-4 space-y-3">
            <div className="flex items-center gap-2">
              <Phone className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              <span className="text-sm font-semibold text-amber-800 dark:text-amber-300">Call Record</span>
            </div>
            {cl ? (
              <div className="space-y-2 text-sm text-amber-700 dark:text-amber-400">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 flex-shrink-0" />
                  <span>Duration: <span className="font-medium">
                    {Math.floor((cl.duration_seconds ?? 0) / 60)}m {(cl.duration_seconds ?? 0) % 60}s
                  </span></span>
                </div>
                {cl.outcome && (
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 flex-shrink-0" />
                    <span>Outcome: <span className="font-medium capitalize">{cl.outcome.replace(/_/g, ' ')}</span></span>
                  </div>
                )}
                {cl.notes && (
                  <div className="mt-2 pt-2 border-t border-amber-200 dark:border-amber-800">
                    <p className="text-xs text-amber-600 dark:text-amber-500 font-medium mb-1">Notes</p>
                    <p className="text-sm text-amber-700 dark:text-amber-400 whitespace-pre-wrap leading-relaxed">{cl.notes}</p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-amber-600 dark:text-amber-500 italic">No call log details available</p>
            )}
          </div>
        ) : (
          <div className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
            {(msg.body && msg.body.trim()) || (msg.body_preview && msg.body_preview.trim())
              ? (msg.body && msg.body.trim() ? msg.body : msg.body_preview)
              : <span className="italic text-gray-400">No message body</span>
            }
          </div>
        )}
      </div>

      {/* Footer metadata */}
      <div className="flex-shrink-0 border-t border-gray-100 dark:border-gray-800 px-6 py-3">
        <div className="flex items-center gap-4 text-[10px] text-gray-400 flex-wrap">
          <span>ID: <span className="font-mono">{msg.external_id?.slice(0, 8)}…</span></span>
          {msg.created_at && <span>Created: {fmtFull(msg.created_at)}</span>}
        </div>
      </div>
    </div>
  );
}

// ── Compose modal ────────────────────────────────────────────────────────────

function ComposeModal({ id, onClose, onSent }) {
  const [step, setStep]       = useState('pick');   // 'pick' | 'compose'
  const [channel, setChannel] = useState('email');
  const [subject, setSubject] = useState('');
  const [body, setBody]       = useState('');

  const send = useMutation({
    mutationFn: (payload) => communicationsApi.send(payload),
    onSuccess: (newMsg) => {
      toast.success('Message sent');
      onSent(newMsg);
      onClose();
    },
    onError: (e) => toast.error(e.message || 'Send failed'),
  });

  function handleSend() {
    if (!body.trim()) { toast.error('Message body is required'); return; }
    send.mutate({ lead_id: Number(id), channel, subject: subject.trim(), body: body.trim() });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-2">
            {step === 'compose' && (
              <button onClick={() => setStep('pick')} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 mr-1 transition-colors">
                <ArrowRight className="w-4 h-4 rotate-180" />
              </button>
            )}
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              {step === 'pick' ? 'New Message' : `New ${channel === 'email' ? 'Email' : 'SMS'}`}
            </h3>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step 1: pick channel */}
        {step === 'pick' && (
          <div className="p-5 space-y-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">How would you like to reach out?</p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { ch: 'email', Icon: Mail,          title: 'Email',  desc: 'Send a detailed email message' },
                { ch: 'sms',   Icon: MessageSquare, title: 'SMS',    desc: 'Send a short text message' },
              ].map(({ ch, Icon, title, desc }) => (
                <button
                  key={ch}
                  onClick={() => { setChannel(ch); setStep('compose'); }}
                  className="flex flex-col items-start gap-2 p-4 rounded-xl border-2 border-gray-100 dark:border-gray-800
                    hover:border-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/20
                    dark:hover:border-brand-600 transition-all text-left group"
                >
                  <div className="w-9 h-9 rounded-lg bg-gray-100 dark:bg-gray-800 group-hover:bg-brand-100 dark:group-hover:bg-brand-900/40
                    flex items-center justify-center transition-colors">
                    <Icon className="w-4 h-4 text-gray-500 dark:text-gray-400 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 group-hover:text-brand-700 dark:group-hover:text-brand-300">{title}</p>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{desc}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: compose */}
        {step === 'compose' && (
          <div className="p-5 space-y-3">
            {channel === 'email' && (
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Subject"
                className="input text-sm"
                autoFocus
              />
            )}
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSend(); }}
              placeholder={channel === 'sms'
                ? 'Type your SMS message… (⌘↵ to send)'
                : 'Type your email message… (⌘↵ to send)'}
              rows={6}
              className="input resize-none text-sm"
              autoFocus={channel === 'sms'}
            />
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400">{body.length} chars</span>
              <button
                onClick={handleSend}
                disabled={send.isPending || !body.trim()}
                className="btn-primary flex items-center gap-2"
              >
                {send.isPending ? <Spinner size="sm" /> : <Send className="w-4 h-4" />}
                Send {channel === 'email' ? 'Email' : 'SMS'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main 3-panel tab ─────────────────────────────────────────────────────────

function CommunicationsTab({ id, lead }) {
  const qc = useQueryClient();
  const [channelFilter, setChannelFilter] = useState('');
  const [search, setSearch]               = useState('');
  const [page, setPage]                   = useState(1);
  const [selected, setSelected]           = useState(null);
  const [composeOpen, setComposeOpen]     = useState(false);

  const params = { page, page_size: 30, lead_id: id };
  if (channelFilter) params.channel = channelFilter;

  const { data, isLoading } = useQuery({
    queryKey: ['comms-timeline', id, channelFilter, page],
    queryFn: () => communicationsApi.timeline(params),
    keepPreviousData: true,
  });

  const allEntries  = data?.results ?? data ?? [];
  const totalCount  = data?.count ?? allEntries.length;
  const totalPages  = Math.max(1, Math.ceil(totalCount / 30));

  const entries = search.trim()
    ? allEntries.filter(e => {
        const q = search.toLowerCase();
        return (e.subject ?? '').toLowerCase().includes(q)
          || (e.body_preview ?? '').toLowerCase().includes(q)
          || (e.body ?? '').toLowerCase().includes(q)
          || (e.sent_by_name ?? '').toLowerCase().includes(q);
      })
    : allEntries;

  // Auto-select latest message when data first loads
  useEffect(() => {
    if (!selected && allEntries.length > 0) {
      setSelected(allEntries[0]);
    }
  }, [allEntries.length]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleSent(newMsg) {
    qc.invalidateQueries({ queryKey: ['comms-timeline', id] });
    setSelected(newMsg);
  }

  const CHANNEL_TABS = [
    { value: '', label: 'All', count: totalCount },
    { value: 'email', label: 'Email' },
    { value: 'sms',   label: 'SMS' },
    { value: 'call',  label: 'Calls' },
  ];

  return (
    <div>
    {composeOpen && (
      <ComposeModal id={id} onClose={() => setComposeOpen(false)} onSent={handleSent} />
    )}
    <div className="flex flex-col" style={{ height: 'calc(100vh - 280px)', minHeight: '520px' }}>

      {/* ── 3 columns ── */}
      <div className="flex flex-1 min-h-0 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">

        {/* ── Column 1: Conversation list ── */}
        <div className="w-56 flex-shrink-0 flex flex-col border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
          {/* Search */}
          <div className="px-2 pt-2 pb-1.5 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
            <div className="relative">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search messages…"
                className="input text-xs py-1.5 h-7 w-full pl-7"
              />
              <MessageSquare className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400 pointer-events-none" />
            </div>
          </div>
          {/* Channel filter */}
          <div className="flex gap-px p-2 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 flex-wrap">
            {CHANNEL_TABS.map((t) => (
              <button key={t.value}
                onClick={() => { setChannelFilter(t.value); setPage(1); setSelected(null); }}
                className={`flex-1 px-1.5 py-1 rounded text-[10px] font-semibold transition-colors
                  ${channelFilter === t.value
                    ? 'bg-brand-600 text-white'
                    : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}>
                {t.label}
              </button>
            ))}
          </div>

          {/* List */}
          <div className="flex-1 overflow-y-auto">
            {isLoading && [1,2,3,4,5].map(i => (
              <div key={i} className="px-3 py-3 border-b border-gray-100 dark:border-gray-800 animate-pulse flex gap-2">
                <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex-shrink-0" />
                <div className="flex-1 space-y-1.5 py-1">
                  <div className="h-2.5 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                  <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded w-full" />
                </div>
              </div>
            ))}
            {!isLoading && entries.length === 0 && (
              <div className="flex flex-col items-center justify-center h-32 text-center px-4">
                <MessageSquare className="w-6 h-6 text-gray-200 dark:text-gray-700 mb-2" />
                <p className="text-xs text-gray-400">No messages found</p>
              </div>
            )}
            {!isLoading && entries.map((e) => (
              <ConvItem key={e.id} msg={e} selected={selected?.id === e.id} onClick={() => setSelected(e)} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-2 py-1.5 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
              <button className="btn-ghost p-1 text-[10px]" disabled={page === 1} onClick={() => setPage(p => p - 1)}>←</button>
              <span className="text-[10px] text-gray-400">{page}/{totalPages}</span>
              <button className="btn-ghost p-1 text-[10px]" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>→</button>
            </div>
          )}
        </div>

        {/* ── Column 2: Message view ── */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Loading skeleton */}
          {isLoading && (
            <div className="flex-1 p-6 space-y-4 animate-pulse">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-gray-200 dark:bg-gray-700" />
                <div className="space-y-1.5 flex-1">
                  <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
                  <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded w-1/4" />
                </div>
              </div>
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3" />
              <div className="space-y-2">
                <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-full" />
                <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-5/6" />
                <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-4/6" />
              </div>
            </div>
          )}
          {!isLoading && <MsgView msg={selected} />}

          {/* ── Compose bar ── */}
          <div className="flex-shrink-0 border-t border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-2.5 flex items-center justify-between">
            <span className="text-xs text-gray-400 dark:text-gray-500">
              {totalCount} message{totalCount !== 1 ? 's' : ''}
            </span>
            <button
              onClick={() => setComposeOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold transition-colors shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              New Message
            </button>
          </div>
        </div>
      </div>
    </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Timeline entry
// ─────────────────────────────────────────────────────────────────────────────

function TimelineEntry({ entry, isLast }) {
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className="w-7 h-7 rounded-full bg-brand-50 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
          <MessageSquare className="w-3 h-3 text-brand-500" />
        </div>
        {!isLast && <div className="w-px flex-1 bg-gray-100 dark:bg-gray-800 mt-1" />}
      </div>
      <div className="pb-4 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-xs font-medium text-gray-800 dark:text-gray-200">
            {entry.actor ?? entry.created_by ?? 'System'}
          </span>
          <span className="text-[10px] text-gray-400">{entry.created_at?.slice(0,16).replace('T',' ')}</span>
          {entry.is_private && (
            <span className="text-[10px] font-medium text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded-full">Private</span>
          )}
        </div>
        <p className="text-sm text-gray-700 dark:text-gray-300">{entry.body ?? entry.note ?? entry.description}</p>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────

export default function PersonDetailPage() {
  const { id } = useParams();
  const qc = useQueryClient();
  const [tab, setTab] = useState('Overview');
  const [note, setNote] = useState('');
  const [isPrivate, setIsPrivate] = useState(false);
  const [confirm, setConfirm] = useState(null);

  const { data: lead, isLoading, error } = useQuery({
    queryKey: ['lead', id],
    queryFn: () => leadsApi.get(id),
  });
  const { data: timeline } = useQuery({
    queryKey: ['lead-timeline', id],
    queryFn: () => leadsApi.getTimeline(id),
  });
  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ['financial-profile', id],
    queryFn: () => financialsApi.getProfile(id),
    enabled: !!lead,
  });

  const moveStage = useMutation({
    mutationFn: (stage) => leadsApi.moveStage(id, stage),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lead', id] }); toast.success('Stage updated'); },
    onError: (e) => toast.error(e.message),
  });
  const addNote = useMutation({
    mutationFn: () => leadsApi.addNote(id, note, isPrivate),
    onSuccess: () => { setNote(''); qc.invalidateQueries({ queryKey: ['lead-timeline', id] }); toast.success('Note added'); },
    onError: (e) => toast.error(e.message),
  });
  const optOut = useMutation({
    mutationFn: () => leadsApi.optOut(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lead', id] }); toast.success('Opted out'); setConfirm(null); },
    onError: (e) => toast.error(e.message),
  });
  const convertLead = useMutation({
    mutationFn: () => leadsApi.convert(id, {}),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lead', id] }); toast.success('Converted to client!'); setConfirm(null); },
    onError: (e) => toast.error(e.message),
  });

  if (isLoading) return <PageSpinner />;
  if (error) return <ErrorAlert error={error} />;
  if (!lead) return null;

  const name = lead.full_name ?? `${lead.first_name} ${lead.last_name}`;
  const isClient = CLIENT_STATUSES.has(lead.status);
  const timelineEntries = timeline?.results ?? timeline ?? [];

  return (
    <div>
      {confirm && <ConfirmModal {...confirm} onCancel={() => setConfirm(null)} />}

      <PageHeader
        crumbs={[{ label: 'Leads & Clients', to: '/leads' }, { label: name }]}
        title={name}
        subtitle={lead.email}
        actions={
          <div className="flex items-center gap-2">
            {!isClient && !['closed_won', 'closed_lost'].includes(lead.status) && (
              <button className="btn-success btn-sm" onClick={() => setConfirm({
                title: 'Convert to Client',
                message: `Convert ${lead.first_name} to a full client record?`,
                onConfirm: () => convertLead.mutate(),
                loading: convertLead.isPending,
              })}>
                <UserPlus className="w-3.5 h-3.5" /> Convert to Client
              </button>
            )}
            <Link to={`/leads/${id}/edit`} className="btn-outline btn-sm">Edit</Link>
          </div>
        }
      />

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-gray-200 dark:border-gray-700 mb-5 overflow-x-auto">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors
              ${tab === t ? 'border-brand-600 text-brand-600' : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'}`}>
            {t}
          </button>
        ))}
      </div>

      {/* ── Overview ── */}
      {tab === 'Overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Contact info */}
          <div className="card p-5">
            <h3 className="section-title mb-3">Contact Info</h3>
            {[
              { icon: Mail,      label: 'Email',     value: lead.email },
              { icon: Phone,     label: 'Phone',     value: lead.phone },
              { icon: MapPin,    label: 'Location',  value: [lead.city, lead.state].filter(Boolean).join(', ') },
              { icon: User,      label: 'Advisor',   value: (lead.assigned_advisor_names ?? []).join(', ') || lead.assigned_advisor_name },
              { icon: Briefcase, label: 'Household', value: lead.household_name },
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
              <Badge status={lead.status} showDot />
              {isClient && lead.kyc_status && <Badge status={lead.kyc_status} showDot />}
              {lead.opt_out && <p className="text-xs text-danger-600 mt-1">⛔ Opted out</p>}
            </div>
          </div>

          {/* Pipeline stage (pre-client) or financial snapshot (client) */}
          <div className="space-y-4">
            {!isClient ? (
              <div className="card p-5">
                <h3 className="section-title mb-3">Pipeline Stage</h3>
                <div className="space-y-1.5">
                  {PIPELINE_STAGES.map((s) => (
                    <button key={s} onClick={() => lead.status !== s && moveStage.mutate(s)}
                      disabled={moveStage.isPending}
                      className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors flex items-center justify-between
                        ${lead.status === s ? 'bg-brand-600 text-white' : 'hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400'}`}>
                      <span className="capitalize">{s.replace(/_/g, ' ')}</span>
                      {lead.status === s && <ArrowRight className="w-3 h-3" />}
                    </button>
                  ))}
                </div>
                {!lead.opt_out && (
                  <button onClick={() => setConfirm({ title: 'Opt Out', message: 'Mark as opted out? No further automated communications (BRU-07).', danger: true, onConfirm: () => optOut.mutate(), loading: optOut.isPending })}
                    className="btn-danger btn-sm w-full justify-center mt-3">
                    Mark Opt-Out
                  </button>
                )}
              </div>
            ) : (
              <>
                {profileLoading && <SkeletonCard />}
                {!profileLoading && profile && (
                  <div className="card p-5 border-l-4 border-brand-500">
                    <p className="text-xs text-gray-400 mb-1">Net Worth (BRU-27)</p>
                    <p className="text-2xl font-bold text-brand-600 dark:text-brand-400">
                      <Money value={profile.net_worth} currency={profile.currency} />
                    </p>
                    {profile.as_of_date && <p className="text-[10px] text-gray-400 mt-1">as of {profile.as_of_date}</p>}
                  </div>
                )}
                {!profileLoading && profile && (
                  <div className="card p-5">
                    <h3 className="section-title mb-3">Financial Summary</h3>
                    <InfoRow label="Annual Income"    value={profile.annual_income != null ? `$${Number(profile.annual_income).toLocaleString()}` : null} />
                    <InfoRow label="Total Assets"     value={profile.total_assets != null ? `$${Number(profile.total_assets).toLocaleString()}` : null} />
                    <InfoRow label="Total Liabilities" value={profile.total_liabilities != null ? `$${Number(profile.total_liabilities).toLocaleString()}` : null} />
                    <InfoRow label="Risk Tolerance"   value={profile.risk_tolerance} />
                    <InfoRow label="Employment"       value={profile.employment_status} />
                  </div>
                )}
              </>
            )}
          </div>

          {/* Add note + opt-out for clients */}
          <div className="space-y-4">
            <div className="card p-5">
              <h3 className="section-title mb-3">Add Note</h3>
              <textarea className="textarea w-full mb-3" rows={4} placeholder="Add an activity note…"
                value={note} onChange={(e) => setNote(e.target.value)} />
              <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400 mb-3 cursor-pointer">
                <input type="checkbox" checked={isPrivate} onChange={(e) => setIsPrivate(e.target.checked)} className="w-3.5 h-3.5 rounded" />
                Private (internal only — BRU-08)
              </label>
              <button className="btn-primary btn-sm w-full justify-center" disabled={!note.trim() || addNote.isPending} onClick={() => addNote.mutate()}>
                {addNote.isPending && <Spinner size="sm" />} Add Note
              </button>
            </div>
            {isClient && !lead.opt_out && (
              <button onClick={() => setConfirm({ title: 'Opt Out', message: 'Mark as opted out? No further automated communications (BRU-07).', danger: true, onConfirm: () => optOut.mutate(), loading: optOut.isPending })}
                className="btn-danger btn-sm w-full justify-center">
                Mark Opt-Out
              </button>
            )}
          </div>
        </div>
      )}

      {/* ── Financial Profile (inline) ── */}
      {tab === 'Financial Profile' && <FinancialProfileTab id={id} />}

      {/* ── Goals (inline) ── */}
      {tab === 'Goals' && <GoalsTab id={id} />}

      {/* ── Documents ── */}
      {tab === 'Documents' && <DocumentsTab id={id} />}

      {/* ── Communications (inline) ── */}
      {tab === 'Communications' && <CommunicationsTab id={id} lead={lead} />}

      {/* ── Timeline ── */}
      {tab === 'Timeline' && (
        <div className="card p-5">
          <h3 className="section-title mb-4 flex items-center gap-2">
            <Clock className="w-4 h-4 text-gray-400" /> Activity Timeline
          </h3>
          <div className="space-y-0">
            {timelineEntries.map((e, i) => (
              <TimelineEntry key={e.id ?? i} entry={e} isLast={i === timelineEntries.length - 1} />
            ))}
            {timelineEntries.length === 0 && (
              <p className="text-sm text-gray-400 text-center py-6">No timeline entries yet.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
