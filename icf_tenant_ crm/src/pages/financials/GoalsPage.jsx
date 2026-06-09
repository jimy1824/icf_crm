import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';
import { CheckCircle, Plus, Target } from 'lucide-react';
import { financialsApi } from '../../api/financials.js';
import { leadsApi } from '../../api/leads.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { PageSpinner } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';

const GOAL_TYPES = ['retirement','education','home_purchase','emergency_fund','debt_payoff','investment','other'];
const GOAL_STATUSES = ['on_track','off_track','achieved','paused'];

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

function MilestoneList({ goalId, cid }) {
  const qc = useQueryClient();
  const { register, handleSubmit, reset } = useForm();

  const { data } = useQuery({
    queryKey: ['goal-milestones', goalId],
    queryFn: () => financialsApi.getMilestones(cid, goalId),
  });

  const addMilestone = useMutation({
    mutationFn: (data) => financialsApi.addMilestone(cid, goalId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['goal-milestones', goalId] });
      toast.success('Milestone added');
      reset();
    },
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
        <input className="input input-sm flex-1 text-xs h-7 py-1 px-2" {...register('title', { required: true })}
          placeholder="Add milestone…" />
        <input type="date" className="input input-sm h-7 py-1 px-2 text-xs w-32" {...register('due_date')} />
        <button type="submit" className="btn-primary btn-xs" disabled={addMilestone.isPending}>
          {addMilestone.isPending ? <Spinner size="sm" /> : <Plus className="w-3 h-3" />}
        </button>
      </form>
    </div>
  );
}

function GoalCard({ goal, cid }) {
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
      {goal.target_date && (
        <p className="text-[10px] text-gray-400 mt-2">Target: {goal.target_date}</p>
      )}
      <button onClick={() => setExpanded(!expanded)}
        className="text-xs text-brand-600 mt-2 hover:text-brand-700">
        {expanded ? 'Hide milestones' : 'Show milestones'}
      </button>
      {expanded && <MilestoneList goalId={goal.id} cid={cid} />}
    </div>
  );
}

export default function GoalsPage() {
  const { clientId } = useParams();
  const [showCreate, setShowCreate] = useState(false);
  const qc = useQueryClient();

  const { data: client } = useQuery({
    queryKey: ['lead', clientId],
    queryFn: () => leadsApi.get(clientId),
  });

  const { data, isLoading } = useQuery({
    queryKey: ['goals', clientId],
    queryFn: () => financialsApi.listGoals(clientId),
  });

  const { register, handleSubmit, reset } = useForm();

  const createGoal = useMutation({
    mutationFn: (data) => financialsApi.createGoal(clientId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['goals', clientId] });
      toast.success('Goal created');
      reset();
      setShowCreate(false);
    },
    onError: (e) => toast.error(e.message),
  });

  const goals = data?.results ?? data ?? [];
  const name = client ? (client.full_name ?? `${client.first_name} ${client.last_name}`) : `#${clientId}`;

  if (isLoading) return <PageSpinner />;

  return (
    <div>
      <PageHeader
        crumbs={[
          { label: 'Leads & Clients', to: '/leads' },
          { label: name, to: `/leads/${clientId}` },
          { label: 'Goals' },
        ]}
        title="Financial Goals"
        subtitle={name}
        icon={Target}
        actions={
          <button onClick={() => setShowCreate(!showCreate)} className="btn-primary btn-sm">
            <Plus className="w-3.5 h-3.5" />
            New Goal
          </button>
        }
      />

      {/* Create form */}
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
                {createGoal.isPending && <Spinner size="sm" />}
                Create Goal
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Goal cards */}
      {goals.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {goals.map((g) => <GoalCard key={g.id} goal={g} cid={clientId} />)}
        </div>
      ) : (
        <EmptyState
          icon={Target}
          title="No goals yet"
          subtitle="Create a financial goal to start tracking progress."
          action={<button onClick={() => setShowCreate(true)} className="btn-primary btn-sm">New Goal</button>}
        />
      )}
    </div>
  );
}
