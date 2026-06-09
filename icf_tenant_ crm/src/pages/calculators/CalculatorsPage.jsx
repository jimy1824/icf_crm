import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Calculator, Info } from 'lucide-react';
import { financialsApi } from '../../api/financials.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Spinner from '../../components/ui/Spinner.jsx';

// BRU-34: all calculator outputs are labelled as ESTIMATES and not financial advice

const CALCULATORS = [
  { key: 'retirement',     label: 'Retirement Planner',     icon: '🏡' },
  { key: 'investment',     label: 'Investment Growth',       icon: '📈' },
  { key: 'net_worth',      label: 'Net Worth Snapshot',      icon: '💰' },
  { key: 'loan',           label: 'Loan / Amortization',     icon: '🏦' },
  { key: 'college',        label: 'College Savings',         icon: '🎓' },
  { key: 'insurance',      label: 'Insurance Needs',         icon: '🛡️' },
  { key: 'risk',           label: 'Risk Assessment',         icon: '⚖️' },
];

function FieldRow({ label, children }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-1.5 sm:gap-3">
      <label className="label sm:w-44 flex-shrink-0">{label}</label>
      <div className="flex-1">{children}</div>
    </div>
  );
}

function EstimateDisclaimer() {
  return (
    <div className="flex items-start gap-2.5 p-3 rounded-lg bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 mb-4">
      <Info className="w-4 h-4 text-warning-500 flex-shrink-0 mt-0.5" />
      <p className="text-xs text-warning-700 dark:text-warning-300">
        <strong>BRU-34 — Estimates only:</strong> These calculations are illustrative projections for planning
        purposes. They are not financial advice and should not be relied upon as a guarantee of future results.
      </p>
    </div>
  );
}

function ResultCard({ label, value, note }) {
  return (
    <div className="bg-brand-50 dark:bg-brand-900/20 rounded-xl p-4 text-center border border-brand-100 dark:border-brand-800">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-xl font-bold text-brand-700 dark:text-brand-300">{value}</p>
      {note && <p className="text-[10px] text-gray-400 mt-1">{note}</p>}
    </div>
  );
}

function fmt(n) {
  if (n == null) return '—';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
}

function RetirementCalc() {
  const [result, setResult] = useState(null);
  const { register, handleSubmit } = useForm({ defaultValues: { current_age: 35, retirement_age: 65, current_savings: 50000, monthly_contribution: 1000, annual_return: 7, inflation_rate: 3 } });
  const calc = useMutation({
    mutationFn: (d) => financialsApi.calculate('retirement', d),
    onSuccess: setResult,
    onError: (e) => toast.error(e.message),
  });
  return (
    <div className="space-y-3">
      <form onSubmit={handleSubmit((d) => calc.mutate(d))} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          {[['Current Age', 'current_age', 'number'], ['Retirement Age', 'retirement_age', 'number'], ['Current Savings ($)', 'current_savings', 'number'], ['Monthly Contribution ($)', 'monthly_contribution', 'number'], ['Expected Annual Return (%)', 'annual_return', 'number'], ['Inflation Rate (%)', 'inflation_rate', 'number']].map(([l, k, t]) => (
            <div key={k} className="space-y-1.5">
              <label className="label">{l}</label>
              <input type={t} className="input" step="any" {...register(k)} />
            </div>
          ))}
        </div>
        <button type="submit" className="btn-primary btn-sm" disabled={calc.isPending}>
          {calc.isPending && <Spinner size="sm" />} Calculate
        </button>
      </form>
      {result && (
        <div className="grid grid-cols-2 gap-3 mt-4">
          <ResultCard label="Projected Savings at Retirement (Estimate)" value={fmt(result.projected_savings)} note="Nominal value" />
          <ResultCard label="Inflation-Adjusted Value (Estimate)" value={fmt(result.real_value)} note="In today's dollars" />
          <ResultCard label="Monthly Income in Retirement (Estimate)" value={fmt(result.monthly_income)} note="Based on 4% rule" />
          <ResultCard label="Years of Savings (Estimate)" value={`${result.years_saving ?? '—'} yrs`} />
        </div>
      )}
    </div>
  );
}

function InvestmentCalc() {
  const [result, setResult] = useState(null);
  const { register, handleSubmit } = useForm({ defaultValues: { initial_amount: 10000, monthly_contribution: 500, annual_return: 8, years: 20 } });
  const calc = useMutation({
    mutationFn: (d) => financialsApi.calculate('investment', d),
    onSuccess: setResult,
    onError: (e) => toast.error(e.message),
  });
  return (
    <div className="space-y-3">
      <form onSubmit={handleSubmit((d) => calc.mutate(d))} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          {[['Initial Investment ($)', 'initial_amount'], ['Monthly Contribution ($)', 'monthly_contribution'], ['Annual Return (%)', 'annual_return'], ['Years', 'years']].map(([l, k]) => (
            <div key={k} className="space-y-1.5">
              <label className="label">{l}</label>
              <input type="number" className="input" step="any" {...register(k)} />
            </div>
          ))}
        </div>
        <button type="submit" className="btn-primary btn-sm" disabled={calc.isPending}>
          {calc.isPending && <Spinner size="sm" />} Calculate
        </button>
      </form>
      {result && (
        <div className="grid grid-cols-3 gap-3 mt-4">
          <ResultCard label="Future Value (Estimate)" value={fmt(result.future_value)} />
          <ResultCard label="Total Contributions" value={fmt(result.total_contributed)} />
          <ResultCard label="Total Gain (Estimate)" value={fmt(result.total_gain)} />
        </div>
      )}
    </div>
  );
}

