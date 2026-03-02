import { useState } from 'react';
import type { FlatOfferVariant, SortState } from '../../../types/supplierItem';
import {
  useUpdateSupplierItemMutation,
  useUpdateOfferCandidateMutation,
  useDeleteOfferCandidateMutation,
  useHideSupplierItemMutation,
  useRestoreSupplierItemMutation,
} from '../supplierApi';
import { useToast } from '../../../components/ui/Toast';
import EditableCell from './EditableCell';
import { getFlowerImage, getDefaultFlowerImage } from '../../../utils/flowerImages';
import type { FilterValue } from './ColumnFilter';
import type { ColumnFilters } from './FilterBar';
import AISuggestionRow from './AISuggestionRow';
import ProductDetailModal from './ProductDetailModal';

function resolvePhotoUrl(url: string): string {
  const basePath = (import.meta.env.BASE_URL || '/').replace(/\/$/, '');
  if (basePath && url.startsWith('/uploads')) {
    return basePath + url;
  }
  return url;
}

// ── Color display map ────────────────────────────────────────────────────────
const COLOR_MAP: Record<string, { bg: string; extra?: string }> = {
  'красный': { bg: 'bg-red-500' },
  'белый': { bg: 'bg-white', extra: 'border border-gray-300' },
  'розовый': { bg: 'bg-pink-400' },
  'жёлтый': { bg: 'bg-yellow-400' },
  'желтый': { bg: 'bg-yellow-400' },
  'оранжевый': { bg: 'bg-orange-500' },
  'фиолетовый': { bg: 'bg-purple-500' },
  'синий': { bg: 'bg-blue-500' },
  'зелёный': { bg: 'bg-green-500' },
  'зеленый': { bg: 'bg-green-500' },
  'микс': { bg: 'bg-gradient-to-br from-red-400 via-yellow-300 to-pink-400' },
};

// ── Toggle Switch ────────────────────────────────────────────────────────────
function ToggleSwitch({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (val: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => !disabled && onChange(!checked)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
        checked ? 'bg-primary-500' : 'bg-gray-300'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow-sm transition-transform ${
          checked ? 'translate-x-[18px]' : 'translate-x-[3px]'
        }`}
      />
    </button>
  );
}

// ── Status Badge ─────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; cls: string }> = {
    active: { label: 'Активен', cls: 'bg-green-100 text-green-700' },
    ambiguous: { label: 'Модерация', cls: 'bg-yellow-100 text-yellow-700' },
    rejected: { label: 'Отклонён', cls: 'bg-red-100 text-red-700' },
    hidden: { label: 'Скрыто', cls: 'bg-gray-100 text-gray-500' },
    deleted: { label: 'Удалён', cls: 'bg-red-50 text-red-400' },
  };
  const c = config[status] || { label: status, cls: 'bg-gray-100 text-gray-600' };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${c.cls}`}>
      {c.label}
    </span>
  );
}

// ── Types ────────────────────────────────────────────────────────────────────
interface AssortmentTableProps {
  items: FlatOfferVariant[];
  isLoading?: boolean;
  selectedIds?: Set<string>;
  onSelectionChange?: (ids: Set<string>) => void;
  filters?: ColumnFilters;
  onFilterChange?: (key: keyof ColumnFilters, value: FilterValue | null) => void;
  sort?: SortState;
  onSortChange?: (field: string) => void;
  expandedAIItemId?: string | null;
  onToggleAIExpand?: (itemId: string) => void;
  onUploadClick?: () => void;
}

type ItemUpdateValue = string | number | string[] | null;

