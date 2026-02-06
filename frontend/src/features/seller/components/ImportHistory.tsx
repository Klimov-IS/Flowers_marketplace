import { useState } from 'react';
import {
  useGetSupplierImportsQuery,
  useGetParseEventsQuery,
  useDeleteImportMutation,
  useReparseImportMutation,
} from '../supplierApi';
import type { ImportBatchListItem } from '../supplierApi';
import Button from '../../../components/ui/Button';

interface ImportHistoryProps {
  supplierId: string;
}

// Status badge component
function StatusBadge({ status, hasErrors }: { status: string; hasErrors: boolean }) {
  if (hasErrors && status === 'published') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
        <span className="text-yellow-500">!</span>
        Ошибки
      </span>
    );
  }

  const statusConfig: Record<string, { label: string; className: string }> = {
    received: { label: 'Получен', className: 'bg-gray-100 text-gray-700' },
    parsed: { label: 'Обработан', className: 'bg-blue-100 text-blue-700' },
    published: { label: 'Готово', className: 'bg-green-100 text-green-700' },
    failed: { label: 'Ошибка', className: 'bg-red-100 text-red-700' },
  };

  const config = statusConfig[status] || { label: status, className: 'bg-gray-100 text-gray-700' };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${config.className}`}>
      {config.label}
    </span>
  );
}

// Import details (expandable row)
function ImportDetails({
  batch,
  onClose,
}: {
  batch: ImportBatchListItem;
  onClose: () => void;
}) {
  const { data: eventsData, isLoading: eventsLoading } = useGetParseEventsQuery(
    { import_id: batch.id, severity: 'error' },
    { skip: batch.parse_errors_count === 0 }
  );

  const [deleteImport, { isLoading: deleteLoading }] = useDeleteImportMutation();
  const [reparseImport, { isLoading: reparseLoading }] = useReparseImportMutation();

  const handleDelete = async () => {
    if (!confirm('Удалить этот импорт? Все связанные позиции будут удалены.')) return;
    try {
      await deleteImport(batch.id).unwrap();
    } catch (err) {
      console.error('Delete failed:', err);
      alert('Ошибка при удалении импорта');
    }
  };

  const handleReparse = async () => {
    try {
      await reparseImport(batch.id).unwrap();
    } catch (err) {
      console.error('Reparse failed:', err);
      alert('Ошибка при перепарсинге');
    }
  };

  return (
    <tr>
      <td colSpan={5} className="px-4 py-3 bg-gray-50 border-b">
        <div className="space-y-3">
          {/* Statistics */}
          <div className="flex gap-6 text-sm">
            <div>
              <span className="text-gray-500">Строк в файле:</span>{' '}
              <span className="font-medium">{batch.raw_rows_count}</span>
            </div>
            <div>
              <span className="text-gray-500">Позиций:</span>{' '}
              <span className="font-medium">{batch.offer_candidates_count}</span>
            </div>
            {batch.parse_errors_count > 0 && (
              <div>
                <span className="text-red-600">Ошибок:</span>{' '}
                <span className="font-medium text-red-600">{batch.parse_errors_count}</span>
              </div>
            )}
          </div>

          {/* Errors list */}
          {batch.parse_errors_count > 0 && (
            <div className="bg-red-50 rounded-lg p-3">
              <h4 className="text-sm font-medium text-red-800 mb-2">Ошибки парсинга:</h4>
              {eventsLoading ? (
                <div className="text-sm text-gray-500">Загрузка...</div>
              ) : (
                <ul className="space-y-1 text-sm text-red-700 max-h-32 overflow-y-auto">
                  {eventsData?.items.slice(0, 10).map((event) => (
                    <li key={event.id} className="flex gap-2">
                      {event.row_ref && (
                        <span className="text-red-500 font-mono">{event.row_ref}:</span>
                      )}
                      <span>{event.message}</span>
                    </li>
                  ))}
                  {eventsData && eventsData.total > 10 && (
                    <li className="text-red-500 italic">
                      ... и ещё {eventsData.total - 10} ошибок
                    </li>
                  )}
                </ul>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleReparse}
              disabled={reparseLoading}
            >
              {reparseLoading ? 'Обработка...' : 'Перепарсить'}
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={handleDelete}
              disabled={deleteLoading}
            >
              {deleteLoading ? 'Удаление...' : 'Удалить'}
            </Button>
            <button
              onClick={onClose}
              className="ml-auto text-sm text-gray-500 hover:text-gray-700"
            >
              Свернуть
            </button>
          </div>
        </div>
      </td>
    </tr>
  );
}

// Single import row
function ImportRow({
  batch,
  isExpanded,
  onToggle,
}: {
  batch: ImportBatchListItem;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <tr
      className={`border-b hover:bg-gray-50 cursor-pointer transition-colors ${
        isExpanded ? 'bg-gray-50' : ''
      }`}
      onClick={onToggle}
    >
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform ${
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
          <span className="font-medium text-gray-900 truncate max-w-xs" title={batch.source_filename || ''}>
            {batch.source_filename || 'Без названия'}
          </span>
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-gray-600">{formatDate(batch.imported_at)}</td>
      <td className="px-4 py-3">
        <StatusBadge status={batch.status} hasErrors={batch.parse_errors_count > 0} />
      </td>
      <td className="px-4 py-3 text-sm text-gray-600">{batch.offer_candidates_count}</td>
    </tr>
  );
}

export default function ImportHistory({ supplierId }: ImportHistoryProps) {
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data, isLoading, isFetching } = useGetSupplierImportsQuery({
    supplier_id: supplierId,
    page,
    per_page: 10,
  });

  const totalPages = data ? Math.ceil(data.total / 10) : 0;

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto" />
        <p className="mt-2 text-sm text-gray-500">Загрузка истории...</p>
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
        <svg
          className="w-12 h-12 text-gray-400 mx-auto mb-3"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <p className="text-gray-600">История импортов пуста</p>
        <p className="text-sm text-gray-500 mt-1">Загрузите первый прайс-лист</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-4 py-3 border-b bg-gray-50">
        <h3 className="font-medium text-gray-900">История импортов</h3>
      </div>

      <table className="w-full">
        <thead>
          <tr className="border-b bg-gray-50 text-left text-sm text-gray-600">
            <th className="px-4 py-2 font-medium">Файл</th>
            <th className="px-4 py-2 font-medium">Дата</th>
            <th className="px-4 py-2 font-medium">Статус</th>
            <th className="px-4 py-2 font-medium">Позиций</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((batch) => (
            <>
              <ImportRow
                key={batch.id}
                batch={batch}
                isExpanded={expandedId === batch.id}
                onToggle={() => setExpandedId((prev) => (prev === batch.id ? null : batch.id))}
              />
              {expandedId === batch.id && (
                <ImportDetails
                  key={`${batch.id}-details`}
                  batch={batch}
                  onClose={() => setExpandedId(null)}
                />
              )}
            </>
          ))}
        </tbody>
      </table>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="px-4 py-3 border-t flex items-center justify-between">
          <div className="text-sm text-gray-600">
            Страница {page} из {totalPages}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || isFetching}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Назад
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages || isFetching}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Вперёд
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
