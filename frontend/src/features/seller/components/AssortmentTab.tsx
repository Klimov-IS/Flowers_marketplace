import { useState, useEffect } from 'react';
import {
  useGetFlatItemsQuery,
  useGetAssortmentMetricsQuery,
} from '../supplierApi';
import { useDebounce } from '../../../hooks/useDebounce';
import AssortmentTable from './AssortmentTable';
import { initialFilters, filtersToParams } from './FilterBar';
import type { ColumnFilters } from './FilterBar';
import type { FilterValue } from './ColumnFilter';
import type { SortState } from '../../../types/supplierItem';
import UploadModal from './UploadModal';
import ImportHistoryModal from './ImportHistoryModal';

type StatusFilter = 'all' | 'published' | 'needs_review' | 'errors';

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: 'all', label: 'Все статусы' },
  { value: 'published', label: 'Опубликовано' },
  { value: 'needs_review', label: 'На проверке' },
  { value: 'errors', label: 'Ошибки' },
];

interface AssortmentTabProps {
  supplierId: string;
}

export default function AssortmentTab({ supplierId }: AssortmentTabProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [filters, setFilters] = useState<ColumnFilters>(initialFilters);
  const [sort, setSort] = useState<SortState>({ field: null, direction: null });
  const perPage = 50;

  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [expandedAIItemId, setExpandedAIItemId] = useState<string | null>(null);

  const debouncedSearch = useDebounce(searchQuery, 300);

  useEffect(() => { setPage(1); }, [debouncedSearch]);
  useEffect(() => { setPage(1); }, [filters, statusFilter]);
  useEffect(() => { setSelectedIds(new Set()); }, [page, debouncedSearch, filters, statusFilter]);

  const filterParams = filtersToParams(filters);

  // Map status filter to API params
  const pillParams: { has_suggestions?: boolean } = {};
  if (statusFilter === 'needs_review') {
    pillParams.has_suggestions = true;
  } else if (statusFilter === 'published') {
    pillParams.has_suggestions = false;
  }

  const { data, isLoading, isFetching } = useGetFlatItemsQuery({
    supplier_id: supplierId,
    q: debouncedSearch || undefined,
    page,
    per_page: perPage,
    ...filterParams,
    ...pillParams,
    sort_by: sort.field || undefined,
    sort_dir: sort.direction || undefined,
  });

  const { data: metrics } = useGetAssortmentMetricsQuery(supplierId);

  const items = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / perPage);

  const handleFilterChange = (key: keyof ColumnFilters, value: FilterValue | null) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleResetFilters = () => {
    setFilters(initialFilters);
    setSort({ field: null, direction: null });
    setStatusFilter('all');
    setSearchQuery('');
  };

  const handleSortChange = (field: string) => {
    setSort((prev) => {
      if (prev.field !== field) return { field, direction: 'asc' };
      if (prev.direction === 'asc') return { field, direction: 'desc' };
      return { field: null, direction: null };
    });
  };

  const hasActiveFilters = searchQuery || statusFilter !== 'all' || sort.field !== null ||
    Object.values(filters).some((f) => f !== null);

  return (
    <div className="space-y-4">
      {/* ── Top Bar ──────────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
        <div className="flex flex-1 gap-3 items-center w-full sm:w-auto">
          {/* Search */}
          <div className="relative flex-1 max-w-sm">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Поиск по названию..."
              className="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 rounded-xl bg-gray-50 focus:bg-white focus:border-primary-300 focus:ring-1 focus:ring-primary-200 outline-none transition-all"
            />
          </div>

          {/* Status dropdown */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            className="px-3 py-2 text-sm border border-gray-200 rounded-xl bg-gray-50 focus:bg-white focus:border-primary-300 focus:ring-1 focus:ring-primary-200 outline-none transition-all cursor-pointer"
          >
            {STATUS_OPTIONS.map((opt) => {
              const count = opt.value === 'all' ? metrics?.total_items
                : opt.value === 'published' ? metrics?.published
                : opt.value === 'needs_review' ? metrics?.needs_review
                : metrics?.errors;
              return (
                <option key={opt.value} value={opt.value}>
                  {opt.label}{count !== undefined ? ` (${count})` : ''}
                </option>
              );
            })}
          </select>

          {/* Reset */}
          {hasActiveFilters && (
            <button
              onClick={handleResetFilters}
              className="text-sm text-gray-400 hover:text-gray-600 transition-colors whitespace-nowrap"
              title="Сбросить все фильтры"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => setIsHistoryModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-xl text-gray-600 hover:bg-gray-50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            История
          </button>
          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="flex items-center gap-1.5 px-4 py-2 text-sm bg-primary-600 text-white rounded-xl hover:bg-primary-700 transition-colors font-medium"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Добавить
          </button>
        </div>
      </div>

      {/* ── Bulk Actions Bar (visible when items selected) ─────────────────── */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 px-4 py-2.5 bg-primary-50 border border-primary-200 rounded-xl text-sm">
          <span className="text-primary-700 font-medium">
            Выбрано: {selectedIds.size}
          </span>
          <div className="h-4 w-px bg-primary-200" />
          <button className="text-primary-600 hover:text-primary-800 font-medium transition-colors">
            Опубликовать
          </button>
          <button className="text-primary-600 hover:text-primary-800 font-medium transition-colors">
            Скрыть
          </button>
          <button className="text-red-500 hover:text-red-700 font-medium transition-colors">
            Удалить
          </button>
        </div>
      )}

      {/* ── Table ────────────────────────────────────────────────────────────── */}
      <AssortmentTable
        items={items}
        isLoading={isLoading}
        selectedIds={selectedIds}
        onSelectionChange={setSelectedIds}
        filters={filters}
        onFilterChange={handleFilterChange}
        sort={sort}
        onSortChange={handleSortChange}
        expandedAIItemId={expandedAIItemId}
        onToggleAIExpand={(itemId) =>
          setExpandedAIItemId((prev) => (prev === itemId ? null : itemId))
        }
        onUploadClick={() => setIsUploadModalOpen(true)}
      />

      {/* ── Pagination ───────────────────────────────────────────────────────── */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">
            {total} позиций · страница {page} из {totalPages}
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || isFetching}
              className="p-2 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>

            {/* Page numbers */}
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              let pageNum: number;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (page <= 3) {
                pageNum = i + 1;
              } else if (page >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = page - 2 + i;
              }
              return (
                <button
                  key={pageNum}
                  onClick={() => setPage(pageNum)}
                  disabled={isFetching}
                  className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                    page === pageNum
                      ? 'bg-primary-500 text-white'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}

            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages || isFetching}
              className="p-2 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* ── Modals ───────────────────────────────────────────────────────────── */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
      />
      <ImportHistoryModal
        isOpen={isHistoryModalOpen}
        onClose={() => setIsHistoryModalOpen(false)}
        supplierId={supplierId}
      />
    </div>
  );
}
