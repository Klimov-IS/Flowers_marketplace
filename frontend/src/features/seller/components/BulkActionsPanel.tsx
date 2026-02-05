interface BulkActionsPanelProps {
  selectedCount: number;
  onBulkDelete: () => void;
  onBulkHide: () => void;
  onBulkRestore: () => void;
  onClearSelection: () => void;
  isDeleting?: boolean;
  isHiding?: boolean;
  isRestoring?: boolean;
}

export default function BulkActionsPanel({
  selectedCount,
  onBulkDelete,
  onBulkHide,
  onBulkRestore,
  onClearSelection,
  isDeleting,
  isHiding,
  isRestoring,
}: BulkActionsPanelProps) {
  if (selectedCount === 0) return null;

  const isLoading = isDeleting || isHiding || isRestoring;

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-primary-50 border border-primary-200 rounded-lg">
      <div className="flex items-center gap-4">
        <span className="text-sm font-medium text-primary-800">
          Выбрано: <strong>{selectedCount}</strong> товар{selectedCount === 1 ? '' : selectedCount < 5 ? 'а' : 'ов'}
        </span>
        <button
          onClick={onClearSelection}
          className="text-sm text-primary-600 hover:text-primary-800 underline"
        >
          Снять выделение
        </button>
      </div>
      <div className="flex items-center gap-2">
        {/* Restore */}
        <button
          onClick={onBulkRestore}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-green-700 bg-green-100 hover:bg-green-200 rounded-md transition-colors disabled:opacity-50"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          {isRestoring ? 'Восстановление...' : 'Восстановить'}
        </button>

        {/* Hide */}
        <button
          onClick={onBulkHide}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-orange-700 bg-orange-100 hover:bg-orange-200 rounded-md transition-colors disabled:opacity-50"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
            />
          </svg>
          {isHiding ? 'Скрытие...' : 'Скрыть'}
        </button>

        {/* Delete */}
        <button
          onClick={() => {
            if (confirm(`Удалить ${selectedCount} товар${selectedCount === 1 ? '' : selectedCount < 5 ? 'а' : 'ов'}? Их можно будет восстановить.`)) {
              onBulkDelete();
            }
          }}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-700 bg-red-100 hover:bg-red-200 rounded-md transition-colors disabled:opacity-50"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
          {isDeleting ? 'Удаление...' : 'Удалить'}
        </button>
      </div>
    </div>
  );
}
