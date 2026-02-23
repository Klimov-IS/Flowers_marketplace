import {
  useGetAISuggestionsQuery,
  useAcceptAISuggestionMutation,
  useRejectAISuggestionMutation,
} from '../supplierApi';
import Button from '../../../components/ui/Button';
import {
  FIELD_LABELS,
  formatConfidence,
  getConfidenceColor,
  formatValue,
} from '../utils/aiSuggestionUtils';

interface AISuggestionRowProps {
  itemId: string;
  colSpan: number;
}

export default function AISuggestionRow({ itemId, colSpan }: AISuggestionRowProps) {
  const { data, isLoading } = useGetAISuggestionsQuery({
    target_id: itemId,
    status: 'needs_review',
    per_page: 50,
  });

  const [acceptSuggestion, { isLoading: isAccepting }] = useAcceptAISuggestionMutation();
  const [rejectSuggestion, { isLoading: isRejecting }] = useRejectAISuggestionMutation();

  const handleAccept = async (suggestionId: string) => {
    try {
      await acceptSuggestion(suggestionId).unwrap();
    } catch (error) {
      console.error('Failed to accept suggestion:', error);
    }
  };

  const handleReject = async (suggestionId: string) => {
    try {
      await rejectSuggestion(suggestionId).unwrap();
    } catch (error) {
      console.error('Failed to reject suggestion:', error);
    }
  };

  return (
    <tr className="bg-yellow-50/50">
      <td colSpan={colSpan} className="px-4 py-3">
        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600" />
            Загрузка предложений...
          </div>
        ) : !data || data.items.length === 0 ? (
          <p className="text-sm text-gray-500">Нет предложений для проверки</p>
        ) : (
          <div className="space-y-2">
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              Предложения для проверки ({data.items.length})
            </div>
            {data.items.map((suggestion) => (
              <div
                key={suggestion.id}
                className="flex items-center justify-between bg-white rounded-lg border border-yellow-200 px-3 py-2"
              >
                <div className="flex items-center gap-4 min-w-0">
                  <span className="text-sm text-gray-500 flex-shrink-0">
                    {FIELD_LABELS[suggestion.field_name || ''] || suggestion.field_name}
                  </span>
                  <span className="text-sm font-medium text-emerald-700 truncate">
                    {formatValue(suggestion.suggested_value?.value)}
                  </span>
                  <span className={`text-xs font-medium flex-shrink-0 ${getConfidenceColor(suggestion.confidence)}`}>
                    {formatConfidence(suggestion.confidence)}
                  </span>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0 ml-4">
                  <Button
                    size="sm"
                    variant="success"
                    onClick={() => handleAccept(suggestion.id)}
                    disabled={isAccepting || isRejecting}
                  >
                    Принять
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => handleReject(suggestion.id)}
                    disabled={isAccepting || isRejecting}
                  >
                    Отклонить
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </td>
    </tr>
  );
}
