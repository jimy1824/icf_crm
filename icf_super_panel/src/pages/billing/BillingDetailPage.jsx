import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { CheckCircle, CreditCard } from 'lucide-react';
import { billingApi } from '../../api/tenants.js';
import { useFetch } from '../../hooks/useFetch.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { PageSpinner } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';

function centsToDisplay(cents, currency = 'USD') {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(cents / 100);
}

function Row({ label, value, children, highlight }) {
  return (
    <div className={`flex justify-between items-start py-2.5 border-b border-gray-50 dark:border-gray-700/50 last:border-0 ${highlight ? 'bg-amber-50/30 dark:bg-amber-900/20 -mx-5 px-5' : ''}`}>
      <span className={`text-xs w-36 flex-shrink-0 ${highlight ? 'text-amber-700 dark:text-amber-400 font-medium' : 'text-gray-400'}`}>{label}</span>
      {children ?? <span className="text-xs text-gray-800 dark:text-gray-200">{value ?? '—'}</span>}
    </div>
  );
}

export default function BillingDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: record, loading, error, refetch } = useFetch(() => billingApi.get(id), [id]);

  const [paymentMethod, setPaymentMethod] = useState('card');
  const [transactionId, setTransactionId] = useState('');
  const [paying, setPaying] = useState(false);
  const [payError, setPayError] = useState(null);

  async function handleRecordPayment(e) {
    e.preventDefault();
    setPaying(true); setPayError(null);
    try {
      await billingApi.recordPayment(id, { payment_method: paymentMethod, transaction_id: transactionId });
      setTransactionId('');
      refetch();
    } catch (err) { setPayError(err); }
    finally { setPaying(false); }
  }

  if (loading) return <PageSpinner />;
  if (error) return <ErrorAlert error={error} />;
  if (!record) return null;

  const invoiceRef = record.invoice_number || `#${record.id}`;

  return (
    <div className="max-w-lg">
      <PageHeader
        crumbs={[{ label: 'Billing', to: '/billing' }, { label: invoiceRef }]}
        title={`Invoice ${invoiceRef}`}
        subtitle={`${record.record_type} — ${record.period_start} to ${record.period_end}`}
      />

      {/* Invoice details */}
      <div className="card p-5 mb-5">
        <div className="flex items-center gap-2 mb-4">
          <CreditCard className="w-4 h-4 text-brand-600" />
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Invoice Details</h2>
          <div className="ml-auto"><Badge status={record.status} showDot /></div>
        </div>

        <div className="divide-y divide-gray-50 dark:divide-gray-700/50">
          <Row label="Type" value={record.record_type} />
          <Row label="Amount" value={centsToDisplay(record.amount_cents, record.currency)} />
          {record.tax_amount_cents > 0 && (
            <Row label="Tax" value={centsToDisplay(record.tax_amount_cents, record.currency)} />
          )}
          {record.discount_amount_cents > 0 && (
            <Row label="Discount" value={`−${centsToDisplay(record.discount_amount_cents, record.currency)}`} />
          )}
          <Row label="Period" value={`${record.period_start} – ${record.period_end}`} />
          {record.external_invoice_id && (
            <Row label="External ID"><span className="text-xs font-mono text-gray-700 dark:text-gray-300">{record.external_invoice_id}</span></Row>
          )}
          {record.payment_method && <Row label="Payment method" value={record.payment_method} />}
          {record.transaction_id && (
            <Row label="Transaction ID"><span className="text-xs font-mono text-gray-700 dark:text-gray-300">{record.transaction_id}</span></Row>
          )}
          {record.paid_at && (
            <Row label="Paid at" value={record.paid_at.slice(0, 19).replace('T', ' ')} highlight />
          )}
          <Row label="Created" value={record.created_at?.slice(0, 10)} />
          {record.notes && <Row label="Notes" value={record.notes} />}
        </div>
      </div>

      {/* Record payment */}
      {record.status === 'pending' && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle className="w-4 h-4 text-emerald-600" />
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Record Payment</h2>
          </div>
          <ErrorAlert error={payError} className="mb-4" />
          <form onSubmit={handleRecordPayment} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">
                  Payment Method
                </label>
                <select
                  className="select"
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value)}
                >
                  <option value="card">Card</option>
                  <option value="bank_transfer">Bank Transfer</option>
                  <option value="check">Check</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">
                  Transaction ID
                </label>
                <input
                  className="input font-mono"
                  placeholder="Optional reference"
                  value={transactionId}
                  onChange={(e) => setTransactionId(e.target.value)}
                />
              </div>
            </div>
            <button type="submit" className="btn-primary" disabled={paying}>
              {paying ? <><Spinner size="sm" />Recording…</> : 'Mark as Paid'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
