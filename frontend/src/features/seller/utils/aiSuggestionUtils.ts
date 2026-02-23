/**
 * Shared AI suggestion utilities.
 */

// Field name translations
export const FIELD_LABELS: Record<string, string> = {
  flower_type: 'Тип цветка',
  variety: 'Сорт',
  origin_country: 'Страна',
  length_cm: 'Длина (см)',
  colors: 'Цвета',
  farm: 'Ферма',
};

// Status translations and colors
export const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  needs_review: { label: 'Ожидает проверки', color: 'bg-yellow-100 text-yellow-800' },
  pending: { label: 'В ожидании', color: 'bg-gray-100 text-gray-800' },
  auto_applied: { label: 'Авто-применено', color: 'bg-green-100 text-green-800' },
  manual_applied: { label: 'Применено вручную', color: 'bg-blue-100 text-blue-800' },
  rejected: { label: 'Отклонено', color: 'bg-red-100 text-red-800' },
};

// Format confidence as percentage
export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

// Get confidence color
export function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return 'text-green-600';
  if (confidence >= 0.7) return 'text-yellow-600';
  return 'text-red-600';
}

// Format suggested value for display
export function formatValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.join(', ');
  }
  if (typeof value === 'object' && value !== null) {
    return JSON.stringify(value);
  }
  return String(value ?? '—');
}
