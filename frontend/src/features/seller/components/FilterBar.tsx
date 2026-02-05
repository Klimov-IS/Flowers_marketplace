import ColumnFilter, {
  FilterValue,
  FilterOption,
  STATUS_OPTIONS,
} from './ColumnFilter';

// Country options
const COUNTRY_OPTIONS: FilterOption[] = [
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

// Common color options
const COLOR_OPTIONS: FilterOption[] = [
  { value: 'красный', label: 'Красный' },
  { value: 'белый', label: 'Белый' },
  { value: 'розовый', label: 'Розовый' },
  { value: 'желтый', label: 'Жёлтый' },
  { value: 'оранжевый', label: 'Оранжевый' },
  { value: 'микс', label: 'Микс' },
  { value: null, label: 'Не указан' },
];

export interface ColumnFilters {
  status: FilterValue | null;
  origin_country: FilterValue | null;
  colors: FilterValue | null;
  price: FilterValue | null;
  length: FilterValue | null;
  stock: FilterValue | null;
}

export const initialFilters: ColumnFilters = {
  status: { type: 'multiselect', selected: ['active'] }, // Default: show only active
  origin_country: null,
  colors: null,
  price: null,
  length: null,
  stock: null,
};

interface FilterBarProps {
  filters: ColumnFilters;
  onFilterChange: (key: keyof ColumnFilters, value: FilterValue | null) => void;
  onResetFilters: () => void;
}

export default function FilterBar({
  filters,
  onFilterChange,
  onResetFilters,
}: FilterBarProps) {
  // Check if any filter is active (besides default status)
  const hasActiveFilters = () => {
    const { status, ...otherFilters } = filters;
    // Check if status is different from default
    const statusValue = status as { type: 'multiselect'; selected: string[] } | null;
    const isStatusNonDefault =
      statusValue?.selected?.length !== 1 ||
      statusValue?.selected?.[0] !== 'active';

    // Check other filters
    const hasOtherFilters = Object.values(otherFilters).some((f) => f !== null);

    return isStatusNonDefault || hasOtherFilters;
  };

  return (
    <div className="flex flex-wrap items-center gap-4 py-3 px-4 bg-gray-50 rounded-lg border border-gray-200">
      <span className="text-sm text-gray-500 font-medium">Фильтры:</span>

      <ColumnFilter
        label="Статус"
        filterType="multiselect"
        options={STATUS_OPTIONS}
        value={filters.status}
        onChange={(v) => onFilterChange('status', v)}
      />

      <ColumnFilter
        label="Страна"
        filterType="multiselect"
        options={COUNTRY_OPTIONS}
        value={filters.origin_country}
        onChange={(v) => onFilterChange('origin_country', v)}
      />

      <ColumnFilter
        label="Цвет"
        filterType="multiselect"
        options={COLOR_OPTIONS}
        value={filters.colors}
        onChange={(v) => onFilterChange('colors', v)}
      />

      <ColumnFilter
        label="Цена"
        filterType="range"
        value={filters.price}
        onChange={(v) => onFilterChange('price', v)}
        suffix="₽"
      />

      <ColumnFilter
        label="Размер"
        filterType="range"
        value={filters.length}
        onChange={(v) => onFilterChange('length', v)}
        suffix="см"
      />

      <ColumnFilter
        label="Остаток"
        filterType="range"
        value={filters.stock}
        onChange={(v) => onFilterChange('stock', v)}
      />

      {hasActiveFilters() && (
        <button
          onClick={onResetFilters}
          className="ml-auto text-sm text-gray-500 hover:text-gray-700 underline"
        >
          Сбросить все
        </button>
      )}
    </div>
  );
}

// Helper to convert filter state to API params
export function filtersToParams(filters: ColumnFilters) {
  const params: {
    status?: string[];
    origin_country?: (string | null)[];
    colors?: (string | null)[];
    price_min?: number;
    price_max?: number;
    length_min?: number;
    length_max?: number;
    stock_min?: number;
    stock_max?: number;
  } = {};

  // Status
  if (filters.status?.type === 'multiselect') {
    params.status = filters.status.selected.filter((s): s is string => s !== null);
  }

  // Origin country
  if (filters.origin_country?.type === 'multiselect') {
    params.origin_country = filters.origin_country.selected;
  }

  // Colors
  if (filters.colors?.type === 'multiselect') {
    params.colors = filters.colors.selected;
  }

  // Price range
  if (filters.price?.type === 'range') {
    if (filters.price.min !== undefined) params.price_min = filters.price.min;
    if (filters.price.max !== undefined) params.price_max = filters.price.max;
  }

  // Length range
  if (filters.length?.type === 'range') {
    if (filters.length.min !== undefined) params.length_min = filters.length.min;
    if (filters.length.max !== undefined) params.length_max = filters.length.max;
  }

  // Stock range
  if (filters.stock?.type === 'range') {
    if (filters.stock.min !== undefined) params.stock_min = filters.stock.min;
    if (filters.stock.max !== undefined) params.stock_max = filters.stock.max;
  }

  return params;
}
