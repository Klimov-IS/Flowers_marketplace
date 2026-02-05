import { useState } from 'react';
import type { SupplierItem, OfferVariant, SortState } from '../../../types/supplierItem';
import {
  useUpdateSupplierItemMutation,
  useUpdateOfferCandidateMutation,
} from '../supplierApi';
import StockIndicator from './StockIndicator';
import EditableCell from './EditableCell';
import EditableSelect from './EditableSelect';
import EditableColorSelect from './EditableColorSelect';
import AIIndicator from './AIIndicator';
import Badge from '../../../components/ui/Badge';
import FilterableHeader from './FilterableHeader';
import type { FilterValue } from './ColumnFilter';
import type { ColumnFilters } from './FilterBar';

interface AssortmentTableProps {
  items: SupplierItem[];
  isLoading?: boolean;
  onViewDetails?: (item: SupplierItem) => void;
  onHideItem?: (itemId: string) => void;
  onDeleteItem?: (itemId: string) => void;
  onRestoreItem?: (itemId: string) => void;
  // Selection props
  selectedIds?: Set<string>;
  onSelectionChange?: (ids: Set<string>) => void;
  // Filter props
  filters?: ColumnFilters;
  onFilterChange?: (key: keyof ColumnFilters, value: FilterValue | null) => void;
  // Sort props
  sort?: SortState;
  onSortChange?: (field: string) => void;
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

// Expanded row component showing editable variants
function ExpandedRow({
  variants,
  onUpdateVariant,
  hasCheckbox,
}: {
  variants: OfferVariant[];
  onUpdateVariant: (
    variantId: string,
    field: string,
    value: string | number | null
  ) => Promise<void>;
  hasCheckbox?: boolean;
}) {
  return (
    <tr className="bg-gray-50">
      <td colSpan={hasCheckbox ? 10 : 9} className="px-4 py-3">
        <div className="ml-8">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500">
                <th className="pb-2 font-medium">Размер (см)</th>
                <th className="pb-2 font-medium">Упаковка</th>
                <th className="pb-2 font-medium">Кол-во</th>
                <th className="pb-2 font-medium">Цена (₽)</th>
                <th className="pb-2 font-medium">Остаток</th>
                <th className="pb-2 font-medium">Статус</th>
              </tr>
            </thead>
            <tbody>
              {variants.map((variant) => (
                <tr key={variant.id} className="border-t border-gray-200">
                  <td className="py-2">
                    <EditableCell
                      value={variant.length_cm}
                      type="number"
                      placeholder="—"
                      onSave={async (val) =>
                        onUpdateVariant(variant.id, 'length_cm', val)
                      }
                    />
                  </td>
                  <td className="py-2">
                    <EditableSelect
                      value={variant.pack_type}
                      options={PACK_TYPE_OPTIONS}
                      onSave={async (val) =>
                        onUpdateVariant(variant.id, 'pack_type', val)
                      }
                    />
                  </td>
                  <td className="py-2">
                    <EditableCell
                      value={variant.pack_qty}
                      type="number"
                      placeholder="—"
                      onSave={async (val) =>
                        onUpdateVariant(variant.id, 'pack_qty', val)
                      }
                    />
                  </td>
                  <td className="py-2">
                    <EditableCell
                      value={variant.price ? parseFloat(variant.price) : null}
                      type="number"
                      placeholder="—"
                      onSave={async (val) =>
                        onUpdateVariant(variant.id, 'price_min', val)
                      }
                    />
                  </td>
                  <td className="py-2">
                    <EditableCell
                      value={variant.stock}
                      type="number"
                      placeholder="0"
                      onSave={async (val) =>
                        onUpdateVariant(variant.id, 'stock_qty', val)
                      }
                    />
                  </td>
                  <td className="py-2">
                    <Badge
                      variant={
                        variant.validation === 'ok'
                          ? 'success'
                          : variant.validation === 'warn'
                          ? 'warning'
                          : 'danger'
                      }
                    >
                      {variant.validation === 'ok' ? 'OK' : variant.validation}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </td>
    </tr>
  );
}

// Value type for item updates (supports strings, numbers, and arrays)
type ItemUpdateValue = string | number | string[] | null;

// Single item row
function ItemRow({
  item,
  isExpanded,
  onToggle,
  onViewDetails,
  onUpdateItem,
  onUpdateVariant,
  onHideItem,
  onDeleteItem,
  onRestoreItem,
  isSelected,
  onToggleSelect,
}: {
  item: SupplierItem;
  isExpanded: boolean;
  onToggle: () => void;
  onViewDetails?: (item: SupplierItem) => void;
  onUpdateItem: (itemId: string, field: string, value: ItemUpdateValue) => Promise<void>;
  onUpdateVariant: (variantId: string, field: string, value: string | number | null) => Promise<void>;
  onHideItem?: (itemId: string) => void;
  onDeleteItem?: (itemId: string) => void;
  onRestoreItem?: (itemId: string) => void;
  isSelected?: boolean;
  onToggleSelect?: () => void;
}) {
  const hasMultipleVariants = item.variants_count > 1;
  const singleVariant = item.variants.length === 1 ? item.variants[0] : null;

  // Format price range for display (when multiple variants)
  const priceRangeDisplay = () => {
    if (!item.price_min) return '—';
    const min = parseFloat(item.price_min).toLocaleString();
    if (item.price_max && item.price_min !== item.price_max) {
      const max = parseFloat(item.price_max).toLocaleString();
      return `${min} – ${max} ₽`;
    }
    return `${min} ₽`;
  };

  // Format length range for display (when multiple variants)
  const lengthRangeDisplay = () => {
    if (!item.length_min) return '—';
    if (item.length_max && item.length_min !== item.length_max) {
      return `${item.length_min}–${item.length_max}`;
    }
    return `${item.length_min}`;
  };

  // Get pack types summary (when multiple variants)
  const packTypesDisplay = () => {
    if (item.variants.length === 0) return '—';
    const types = [...new Set(item.variants.map((v) => v.pack_type).filter(Boolean))];
    if (types.length === 0) return '—';
    if (types.length === 1) return types[0];
    return `${types.length} типа`;
  };

  return (
    <>
      <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
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

        {/* Expand button */}
        <td className="w-10 px-2 py-3 text-center">
          {hasMultipleVariants ? (
            <button
              onClick={onToggle}
              className="p-1 hover:bg-gray-200 rounded transition-colors"
              title={isExpanded ? 'Свернуть' : 'Развернуть'}
            >
              <svg
                className={`w-4 h-4 text-gray-500 transition-transform ${
                  isExpanded ? 'rotate-90' : ''
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          ) : (
            <span className="inline-block w-4" />
          )}
        </td>

        {/* Name - show clean_name as primary, raw_name as secondary */}
        <td className="px-3 py-3">
          <div className="flex items-center gap-1">
            <EditableCell
              value={item.attributes?.clean_name || item.raw_name}
              type="text"
              onSave={async (val) => onUpdateItem(item.id, 'raw_name', val)}
              className="font-medium text-gray-900"
            />
            {item.attributes?._sources?.clean_name === 'ai' && (
              <AIIndicator
                source="ai"
                confidence={item.attributes?._confidences?.clean_name}
              />
            )}
          </div>
          {/* Show raw_name as secondary info when different from clean_name */}
          {item.attributes?.clean_name && item.attributes.clean_name !== item.raw_name && (
            <div
              className="text-xs text-gray-400 mt-0.5 px-2 truncate max-w-xs"
              title={item.raw_name}
            >
              Исходное: {item.raw_name}
            </div>
          )}
          {item.source_file && !item.attributes?.clean_name && (
            <div className="text-xs text-gray-400 mt-0.5 px-2">{item.source_file}</div>
          )}
          {item.attributes?.flower_type && (
            <div className="text-xs text-purple-600 mt-0.5 px-2">
              {item.attributes.flower_type}
              {item.attributes.subtype && ` ${item.attributes.subtype.toLowerCase()}`}
              {item.attributes.variety && ` ${item.attributes.variety}`}
            </div>
          )}
        </td>

        {/* Origin - dropdown select */}
        <td className="px-3 py-3">
          <div className="flex items-center gap-1">
            <EditableSelect
              value={item.origin_country}
              options={COUNTRY_OPTIONS}
              onSave={async (val) => onUpdateItem(item.id, 'origin_country', val)}
            />
            <AIIndicator
              source={item.attributes?._sources?.origin_country}
              confidence={item.attributes?._confidences?.origin_country}
            />
          </div>
        </td>

        {/* Colors - multi-select */}
        <td className="px-3 py-3">
          <div className="flex items-center gap-1">
            <EditableColorSelect
              value={item.colors || []}
              onSave={async (colors) => onUpdateItem(item.id, 'colors', colors)}
            />
            <AIIndicator
              source={item.attributes?._sources?.colors}
              confidence={item.attributes?._confidences?.colors}
            />
          </div>
        </td>

        {/* Length - editable if single variant */}
        <td className="px-3 py-3">
          {singleVariant ? (
            <EditableCell
              value={singleVariant.length_cm}
              type="number"
              placeholder="—"
              suffix=" см"
              onSave={async (val) => onUpdateVariant(singleVariant.id, 'length_cm', val)}
            />
          ) : (
            <span className="text-gray-600">{lengthRangeDisplay()} см</span>
          )}
        </td>

        {/* Pack type - editable if single variant */}
        <td className="px-3 py-3">
          {singleVariant ? (
            <EditableSelect
              value={singleVariant.pack_type}
              options={PACK_TYPE_OPTIONS}
              onSave={async (val) => onUpdateVariant(singleVariant.id, 'pack_type', val)}
            />
          ) : (
            <span className="text-gray-600">{packTypesDisplay()}</span>
          )}
        </td>

        {/* Price - editable if single variant */}
        <td className="px-3 py-3">
          {singleVariant ? (
            <EditableCell
              value={singleVariant.price ? parseFloat(singleVariant.price) : null}
              type="number"
              placeholder="—"
              suffix=" ₽"
              onSave={async (val) => onUpdateVariant(singleVariant.id, 'price_min', val)}
              className="font-medium"
            />
          ) : (
            <span className="font-medium">{priceRangeDisplay()}</span>
          )}
        </td>

        {/* Stock - editable if single variant */}
        <td className="px-3 py-3">
          {singleVariant ? (
            <EditableCell
              value={singleVariant.stock ?? 0}
              type="number"
              placeholder="0"
              onSave={async (val) => onUpdateVariant(singleVariant.id, 'stock_qty', val)}
            />
          ) : (
            <StockIndicator stock={item.stock_total} />
          )}
        </td>

        {/* Actions */}
        <td className="px-3 py-3">
          <div className="flex gap-1">
            {/* View Details */}
            <button
              onClick={() => onViewDetails?.(item)}
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

            {/* Show Restore for hidden/deleted items, otherwise show Hide/Delete */}
            {(item.status === 'hidden' || item.status === 'deleted') ? (
              <button
                onClick={() => onRestoreItem?.(item.id)}
                className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                title="Восстановить"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
              </button>
            ) : (
              <>
                {/* Hide */}
                <button
                  onClick={() => onHideItem?.(item.id)}
                  className="p-1.5 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors"
                  title="Скрыть"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                    />
                  </svg>
                </button>

                {/* Delete */}
                <button
                  onClick={() => {
                    if (confirm('Удалить этот товар? Его можно будет восстановить.')) {
                      onDeleteItem?.(item.id);
                    }
                  }}
                  className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                  title="Удалить"
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
              </>
            )}
          </div>
        </td>
      </tr>

      {/* Expanded variants */}
      {isExpanded && hasMultipleVariants && (
        <ExpandedRow
          variants={item.variants}
          onUpdateVariant={onUpdateVariant}
          hasCheckbox={!!onToggleSelect}
        />
      )}
    </>
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
  onViewDetails,
  onHideItem,
  onDeleteItem,
  onRestoreItem,
  selectedIds,
  onSelectionChange,
  filters,
  onFilterChange,
  sort,
  onSortChange,
}: AssortmentTableProps) {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [updateSupplierItem] = useUpdateSupplierItemMutation();
  const [updateOfferCandidate] = useUpdateOfferCandidateMutation();

  const hasSelection = !!selectedIds && !!onSelectionChange;

  // Check if all items on current page are selected
  const allSelected = hasSelection && items.length > 0 && items.every((item) => selectedIds.has(item.id));
  const someSelected = hasSelection && items.some((item) => selectedIds.has(item.id)) && !allSelected;

  const handleSelectAll = () => {
    if (!onSelectionChange) return;
    if (allSelected) {
      // Deselect all
      onSelectionChange(new Set());
    } else {
      // Select all on current page
      onSelectionChange(new Set(items.map((item) => item.id)));
    }
  };

  const handleToggleSelect = (itemId: string) => {
    if (!selectedIds || !onSelectionChange) return;
    const next = new Set(selectedIds);
    if (next.has(itemId)) {
      next.delete(itemId);
    } else {
      next.add(itemId);
    }
    onSelectionChange(next);
  };

  const toggleExpanded = (itemId: string) => {
    setExpandedItems((prev) => {
      const next = new Set(prev);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
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
        <p className="text-gray-500">Загрузите прайс-лист, чтобы добавить товары</p>
      </div>
    );
  }

  return (
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
            <th className="w-10 px-2 py-3" /> {/* Expand */}

            {/* Название - sortable only */}
            <FilterableHeader
              label="Название"
              sortField="raw_name"
              currentSort={sort}
              onSort={onSortChange}
              width="18%"
            />

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
              width="12%"
            />

            {/* Размеры - filter + sort */}
            <FilterableHeader
              label="Размеры"
              sortField="length_min"
              currentSort={sort}
              onSort={onSortChange}
              filterType="range"
              filterValue={filters?.length}
              onFilterChange={onFilterChange ? (v) => onFilterChange('length', v) : undefined}
              filterSuffix="см"
              width="12%"
            />

            {/* Упаковка - no filter/sort */}
            <th className="px-3 py-3 font-medium" style={{ width: '12%' }}>
              Упаковка
            </th>

            {/* Цена - filter + sort */}
            <FilterableHeader
              label="Цена"
              sortField="price_min"
              currentSort={sort}
              onSort={onSortChange}
              filterType="range"
              filterValue={filters?.price}
              onFilterChange={onFilterChange ? (v) => onFilterChange('price', v) : undefined}
              filterSuffix="р"
              width="12%"
            />

            {/* Остаток - filter + sort */}
            <FilterableHeader
              label="Остаток"
              sortField="stock_total"
              currentSort={sort}
              onSort={onSortChange}
              filterType="range"
              filterValue={filters?.stock}
              onFilterChange={onFilterChange ? (v) => onFilterChange('stock', v) : undefined}
              width="12%"
            />

            <th className="px-3 py-3 font-medium" style={{ width: '12%' }}>
              Действия
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <ItemRow
              key={item.id}
              item={item}
              isExpanded={expandedItems.has(item.id)}
              onToggle={() => toggleExpanded(item.id)}
              onViewDetails={onViewDetails}
              onUpdateItem={handleUpdateItem}
              onUpdateVariant={handleUpdateVariant}
              onHideItem={onHideItem}
              onDeleteItem={onDeleteItem}
              onRestoreItem={onRestoreItem}
              isSelected={selectedIds?.has(item.id)}
              onToggleSelect={hasSelection ? () => handleToggleSelect(item.id) : undefined}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
