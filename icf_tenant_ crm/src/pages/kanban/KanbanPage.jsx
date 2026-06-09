import { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Filter, Plus, RefreshCw, User } from 'lucide-react';
import toast from 'react-hot-toast';
import { leadsApi } from '../../api/leads.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import Spinner from '../../components/ui/Spinner.jsx';

const STAGES = [
  { key: 'new',          label: 'New Leads',      color: 'bg-blue-500' },
  { key: 'contacted',    label: 'Contacted',       color: 'bg-indigo-500' },
  { key: 'qualified',    label: 'Qualified',       color: 'bg-violet-500' },
  { key: 'in_discussion',label: 'In Discussion',   color: 'bg-purple-500' },
  { key: 'proposal_sent',label: 'Proposal Sent',   color: 'bg-amber-500' },
  { key: 'closed_won',   label: 'Closed Won',      color: 'bg-success-500' },
  { key: 'closed_lost',  label: 'Closed Lost',     color: 'bg-gray-400' },
];

function LeadCard({ lead, onDragStart }) {
  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, lead)}
      className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700
                 p-3 shadow-card cursor-grab active:cursor-grabbing hover:shadow-card-hover
                 transition-shadow select-none"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-xs font-semibold text-gray-900 dark:text-white leading-tight line-clamp-2">
          {lead.full_name ?? `${lead.first_name ?? ''} ${lead.last_name ?? ''}`.trim()}
        </p>
        {lead.priority && <Badge status={lead.priority} className="text-[10px] flex-shrink-0" />}
      </div>
      {lead.email && <p className="text-[10px] text-gray-400 truncate mb-1.5">{lead.email}</p>}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1 text-[10px] text-gray-400">
          <User className="w-2.5 h-2.5" />
          <span>{lead.assigned_advisor_name ?? `Advisor #${lead.assigned_advisor}`}</span>
        </div>
        <Link
          to={`/leads/${lead.id}`}
          onClick={(e) => e.stopPropagation()}
          className="text-[10px] text-brand-600 hover:text-brand-700 font-medium"
        >
          Open →
        </Link>
      </div>
      {lead.campaign_name && (
        <p className="text-[10px] text-violet-500 mt-1 truncate">📣 {lead.campaign_name}</p>
      )}
    </div>
  );
}

export default function KanbanPage() {
  const qc = useQueryClient();
  const [draggedLead, setDraggedLead] = useState(null);
  const [dragOverStage, setDragOverStage] = useState(null);
  const [movingId, setMovingId] = useState(null);

  const { data: kanban, isLoading } = useQuery({
    queryKey: ['kanban'],
    queryFn: leadsApi.kanban,
  });

  const moveStage = useMutation({
    mutationFn: ({ id, stage }) => leadsApi.moveStage(id, stage),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kanban'] });
      qc.invalidateQueries({ queryKey: ['leads'] });
      toast.success('Stage updated');
    },
    onError: (e) => toast.error(e.message),
    onSettled: () => setMovingId(null),
  });

  const handleDragStart = useCallback((e, lead) => {
    setDraggedLead(lead);
    e.dataTransfer.effectAllowed = 'move';
  }, []);

  const handleDragOver = useCallback((e, stageKey) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverStage(stageKey);
  }, []);

  const handleDrop = useCallback((e, stageKey) => {
    e.preventDefault();
    if (!draggedLead || draggedLead.status === stageKey) { setDraggedLead(null); setDragOverStage(null); return; }
    setMovingId(draggedLead.id);
    moveStage.mutate({ id: draggedLead.id, stage: stageKey });
    setDraggedLead(null);
    setDragOverStage(null);
  }, [draggedLead, moveStage]);

  // kanban response shape: { stages: { new: [...], contacted: [...], ... } }
  const stages = kanban?.stages ?? kanban ?? {};

  return (
    <div className="h-full flex flex-col">
      <PageHeader
        title="Pipeline Kanban"
        subtitle="Drag cards between stages — BRU-31: each move updates lead status, timeline, and audit automatically."
        actions={
          <div className="flex items-center gap-2">
            <button className="btn-ghost btn-sm" onClick={() => qc.invalidateQueries({ queryKey: ['kanban'] })}>
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </button>
            <Link to="/leads/new" className="btn-primary btn-sm">
              <Plus className="w-3.5 h-3.5" />
              New Lead
            </Link>
          </div>
        }
      />

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Spinner size="lg" className="text-brand-500" />
        </div>
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-4 flex-1 min-h-0">
          {STAGES.map((s) => {
            const cards = stages[s.key] ?? [];
            const isOver = dragOverStage === s.key;
            return (
              <div
                key={s.key}
                className={`flex-shrink-0 w-64 flex flex-col rounded-xl border transition-colors
                  ${isOver
                    ? 'border-brand-400 bg-brand-50 dark:bg-brand-900/20'
                    : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50'}`}
                onDragOver={(e) => handleDragOver(e, s.key)}
                onDragLeave={() => setDragOverStage(null)}
                onDrop={(e) => handleDrop(e, s.key)}
              >
                {/* Column header */}
                <div className="flex items-center justify-between px-3 py-2.5 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${s.color}`} />
                    <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">{s.label}</span>
                  </div>
                  <span className="text-xs text-gray-400 bg-white dark:bg-gray-700 px-1.5 py-0.5 rounded-full font-medium">
                    {cards.length}
                  </span>
                </div>

                {/* Cards */}
                <div className="flex-1 overflow-y-auto p-2 space-y-2 min-h-[120px]">
                  {cards.map((lead) => (
                    <div key={lead.id} className={`transition-opacity ${movingId === lead.id ? 'opacity-40' : ''}`}>
                      <LeadCard lead={lead} onDragStart={handleDragStart} />
                    </div>
                  ))}
                  {cards.length === 0 && (
                    <div className={`h-20 rounded-lg border-2 border-dashed flex items-center justify-center
                      ${isOver ? 'border-brand-400 bg-brand-50/50' : 'border-gray-200 dark:border-gray-700'}`}>
                      <span className="text-[10px] text-gray-400">Drop here</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
