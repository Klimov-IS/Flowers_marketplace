import type { AssortmentMetrics } from '../supplierApi';

export type AssortmentPillFilter = 'all' | 'published' | 'needs_review' | 'errors';

const PILLS: { value: AssortmentPillFilter; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'published', label: 'Опубликовано' },
  { value: 'needs_review', label: 'На проверке' },
  { value: 'errors', label: 'Ошибки' },
];

interface AssortmentStatusPillsProps {
  activeFilter: AssortmentPillFilter;
  onFilterChange: (filter: AssortmentPillFilter) => void;
  metrics?: AssortmentMetrics;
}

function getCount(pill: AssortmentPillFilter, metrics?: AssortmentMetrics): number | undefined {
  if (!metrics) return undefined;
  switch (pill) {
    case 'all': return metrics.total_items;
    case 'published': return metrics.published;
    case 'needs_review': return metrics.needs_review;
    case 'errors': return metrics.errors;
  }
}

export default function AssortmentStatusPills({
  activeFilter,
  onFilterChange,
  metrics,
}: AssortmentStatusPillsProps) {
  return (
    <div className="flex gap-2">
      {PILLS.map((pill) => {
        const isActive = activeFilter === pill.value;
        const count = getCount(pill.value, metrics);
        return (
          <button
            key={pill.value}
            onClick={() => onFilterChange(pill.value)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              isActive
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {pill.label}
            {count !== undefined && (
              <span className="ml-1">({count})</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
