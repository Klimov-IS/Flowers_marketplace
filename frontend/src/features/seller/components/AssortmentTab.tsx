import { useState, useEffect } from 'react';
import {
  useGetAdminProductsQuery,
  useBulkDeleteProductsMutation,
  useBulkHideProductsMutation,
  useBulkRestoreProductsMutation,
} from '../supplierApi';
import type { AdminProduct } from '../supplierApi';
import { useToast } from '../../../components/ui/Toast';
import ConfirmModal from '../../../components/ui/ConfirmModal';
import { useDebounce } from '../../../hooks/useDebounce';
import AssortmentTable from './AssortmentTable';
import { initialFilters, filtersToParams } from './FilterBar';
import type { ColumnFilters } from './FilterBar';
import type { FilterValue } from './ColumnFilter';
import type { FlatOfferVariant, SortState } from '../../../types/supplierItem';
import UploadModal from './UploadModal';
import CreateItemModal from './CreateItemModal';

type StatusFilter = 'all' | 'active' | 'hidden';

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: 'all', label: 'Все статусы' },
  { value: 'active', label: 'Активные' },
  { value: 'hidden', label: 'Скрытые' },
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
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [expandedAIItemId, setExpandedAIItemId] = useState<string | null>(null);
  const [bulkConfirm, setBulkConfirm] = useState<{ action: 'delete' | 'hide' | 'restore'; } | null>(null);

  const [bulkDelete, { isLoading: isBulkDeleting }] = useBulkDeleteProductsMutation();
  const [bulkHide, { isLoading: isBulkHiding }] = useBulkHideProductsMutation();
  const [bulkRestore, { isLoading: isBulkRestoring }] = useBulkRestoreProductsMutation();
  const { showToast } = useToast();

  const debouncedSearch = useDebounce(searchQuery, 300);

  useEffect(() => { setPage(1); }, [debouncedSearch]);
  useEffect(() => { setPage(1); }, [filters, statusFilter]);
  useEffect(() => { setSelectedIds(new Set()); }, [page, debouncedSearch, filters, statusFilter]);

  const filterParams = filtersToParams(filters);

  const { data, isLoading, isFetching } = useGetAdminProductsQuery({
    q: debouncedSearch || undefined,
    page,
    per_page: perPage,
    ...filterParams,
    // Status dropdown overrides column filter
    ...(statusFilter !== 'all' ? { status: [statusFilter] } : {}),
    sort_by: sort.field || undefined,
    sort_dir: sort.direction || undefined,
  });

  // Map AdminProduct[] to FlatOfferVariant[] for table compatibility
  const items: FlatOfferVariant[] = (data?.products || []).map((p: AdminProduct) => ({
    variant_id: p.id,
    item_id: p.id,
    raw_name: p.title || p.raw_name || '',
    flower_type: p.flower_type,
    subtype: null,
    variety: p.variety,
    origin_country: p.origin_country,
    colors: p.color ? [p.color] : [],
    length_cm: p.length_cm,
    pack_type: p.pack_type,
    pack_qty: p.pack_qty,
    price: String(p.price),
    stock: p.stock_qty,
    item_status: p.status,
    validation: 'ok' as const,
    source_file: null,
    possible_duplicate: false,
    has_pending_suggestions: false,
    photo_url: p.photo_url,
  }));
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

  const handleBulkAction = async () => {
    if (!bulkConfirm || selectedIds.size === 0) return;
    const productIds = [...selectedIds];
    try {
      if (bulkConfirm.action === 'delete') {
        const result = await bulkDelete(productIds).unwrap();
        showToast(`Удалено: ${result.affected_count} позиций`, 'success');
      } else if (bulkConfirm.action === 'hide') {
        const result = await bulkHide(productIds).unwrap();
        showToast(`Скрыто: ${result.affected_count} позиций`, 'success');
      } else if (bulkConfirm.action === 'restore') {
        const result = await bulkRestore(productIds).unwrap();
        showToast(`Опубликовано: ${result.affected_count} позиций`, 'success');
      }
      setSelectedIds(new Set());
    } catch {
      showToast('Ошибка при выполнении действия', 'error');
    }
    setBulkConfirm(null);
  };

  const hasActiveFilters = searchQuery || statusFilter !== 'all' || sort.field !== null ||
    Object.values(filters).some((f) => f !== null);

  return (
    <div className="space-y-4">
      {/* ── Top Bar ──────────────────────────────────────────────────────── */}
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
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          {/* Reset — text button */}
          {hasActiveFilters && (
            <button
              onClick={handleResetFilters}
              className="text-sm text-gray-500 hover:text-gray-700 transition-colors whitespace-nowrap underline decoration-dashed underline-offset-2"
            >
              Сбросить
            </button>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-1.5 px-4 py-2 text-sm border border-primary-600 text-primary-600 rounded-xl hover:bg-primary-50 transition-colors font-medium"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Добавить товар
          </button>
          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="flex items-center gap-1.5 px-4 py-2 text-sm bg-primary-600 text-white rounded-xl hover:bg-primary-700 transition-colors font-medium"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Загрузить прайс
          </button>
        </div>
      </div>

      {/* ── Bulk Actions Bar ──────────────────────────────────────────────── */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 px-4 py-2.5 bg-primary-50 border border-primary-200 rounded-xl text-sm">
          <span className="text-primary-700 font-medium">
            Выбрано: {selectedIds.size}
          </span>
          <div className="h-4 w-px bg-primary-200" />
          <button
            onClick={() => setBulkConfirm({ action: 'restore' })}
            className="text-primary-600 hover:text-primary-800 font-medium transition-colors"
          >
            Опубликовать
          </button>
          <button
            onClick={() => setBulkConfirm({ action: 'hide' })}
            className="text-primary-600 hover:text-primary-800 font-medium transition-colors"
          >
            Скрыть
          </button>
          <button
            onClick={() => setBulkConfirm({ action: 'delete' })}
            className="text-red-500 hover:text-red-700 font-medium transition-colors"
          >
            Удалить
          </button>
        </div>
      )}

      {/* ── Table ─────────────────────────────────────────────────────────── */}
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

      {/* ── Pagination ────────────────────────────────────────────────────── */}
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

      {/* ── Modals ────────────────────────────────────────────────────────── */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
      />
      <CreateItemModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        supplierId={supplierId}
      />
      <ConfirmModal
        isOpen={!!bulkConfirm}
        onClose={() => setBulkConfirm(null)}
        onConfirm={handleBulkAction}
        isLoading={isBulkDeleting || isBulkHiding || isBulkRestoring}
        title={
          bulkConfirm?.action === 'delete' ? 'Удалить выбранные?' :
          bulkConfirm?.action === 'hide' ? 'Скрыть выбранные?' :
          'Опубликовать выбранные?'
        }
        message={`Это действие будет применено к ${selectedIds.size} выбранным позициям.`}
        confirmLabel={
          bulkConfirm?.action === 'delete' ? 'Удалить' :
          bulkConfirm?.action === 'hide' ? 'Скрыть' :
          'Опубликовать'
        }
        variant={bulkConfirm?.action === 'delete' ? 'danger' : 'primary'}
      />
    </div>
  );
}