function LoanCalc() {
  const [result, setResult] = useState(null);
  const { register, handleSubmit } = useForm({ defaultValues: { loan_amount: 300000, annual_rate: 6.5, term_years: 30 } });
  const calc = useMutation({
    mutationFn: (d) => financialsApi.calculate('loan', d),
    onSuccess: setResult,
    onError: (e) => toast.error(e.message),
  });
  return (
    <div className="space-y-3">
      <form onSubmit={handleSubmit((d) => calc.mutate(d))} className="space-y-3">
        <div className="grid grid-cols-3 gap-3">
          <div className="space-y-1.5">
            <label className="label">Loan Amount ($)</label>
            <input type="number" className="input" {...register('loan_amount')} />
          </div>
          <div className="space-y-1.5">
            <label className="label">Annual Interest (%)</label>
            <input type="number" className="input" step="0.01" {...register('annual_rate')} />
          </div>
          <div className="space-y-1.5">
            <label className="label">Term (years)</label>
            <input type="number" className="input" {...register('term_years')} />
          </div>
        </div>
        <button type="submit" className="btn-primary btn-sm" disabled={calc.isPending}>
          {calc.isPending && <Spinner size="sm" />} Calculate
        </button>
      </form>
      {result && (
        <div className="grid grid-cols-3 gap-3 mt-4">
          <ResultCard label="Monthly Payment (Estimate)" value={fmt(result.monthly_payment)} />
          <ResultCard label="Total Interest Paid" value={fmt(result.total_interest)} />
          <ResultCard label="Total Cost" value={fmt(result.total_cost)} />
        </div>
      )}
    </div>
  );
}

function CollegeCalc() {
  const [result, setResult] = useState(null);
  const { register, handleSubmit } = useForm({ defaultValues: { child_age: 5, college_age: 18, annual_cost: 30000, current_savings: 0, annual_return: 6 } });
  const calc = useMutation({
    mutationFn: (d) => financialsApi.calculate('college', d),
    onSuccess: setResult,
    onError: (e) => toast.error(e.message),
  });
  return (
    <div className="space-y-3">
      <form onSubmit={handleSubmit((d) => calc.mutate(d))} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          {[['Child\'s Current Age', 'child_age'], ['College Start Age', 'college_age'], ['Annual College Cost ($)', 'annual_cost'], ['Current Savings ($)', 'current_savings'], ['Annual Return (%)', 'annual_return']].map(([l, k]) => (
            <div key={k} className="space-y-1.5">
              <label className="label">{l}</label>
              <input type="number" className="input" step="any" {...register(k)} />
            </div>
          ))}
        </div>
        <button type="submit" className="btn-primary btn-sm" disabled={calc.isPending}>
          {calc.isPending && <Spinner size="sm" />} Calculate
        </button>
      </form>
      {result && (
        <div className="grid grid-cols-2 gap-3 mt-4">
          <ResultCard label="Total College Cost (Estimate)" value={fmt(result.total_cost)} />
          <ResultCard label="Monthly Savings Needed (Estimate)" value={fmt(result.monthly_savings_needed)} />
        </div>
      )}
    </div>
  );
}

function InsuranceCalc() {
  const [result, setResult] = useState(null);
  const { register, handleSubmit } = useForm({ defaultValues: { annual_income: 100000, years_income_needed: 10, existing_coverage: 0, total_debt: 50000 } });
  const calc = useMutation({
    mutationFn: (d) => financialsApi.calculate('insurance', d),
    onSuccess: setResult,
    onError: (e) => toast.error(e.message),
  });
  return (
    <div className="space-y-3">
      <form onSubmit={handleSubmit((d) => calc.mutate(d))} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          {[['Annual Income ($)', 'annual_income'], ['Years Income Needed', 'years_income_needed'], ['Existing Coverage ($)', 'existing_coverage'], ['Total Debt ($)', 'total_debt']].map(([l, k]) => (
            <div key={k} className="space-y-1.5">
              <label className="label">{l}</label>
              <input type="number" className="input" step="any" {...register(k)} />
            </div>
          ))}
        </div>
        <button type="submit" className="btn-primary btn-sm" disabled={calc.isPending}>
          {calc.isPending && <Spinner size="sm" />} Calculate
        </button>
      </form>
      {result && (
        <div className="grid grid-cols-2 gap-3 mt-4">
          <ResultCard label="Recommended Coverage (Estimate)" value={fmt(result.recommended_coverage)} />
          <ResultCard label="Coverage Gap (Estimate)" value={fmt(result.coverage_gap)} />
        </div>
      )}
    </div>
  );
}

