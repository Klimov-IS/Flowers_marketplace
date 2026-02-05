import { useState, useRef, useEffect } from 'react';
import type { FilterValue, FilterOption, FilterType, MultiSelectFilterValue } from './ColumnFilter';

interface FilterableHeaderProps {
  label: string;
  sortField?: string;
  currentSort?: { field: string | null; direction: 'asc' | 'desc' | null };
  onSort?: (field: string) => void;
  // Filter props
  filterType?: FilterType;
  filterOptions?: FilterOption[];
  filterValue?: FilterValue | null;
  onFilterChange?: (value: FilterValue | null) => void;
  filterSuffix?: string;
  // Style
  width?: string;
}

export default function FilterableHeader({
  label,
  sortField,
  currentSort,
  onSort,
  filterType,
  filterOptions,
  filterValue,
  onFilterChange,
  filterSuffix,
  width,
}: FilterableHeaderProps) {
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [localMin, setLocalMin] = useState<string>('');
  const [localMax, setLocalMax] = useState<string>('');
  const containerRef = useRef<HTMLTableCellElement>(null);

  // Sync local range state with filterValue
  useEffect(() => {
    if (filterValue?.type === 'range') {
      setLocalMin(filterValue.min?.toString() ?? '');
      setLocalMax(filterValue.max?.toString() ?? '');
    } else {
      setLocalMin('');
      setLocalMax('');
    }
  }, [filterValue]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsFilterOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Check if filter is active
  const hasActiveFilter = () => {
    if (!filterValue) return false;
    if (filterValue.type === 'multiselect') {
      return filterValue.selected.length > 0 && filterValue.selected.length !== filterOptions?.length;
    }
    if (filterValue.type === 'range') {
      return filterValue.min !== undefined || filterValue.max !== undefined;
    }
    return false;
  };

  // Check if this column is being sorted
  const isSorted = currentSort && currentSort.field === sortField && currentSort.direction !== null;
  const sortDirection = currentSort && currentSort.field === sortField ? currentSort.direction : null;

  // Handle sort click
  const handleSortClick = () => {
    if (sortField && onSort) {
      onSort(sortField);
    }
  };

  // Handle multiselect toggle
  const handleMultiSelectToggle = (optionValue: string | null) => {
    if (!onFilterChange) return;
    const currentValue = filterValue as MultiSelectFilterValue | null;
    const currentSelected = currentValue?.selected ?? [];

    let newSelected: (string | null)[];
    if (currentSelected.includes(optionValue)) {
      newSelected = currentSelected.filter((v) => v !== optionValue);
    } else {
      newSelected = [...currentSelected, optionValue];
    }

    if (newSelected.length === 0 || newSelected.length === filterOptions?.length) {
      onFilterChange(null);
    } else {
      onFilterChange({ type: 'multiselect', selected: newSelected });
    }
  };

  // Handle select all
  const handleSelectAll = () => {
    if (!onFilterChange) return;
    onFilterChange(null);
  };

  // Handle range apply
  const handleRangeApply = () => {
    if (!onFilterChange) return;
    const min = localMin ? parseFloat(localMin) : undefined;
    const max = localMax ? parseFloat(localMax) : undefined;

    if (min === undefined && max === undefined) {
      onFilterChange(null);
    } else {
      onFilterChange({ type: 'range', min, max });
    }
    setIsFilterOpen(false);
  };

  // Handle range reset
  const handleRangeReset = () => {
    if (!onFilterChange) return;
    setLocalMin('');
    setLocalMax('');
    onFilterChange(null);
    setIsFilterOpen(false);
  };

  // Render multiselect dropdown
  const renderMultiSelectDropdown = () => {
    const currentValue = filterValue as MultiSelectFilterValue | null;
    const currentSelected = currentValue?.selected ?? [];
    const allSelected = currentSelected.length === 0 || currentSelected.length === filterOptions?.length;

    return (
      <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
        <div className="p-2 max-h-64 overflow-y-auto">
          {/* Select All */}
          <label className="flex items-center gap-2 px-2 py-1.5 hover:bg-gray-50 rounded cursor-pointer">
            <input
              type="checkbox"
              checked={allSelected}
              onChange={handleSelectAll}
              className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
            />
            <span className="text-sm font-medium text-gray-700">Все</span>
          </label>

          <hr className="my-1 border-gray-200" />

          {/* Options */}
          {filterOptions?.map((option) => (
            <label
              key={option.value ?? '__null__'}
              className="flex items-center gap-2 px-2 py-1.5 hover:bg-gray-50 rounded cursor-pointer"
            >
              <input
                type="checkbox"
                checked={allSelected || currentSelected.includes(option.value)}
                onChange={() => handleMultiSelectToggle(option.value)}
                className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700">{option.label}</span>
            </label>
          ))}
        </div>
      </div>
    );
  };

  // Render range dropdown
  const renderRangeDropdown = () => {
    return (
      <div className="absolute top-full left-0 mt-1 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-50 p-3">
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">От</label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                value={localMin}
                onChange={(e) => setLocalMin(e.target.value)}
                placeholder="мин"
                className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:ring-primary-500 focus:border-primary-500"
              />
              {filterSuffix && <span className="text-sm text-gray-500">{filterSuffix}</span>}
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">До</label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                value={localMax}
                onChange={(e) => setLocalMax(e.target.value)}
                placeholder="макс"
                className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:ring-primary-500 focus:border-primary-500"
              />
              {filterSuffix && <span className="text-sm text-gray-500">{filterSuffix}</span>}
            </div>
          </div>
          <div className="flex gap-2 pt-1">
            <button
              onClick={handleRangeReset}
              className="flex-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded transition-colors"
            >
              Сбросить
            </button>
            <button
              onClick={handleRangeApply}
              className="flex-1 px-3 py-1.5 text-sm text-white bg-primary-600 hover:bg-primary-700 rounded transition-colors"
            >
              OK
            </button>
          </div>
        </div>
      </div>
    );
  };

  const hasFilter = filterType && onFilterChange;
  const hasSorting = sortField && onSort;

  return (
    <th
      className="px-3 py-3 font-medium text-left text-sm text-gray-600"
      style={{ width }}
      ref={containerRef}
    >
      <div className="flex items-center gap-1">
        {/* Label + Sort */}
        {hasSorting ? (
          <button
            onClick={handleSortClick}
            className="flex items-center gap-1 hover:text-gray-900 transition-colors"
          >
            <span>{label}</span>
            {/* Sort indicator */}
            {isSorted && (
              <svg
                className={`w-3.5 h-3.5 text-primary-600 ${sortDirection === 'desc' ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
            )}
          </button>
        ) : (
          <span>{label}</span>
        )}

        {/* Filter icon */}
        {hasFilter && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsFilterOpen(!isFilterOpen);
            }}
            className={`p-0.5 rounded transition-colors ${
              hasActiveFilter()
                ? 'text-primary-600 bg-primary-50'
                : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
            }`}
            title="Фильтр"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Filter dropdown */}
      {isFilterOpen && hasFilter && (
        <div className="relative">
          {filterType === 'multiselect' && renderMultiSelectDropdown()}
          {filterType === 'range' && renderRangeDropdown()}
        </div>
      )}
    </th>
  );
}
