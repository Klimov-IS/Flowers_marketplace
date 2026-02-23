import { useState } from 'react';
import type { FlatOfferVariant, SortState } from '../../../types/supplierItem';
import {
  useUpdateSupplierItemMutation,
  useUpdateOfferCandidateMutation,
  useDeleteOfferCandidateMutation,
} from '../supplierApi';
import StockIndicator from './StockIndicator';
import EditableCell from './EditableCell';
import EditableSelect from './EditableSelect';
import EditableColorSelect from './EditableColorSelect';
import { getFlowerImage, getDefaultFlowerImage } from '../../../utils/flowerImages';
import FilterableHeader from './FilterableHeader';
import type { FilterValue } from './ColumnFilter';
import type { ColumnFilters } from './FilterBar';
import AISuggestionRow from './AISuggestionRow';

// Simple modal for viewing variant details
function VariantDetailsModal({
  variant,
  onClose,
}: {
  variant: FlatOfferVariant;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <h3 className="text-lg font-medium text-gray-900">Детали варианта</h3>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 rounded"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="p-4 space-y-3">
          {/* IDs */}
          <div className="bg-gray-50 p-3 rounded-lg space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Variant ID:</span>
              <code className="text-xs bg-gray-200 px-2 py-0.5 rounded select-all">
                {variant.variant_id}
              </code>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Item ID:</span>
              <code className="text-xs bg-gray-200 px-2 py-0.5 rounded select-all">
                {variant.item_id}
              </code>
            </div>
          </div>

          {/* Variant fields */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-gray-500">Тип:</span>
              <p className="font-medium">{variant.flower_type || '—'}</p>
            </div>
            <div>
              <span className="text-gray-500">Подтип:</span>
              <p className="font-medium">{variant.subtype || '—'}</p>
            </div>
            <div>
              <span className="text-gray-500">Сорт:</span>
              <p className="font-medium">{variant.variety || '—'}</p>
            </div>
            <div>
              <span className="text-gray-500">Страна:</span>
              <p className="font-medium">{variant.origin_country || '—'}</p>
            </div>
            <div>
              <span className="text-gray-500">Цвета:</span>
              <p className="font-medium">{variant.colors?.length ? variant.colors.join(', ') : '—'}</p>
            </div>
            <div>
              <span className="text-gray-500">Размер:</span>
              <p className="font-medium">{variant.length_cm ? `${variant.length_cm} см` : '—'}</p>
            </div>
            <div>
              <span className="text-gray-500">Упаковка:</span>
              <p className="font-medium">
                {variant.pack_type || '—'} {variant.pack_qty ? `(${variant.pack_qty})` : ''}
              </p>
            </div>
            <div>
              <span className="text-gray-500">Цена:</span>
              <p className="font-medium">{variant.price} ₽</p>
            </div>
            <div>
              <span className="text-gray-500">Остаток:</span>
              <p className="font-medium">{variant.stock ?? '—'}</p>
            </div>
            <div>
              <span className="text-gray-500">Статус:</span>
              <p className="font-medium">{variant.item_status}</p>
            </div>
          </div>

          {/* Raw name */}
          <div className="text-sm">
            <span className="text-gray-500">Исходное название:</span>
            <p className="font-mono text-xs bg-gray-100 p-2 rounded mt-1 break-all">
              {variant.raw_name}
            </p>
          </div>

          {/* Source file */}
          {variant.source_file && (
            <div className="text-sm">
              <span className="text-gray-500">Файл-источник:</span>
              <p className="text-xs text-gray-600">{variant.source_file}</p>
            </div>
          )}
        </div>
        <div className="px-4 py-3 border-t bg-gray-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
}

interface AssortmentTableProps {
  items: FlatOfferVariant[];
  isLoading?: boolean;
  // Selection props
  selectedIds?: Set<string>;
  onSelectionChange?: (ids: Set<string>) => void;
  // Filter props
  filters?: ColumnFilters;
  onFilterChange?: (key: keyof ColumnFilters, value: FilterValue | null) => void;
  // Sort props
  sort?: SortState;
  onSortChange?: (field: string) => void;
  // AI suggestion expansion
  expandedAIItemId?: string | null;
  onToggleAIExpand?: (itemId: string) => void;
  // Empty state action
  onUploadClick?: () => void;
}

const PACK_TYPE_OPTIONS = [
  { value: null, label: '—' },
  { value: 'бак', label: 'Бак' },
  { value: 'упак', label: 'Упаковка' },
  { value: 'шт', label: 'Штука' },
];

const COUNTRY_OPTIONS = [
  { value: null, label: '—' },
  { value: 'Эквадор', label: 'Эквадор' },
  { value: 'Колумбия', label: 'Колумбия' },
  { value: 'Нидерланды', label: 'Нидерланды' },
  { value: 'Кения', label: 'Кения' },
  { value: 'Израиль', label: 'Израиль' },
  { value: 'Россия', label: 'Россия' },
  { value: 'Эфиопия', label: 'Эфиопия' },
  { value: 'Италия', label: 'Италия' },
];

// Value type for item updates (supports strings, numbers, and arrays)
type ItemUpdateValue = string | number | string[] | null;

// Single flat row (1 variant = 1 row)
function FlatVariantRow({
  variant,
  onViewDetails,
  onUpdateItem,
  onUpdateVariant,
  onDeleteVariant,
  isSelected,
  onToggleSelect,
  onAIClick,
}: {
  variant: FlatOfferVariant;
  onViewDetails?: (variant: FlatOfferVariant) => void;
  onUpdateItem: (itemId: string, field: string, value: ItemUpdateValue) => Promise<void>;
  onUpdateVariant: (variantId: string, field: string, value: string | number | null) => Promise<void>;
  onDeleteVariant: (variantId: string) => void;
  isSelected?: boolean;
  onToggleSelect?: () => void;
  onAIClick?: () => void;
}) {
  return (
    <tr className={`border-b border-gray-100 hover:bg-gray-50 transition-colors ${variant.has_pending_suggestions ? 'bg-yellow-50' : ''}`}>
      {/* Checkbox */}
      {onToggleSelect && (
        <td className="w-10 px-2 py-3 text-center">
          <input
            type="checkbox"
            checked={isSelected || false}
            onChange={onToggleSelect}
            className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500 cursor-pointer"
          />
        </td>
      )}

      {/* Тип цветка */}
      <td className="px-3 py-3">
        <div className="flex items-center gap-2">
          {/* Thumbnail */}
          <img
            src={getFlowerImage(variant.flower_type)}
            alt=""
            className="w-8 h-8 rounded object-cover flex-shrink-0 bg-gray-100"
            loading="lazy"
            onError={(e) => {
              (e.target as HTMLImageElement).src = getDefaultFlowerImage();
            }}
          />
          <div className="flex flex-col gap-0.5 min-w-0">
            <span
              className="font-medium text-gray-900 truncate cursor-help"
              title={variant.raw_name}
            >
              {variant.flower_type
                ? `${variant.flower_type}${variant.subtype ? ` ${variant.subtype.toLowerCase()}` : ''}`
                : '—'}
            </span>
            {/* Possible duplicate badge */}
            {variant.possible_duplicate && (
              <span
                className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-800 rounded cursor-help w-fit"
                title="Найдены другие позиции с таким же типом и сортом. Возможно, это дубликаты."
              >
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                  <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                </svg>
                Дубль?
              </span>
            )}
          </div>
        </div>
      </td>

      {/* Сорт - редактируемый */}
      <td className="px-3 py-3">
        <EditableCell
          value={variant.variety || ''}
          type="text"
          placeholder="—"
          onSave={async (val) => onUpdateItem(variant.item_id, 'variety', val)}
          className="text-gray-900 truncate"
        />
      </td>

      {/* Страна - dropdown select */}
      <td className="px-3 py-3">
        <EditableSelect
          value={variant.origin_country}
          options={COUNTRY_OPTIONS}
          onSave={async (val) => onUpdateItem(variant.item_id, 'origin_country', val)}
        />
      </td>

      {/* Цвета - editable */}
      <td className="px-3 py-3">
        <EditableColorSelect
          value={variant.colors || []}
          onSave={async (colors) => onUpdateItem(variant.item_id, 'colors', colors)}
        />
      </td>

      {/* Размер - редактируемый */}
      <td className="px-3 py-3">
        <EditableCell
          value={variant.length_cm}
          type="number"
          placeholder="—"
          suffix=" см"
          onSave={async (val) => onUpdateVariant(variant.variant_id, 'length_cm', val)}
        />
      </td>

      {/* Упаковка - редактируемый */}
      <td className="px-3 py-3">
        <div className="flex items-center gap-1">
          <EditableSelect
            value={variant.pack_type}
            options={PACK_TYPE_OPTIONS}
            onSave={async (val) => onUpdateVariant(variant.variant_id, 'pack_type', val)}
          />
          {variant.pack_qty && (
            <EditableCell
              value={variant.pack_qty}
              type="number"
              placeholder=""
              onSave={async (val) => onUpdateVariant(variant.variant_id, 'pack_qty', val)}
              className="w-12 text-gray-500"
            />
          )}
        </div>
      </td>

      {/* Цена - редактируемый */}
      <td className="px-3 py-3">
        <EditableCell
          value={variant.price ? parseFloat(variant.price) : null}
          type="number"
          placeholder="—"
          suffix=" ₽"
          onSave={async (val) => onUpdateVariant(variant.variant_id, 'price_min', val)}
          className="font-medium"
        />
      </td>

      {/* Остаток - редактируемый */}
      <td className="px-3 py-3">
        <StockIndicator stock={variant.stock ?? 0} />
      </td>

      {/* Actions */}
      <td className="px-3 py-3">
        <div className="flex gap-1">
          {/* AI suggestion warning */}
          {variant.has_pending_suggestions && onAIClick && (
            <button
              onClick={onAIClick}
              className="p-1.5 text-yellow-600 hover:text-yellow-800 hover:bg-yellow-100 rounded transition-colors"
              title="Есть предложения для проверки"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </button>
          )}

          {/* View Details */}
          <button
            onClick={() => onViewDetails?.(variant)}
            className="p-1.5 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded transition-colors"
            title="Детали"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
              />
            </svg>
          </button>

          {/* Delete variant */}
          <button
            onClick={() => {
              if (confirm('Удалить этот вариант? Это действие нельзя отменить.')) {
                onDeleteVariant(variant.variant_id);
              }
            }}
            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
            title="Удалить вариант"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>
      </td>
    </tr>
  );
}

// Filter options for headers
const COUNTRY_FILTER_OPTIONS = [
  { value: 'Эквадор', label: 'Эквадор' },
  { value: 'Колумбия', label: 'Колумбия' },
  { value: 'Нидерланды', label: 'Нидерланды' },
  { value: 'Кения', label: 'Кения' },
  { value: 'Израиль', label: 'Израиль' },
  { value: 'Россия', label: 'Россия' },
  { value: 'Эфиопия', label: 'Эфиопия' },
  { value: 'Италия', label: 'Италия' },
  { value: null, label: 'Не указана' },
];

const COLOR_FILTER_OPTIONS = [
  { value: 'красный', label: 'Красный' },
  { value: 'белый', label: 'Белый' },
  { value: 'розовый', label: 'Розовый' },
  { value: 'желтый', label: 'Желтый' },
  { value: 'оранжевый', label: 'Оранжевый' },
  { value: 'микс', label: 'Микс' },
  { value: null, label: 'Не указан' },
];

export default function AssortmentTable({
  items,
  isLoading,
  selectedIds,
  onSelectionChange,
  filters,
  onFilterChange,
  sort,
  onSortChange,
  expandedAIItemId,
  onToggleAIExpand,
  onUploadClick,
}: AssortmentTableProps) {
  const [updateSupplierItem] = useUpdateSupplierItemMutation();
  const [updateOfferCandidate] = useUpdateOfferCandidateMutation();
  const [deleteOfferCandidate] = useDeleteOfferCandidateMutation();

  // Internal state for details modal
  const [viewingVariant, setViewingVariant] = useState<FlatOfferVariant | null>(null);

  const hasSelection = !!selectedIds && !!onSelectionChange;

  // Check if all items on current page are selected
  const allSelected = hasSelection && items.length > 0 && items.every((v) => selectedIds.has(v.variant_id));
  const someSelected = hasSelection && items.some((v) => selectedIds.has(v.variant_id)) && !allSelected;

  const handleSelectAll = () => {
    if (!onSelectionChange) return;
    if (allSelected) {
      // Deselect all
      onSelectionChange(new Set());
    } else {
      // Select all on current page
      onSelectionChange(new Set(items.map((v) => v.variant_id)));
    }
  };

  const handleToggleSelect = (variantId: string) => {
    if (!selectedIds || !onSelectionChange) return;
    const next = new Set(selectedIds);
    if (next.has(variantId)) {
      next.delete(variantId);
    } else {
      next.add(variantId);
    }
    onSelectionChange(next);
  };

  const handleUpdateItem = async (
    itemId: string,
    field: string,
    value: ItemUpdateValue
  ) => {
    const data: Record<string, unknown> = {};
    data[field] = value;
    await updateSupplierItem({ id: itemId, data }).unwrap();
  };

  const handleUpdateVariant = async (
    variantId: string,
    field: string,
    value: string | number | null
  ) => {
    const data: Record<string, unknown> = {};
    data[field] = value;
    await updateOfferCandidate({ id: variantId, data }).unwrap();
  };

  const handleDeleteVariant = async (variantId: string) => {
    try {
      await deleteOfferCandidate(variantId).unwrap();
    } catch (error) {
      console.error('Failed to delete variant:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto" />
        <p className="mt-4 text-gray-500">Загрузка ассортимента...</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
        <div className="text-gray-400 mb-3">
          <svg
            className="w-16 h-16 mx-auto"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
            />
          </svg>
        </div>
        <p className="text-lg text-gray-600 mb-2">Ассортимент пуст</p>
        <p className="text-gray-500 mb-4">Загрузите прайс-лист, чтобы добавить товары</p>
        {onUploadClick && (
          <button
            onClick={onUploadClick}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Загрузить прайс-лист
          </button>
        )}
      </div>
    );
  }

  return (
    <>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr className="text-left text-sm text-gray-600">
              {/* Checkbox header */}
              {hasSelection && (
                <th className="w-10 px-2 py-3 text-center">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    ref={(el) => {
                      if (el) el.indeterminate = someSelected;
                    }}
                    onChange={handleSelectAll}
                    className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500 cursor-pointer"
                    title={allSelected ? 'Снять выделение' : 'Выбрать все'}
                  />
                </th>
              )}

              {/* Тип цветка - sortable */}
              <FilterableHeader
                label="Тип"
                sortField="raw_name"
                currentSort={sort}
                onSort={onSortChange}
                width="14%"
              />

              {/* Сорт */}
              <th className="px-3 py-3 font-medium" style={{ width: '10%' }}>
                Сорт
              </th>

              {/* Страна - filter + sort */}
              <FilterableHeader
                label="Страна"
                sortField="origin_country"
                currentSort={sort}
                onSort={onSortChange}
                filterType="multiselect"
                filterOptions={COUNTRY_FILTER_OPTIONS}
                filterValue={filters?.origin_country}
                onFilterChange={onFilterChange ? (v) => onFilterChange('origin_country', v) : undefined}
                width="10%"
              />

              {/* Цвет - filter only (array, no sort) */}
              <FilterableHeader
                label="Цвет"
                filterType="multiselect"
                filterOptions={COLOR_FILTER_OPTIONS}
                filterValue={filters?.colors}
                onFilterChange={onFilterChange ? (v) => onFilterChange('colors', v) : undefined}
                width="10%"
              />

              {/* Размер - filter + sort */}
              <FilterableHeader
                label="Размер"
                sortField="length_cm"
                currentSort={sort}
                onSort={onSortChange}
                filterType="range"
                filterValue={filters?.length}
                onFilterChange={onFilterChange ? (v) => onFilterChange('length', v) : undefined}
                filterSuffix="см"
                width="10%"
              />

              {/* Упаковка - no filter/sort */}
              <th className="px-3 py-3 font-medium" style={{ width: '12%' }}>
                Упаковка
              </th>

              {/* Цена - filter + sort */}
              <FilterableHeader
                label="Цена"
                sortField="price"
                currentSort={sort}
                onSort={onSortChange}
                filterType="range"
                filterValue={filters?.price}
                onFilterChange={onFilterChange ? (v) => onFilterChange('price', v) : undefined}
                filterSuffix="р"
                width="10%"
              />

              {/* Остаток - filter + sort */}
              <FilterableHeader
                label="Остаток"
                sortField="stock"
                currentSort={sort}
                onSort={onSortChange}
                filterType="range"
                filterValue={filters?.stock}
                onFilterChange={onFilterChange ? (v) => onFilterChange('stock', v) : undefined}
                width="10%"
              />

              <th className="px-3 py-3 font-medium" style={{ width: '10%' }}>
                Действия
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((variant) => {
              // Total columns: checkbox(opt) + type + sort + country + color + size + pack + price + stock + actions = 9 or 10
              const colSpan = hasSelection ? 10 : 9;
              return (
                <>{/* Fragment wrapping variant row + optional AI expand row */}
                  <FlatVariantRow
                    key={variant.variant_id}
                    variant={variant}
                    onViewDetails={setViewingVariant}
                    onUpdateItem={handleUpdateItem}
                    onUpdateVariant={handleUpdateVariant}
                    onDeleteVariant={handleDeleteVariant}
                    isSelected={selectedIds?.has(variant.variant_id)}
                    onToggleSelect={hasSelection ? () => handleToggleSelect(variant.variant_id) : undefined}
                    onAIClick={
                      variant.has_pending_suggestions && onToggleAIExpand
                        ? () => onToggleAIExpand(variant.item_id)
                        : undefined
                    }
                  />
                  {expandedAIItemId === variant.item_id && (
                    <AISuggestionRow
                      key={`ai-${variant.item_id}`}
                      itemId={variant.item_id}
                      colSpan={colSpan}
                    />
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Details modal */}
      {viewingVariant && (
        <VariantDetailsModal
          variant={viewingVariant}
          onClose={() => setViewingVariant(null)}
        />
      )}
    </>
  );
}
