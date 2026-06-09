import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { FileText, Upload, CheckCircle, Clock, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { getDocuments, uploadDocument } from '../api/portal.js';
import PageHeader from '../components/ui/PageHeader.jsx';
import Badge from '../components/ui/Badge.jsx';
import DataTable from '../components/ui/DataTable.jsx';
import EmptyState from '../components/ui/EmptyState.jsx';

const DOC_TYPES = [
  { value: 'identity', label: 'Identity Document' },
  { value: 'financial', label: 'Financial Statement' },
  { value: 'kyc', label: 'KYC Form' },
  { value: 'contract', label: 'Contract / Agreement' },
  { value: 'tax', label: 'Tax Document' },
  { value: 'other', label: 'Other' },
];

const STATUS_VARIANTS = {
  pending: 'amber',
  verified: 'emerald',
  rejected: 'red',
  expired: 'gray',
};

const COLUMNS = [
  {
    key: 'name',
    label: 'Document',
    render: (row) => (
      <div className="flex items-center gap-2">
        <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
        <div>
          <p className="text-xs font-medium text-gray-800 dark:text-gray-200 truncate max-w-[200px]">
            {row.original_filename || row.storage_ref || 'Document'}
          </p>
          <p className="text-[10px] text-gray-400">
            {DOC_TYPES.find((t) => t.value === row.doc_type)?.label ?? row.doc_type ?? '—'}
          </p>
        </div>
      </div>
    ),
  },
  {
    key: 'kyc_status',
    label: 'KYC Status',
    render: (row) => {
      const status = row.kyc_status || row.status || 'pending';
      return (
        <Badge variant={STATUS_VARIANTS[status] ?? 'gray'}>
          {status}
        </Badge>
      );
    },
  },
  {
    key: 'uploaded_at',
    label: 'Uploaded',
    render: (row) => {
      const date = row.uploaded_at || row.created_at;
      return (
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {date ? format(new Date(date), 'MMM d, yyyy') : '—'}
        </span>
      );
    },
  },
  {
    key: 'status_icon',
    label: '',
    render: (row) => {
      const status = row.kyc_status || row.status || 'pending';
      if (status === 'verified') {
        return <CheckCircle className="w-4 h-4 text-emerald-500" />;
      }
      if (status === 'pending') {
        return <Clock className="w-4 h-4 text-amber-500" />;
      }
      return null;
    },
  },
];

function UploadZone({ onUpload, isPending }) {
  const [docType, setDocType] = useState('');
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef(null);

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) setFile(droppedFile);
  }

  function handleFileChange(e) {
    setFile(e.target.files?.[0] ?? null);
  }

  function handleSubmit() {
    if (!file) {
      toast.error('Please select a file to upload');
      return;
    }
    if (!docType) {
      toast.error('Please select a document type');
      return;
    }
    onUpload({ doc_type: docType, storage_ref: file.name, original_filename: file.name });
    setFile(null);
    setDocType('');
    if (fileRef.current) fileRef.current.value = '';
  }

  return (
    <div className="card p-5 mb-6">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Upload Document</h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        {/* Type selector */}
        <div>
          <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">
            Document Type <span className="text-red-500">*</span>
          </label>
          <select
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
            className="select"
          >
            <option value="">Select category…</option>
            {DOC_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>

        {/* File input */}
        <div>
          <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">
            File <span className="text-red-500">*</span>
          </label>
          <input
            ref={fileRef}
            type="file"
            onChange={handleFileChange}
            className="block w-full text-xs text-gray-600 dark:text-gray-400
                       file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0
                       file:text-xs file:font-medium file:bg-brand-50 file:text-brand-700
                       dark:file:bg-brand-900/30 dark:file:text-brand-300
                       hover:file:bg-brand-100 dark:hover:file:bg-brand-900/50
                       cursor-pointer"
          />
        </div>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors mb-4 ${
          dragOver
            ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20'
            : file
            ? 'border-emerald-400 bg-emerald-50 dark:bg-emerald-900/20'
            : 'border-gray-200 dark:border-gray-600 hover:border-brand-400 hover:bg-gray-50 dark:hover:bg-gray-800'
        }`}
      >
        {file ? (
          <div className="flex items-center justify-center gap-2">
            <FileText className="w-5 h-5 text-emerald-500" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{file.name}</span>
            <button
              onClick={(e) => { e.stopPropagation(); setFile(null); if (fileRef.current) fileRef.current.value = ''; }}
              className="ml-1 p-0.5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-400"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <>
            <Upload className="w-8 h-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Drag & drop a file here, or <span className="text-brand-600 dark:text-brand-400">click to browse</span>
            </p>
            <p className="text-xs text-gray-400 mt-1">PDF, JPG, PNG up to 10MB</p>
          </>
        )}
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={isPending || !file || !docType}
          className="btn-primary"
        >
          {isPending ? (
            <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
          ) : (
            <Upload className="w-4 h-4" />
          )}
          Upload Document
        </button>
      </div>
    </div>
  );
}

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const { data, isLoading, isError } = useQuery({
    queryKey: ['documents', page],
    queryFn: () => getDocuments({ page, page_size: pageSize }),
  });

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      toast.success('Document uploaded successfully. Pending review.');
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: (err) => {
      toast.error(err.message || 'Upload failed');
    },
  });

  const documents = data?.results ?? data ?? [];
  const totalCount = data?.count ?? documents.length;

  return (
    <div>
      <PageHeader
        title="Documents"
        subtitle="Your uploaded documents and KYC files"
      />

      <UploadZone
        onUpload={(payload) => uploadMutation.mutate(payload)}
        isPending={uploadMutation.isPending}
      />

      {/* Documents table */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            Your Documents
          </h3>
        </div>

        {isError ? (
          <div className="px-6 py-8 text-center text-sm text-red-600 dark:text-red-400">
            Unable to load documents. Please try again later.
          </div>
        ) : (
          <DataTable
            columns={COLUMNS}
            data={documents}
            loading={isLoading}
            emptyText="No documents uploaded yet. Upload your first document above."
            totalCount={totalCount}
            page={page}
            pageSize={pageSize}
            onPageChange={setPage}
            rowKey={(row) => row.id}
          />
        )}
      </div>

      <div className="mt-4 p-4 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          All documents are encrypted and securely stored. Your advisor reviews uploaded documents for KYC compliance.
          Documents marked "Pending" are awaiting review.
        </p>
      </div>
    </div>
  );
}
