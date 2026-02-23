import { useState, useEffect } from 'react';
import {
  useGetFlatItemsQuery,
  useGetAssortmentMetricsQuery,
} from '../supplierApi';
import { useDebounce } from '../../../hooks/useDebounce';
import AssortmentTable from './AssortmentTable';
import SearchBar from './SearchBar';
import { initialFilters, filtersToParams } from './FilterBar';
import type { ColumnFilters } from './FilterBar';
import type { FilterValue, MultiSelectFilterValue } from './ColumnFilter';
import Button from '../../../components/ui/Button';
import type { SortState } from '../../../types/supplierItem';
import AssortmentStatusPills, { type AssortmentPillFilter } from './AssortmentStatusPills';
import UploadModal from './UploadModal';
import ImportHistoryModal from './ImportHistoryModal';

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

  // New state for pills, modals, AI expand
  const [pillFilter, setPillFilter] = useState<AssortmentPillFilter>('all');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [expandedAIItemId, setExpandedAIItemId] = useState<string | null>(null);

  // Debounce search query
  const debouncedSearch = useDebounce(searchQuery, 300);

  // Reset page when search changes
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

  // Reset page when filters or pill change
  useEffect(() => {
    setPage(1);
  }, [filters, pillFilter]);

  // Clear selection when page, search, or filters change
  useEffect(() => {
    setSelectedIds(new Set());
  }, [page, debouncedSearch, filters, pillFilter]);

  // Convert filters to API params
  const filterParams = filtersToParams(filters);

  // Map pill filter to API params
  const pillParams: { has_suggestions?: boolean } = {};
  if (pillFilter === 'needs_review') {
    pillParams.has_suggestions = true;
  } else if (pillFilter === 'published') {
    pillParams.has_suggestions = false;
  }
  // For 'errors' pill, we could add validation filter - keeping it simple for now

  // Fetch flat items (1 row = 1 variant)
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

  // Fetch assortment metrics for pills
  const { data: metrics } = useGetAssortmentMetricsQuery(supplierId);

  const items = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / perPage);

  // Filter handlers
  const handleFilterChange = (key: keyof ColumnFilters, value: FilterValue | null) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleResetFilters = () => {
    setFilters(initialFilters);
    setSort({ field: null, direction: null });
    setPillFilter('all');
  };

  // Sort handler - cycles through: asc -> desc -> none
  const handleSortChange = (field: string) => {
    setSort((prev) => {
      if (prev.field !== field) {
        return { field, direction: 'asc' };
      }
      if (prev.direction === 'asc') {
        return { field, direction: 'desc' };
      }
      return { field: null, direction: null };
    });
  };

  // Check if any filter is active (besides default status)
  const hasActiveFilters = () => {
    const { status, ...otherFilters } = filters;
    const statusValue = status as MultiSelectFilterValue | null;
    const isStatusNonDefault =
      statusValue?.selected?.length !== 2 ||
      !statusValue?.selected?.includes('active') ||
      !statusValue?.selected?.includes('hidden');
    const hasOtherFilters = Object.values(otherFilters).some((f) => f !== null);
    const hasSorting = sort.field !== null;
    const hasPillFilter = pillFilter !== 'all';
    return isStatusNonDefault || hasOtherFilters || hasSorting || hasPillFilter;
  };

  return (
    <div className="space-y-4">
      {/* Search and actions bar */}
      <div className="flex gap-4 items-center justify-between">
        <div className="flex-1 max-w-md">
          <SearchBar
            value={searchQuery}
            onChange={setSearchQuery}
            placeholder="Поиск по названию..."
          />
        </div>

        {/* Reset filters button */}
        {hasActiveFilters() && (
          <button
            onClick={handleResetFilters}
            className="text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Сбросить фильтры
          </button>
        )}

        {/* Action buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => setIsHistoryModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            История
          </button>
          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Загрузить прайс
          </button>
        </div>
      </div>

      {/* Status pills */}
      <AssortmentStatusPills
        activeFilter={pillFilter}
        onFilterChange={setPillFilter}
        metrics={metrics}
      />

      {/* Table */}
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

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between py-4">
          <div className="text-sm text-gray-600">
            Страница {page} из {totalPages}
          </div>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || isFetching}
            >
              Назад
            </Button>
            <Button
              variant="secondary"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages || isFetching}
            >
              Вперед
            </Button>
          </div>
        </div>
      )}

      {/* Modals */}
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
