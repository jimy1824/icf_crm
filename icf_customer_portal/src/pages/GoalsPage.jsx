import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { ChevronDown, ChevronUp, Target, TrendingUp } from 'lucide-react';
import { getGoals } from '../api/portal.js';
import PageHeader from '../components/ui/PageHeader.jsx';
import Badge from '../components/ui/Badge.jsx';
import EmptyState from '../components/ui/EmptyState.jsx';
import { PageSpinner } from '../components/ui/Spinner.jsx';
import { RadialBarChart, RadialBar, ResponsiveContainer, Tooltip } from 'recharts';

const GOAL_TYPE_LABELS = {
  retirement: 'Retirement',
  education: 'Education',
  home_purchase: 'Home Purchase',
  emergency_fund: 'Emergency Fund',
  wealth_building: 'Wealth Building',
  debt_payoff: 'Debt Payoff',
  other: 'Other',
};

function ProgressRing({ percentage }) {
  const pct = Math.min(100, Math.max(0, percentage ?? 0));
  const data = [{ name: 'progress', value: pct, fill: pct >= 100 ? '#10b981' : pct >= 50 ? '#3b82f6' : '#f59e0b' }];

  return (
    <div className="w-20 h-20 flex-shrink-0">
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          cx="50%"
          cy="50%"
          innerRadius="60%"
          outerRadius="80%"
          startAngle={90}
          endAngle={-270}
          data={data}
        >
          <RadialBar dataKey="value" cornerRadius={4} background={{ fill: '#e5e7eb' }} />
          <Tooltip formatter={(v) => [`${v.toFixed(0)}%`, 'Progress']} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="relative -mt-12 flex items-center justify-center">
        <span className="text-xs font-bold text-gray-700 dark:text-gray-200">{pct.toFixed(0)}%</span>
      </div>
    </div>
  );
}

function MilestoneList({ milestones }) {
  if (!milestones || milestones.length === 0) {
    return <p className="text-xs text-gray-400 dark:text-gray-500 pl-4">No milestones defined.</p>;
  }
  return (
    <ul className="space-y-2 pl-4">
      {milestones.map((ms) => (
        <li key={ms.id} className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${ms.is_completed ? 'bg-emerald-500' : 'bg-gray-300 dark:bg-gray-600'}`} />
          <span className={`text-xs ${ms.is_completed ? 'text-gray-400 line-through' : 'text-gray-600 dark:text-gray-300'}`}>
            {ms.title}
          </span>
          {ms.due_date && (
            <span className="text-[10px] text-gray-400 ml-auto">
              {format(new Date(ms.due_date), 'MMM d, yyyy')}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}

function GoalCard({ goal }) {
  const [expanded, setExpanded] = useState(false);
  const pct = Math.min(100, Math.max(0, goal.progress_percentage ?? 0));

  const currency = goal.currency || 'USD';
  const fmt = new Intl.NumberFormat('en-US', { style: 'currency', currency, minimumFractionDigits: 0 });

  return (
    <div className="card overflow-hidden">
      <div className="p-5">
        <div className="flex items-start gap-4">
          {/* Progress ring */}
          <ProgressRing percentage={pct} />

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2 mb-1">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{goal.title}</h3>
              <div className="flex items-center gap-1.5 flex-shrink-0">
                {goal.is_off_track && (
                  <Badge variant="amber">Off Track</Badge>
                )}
                {goal.goal_type && (
                  <Badge variant="gray">{GOAL_TYPE_LABELS[goal.goal_type] ?? goal.goal_type}</Badge>
                )}
              </div>
            </div>

            {/* Amounts */}
            <div className="grid grid-cols-2 gap-2 mt-2">
              {goal.target_amount != null && (
                <div>
                  <p className="text-[10px] text-gray-400 uppercase tracking-wide">Target</p>
                  <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">
                    {fmt.format(goal.target_amount)}
                  </p>
                </div>
              )}
              {goal.current_value != null && (
                <div>
                  <p className="text-[10px] text-gray-400 uppercase tracking-wide">Current</p>
                  <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                    {fmt.format(goal.current_value)}
                  </p>
                </div>
              )}
            </div>

            {/* Progress bar */}
            <div className="mt-2">
              <div className="h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    goal.is_off_track ? 'bg-amber-400' : pct >= 100 ? 'bg-emerald-500' : 'bg-brand-500'
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>

            {/* Target date */}
            {goal.target_date && (
              <p className="text-xs text-gray-400 mt-1.5">
                Target date: {format(new Date(goal.target_date), 'MMMM d, yyyy')}
              </p>
            )}
          </div>
        </div>

        {/* Milestones toggle */}
        {goal.milestones && goal.milestones.length > 0 && (
          <button
            onClick={() => setExpanded((e) => !e)}
            className="mt-3 flex items-center gap-1 text-xs text-brand-600 dark:text-brand-400 hover:underline font-medium"
          >
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            {expanded ? 'Hide' : 'Show'} milestones ({goal.milestones.length})
          </button>
        )}
      </div>

      {/* Milestones panel */}
      {expanded && (
        <div className="border-t border-gray-100 dark:border-gray-700 px-5 py-4 bg-gray-50 dark:bg-gray-800/50">
          <MilestoneList milestones={goal.milestones} />
        </div>
      )}
    </div>
  );
}

export default function GoalsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['goals'],
    queryFn: getGoals,
  });

  const goals = data?.results ?? data ?? [];
  const offTrackCount = goals.filter((g) => g.is_off_track).length;

  if (isLoading) return <PageSpinner />;

  return (
    <div>
      <PageHeader
        title="My Goals"
        subtitle="Your financial goals and progress — managed by your advisor"
      />

      {offTrackCount > 0 && (
        <div className="mb-4 px-4 py-3 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0" />
          <p className="text-sm text-amber-700 dark:text-amber-300">
            {offTrackCount} {offTrackCount === 1 ? 'goal is' : 'goals are'} currently off track. Contact your advisor to discuss.
          </p>
        </div>
      )}

      {isError ? (
        <div className="card p-6 text-center text-sm text-red-600 dark:text-red-400">
          Unable to load goals. Please try again later.
        </div>
      ) : goals.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={Target}
            title="No goals set yet"
            description="Your advisor will create financial goals based on your plan. Check back soon."
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {goals.map((goal) => (
            <GoalCard key={goal.id} goal={goal} />
          ))}
        </div>
      )}

      <div className="mt-6 p-4 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Goal progress is updated by your advisor and reflects your financial plan. Contact your advisor if you have questions about any goal.
        </p>
      </div>
    </div>
  );
}
