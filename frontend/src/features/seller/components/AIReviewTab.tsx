import { useState } from 'react';
import {
  useGetAISuggestionsQuery,
  useAcceptAISuggestionMutation,
  useRejectAISuggestionMutation,
  type AISuggestion,
} from '../supplierApi';
import Button from '../../../components/ui/Button';

interface AIReviewTabProps {
  supplierId: string;
}

// Field name translations
const FIELD_LABELS: Record<string, string> = {
  flower_type: 'Тип цветка',
  variety: 'Сорт',
  origin_country: 'Страна',
  length_cm: 'Длина (см)',
  colors: 'Цвета',
  farm: 'Ферма',
};

// Status translations and colors
const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  needs_review: { label: 'Ожидает проверки', color: 'bg-yellow-100 text-yellow-800' },
  pending: { label: 'В ожидании', color: 'bg-gray-100 text-gray-800' },
  auto_applied: { label: 'Авто-применено', color: 'bg-green-100 text-green-800' },
  manual_applied: { label: 'Применено вручную', color: 'bg-blue-100 text-blue-800' },
  rejected: { label: 'Отклонено', color: 'bg-red-100 text-red-800' },
};

// Format confidence as percentage
function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

// Get confidence color
function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return 'text-green-600';
  if (confidence >= 0.7) return 'text-yellow-600';
  return 'text-red-600';
}

// Format suggested value for display
function formatValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.join(', ');
  }
  if (typeof value === 'object' && value !== null) {
    return JSON.stringify(value);
  }
  return String(value ?? '—');
}

export default function AIReviewTab({ supplierId }: AIReviewTabProps) {
  const [statusFilter, setStatusFilter] = useState<string>('needs_review');
  const [page, setPage] = useState(1);
  const perPage = 20;

  // Fetch suggestions
  const { data, isLoading, isFetching } = useGetAISuggestionsQuery({
    status: statusFilter || undefined,
    supplier_id: supplierId,
    page,
    per_page: perPage,
  });

  const [acceptSuggestion, { isLoading: isAccepting }] = useAcceptAISuggestionMutation();
  const [rejectSuggestion, { isLoading: isRejecting }] = useRejectAISuggestionMutation();

  const suggestions = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / perPage);

  const handleAccept = async (suggestion: AISuggestion) => {
    try {
      await acceptSuggestion(suggestion.id).unwrap();
    } catch (err) {
      console.error('Failed to accept suggestion:', err);
    }
  };

  const handleReject = async (suggestion: AISuggestion) => {
    try {
      await rejectSuggestion(suggestion.id).unwrap();
    } catch (err) {
      console.error('Failed to reject suggestion:', err);
    }
  };

  const isProcessing = isAccepting || isRejecting;

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex gap-4 items-center justify-between">
        <div className="flex gap-2">
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
          >
            <option value="">Все статусы</option>
            <option value="needs_review">Ожидает проверки</option>
            <option value="pending">В ожидании</option>
            <option value="auto_applied">Авто-применено</option>
            <option value="manual_applied">Применено вручную</option>
            <option value="rejected">Отклонено</option>
          </select>
        </div>
        <div className="text-sm text-gray-500">
          {total > 0 && (
            <span>
              Найдено: <strong>{total}</strong> предложений
            </span>
          )}
        </div>
      </div>

      {/* Suggestions list */}
      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
        </div>
      ) : suggestions.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          {statusFilter === 'needs_review'
            ? 'Нет предложений, требующих проверки'
            : 'Предложения не найдены'}
        </div>
      ) : (
        <div className="space-y-3">
          {suggestions.map((suggestion) => (
            <SuggestionCard
              key={suggestion.id}
              suggestion={suggestion}
              onAccept={() => handleAccept(suggestion)}
              onReject={() => handleReject(suggestion)}
              isProcessing={isProcessing}
            />
          ))}
        </div>
      )}

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
    </div>
  );
}

// Suggestion card component
interface SuggestionCardProps {
  suggestion: AISuggestion;
  onAccept: () => void;
  onReject: () => void;
  isProcessing: boolean;
}

function SuggestionCard({ suggestion, onAccept, onReject, isProcessing }: SuggestionCardProps) {
  const statusConfig = STATUS_CONFIG[suggestion.applied_status] || {
    label: suggestion.applied_status,
    color: 'bg-gray-100 text-gray-800',
  };

  const fieldLabel = FIELD_LABELS[suggestion.field_name || ''] || suggestion.field_name || '—';
  const suggestedValue = formatValue(suggestion.suggested_value?.value);
  const canProcess = suggestion.applied_status === 'needs_review' || suggestion.applied_status === 'pending';

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      <div className="flex items-start justify-between">
        {/* Left side: info */}
        <div className="flex-1 space-y-2">
          {/* Item name and supplier */}
          <div>
            <div className="font-medium text-gray-900">{suggestion.item_raw_name || '—'}</div>
            {suggestion.supplier_name && (
              <div className="text-sm text-gray-500">{suggestion.supplier_name}</div>
            )}
          </div>

          {/* Field and value */}
          <div className="flex items-center gap-4">
            <div className="text-sm">
              <span className="text-gray-500">Поле:</span>{' '}
              <span className="font-medium">{fieldLabel}</span>
            </div>
            <div className="text-sm">
              <span className="text-gray-500">Значение:</span>{' '}
              <span className="font-medium text-emerald-600">{suggestedValue}</span>
            </div>
          </div>

          {/* Confidence and status */}
          <div className="flex items-center gap-4">
            <div className="text-sm">
              <span className="text-gray-500">Уверенность:</span>{' '}
              <span className={`font-medium ${getConfidenceColor(suggestion.confidence)}`}>
                {formatConfidence(suggestion.confidence)}
              </span>
            </div>
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig.color}`}>
              {statusConfig.label}
            </span>
          </div>
        </div>

        {/* Right side: actions */}
        {canProcess && (
          <div className="flex gap-2 ml-4">
            <Button
              variant="primary"
              size="sm"
              onClick={onAccept}
              disabled={isProcessing}
            >
              Принять
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={onReject}
              disabled={isProcessing}
            >
              Отклонить
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
