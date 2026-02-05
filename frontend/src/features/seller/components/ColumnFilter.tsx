import { useState, useRef, useEffect } from 'react';

// Filter types
export type FilterType = 'multiselect' | 'range' | 'text';

export interface FilterOption {
  value: string | null;
  label: string;
}

export interface MultiSelectFilterValue {
  type: 'multiselect';
  selected: (string | null)[];
}

export interface RangeFilterValue {
  type: 'range';
  min?: number;
  max?: number;
}

export interface TextFilterValue {
  type: 'text';
  value: string;
}

export type FilterValue = MultiSelectFilterValue | RangeFilterValue | TextFilterValue;

interface ColumnFilterProps {
  label: string;
  filterType: FilterType;
  options?: FilterOption[]; // For multiselect
  value: FilterValue | null;
  onChange: (value: FilterValue | null) => void;
  placeholder?: string;
  suffix?: string; // For range inputs (e.g., "см", "₽")
}

export default function ColumnFilter({
  label,
  filterType,
  options,
  value,
  onChange,
  placeholder: _placeholder,
  suffix,
}: ColumnFilterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Local state for range inputs
  const [localMin, setLocalMin] = useState<string>('');
  const [localMax, setLocalMax] = useState<string>('');

  // Sync local range state with value
  useEffect(() => {
    if (value?.type === 'range') {
      setLocalMin(value.min?.toString() ?? '');
      setLocalMax(value.max?.toString() ?? '');
    } else {
      setLocalMin('');
      setLocalMax('');
    }
  }, [value]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Check if filter has active value
  const hasActiveFilter = () => {
    if (!value) return false;
    if (value.type === 'multiselect') {
      return value.selected.length > 0 && value.selected.length !== options?.length;
    }
    if (value.type === 'range') {
      return value.min !== undefined || value.max !== undefined;
    }
    if (value.type === 'text') {
      return value.value.trim().length > 0;
    }
    return false;
  };

  // Handle multiselect toggle
  const handleMultiSelectToggle = (optionValue: string | null) => {
    const currentValue = value as MultiSelectFilterValue | null;
    const currentSelected = currentValue?.selected ?? [];

    let newSelected: (string | null)[];
    if (currentSelected.includes(optionValue)) {
      newSelected = currentSelected.filter((v) => v !== optionValue);
    } else {
      newSelected = [...currentSelected, optionValue];
    }

    if (newSelected.length === 0 || newSelected.length === options?.length) {
      onChange(null); // All selected = no filter
    } else {
      onChange({ type: 'multiselect', selected: newSelected });
    }
  };

  // Handle select all / none
  const handleSelectAll = () => {
    onChange(null);
  };

  // Handle range apply
  const handleRangeApply = () => {
    const min = localMin ? parseFloat(localMin) : undefined;
    const max = localMax ? parseFloat(localMax) : undefined;

    if (min === undefined && max === undefined) {
      onChange(null);
    } else {
      onChange({ type: 'range', min, max });
    }
    setIsOpen(false);
  };

  // Handle range reset
  const handleRangeReset = () => {
    setLocalMin('');
    setLocalMax('');
    onChange(null);
    setIsOpen(false);
  };

  // Render multiselect dropdown
  const renderMultiSelectDropdown = () => {
    const currentValue = value as MultiSelectFilterValue | null;
    const currentSelected = currentValue?.selected ?? [];
    const allSelected = currentSelected.length === 0 || currentSelected.length === options?.length;

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
          {options?.map((option) => (
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
              {suffix && <span className="text-sm text-gray-500">{suffix}</span>}
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
              {suffix && <span className="text-sm text-gray-500">{suffix}</span>}
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

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-1 text-sm font-medium transition-colors ${
          hasActiveFilter()
            ? 'text-primary-600'
            : 'text-gray-600 hover:text-gray-900'
        }`}
      >
        {label}
        <svg
          className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
        {hasActiveFilter() && (
          <span className="ml-0.5 w-2 h-2 bg-primary-600 rounded-full" />
        )}
      </button>

      {isOpen && (
        <>
          {filterType === 'multiselect' && renderMultiSelectDropdown()}
          {filterType === 'range' && renderRangeDropdown()}
        </>
      )}
    </div>
  );
}

// Status filter options
export const STATUS_OPTIONS: FilterOption[] = [
  { value: 'active', label: 'Активный' },
  { value: 'hidden', label: 'Скрытый' },
  { value: 'deleted', label: 'Удалённый' },
];
