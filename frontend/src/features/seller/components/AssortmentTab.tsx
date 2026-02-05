import { useState, useEffect } from 'react';
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
import FilterBar, { ColumnFilters, initialFilters, filtersToParams } from './FilterBar';
import type { FilterValue } from './ColumnFilter';
import Button from '../../../components/ui/Button';
import type { SupplierItem } from '../../../types/supplierItem';

interface AssortmentTabProps {
  supplierId: string;
}

export default function AssortmentTab({ supplierId }: AssortmentTabProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [selectedItem, setSelectedItem] = useState<SupplierItem | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [filters, setFilters] = useState<ColumnFilters>(initialFilters);
  const perPage = 50;

  // Debounce search query
  const debouncedSearch = useDebounce(searchQuery, 300);

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
        <div className="text-sm text-gray-500">
          {total > 0 && (
            <span>
              Найдено: <strong>{total}</strong> товаров
            </span>
          )}
        </div>
      </div>

      {/* Column Filters */}
      <FilterBar
        filters={filters}
        onFilterChange={handleFilterChange}
        onResetFilters={handleResetFilters}
      />

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
