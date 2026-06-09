/**
 * DataTable — enterprise-grade server-side data table.
 *
 * All pagination, sorting, and filtering are driven by the parent through
 * props + callbacks. This component NEVER sorts or paginates locally.
 *
 * Props
 * ─────
 * columns        Array of column descriptors:
 *                  { key, label, sortable?, render?(row, value) }
 * data           Array of row objects (current page only)
 * loading        boolean — shows skeleton overlay
 * error          string | null — shows error state
 * emptyText      string — shown when data is empty and not loading
 * totalCount     number — total records across all pages
 * page           number — current 1-based page number
 * pageSize       number — rows per page
 * onPageChange   (newPage: number) => void
 * onPageSizeChange (newSize: number) => void  [optional]
 * ordering       string — current ordering field (e.g. '-created_at')
 * onSort         (field: string) => void  — called with bare field name; wrapper toggles asc/desc
 * search         string — current search term
 * onSearch       (term: string) => void
 * searchPlaceholder string [optional]
 * toolbar        ReactNode — extra controls rendered left of search (filters, date pickers, etc.)
 * rowKey         (row) => string|number   — unique key extractor
 * pageSizeOptions [optional] array of numbers, default [10, 20, 50]
 */

import { useCallback, useRef } from 'react';
import { ChevronDown, ChevronUp, ChevronsUpDown, ChevronLeft, ChevronRight, Search } from 'lucide-react';

const DEFAULT_PAGE_SIZES = [10, 20, 50];

// ── Sort icon ────────────────────────────────────────────────────────────────

function SortIcon({ field, ordering }) {
  if (!ordering) return <ChevronsUpDown className="w-3 h-3 text-gray-300 dark:text-gray-600" />;
  const active = ordering === field || ordering === `-${field}`;
  if (!active) return <ChevronsUpDown className="w-3 h-3 text-gray-300 dark:text-gray-600" />;
  if (ordering.startsWith('-')) return <ChevronDown className="w-3 h-3 text-brand-600" />;
  return <ChevronUp className="w-3 h-3 text-brand-600" />;
}

// ── Skeleton rows ─────────────────────────────────────────────────────────────

function SkeletonRows({ cols, count = 5 }) {
  return Array.from({ length: count }).map((_, i) => (
    <tr key={i}>
      {Array.from({ length: cols }).map((_, j) => (
        <td key={j} className="px-4 py-3">
          <div className="skeleton h-4 rounded w-full max-w-[180px]" />
        </td>
      ))}
    </tr>
  ));
}

// ── Pagination bar ────────────────────────────────────────────────────────────

function PaginationBar({ page, pageSize, totalCount, pageSizeOptions, onPageChange, onPageSizeChange }) {
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const from = totalCount === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, totalCount);

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-900">
      {/* Left: count + page size */}
      <div className="flex items-center gap-3">
        <span>
          {totalCount === 0
            ? 'No results'
            : `${from}–${to} of ${totalCount.toLocaleString()} rows`}
        </span>
        {onPageSizeChange && (
          <div className="flex items-center gap-1.5">
            <span>Rows per page:</span>
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              className="border border-gray-200 dark:border-gray-600 rounded px-1.5 py-0.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-xs"
            >
              {(pageSizeOptions || DEFAULT_PAGE_SIZES).map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Right: page controls */}
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="Previous page"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        {Array.from({ length: totalPages }, (_, i) => i + 1)
          .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 2)
          .reduce((acc, p, idx, arr) => {
            if (idx > 0 && arr[idx - 1] !== p - 1) acc.push('…');
            acc.push(p);
            return acc;
          }, [])
          .map((item, idx) =>
            item === '…' ? (
              <span key={`ellipsis-${idx}`} className="px-1 text-gray-400">…</span>
            ) : (
              <button
                key={item}
                onClick={() => onPageChange(item)}
                className={`min-w-[28px] h-7 rounded text-xs font-medium transition-colors ${
                  item === page
                    ? 'bg-brand-600 text-white'
                    : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                {item}
              </button>
            )
          )}

        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="Next page"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function DataTable({
  columns,
  data = [],
  loading = false,
  error = null,
  emptyText = 'No data found.',
  totalCount = 0,
  page = 1,
  pageSize = 20,
  onPageChange,
  onPageSizeChange,
  ordering = '',
  onSort,
  search = '',
  onSearch,
  searchPlaceholder = 'Search…',
  toolbar,
  rowKey,
  pageSizeOptions,
}) {
  const searchRef = useRef(null);

  const handleSort = useCallback((field) => {
    if (!onSort) return;
    if (ordering === field) {
      onSort(`-${field}`);
    } else if (ordering === `-${field}`) {
      onSort(field);
    } else {
      onSort(field);
    }
  }, [ordering, onSort]);

  const searchTimeout = useRef(null);
  const handleSearchChange = (e) => {
    const val = e.target.value;
    clearTimeout(searchTimeout.current);
    searchTimeout.current = setTimeout(() => onSearch?.(val), 350);
  };

  return (
    <div className="flex flex-col rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden bg-white dark:bg-gray-900">
      {/* ── Toolbar ── */}
      <div className="flex flex-wrap items-center gap-3 px-4 py-3 border-b border-gray-100 dark:border-gray-700 bg-white dark:bg-gray-900">
        {toolbar && <div className="flex items-center gap-2 flex-wrap">{toolbar}</div>}
        <div className="ml-auto flex items-center gap-2 min-w-[200px]">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
            <input
              ref={searchRef}
              type="search"
              defaultValue={search}
              onChange={handleSearchChange}
              placeholder={searchPlaceholder}
              className="w-full pl-8 pr-3 py-1.5 text-xs
                         border border-gray-200 dark:border-gray-600
                         rounded-lg
                         bg-white dark:bg-gray-800
                         text-gray-900 dark:text-gray-100
                         placeholder:text-gray-400 dark:placeholder:text-gray-500
                         focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
            />
          </div>
        </div>
      </div>

      {/* ── Error state ── */}
      {error && !loading && (
        <div className="px-6 py-8 text-center text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {/* ── Table ── */}
      {!error && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-800/60 border-b border-gray-100 dark:border-gray-700">
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className={`text-left px-4 py-3 text-gray-500 dark:text-gray-400 font-semibold whitespace-nowrap select-none ${
                      col.sortable ? 'cursor-pointer hover:text-gray-700 dark:hover:text-gray-200' : ''
                    }`}
                    onClick={col.sortable ? () => handleSort(col.key) : undefined}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                      {col.sortable && <SortIcon field={col.key} ordering={ordering} />}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
              {loading ? (
                <SkeletonRows cols={columns.length} count={pageSize > 10 ? 8 : 5} />
              ) : data.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} className="px-6 py-12 text-center text-sm text-gray-400 dark:text-gray-500">
                    {emptyText}
                  </td>
                </tr>
              ) : (
                data.map((row) => (
                  <tr
                    key={rowKey ? rowKey(row) : row.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors"
                  >
                    {columns.map((col) => (
                      <td key={col.key} className="px-4 py-3 text-gray-700 dark:text-gray-200 align-top">
                        {col.render
                          ? col.render(row, row[col.key])
                          : <span className="text-xs">{row[col.key] ?? '—'}</span>}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Pagination ── */}
      {!error && (
        <PaginationBar
          page={page}
          pageSize={pageSize}
          totalCount={totalCount}
          pageSizeOptions={pageSizeOptions}
          onPageChange={onPageChange}
          onPageSizeChange={onPageSizeChange}
        />
      )}
    </div>
  );
}
