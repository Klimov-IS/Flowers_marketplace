import { useState, useEffect } from 'react';
import { useGetSupplierItemsQuery } from '../supplierApi';
import { useDebounce } from '../../../hooks/useDebounce';
import AssortmentTable from './AssortmentTable';
import SearchBar from './SearchBar';
import ItemDetailsModal from './ItemDetailsModal';
import Button from '../../../components/ui/Button';
import type { SupplierItem } from '../../../types/supplierItem';

interface AssortmentTabProps {
  supplierId: string;
}

export default function AssortmentTab({ supplierId }: AssortmentTabProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [selectedItem, setSelectedItem] = useState<SupplierItem | null>(null);
  const perPage = 50;

  // Debounce search query
  const debouncedSearch = useDebounce(searchQuery, 300);

  // Reset page when search changes
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

  // Fetch items
  const { data, isLoading, isFetching } = useGetSupplierItemsQuery({
    supplier_id: supplierId,
    q: debouncedSearch || undefined,
    page,
    per_page: perPage,
  });

  const items = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / perPage);

  const handleViewDetails = (item: SupplierItem) => {
    setSelectedItem(item);
  };

  const handleCloseModal = () => {
    setSelectedItem(null);
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

      {/* Table */}
      <AssortmentTable
        items={items}
        isLoading={isLoading}
        onViewDetails={handleViewDetails}
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
