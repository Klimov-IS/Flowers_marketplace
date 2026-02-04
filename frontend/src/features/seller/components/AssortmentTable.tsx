import { useState } from 'react';
import type { SupplierItem, OfferVariant } from '../../../types/supplierItem';
import {
  useUpdateSupplierItemMutation,
  useUpdateOfferCandidateMutation,
} from '../supplierApi';
import ColorSquares from './ColorSquares';
import StockIndicator from './StockIndicator';
import EditableCell from './EditableCell';
import EditableSelect from './EditableSelect';
import Badge from '../../../components/ui/Badge';

interface AssortmentTableProps {
  items: SupplierItem[];
  isLoading?: boolean;
  onViewDetails?: (item: SupplierItem) => void;
}

const PACK_TYPE_OPTIONS = [
  { value: null, label: '—' },
  { value: 'бак', label: 'Бак' },
  { value: 'упак', label: 'Упаковка' },
  { value: 'шт', label: 'Штука' },
];

// Expanded row component showing editable variants
function ExpandedRow({
  variants,
  onUpdateVariant,
}: {
  variants: OfferVariant[];
  onUpdateVariant: (
    variantId: string,
    field: string,
    value: string | number | null
  ) => Promise<void>;
}) {
  return (
    <tr className="bg-gray-50">
      <td colSpan={9} className="px-4 py-3">
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

// Single item row
function ItemRow({
  item,
  isExpanded,
  onToggle,
  onViewDetails,
  onUpdateItem,
  onUpdateVariant,
}: {
  item: SupplierItem;
  isExpanded: boolean;
  onToggle: () => void;
  onViewDetails?: (item: SupplierItem) => void;
  onUpdateItem: (itemId: string, field: string, value: string | number | null) => Promise<void>;
  onUpdateVariant: (variantId: string, field: string, value: string | number | null) => Promise<void>;
}) {
  const hasVariants = item.variants_count > 1;

  // Format price range (read-only display)
  const priceDisplay = () => {
    if (!item.price_min) return '—';
    const min = parseFloat(item.price_min).toLocaleString();
    if (item.price_max && item.price_min !== item.price_max) {
      const max = parseFloat(item.price_max).toLocaleString();
      return `${min} – ${max}`;
    }
    return min;
  };

  // Format length range (read-only display)
  const lengthDisplay = () => {
    if (!item.length_min) return '—';
    if (item.length_max && item.length_min !== item.length_max) {
      return `${item.length_min}–${item.length_max} см`;
    }
    return `${item.length_min} см`;
  };

  // Get pack type from first variant or show count
  const packDisplay = () => {
    if (item.variants.length === 0) return '—';
    const types = [...new Set(item.variants.map((v) => v.pack_type).filter(Boolean))];
    if (types.length === 0) return '—';
    if (types.length === 1) return types[0];
    return `${types.length} типа`;
  };

  return (
    <>
      <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
        {/* Expand button */}
        <td className="w-10 px-2 py-3 text-center">
          {hasVariants ? (
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

        {/* Name - editable */}
        <td className="px-3 py-3">
          <EditableCell
            value={item.raw_name}
            type="text"
            onSave={async (val) => onUpdateItem(item.id, 'raw_name', val)}
            className="font-medium text-gray-900"
          />
          {item.source_file && (
            <div className="text-xs text-gray-400 mt-0.5 px-2">{item.source_file}</div>
          )}
        </td>

        {/* Origin - editable */}
        <td className="px-3 py-3">
          <EditableCell
            value={item.origin_country}
            type="text"
            placeholder="—"
            onSave={async (val) => onUpdateItem(item.id, 'origin_country', val)}
          />
        </td>

        {/* Colors - read-only (complex to edit inline) */}
        <td className="px-3 py-3">
          <ColorSquares colors={item.colors} />
        </td>

        {/* Lengths - read-only aggregated */}
        <td className="px-3 py-3 text-gray-600">{lengthDisplay()}</td>

        {/* Pack - read-only aggregated */}
        <td className="px-3 py-3 text-gray-600">{packDisplay()}</td>

        {/* Price - read-only aggregated */}
        <td className="px-3 py-3 font-medium">{priceDisplay()} ₽</td>

        {/* Stock - editable if single variant, else aggregated */}
        <td className="px-3 py-3">
          {item.variants.length === 1 ? (
            <EditableCell
              value={item.stock_total}
              type="number"
              placeholder="0"
              onSave={async (val) =>
                onUpdateVariant(item.variants[0].id, 'stock_qty', val)
              }
            />
          ) : (
            <StockIndicator stock={item.stock_total} />
          )}
        </td>

        {/* Actions */}
        <td className="px-3 py-3">
          <div className="flex gap-2">
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
          </div>
        </td>
      </tr>

      {/* Expanded variants */}
      {isExpanded && hasVariants && (
        <ExpandedRow variants={item.variants} onUpdateVariant={onUpdateVariant} />
      )}
    </>
  );
}

export default function AssortmentTable({
  items,
  isLoading,
  onViewDetails,
}: AssortmentTableProps) {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [updateSupplierItem] = useUpdateSupplierItemMutation();
  const [updateOfferCandidate] = useUpdateOfferCandidateMutation();

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
    value: string | number | null
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
            <th className="w-10 px-2 py-3" /> {/* Expand */}
            <th className="px-3 py-3 font-medium" style={{ width: '18%' }}>
              Название
            </th>
            <th className="px-3 py-3 font-medium" style={{ width: '10%' }}>
              Страна
            </th>
            <th className="px-3 py-3 font-medium" style={{ width: '12%' }}>
              Цвет
            </th>
            <th className="px-3 py-3 font-medium" style={{ width: '12%' }}>
              Размеры
            </th>
            <th className="px-3 py-3 font-medium" style={{ width: '12%' }}>
              Упаковка
            </th>
            <th className="px-3 py-3 font-medium" style={{ width: '12%' }}>
              Цена
            </th>
            <th className="px-3 py-3 font-medium" style={{ width: '12%' }}>
              Остаток
            </th>
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
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