function RiskCalc() {
  const [result, setResult] = useState(null);
  const { register, handleSubmit } = useForm({ defaultValues: { age: 40, time_horizon: 20, income_stability: 3, loss_tolerance: 2, investment_experience: 2 } });
  const calc = useMutation({
    mutationFn: (d) => financialsApi.calculate('risk', d),
    onSuccess: setResult,
    onError: (e) => toast.error(e.message),
  });
  return (
    <div className="space-y-3">
      <form onSubmit={handleSubmit((d) => calc.mutate(d))} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="label">Age</label>
            <input type="number" className="input" {...register('age')} />
          </div>
          <div className="space-y-1.5">
            <label className="label">Investment Horizon (years)</label>
            <input type="number" className="input" {...register('time_horizon')} />
          </div>
          {[['Income Stability (1–5)', 'income_stability'], ['Loss Tolerance (1–5)', 'loss_tolerance'], ['Investment Experience (1–5)', 'investment_experience']].map(([l, k]) => (
            <div key={k} className="space-y-1.5">
              <label className="label">{l}</label>
              <input type="number" className="input" min={1} max={5} {...register(k)} />
            </div>
          ))}
        </div>
        <button type="submit" className="btn-primary btn-sm" disabled={calc.isPending}>
          {calc.isPending && <Spinner size="sm" />} Calculate
        </button>
      </form>
      {result && (
        <div className="grid grid-cols-2 gap-3 mt-4">
          <ResultCard label="Risk Score (Estimate)" value={`${result.risk_score ?? '—'} / 100`} />
          <ResultCard label="Risk Profile" value={result.risk_profile ?? '—'} note="Conservative / Moderate / Aggressive" />
        </div>
      )}
    </div>
  );
}

function NetWorthCalc() {
  const [result, setResult] = useState(null);
  const { register, handleSubmit } = useForm({ defaultValues: { total_assets: 0, total_liabilities: 0 } });
  const calc = useMutation({
    mutationFn: (d) => financialsApi.calculate('net_worth', d),
    onSuccess: setResult,
    onError: (e) => toast.error(e.message),
  });
  return (
    <div className="space-y-3">
      <p className="text-xs text-gray-400">
        Use this calculator for quick what-if analysis. The authoritative net worth is derived by the backend (BRU-27).
      </p>
      <form onSubmit={handleSubmit((d) => calc.mutate(d))} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="label">Total Assets ($)</label>
            <input type="number" className="input" step="1000" {...register('total_assets')} />
          </div>
          <div className="space-y-1.5">
            <label className="label">Total Liabilities ($)</label>
            <input type="number" className="input" step="1000" {...register('total_liabilities')} />
          </div>
        </div>
        <button type="submit" className="btn-primary btn-sm" disabled={calc.isPending}>
          {calc.isPending && <Spinner size="sm" />} Calculate
        </button>
      </form>
      {result && (
        <div className="grid grid-cols-1 gap-3 mt-4">
          <ResultCard label="Net Worth Estimate" value={fmt(result.net_worth)} note="Illustrative only — authoritative value from financial profile" />
        </div>
      )}
    </div>
  );
}

const CALC_COMPONENTS = {
  retirement: RetirementCalc,
  investment: InvestmentCalc,
  net_worth: NetWorthCalc,
  loan: LoanCalc,
  college: CollegeCalc,
  insurance: InsuranceCalc,
  risk: RiskCalc,
};

export default function CalculatorsPage() {
  const [active, setActive] = useState('retirement');
  const ActiveCalc = CALC_COMPONENTS[active];

  return (
    <div>
      <PageHeader
        title="Financial Calculators"
        subtitle="Planning tools — all outputs are estimates (BRU-34)"
        icon={Calculator}
      />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
        {/* Sidebar picker */}
        <div className="card p-3 h-fit">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-2 mb-2">Calculators</p>
          {CALCULATORS.map((c) => (
            <button key={c.key} onClick={() => setActive(c.key)}
              className={`w-full text-left px-3 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2.5 mb-0.5
                ${active === c.key
                  ? 'bg-brand-600 text-white'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}`}>
              <span>{c.icon}</span>
              <span>{c.label}</span>
            </button>
          ))}
        </div>

        {/* Calculator area */}
        <div className="lg:col-span-3">
          <div className="card p-6">
            <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-4">
              {CALCULATORS.find((c) => c.key === active)?.label}
            </h2>
            <EstimateDisclaimer />
            {ActiveCalc && <ActiveCalc />}
          </div>
        </div>
      </div>
    </div>
  );
}
