import { useState, useEffect, useRef } from 'react';
import {
  useGetSupplierItemsQuery,
  useDeleteSupplierItemMutation,
  useHideSupplierItemMutation,
  useRestoreSupplierItemMutation,
  useBulkDeleteItemsMutation,
  useBulkHideItemsMutation,
  useBulkRestoreItemsMutation,
} from '../supplierApi';
import { useDebounce } from '../../../hooks/useDebounce';
import AssortmentTable from './AssortmentTable';
import SearchBar from './SearchBar';
import ItemDetailsModal from './ItemDetailsModal';
import BulkActionsPanel from './BulkActionsPanel';
import { initialFilters, filtersToParams, STATUS_OPTIONS } from './FilterBar';
import type { ColumnFilters } from './FilterBar';
import type { FilterValue, MultiSelectFilterValue } from './ColumnFilter';
import Button from '../../../components/ui/Button';
import type { SupplierItem, SortState } from '../../../types/supplierItem';

interface AssortmentTabProps {
  supplierId: string;
}

export default function AssortmentTab({ supplierId }: AssortmentTabProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [selectedItem, setSelectedItem] = useState<SupplierItem | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [filters, setFilters] = useState<ColumnFilters>(initialFilters);
  const [sort, setSort] = useState<SortState>({ field: null, direction: null });
  const [isStatusOpen, setIsStatusOpen] = useState(false);
  const statusDropdownRef = useRef<HTMLDivElement>(null);
  const perPage = 50;

  // Debounce search query
  const debouncedSearch = useDebounce(searchQuery, 300);

  // Close status dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (statusDropdownRef.current && !statusDropdownRef.current.contains(event.target as Node)) {
        setIsStatusOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Reset page when search changes
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [filters]);

  // Clear selection when page, search, or filters change
  useEffect(() => {
    setSelectedIds(new Set());
  }, [page, debouncedSearch, filters]);

  // Convert filters to API params
  const filterParams = filtersToParams(filters);

  // Fetch items
  const { data, isLoading, isFetching } = useGetSupplierItemsQuery({
    supplier_id: supplierId,
    q: debouncedSearch || undefined,
    page,
    per_page: perPage,
    ...filterParams,
    sort_by: sort.field || undefined,
    sort_dir: sort.direction || undefined,
  });

  // Item action mutations
  const [deleteItem] = useDeleteSupplierItemMutation();
  const [hideItem] = useHideSupplierItemMutation();
  const [restoreItem] = useRestoreSupplierItemMutation();

  // Bulk action mutations
  const [bulkDelete, { isLoading: isBulkDeleting }] = useBulkDeleteItemsMutation();
  const [bulkHide, { isLoading: isBulkHiding }] = useBulkHideItemsMutation();
  const [bulkRestore, { isLoading: isBulkRestoring }] = useBulkRestoreItemsMutation();

  const items = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / perPage);

  const handleViewDetails = (item: SupplierItem) => {
    setSelectedItem(item);
  };

  const handleCloseModal = () => {
    setSelectedItem(null);
  };

  const handleHideItem = async (itemId: string) => {
    try {
      await hideItem(itemId).unwrap();
    } catch (error) {
      console.error('Failed to hide item:', error);
    }
  };

  const handleDeleteItem = async (itemId: string) => {
    try {
      await deleteItem(itemId).unwrap();
    } catch (error) {
      console.error('Failed to delete item:', error);
    }
  };

  const handleRestoreItem = async (itemId: string) => {
    try {
      await restoreItem(itemId).unwrap();
    } catch (error) {
      console.error('Failed to restore item:', error);
    }
  };

  // Bulk action handlers
  const handleBulkDelete = async () => {
    try {
      await bulkDelete(Array.from(selectedIds)).unwrap();
      setSelectedIds(new Set());
    } catch (error) {
      console.error('Failed to bulk delete items:', error);
    }
  };

  const handleBulkHide = async () => {
    try {
      await bulkHide(Array.from(selectedIds)).unwrap();
      setSelectedIds(new Set());
    } catch (error) {
      console.error('Failed to bulk hide items:', error);
    }
  };

  const handleBulkRestore = async () => {
    try {
      await bulkRestore(Array.from(selectedIds)).unwrap();
      setSelectedIds(new Set());
    } catch (error) {
      console.error('Failed to bulk restore items:', error);
    }
  };

  // Filter handlers
  const handleFilterChange = (key: keyof ColumnFilters, value: FilterValue | null) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleResetFilters = () => {
    setFilters(initialFilters);
    setSort({ field: null, direction: null });
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
      statusValue?.selected?.length !== 1 ||
      statusValue?.selected?.[0] !== 'active';
    const hasOtherFilters = Object.values(otherFilters).some((f) => f !== null);
    const hasSorting = sort.field !== null;
    return isStatusNonDefault || hasOtherFilters || hasSorting;
  };

  // Handle status filter toggle
  const handleStatusToggle = (value: string | null) => {
    const currentValue = filters.status as MultiSelectFilterValue | null;
    const currentSelected = currentValue?.selected ?? [];

    let newSelected: (string | null)[];
    if (currentSelected.includes(value)) {
      newSelected = currentSelected.filter((v) => v !== value);
    } else {
      newSelected = [...currentSelected, value];
    }

    if (newSelected.length === 0) {
      // If nothing selected, show all (default behavior)
      setFilters((prev) => ({ ...prev, status: null }));
    } else {
      setFilters((prev) => ({ ...prev, status: { type: 'multiselect', selected: newSelected } }));
    }
  };

  // Get status display text
  const getStatusDisplayText = () => {
    const statusValue = filters.status as MultiSelectFilterValue | null;
    if (!statusValue || statusValue.selected.length === 0) {
      return 'Все статусы';
    }
    if (statusValue.selected.length === 1) {
      const selected = statusValue.selected[0];
      const option = STATUS_OPTIONS.find((o) => o.value === selected);
      return option?.label || selected;
    }
    return `${statusValue.selected.length} статуса`;
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

        {/* Status filter dropdown */}
        <div className="relative" ref={statusDropdownRef}>
          <button
            onClick={() => setIsStatusOpen(!isStatusOpen)}
            className={`flex items-center gap-2 px-3 py-2 text-sm border rounded-lg transition-colors ${
              filters.status ? 'border-primary-300 bg-primary-50 text-primary-700' : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            <span>{getStatusDisplayText()}</span>
            <svg
              className={`w-4 h-4 transition-transform ${isStatusOpen ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {isStatusOpen && (
            <div className="absolute top-full right-0 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
              <div className="p-2">
                {STATUS_OPTIONS.map((option) => {
                  const statusValue = filters.status as MultiSelectFilterValue | null;
                  const isChecked = !statusValue || statusValue.selected.includes(option.value);
                  return (
                    <label
                      key={option.value ?? '__null__'}
                      className="flex items-center gap-2 px-2 py-1.5 hover:bg-gray-50 rounded cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => handleStatusToggle(option.value)}
                        className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                      />
                      <span className="text-sm text-gray-700">{option.label}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}
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

        <div className="text-sm text-gray-500">
          {total > 0 && (
            <span>
              Найдено: <strong>{total}</strong> товаров
            </span>
          )}
        </div>
      </div>

      {/* Bulk Actions Panel */}
      <BulkActionsPanel
        selectedCount={selectedIds.size}
        onBulkDelete={handleBulkDelete}
        onBulkHide={handleBulkHide}
        onBulkRestore={handleBulkRestore}
        onClearSelection={() => setSelectedIds(new Set())}
        isDeleting={isBulkDeleting}
        isHiding={isBulkHiding}
        isRestoring={isBulkRestoring}
      />

      {/* Table */}
      <AssortmentTable
        items={items}
        isLoading={isLoading}
        onViewDetails={handleViewDetails}
        onHideItem={handleHideItem}
        onDeleteItem={handleDeleteItem}
        onRestoreItem={handleRestoreItem}
        selectedIds={selectedIds}
        onSelectionChange={setSelectedIds}
        filters={filters}
        onFilterChange={handleFilterChange}
        sort={sort}
        onSortChange={handleSortChange}
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

      {/* Item Details Modal */}
      <ItemDetailsModal
        item={selectedItem}
        isOpen={!!selectedItem}
        onClose={handleCloseModal}
      />
    </div>
  );
}
