import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';
import { Building2, PiggyBank, Shield, TrendingUp } from 'lucide-react';
import { financialsApi } from '../../api/financials.js';
import { leadsApi } from '../../api/leads.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import { PageSpinner } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';
import Badge from '../../components/ui/Badge.jsx';

const TABS = ['Summary', 'Assets & Liabilities', 'Insurance', 'Accounts'];

function Money({ value, currency = 'USD' }) {
  if (value == null) return <span className="text-gray-400">—</span>;
  return (
    <span className="font-semibold text-gray-900 dark:text-white">
      {new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(value)}
    </span>
  );
}

function Field({ label, children }) {
  return (
    <div className="space-y-1.5">
      <label className="label">{label}</label>
      {children}
    </div>
  );
}

function SummaryTab({ profile, cid }) {
  const qc = useQueryClient();
  const { register, handleSubmit, reset } = useForm({
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
      ? financialsApi.updateProfile(cid, data)
      : financialsApi.createProfile(cid, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['financial-profile', cid] });
      toast.success('Profile saved');
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      {/* Net worth — read-only from API (BRU-27) */}
      <div className="card p-5 border-l-4 border-brand-500">
        <p className="text-xs text-gray-400 mb-1">Net Worth — derived by backend (BRU-27)</p>
        <div className="flex items-end gap-3">
          <span className="text-3xl font-bold text-brand-600 dark:text-brand-400">
            <Money value={profile?.net_worth} currency={profile?.currency} />
          </span>
          {profile?.as_of_date && (
            <span className="text-xs text-gray-400 mb-1">as of {profile.as_of_date}</span>
          )}
        </div>
        <div className="grid grid-cols-3 gap-3 mt-4">
          {[
            { label: 'Total Assets',      value: profile?.total_assets,      color: 'text-success-600' },
            { label: 'Total Liabilities', value: profile?.total_liabilities,  color: 'text-danger-600' },
            { label: 'Annual Income',     value: profile?.annual_income,       color: 'text-brand-600' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 text-center">
              <p className="text-[10px] text-gray-400 mb-1">{label}</p>
              <p className={`text-sm font-semibold ${color}`}>
                <Money value={value} />
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Editable fields */}
      <div className="card p-5">
        <h3 className="section-title mb-4">Profile Details</h3>
        <form onSubmit={handleSubmit((d) => save.mutate(d))} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Annual Income">
              <input type="number" className="input" step="1000" {...register('annual_income')} />
            </Field>
            <Field label="Currency">
              <select className="select" {...register('currency')}>
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="GBP">GBP</option>
                <option value="CAD">CAD</option>
              </select>
            </Field>
            <Field label="Risk Tolerance">
              <select className="select" {...register('risk_tolerance')}>
                <option value="">Select…</option>
                <option value="conservative">Conservative</option>
                <option value="moderate">Moderate</option>
                <option value="aggressive">Aggressive</option>
              </select>
            </Field>
            <Field label="Employment Status">
              <select className="select" {...register('employment_status')}>
                <option value="">Select…</option>
                <option value="employed">Employed</option>
                <option value="self_employed">Self-employed</option>
                <option value="retired">Retired</option>
                <option value="unemployed">Unemployed</option>
              </select>
            </Field>
            <Field label="Tax Bracket (%)">
              <input type="number" className="input" min="0" max="100" step="0.5" {...register('tax_bracket')} />
            </Field>
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

function AssetsTab({ profile, cid }) {
  const qc = useQueryClient();
  const { register, handleSubmit, reset } = useForm();

  const addAccount = useMutation({
    mutationFn: (data) => financialsApi.addAccount(cid, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['financial-profile', cid] });
      toast.success('Account added');
      reset();
    },
    onError: (e) => toast.error(e.message),
  });

  const removeAccount = useMutation({
    mutationFn: (accountId) => financialsApi.removeAccount(cid, accountId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['financial-profile', cid] });
      toast.success('Account removed');
    },
    onError: (e) => toast.error(e.message),
  });

  const accounts = profile?.accounts ?? [];

  return (
    <div className="space-y-5">
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <h3 className="section-title flex items-center gap-2">
            <Building2 className="w-4 h-4 text-gray-400" /> Financial Accounts
          </h3>
        </div>
        <table className="w-full">
          <thead><tr>
            <th className="th">Account Name</th>
            <th className="th">Type</th>
            <th className="th">Balance</th>
            <th className="th hidden md:table-cell">Institution</th>
            <th className="th w-10" />
          </tr></thead>
          <tbody>
            {accounts.map((a) => (
              <tr key={a.id} className="hover:bg-gray-50/60 dark:hover:bg-gray-800/60">
                <td className="td text-sm">{a.name}</td>
                <td className="td text-xs text-gray-500">{a.account_type}</td>
                <td className="td text-sm font-medium text-gray-900 dark:text-white">
                  <Money value={a.balance} currency={a.currency} />
                </td>
                <td className="td hidden md:table-cell text-xs text-gray-400">{a.institution}</td>
                <td className="td">
                  <button onClick={() => removeAccount.mutate(a.id)}
                    className="text-xs text-danger-600 hover:text-danger-700 font-medium">
                    Remove
                  </button>
                </td>
              </tr>
            ))}
            {accounts.length === 0 && (
              <tr><td colSpan={5} className="td text-center text-sm text-gray-400 py-6">No accounts added yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Add account form */}
      <div className="card p-5">
        <h3 className="section-title mb-4">Add Account</h3>
        <form onSubmit={handleSubmit((d) => addAccount.mutate(d))} className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <Field label="Name">
            <input className="input" {...register('name', { required: true })} placeholder="e.g. Checking" />
          </Field>
          <Field label="Type">
            <select className="select" {...register('account_type')}>
              <option value="checking">Checking</option>
              <option value="savings">Savings</option>
              <option value="investment">Investment</option>
              <option value="retirement">Retirement</option>
              <option value="real_estate">Real Estate</option>
              <option value="other">Other</option>
            </select>
          </Field>
          <Field label="Balance">
            <input type="number" className="input" step="100" {...register('balance')} placeholder="0" />
          </Field>
          <Field label="Institution">
            <input className="input" {...register('institution')} placeholder="Bank name" />
          </Field>
          <div className="col-span-full flex justify-end">
            <button type="submit" className="btn-primary btn-sm" disabled={addAccount.isPending}>
              {addAccount.isPending && <Spinner size="sm" />}
              Add Account
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function InsuranceTab({ profile, cid }) {
  const qc = useQueryClient();
  const { register, handleSubmit, reset } = useForm();

  const addInsurance = useMutation({
    mutationFn: (data) => financialsApi.addInsurance(cid, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['financial-profile', cid] });
      toast.success('Insurance added');
      reset();
    },
    onError: (e) => toast.error(e.message),
  });

  const removeInsurance = useMutation({
    mutationFn: (insId) => financialsApi.removeInsurance(cid, insId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['financial-profile', cid] });
      toast.success('Insurance removed');
    },
    onError: (e) => toast.error(e.message),
  });

  const policies = profile?.insurance_policies ?? [];

  return (
    <div className="space-y-5">
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <h3 className="section-title flex items-center gap-2">
            <Shield className="w-4 h-4 text-gray-400" /> Insurance Policies
          </h3>
        </div>
        <table className="w-full">
          <thead><tr>
            <th className="th">Type</th>
            <th className="th">Provider</th>
            <th className="th">Coverage</th>
            <th className="th hidden md:table-cell">Premium</th>
            <th className="th w-10" />
          </tr></thead>
          <tbody>
            {policies.map((p) => (
              <tr key={p.id} className="hover:bg-gray-50/60 dark:hover:bg-gray-800/60">
                <td className="td text-xs capitalize">{p.insurance_type?.replace(/_/g,' ')}</td>
                <td className="td text-xs text-gray-500">{p.provider}</td>
                <td className="td text-sm font-medium"><Money value={p.coverage_amount} /></td>
                <td className="td hidden md:table-cell text-xs text-gray-400">
                  <Money value={p.annual_premium} /> /yr
                </td>
                <td className="td">
                  <button onClick={() => removeInsurance.mutate(p.id)}
                    className="text-xs text-danger-600 hover:text-danger-700 font-medium">
                    Remove
                  </button>
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
          <Field label="Type">
            <select className="select" {...register('insurance_type')}>
              <option value="life">Life</option>
              <option value="health">Health</option>
              <option value="disability">Disability</option>
              <option value="long_term_care">Long-Term Care</option>
              <option value="auto">Auto</option>
              <option value="home">Home</option>
              <option value="other">Other</option>
            </select>
          </Field>
          <Field label="Provider">
            <input className="input" {...register('provider')} placeholder="Insurance co." />
          </Field>
          <Field label="Coverage Amount">
            <input type="number" className="input" step="1000" {...register('coverage_amount')} />
          </Field>
          <Field label="Annual Premium">
            <input type="number" className="input" step="100" {...register('annual_premium')} />
          </Field>
          <div className="col-span-full flex justify-end">
            <button type="submit" className="btn-primary btn-sm" disabled={addInsurance.isPending}>
              {addInsurance.isPending && <Spinner size="sm" />}
              Add Policy
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function FinancialProfilePage() {
  const { clientId } = useParams();
  const [tab, setTab] = useState('Summary');

  const { data: client } = useQuery({
    queryKey: ['lead', clientId],
    queryFn: () => leadsApi.get(clientId),
  });

  const { data: profile, isLoading, error } = useQuery({
    queryKey: ['financial-profile', clientId],
    queryFn: () => financialsApi.getProfile(clientId),
  });

  if (isLoading) return <PageSpinner />;
  if (error && error.status !== 404) return <ErrorAlert error={error} />;

  const name = client ? (client.full_name ?? `${client.first_name} ${client.last_name}`) : `#${clientId}`;

  return (
    <div>
      <PageHeader
        crumbs={[
          { label: 'Leads & Clients', to: '/leads' },
          { label: name, to: `/leads/${clientId}` },
          { label: 'Financial Profile' },
        ]}
        title="Financial Profile"
        subtitle={name}
        icon={TrendingUp}
        actions={<Link to={`/leads/${clientId}/goals`} className="btn-outline btn-sm">Goals →</Link>}
      />

      <div className="flex gap-1 border-b border-gray-200 dark:border-gray-700 mb-5 overflow-x-auto">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors
              ${tab === t
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'}`}>
            {t}
          </button>
        ))}
      </div>

      {tab === 'Summary' && <SummaryTab profile={profile} cid={clientId} />}
      {tab === 'Assets & Liabilities' && <AssetsTab profile={profile} cid={clientId} />}
      {tab === 'Insurance' && <InsuranceTab profile={profile} cid={clientId} />}
      {tab === 'Accounts' && (
        <div className="text-sm text-gray-400 text-center py-8">
          Account details are shown in the Assets & Liabilities tab.
        </div>
      )}
    </div>
  );
}