// ── Sortable header helper ───────────────────────────────────────────────────
function SortHeader({
  label,
  field,
  sort,
  onSort,
  className = '',
}: {
  label: string;
  field: string;
  sort?: SortState;
  onSort?: (field: string) => void;
  className?: string;
}) {
  const active = sort?.field === field;
  const dir = active ? sort?.direction : null;
  return (
    <th
      className={`px-3 py-3 font-medium text-left cursor-pointer select-none hover:text-gray-900 transition-colors ${className}`}
      onClick={() => onSort?.(field)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        <svg className={`w-3.5 h-3.5 ${active ? 'text-primary-600' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          {dir === 'asc' ? (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
          ) : dir === 'desc' ? (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l4-4 4 4M8 15l4 4 4-4" />
          )}
        </svg>
      </span>
    </th>
  );
}

// ── Single Row ───────────────────────────────────────────────────────────────
function FlatVariantRow({
  variant,
  index,
  onViewDetails,
  onUpdateItem,
  onUpdateVariant,
  onDeleteVariant,
  onHideItem,
  onRestoreItem,
  isSelected,
  onToggleSelect,
  onAIClick,
}: {
  variant: FlatOfferVariant;
  index: number;
  onViewDetails?: (variant: FlatOfferVariant) => void;
  onUpdateItem: (itemId: string, field: string, value: ItemUpdateValue) => Promise<void>;
  onUpdateVariant: (variantId: string, field: string, value: string | number | null) => Promise<void>;
  onDeleteVariant: (variantId: string) => void;
  onHideItem: (itemId: string) => void;
  onRestoreItem: (itemId: string) => void;
  isSelected?: boolean;
  onToggleSelect?: () => void;
  onAIClick?: () => void;
}) {
  const isEven = index % 2 === 0;
  const rowBg = variant.item_status === 'hidden'
    ? 'bg-gray-50 opacity-60'
    : variant.has_pending_suggestions
      ? 'bg-yellow-50'
      : isEven
        ? 'bg-white'
        : 'bg-gray-50/50';

  // Build display name: "Тип субтип · Сорт"
  const typeName = variant.flower_type
    ? `${variant.flower_type}${variant.subtype ? ` ${variant.subtype.toLowerCase()}` : ''}`
    : variant.raw_name || '—';

  // Color display
  const primaryColor = variant.colors?.[0]?.toLowerCase();
  const colorInfo = primaryColor ? COLOR_MAP[primaryColor] : null;

  return (
    <tr className={`border-b border-gray-100 hover:bg-primary-50/30 transition-colors ${rowBg}`}>
      {/* Checkbox */}
      {onToggleSelect && (
        <td className="w-10 px-3 py-3 text-center">
          <input
            type="checkbox"
            checked={isSelected || false}
            onChange={onToggleSelect}
            className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500 cursor-pointer"
          />
        </td>
      )}

      {/* Название (merged: image + type + subtype) */}
      <td className="px-3 py-3">
        <div className="flex items-center gap-3">
          <img
            src={variant.photo_url ? resolvePhotoUrl(variant.photo_url) : getFlowerImage(variant.flower_type)}
            alt=""
            className="w-10 h-10 rounded-lg object-cover flex-shrink-0 bg-gray-100"
            loading="lazy"
            onError={(e) => {
              (e.target as HTMLImageElement).src = getDefaultFlowerImage();
            }}
          />
          <div className="min-w-0">
            <div className="font-medium text-gray-900 truncate" title={variant.raw_name}>
              {typeName}
            </div>
            {/* AI badge */}
            {variant.has_pending_suggestions && (
              <button
                onClick={onAIClick}
                className="inline-flex items-center gap-1 mt-0.5 text-xs text-yellow-700 bg-yellow-100 px-1.5 py-0.5 rounded font-medium"
                title="Есть предложения ИИ"
              >
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                ИИ
              </button>
            )}
          </div>
        </div>
      </td>

      {/* Сорт — editable */}
      <td className="px-3 py-3">
        <EditableCell
          value={variant.variety || ''}
          type="text"
          placeholder="—"
          onSave={async (val) => onUpdateItem(variant.item_id, 'variety', val)}
          className="text-gray-700 truncate"
        />
      </td>

      {/* Цвет — circle + text */}
      <td className="px-3 py-3">
        {primaryColor ? (
          <div className="flex items-center gap-2">
            <span
              className={`w-5 h-5 rounded-full flex-shrink-0 ${colorInfo?.bg || 'bg-gray-300'} ${colorInfo?.extra || ''}`}
            />
            <span className="text-sm text-gray-700 capitalize truncate">{primaryColor}</span>
          </div>
        ) : (
          <span className="text-gray-400 text-sm">—</span>
        )}
      </td>

      {/* Длина — editable */}
      <td className="px-3 py-3">
        <EditableCell
          value={variant.length_cm}
          type="number"
          placeholder="—"
          suffix=" см"
          onSave={async (val) => onUpdateVariant(variant.variant_id, 'length_cm', val)}
        />
      </td>

      {/* Цена — editable */}
      <td className="px-3 py-3">
        <EditableCell
          value={variant.price ? parseFloat(variant.price) : null}
          type="number"
          placeholder="—"
          suffix=" ₽"
          onSave={async (val) => onUpdateVariant(variant.variant_id, 'price_min', val)}
          className="font-semibold text-gray-900"
        />
      </td>

      {/* Упак. — just pack_qty number, editable */}
      <td className="px-3 py-3 text-center">
        <EditableCell
          value={variant.pack_qty}
          type="number"
          placeholder="—"
          onSave={async (val) => onUpdateVariant(variant.variant_id, 'pack_qty', val)}
          className="text-gray-700"
        />
      </td>

      {/* Наличие — toggle switch */}
      <td className="px-3 py-3 text-center">
        <ToggleSwitch
          checked={(variant.stock ?? 0) > 0}
          onChange={async (val) => {
            await onUpdateVariant(variant.variant_id, 'stock_qty', val ? 999 : 0);
          }}
        />
      </td>

      {/* Статус — badge */}
      <td className="px-3 py-3">
        <StatusBadge status={variant.item_status} />
      </td>

      {/* Действия — edit + delete */}
      <td className="px-3 py-3">
        <div className="flex items-center gap-1">
          {/* View/Edit */}
          <button
            onClick={() => onViewDetails?.(variant)}
            className="p-1.5 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
            title="Редактировать"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>

          {/* Hide / Restore */}
          {variant.item_status === 'active' ? (
            <button
              onClick={() => onHideItem(variant.item_id)}
              className="p-1.5 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded-lg transition-colors"
              title="Скрыть"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
              </svg>
            </button>
          ) : variant.item_status === 'hidden' ? (
            <button
              onClick={() => onRestoreItem(variant.item_id)}
              className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors"
              title="Восстановить"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </button>
          ) : null}

          {/* Delete */}
          <button
            onClick={() => {
              if (confirm('Удалить этот вариант?')) {
                onDeleteVariant(variant.variant_id);
              }
            }}
            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            title="Удалить"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </td>
    </tr>
  );
}

// ── Main Table ───────────────────────────────────────────────────────────────
export default function AssortmentTable({
  items,
  isLoading,
  selectedIds,
  onSelectionChange,
  sort,
  onSortChange,
  expandedAIItemId,
  onToggleAIExpand,
  onUploadClick,
}: AssortmentTableProps) {
  const [updateSupplierItem] = useUpdateSupplierItemMutation();
  const [updateOfferCandidate] = useUpdateOfferCandidateMutation();
  const [deleteOfferCandidate] = useDeleteOfferCandidateMutation();
  const [hideSupplierItem] = useHideSupplierItemMutation();
  const [restoreSupplierItem] = useRestoreSupplierItemMutation();
  const { showToast } = useToast();

  const [viewingVariant, setViewingVariant] = useState<FlatOfferVariant | null>(null);

  const hasSelection = !!selectedIds && !!onSelectionChange;

  const allSelected = hasSelection && items.length > 0 && items.every((v) => selectedIds.has(v.variant_id));
  const someSelected = hasSelection && items.some((v) => selectedIds.has(v.variant_id)) && !allSelected;

  const handleSelectAll = () => {
    if (!onSelectionChange) return;
    if (allSelected) {
      onSelectionChange(new Set());
    } else {
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

  const handleUpdateItem = async (itemId: string, field: string, value: ItemUpdateValue) => {
    const data: Record<string, unknown> = {};
    data[field] = value;
    await updateSupplierItem({ id: itemId, data }).unwrap();
  };

  const handleUpdateVariant = async (variantId: string, field: string, value: string | number | null) => {
    const data: Record<string, unknown> = {};
    data[field] = value;
    await updateOfferCandidate({ id: variantId, data }).unwrap();
  };

  const handleDeleteVariant = async (variantId: string) => {
    try {
      await deleteOfferCandidate(variantId).unwrap();
      showToast('Вариант удалён', 'success');
    } catch {
      showToast('Ошибка при удалении', 'error');
    }
  };

  const handleHideItem = async (itemId: string) => {
    try {
      await hideSupplierItem(itemId).unwrap();
      showToast('Позиция скрыта', 'success');
    } catch {
      showToast('Ошибка при скрытии', 'error');
    }
  };

  const handleRestoreItem = async (itemId: string) => {
    try {
      await restoreSupplierItem(itemId).unwrap();
      showToast('Позиция восстановлена', 'success');
    } catch {
      showToast('Ошибка при восстановлении', 'error');
    }
  };

  // Total column span for AI expansion row
  const colSpan = (hasSelection ? 1 : 0) + 9;

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600 mx-auto" />
        <p className="mt-4 text-sm text-gray-500">Загрузка ассортимента...</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center">
        <div className="text-5xl mb-3">📦</div>
        <p className="text-lg text-gray-700 font-medium mb-1">Ассортимент пуст</p>
        <p className="text-sm text-gray-500 mb-4">Загрузите прайс-лист, чтобы добавить товары</p>
        {onUploadClick && (
          <button
            onClick={onUploadClick}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary-600 text-white rounded-xl hover:bg-primary-700 transition-colors text-sm font-medium"
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
      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs text-gray-500 uppercase tracking-wider bg-gray-50 border-b border-gray-200">
                {/* Checkbox */}
                {hasSelection && (
                  <th className="w-10 px-3 py-3 text-center">
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

                <SortHeader label="Название" field="raw_name" sort={sort} onSort={onSortChange} className="min-w-[200px]" />
                <th className="px-3 py-3 font-medium">Сорт</th>
                <th className="px-3 py-3 font-medium">Цвет</th>
                <SortHeader label="Длина" field="length_cm" sort={sort} onSort={onSortChange} />
                <SortHeader label="Цена ₽" field="price" sort={sort} onSort={onSortChange} />
                <th className="px-3 py-3 font-medium text-center">Упак.</th>
                <th className="px-3 py-3 font-medium text-center">Наличие</th>
                <th className="px-3 py-3 font-medium">Статус</th>
                <th className="px-3 py-3 font-medium">Действия</th>
              </tr>
            </thead>
            <tbody>
              {items.map((variant, idx) => (
                <>{/* Fragment for variant row + optional AI row */}
                  <FlatVariantRow
                    key={variant.variant_id}
                    variant={variant}
                    index={idx}
                    onViewDetails={setViewingVariant}
                    onUpdateItem={handleUpdateItem}
                    onUpdateVariant={handleUpdateVariant}
                    onDeleteVariant={handleDeleteVariant}
                    onHideItem={handleHideItem}
                    onRestoreItem={handleRestoreItem}
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
              ))}
            </tbody>
          </table>
        </div>

        {/* Table footer */}
        <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-500">
          Показано {items.length} позиций
        </div>
      </div>

      {/* Product details modal */}
      {viewingVariant && (
        <ProductDetailModal
          isOpen={!!viewingVariant}
          onClose={() => setViewingVariant(null)}
          variant={viewingVariant}
        />
      )}
    </>
  );
}
