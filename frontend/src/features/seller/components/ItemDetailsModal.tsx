import Modal from '../../../components/ui/Modal';
import Badge from '../../../components/ui/Badge';
import Button from '../../../components/ui/Button';
import ColorSquares from './ColorSquares';
import StockIndicator from './StockIndicator';
import type { SupplierItem } from '../../../types/supplierItem';

interface ItemDetailsModalProps {
  item: SupplierItem | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function ItemDetailsModal({
  item,
  isOpen,
  onClose,
}: ItemDetailsModalProps) {
  if (!item) return null;

  const statusLabel = (status: string) => {
    switch (status) {
      case 'active':
        return 'Активен';
      case 'ambiguous':
        return 'На проверке';
      case 'rejected':
        return 'Отклонён';
      default:
        return status;
    }
  };

  const statusVariant = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'ambiguous':
        return 'warning';
      case 'rejected':
        return 'danger';
      default:
        return 'default';
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Детали товара" size="lg">
      <div className="space-y-6">
        {/* Header with status */}
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">{item.raw_name}</h2>
            <p className="text-sm text-gray-500 mt-1">ID: {item.id}</p>
          </div>
          <Badge variant={statusVariant(item.status)}>
            {statusLabel(item.status)}
          </Badge>
        </div>

        {/* Source data section */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Исходные данные</h3>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <dt className="text-gray-500">Raw Name:</dt>
            <dd className="text-gray-900 font-mono text-xs bg-gray-100 px-2 py-1 rounded">
              {item.raw_name}
            </dd>
            <dt className="text-gray-500">Источник (файл):</dt>
            <dd className="text-gray-900">{item.source_file || '—'}</dd>
          </dl>
        </div>

        {/* Normalized data section */}
        <div className="bg-blue-50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-blue-800 mb-3">Нормализованные данные</h3>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <dt className="text-blue-600">Страна:</dt>
            <dd className="text-gray-900 font-medium">{item.origin_country || '—'}</dd>

            <dt className="text-blue-600">Цвета:</dt>
            <dd>
              {item.colors.length > 0 ? (
                <div className="flex items-center gap-2">
                  <ColorSquares colors={item.colors} />
                  <span className="text-gray-600 text-xs">
                    ({item.colors.join(', ')})
                  </span>
                </div>
              ) : (
                <span className="text-gray-400">—</span>
              )}
            </dd>

            <dt className="text-blue-600">Диапазон длин:</dt>
            <dd className="text-gray-900">
              {item.length_min ? (
                item.length_max && item.length_min !== item.length_max
                  ? `${item.length_min}–${item.length_max} см`
                  : `${item.length_min} см`
              ) : '—'}
            </dd>

            <dt className="text-blue-600">Диапазон цен:</dt>
            <dd className="text-gray-900 font-medium">
              {item.price_min ? (
                item.price_max && item.price_min !== item.price_max
                  ? `${parseFloat(item.price_min).toLocaleString()}–${parseFloat(item.price_max).toLocaleString()} ₽`
                  : `${parseFloat(item.price_min).toLocaleString()} ₽`
              ) : '—'}
            </dd>

            <dt className="text-blue-600">Общий остаток:</dt>
            <dd>
              <StockIndicator stock={item.stock_total} />
            </dd>
          </dl>
        </div>

        {/* Variants section */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-3">
            Варианты ({item.variants_count})
          </h3>

          {item.variants.length > 0 ? (
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr className="text-left text-gray-600">
                    <th className="px-3 py-2 font-medium">Размер</th>
                    <th className="px-3 py-2 font-medium">Упаковка</th>
                    <th className="px-3 py-2 font-medium">Кол-во</th>
                    <th className="px-3 py-2 font-medium">Цена</th>
                    <th className="px-3 py-2 font-medium">Остаток</th>
                    <th className="px-3 py-2 font-medium">Статус</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {item.variants.map((variant) => (
                    <tr key={variant.id} className="hover:bg-gray-50">
                      <td className="px-3 py-2">
                        {variant.length_cm ? `${variant.length_cm} см` : '—'}
                      </td>
                      <td className="px-3 py-2">{variant.pack_type || '—'}</td>
                      <td className="px-3 py-2">
                        {variant.pack_qty ? `${variant.pack_qty} шт` : '—'}
                      </td>
                      <td className="px-3 py-2 font-medium">
                        {parseFloat(variant.price).toLocaleString()} ₽
                        {variant.price_max && (
                          <span className="text-gray-500 font-normal">
                            {' '}– {parseFloat(variant.price_max).toLocaleString()} ₽
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <StockIndicator stock={variant.stock || 0} />
                      </td>
                      <td className="px-3 py-2">
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
          ) : (
            <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg">
              Нет вариантов
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          <Button variant="secondary" onClick={onClose}>
            Закрыть
          </Button>
        </div>
      </div>
    </Modal>
  );
}
