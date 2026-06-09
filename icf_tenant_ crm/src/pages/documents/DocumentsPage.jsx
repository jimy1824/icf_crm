import { useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { FileText, Lock, Upload, CheckCircle, XCircle, Clock } from 'lucide-react';
import { documentsApi } from '../../api/documents.js';
import { leadsApi } from '../../api/leads.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { PageSpinner, SkeletonRow } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';
import ConfirmModal from '../../components/ui/ConfirmModal.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';

const KYC_ACTIONS = {
  pending: [
    { label: 'Verify',  action: 'verify',  icon: CheckCircle, className: 'text-success-600 hover:text-success-700' },
    { label: 'Reject',  action: 'reject',  icon: XCircle,     className: 'text-danger-600 hover:text-danger-700' },
  ],
  verified: [
    { label: 'Legal Hold', action: 'legal_hold', icon: Lock, className: 'text-warning-600 hover:text-warning-700' },
  ],
  rejected: [],
};

export default function DocumentsPage() {
  const { clientId } = useParams();
  const qc = useQueryClient();
  const fileRef = useRef(null);
  const [docType, setDocType] = useState('identity');
  const [confirm, setConfirm] = useState(null);
  const [filter, setFilter] = useState('');

  const { data: client } = useQuery({
    queryKey: ['lead', clientId],
    queryFn: () => leadsApi.get(clientId),
  });
  const { data, isLoading } = useQuery({
    queryKey: ['documents', clientId, filter],
    queryFn: () => documentsApi.list({ client: clientId, kyc_status: filter || undefined }),
  });

  const upload = useMutation({
    mutationFn: ({ file, docType }) => documentsApi.upload(clientId, file, docType),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents', clientId] });
      toast.success('Document uploaded');
      if (fileRef.current) fileRef.current.value = '';
    },
    onError: (e) => toast.error(e.message),
  });

  const kycAction = useMutation({
    mutationFn: ({ docId, action, notes }) => {
      if (action === 'verify') return documentsApi.verify(docId, { notes });
      if (action === 'reject') return documentsApi.reject(docId, { notes });
      if (action === 'legal_hold') return documentsApi.legalHold(docId, { notes });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents', clientId] });
      toast.success('Document updated');
      setConfirm(null);
    },
    onError: (e) => toast.error(e.message),
  });

  const deleteDoc = useMutation({
    mutationFn: (docId) => documentsApi.delete(docId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents', clientId] });
      toast.success('Document deleted');
      setConfirm(null);
    },
    onError: (e) => toast.error(e.message),
  });

  const docs = data?.results ?? data ?? [];
  const name = client ? (client.full_name ?? `${client.first_name} ${client.last_name}`) : `#${clientId}`;

  return (
    <div>
      {confirm && <ConfirmModal {...confirm} onCancel={() => setConfirm(null)} />}

      <PageHeader
        crumbs={[
          { label: 'Leads & Clients', to: '/leads' },
          { label: name, to: `/leads/${clientId}` },
          { label: 'Documents' },
        ]}
        title="Documents & KYC"
        subtitle={name}
        icon={FileText}
      />

      {/* Upload */}
      <div className="card p-5 mb-5">
        <h3 className="section-title mb-3 flex items-center gap-2">
          <Upload className="w-4 h-4 text-gray-400" /> Upload Document
        </h3>
        <div className="flex flex-col sm:flex-row gap-3 items-end">
          <div className="space-y-1.5 flex-1 max-w-xs">
            <label className="label">Document Type</label>
            <select className="select" value={docType} onChange={(e) => setDocType(e.target.value)}>
              <option value="identity">Identity (Passport / DL)</option>
              <option value="address_proof">Address Proof</option>
              <option value="income">Income Verification</option>
              <option value="tax">Tax Document</option>
              <option value="financial_statement">Financial Statement</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div className="space-y-1.5 flex-1">
            <label className="label">File</label>
            <input ref={fileRef} type="file" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
              className="input text-xs file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:bg-brand-50 file:text-brand-600 file:text-xs cursor-pointer"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) upload.mutate({ file, docType });
              }} />
          </div>
          {upload.isPending && <Spinner size="md" className="text-brand-500 mb-2" />}
        </div>
        <p className="text-[10px] text-gray-400 mt-2">Accepted: PDF, JPG, PNG, DOC, DOCX</p>
      </div>

      {/* KYC filter */}
      <div className="flex items-center gap-2 mb-4">
        {['', 'pending', 'verified', 'rejected'].map((f) => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${filter === f ? 'bg-brand-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200'}`}>
            {f === '' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Documents table */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead><tr>
            <th className="th">File Name</th>
            <th className="th">Type</th>
            <th className="th">KYC Status</th>
            <th className="th hidden md:table-cell">Uploaded By</th>
            <th className="th hidden md:table-cell">Date</th>
            <th className="th">Actions</th>
          </tr></thead>
          <tbody>
            {isLoading && [1,2,3].map((i) => <SkeletonRow key={i} cols={6} />)}
            {!isLoading && docs.map((d) => {
              const actions = KYC_ACTIONS[d.kyc_status] ?? KYC_ACTIONS.pending;
              return (
                <tr key={d.id} className="hover:bg-gray-50/60 dark:hover:bg-gray-800/60">
                  <td className="td">
                    <div className="flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                      <span className="text-xs text-gray-800 dark:text-gray-200 truncate max-w-[160px]">
                        {d.file_name ?? d.name}
                      </span>
                    </div>
                  </td>
                  <td className="td text-xs text-gray-500 capitalize">{d.document_type?.replace(/_/g,' ')}</td>
                  <td className="td"><Badge status={d.kyc_status ?? 'pending'} showDot /></td>
                  <td className="td hidden md:table-cell text-xs text-gray-400">{d.uploaded_by_name ?? '—'}</td>
                  <td className="td hidden md:table-cell text-xs text-gray-400">{d.uploaded_at?.slice(0,10)}</td>
                  <td className="td">
                    <div className="flex items-center gap-2">
                      {actions.map(({ label, action, icon: Icon, className }) => (
                        <button key={action}
                          onClick={() => setConfirm({
                            title: `${label} Document`,
                            message: `${label} "${d.file_name ?? d.name}"?`,
                            danger: action === 'reject',
                            onConfirm: () => kycAction.mutate({ docId: d.id, action }),
                            loading: kycAction.isPending,
                          })}
                          className={`flex items-center gap-1 text-xs font-medium ${className}`}>
                          <Icon className="w-3 h-3" />
                          {label}
                        </button>
                      ))}
                      {d.legal_hold && (
                        <span className="text-[10px] text-warning-600 bg-warning-50 dark:bg-warning-900/20 px-1.5 py-0.5 rounded-full">
                          Legal Hold
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
            {!isLoading && docs.length === 0 && (
              <tr><td colSpan={6} className="td py-0">
                <EmptyState icon={FileText} title="No documents found"
                  subtitle="Upload a document to start KYC verification." />
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
