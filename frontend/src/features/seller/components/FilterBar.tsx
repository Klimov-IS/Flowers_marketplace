/**
 * FilterBar - Types, constants, and utilities for column filters
 *
 * The FilterBar UI component has been removed in favor of inline column header filters.
 * This file now only exports types and helper functions used by AssortmentTab and AssortmentTable.
 */

import type { FilterValue, FilterOption } from './ColumnFilter';
export { STATUS_OPTIONS } from './ColumnFilter';

// Country options
export const COUNTRY_OPTIONS: FilterOption[] = [
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
export const COLOR_OPTIONS: FilterOption[] = [
  { value: 'красный', label: 'Красный' },
  { value: 'белый', label: 'Белый' },
  { value: 'розовый', label: 'Розовый' },
  { value: 'желтый', label: 'Желтый' },
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
