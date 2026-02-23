import { useState } from 'react';

// Product types matching database values (Russian)
const PRODUCT_TYPES = [
  { value: 'Роза', label: 'Роза' },
  { value: 'Тюльпан', label: 'Тюльпан' },
  { value: 'Хризантема', label: 'Хризантема' },
  { value: 'Гвоздика', label: 'Гвоздика' },
  { value: 'Альстромерия', label: 'Альстромерия' },
  { value: 'Гипсофила', label: 'Гипсофила' },
  { value: 'Эустома', label: 'Эустома' },
  { value: 'Гортензия', label: 'Гортензия' },
  { value: 'Пион', label: 'Пион' },
  { value: 'Лилия', label: 'Лилия' },
  { value: 'Ирис', label: 'Ирис' },
  { value: 'Фрезия', label: 'Фрезия' },
  { value: 'Ранункулюс', label: 'Ранункулюс' },
  { value: 'Орхидея', label: 'Орхидея' },
  { value: 'Эвкалипт', label: 'Эвкалипт' },
  { value: 'Рускус', label: 'Рускус' },
  { value: 'Статица', label: 'Статица' },
  { value: 'Гиперикум', label: 'Гиперикум' },
];

// Countries matching actual database values (Russian names)
const COUNTRIES = [
  { value: 'Эквадор', label: 'Эквадор', flag: '🇪🇨' },
  { value: 'Колумбия', label: 'Колумбия', flag: '🇨🇴' },
  { value: 'Нидерланды', label: 'Нидерланды', flag: '🇳🇱' },
  { value: 'Кения', label: 'Кения', flag: '🇰🇪' },
  { value: 'Израиль', label: 'Израиль', flag: '🇮🇱' },
  { value: 'Россия', label: 'Россия', flag: '🇷🇺' },
  { value: 'Эфиопия', label: 'Эфиопия', flag: '🇪🇹' },
  { value: 'Италия', label: 'Италия', flag: '🇮🇹' },
];

interface FilterSidebarProps {
  filters: {
    product_type?: string;
    origin_country?: string[];
    colors?: string[];
    in_stock?: boolean;
  };
  onFilterChange: (key: string, value: unknown) => void;
  onReset: () => void;
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      className={`w-4 h-4 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  );
}

export default function FilterSidebar({ filters, onFilterChange, onReset }: FilterSidebarProps) {
  const [typesOpen, setTypesOpen] = useState(false);
  const [countriesOpen, setCountriesOpen] = useState(false);

  const handleProductTypeChange = (value: string) => {
    onFilterChange('product_type', filters.product_type === value ? undefined : value);
  };

  const handleCountryToggle = (country: string) => {
    const current = filters.origin_country || [];
    const updated = current.includes(country)
      ? current.filter((c) => c !== country)
      : [...current, country];
    onFilterChange('origin_country', updated.length > 0 ? updated : undefined);
  };

  const activeTypesCount = filters.product_type ? 1 : 0;
  const activeCountriesCount = filters.origin_country?.length || 0;

  return (
    <aside className="w-64 flex-shrink-0 bg-white rounded-lg border border-gray-200 p-5 sticky top-24 max-h-[calc(100vh-7rem)] overflow-y-auto">
      {/* Header */}
      <div className="flex justify-between items-center mb-5 pb-3 border-b border-gray-200">
        <h2 className="font-semibold text-gray-900">Фильтры</h2>
        <button
          onClick={onReset}
          className="text-sm text-primary-600 hover:text-primary-700"
        >
          Сбросить
        </button>
      </div>

      {/* Product Type — collapsible */}
      <div className="mb-3 pb-3 border-b border-gray-100">
        <button
          onClick={() => setTypesOpen(!typesOpen)}
          className="flex items-center justify-between w-full py-1 text-left"
        >
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Тип цветка
            {activeTypesCount > 0 && (
              <span className="ml-1.5 inline-flex items-center justify-center w-5 h-5 text-xs font-medium bg-primary-100 text-primary-700 rounded-full normal-case">
                {activeTypesCount}
              </span>
            )}
          </span>
          <ChevronIcon open={typesOpen} />
        </button>
        {typesOpen && (
          <div className="space-y-2 mt-3">
            {PRODUCT_TYPES.map((type) => (
              <label key={type.value} className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={filters.product_type === type.value}
                  onChange={() => handleProductTypeChange(type.value)}
                  className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700 group-hover:text-gray-900">
                  {type.label}
                </span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Country — collapsible */}
      <div className="mb-3 pb-3 border-b border-gray-100">
        <button
          onClick={() => setCountriesOpen(!countriesOpen)}
          className="flex items-center justify-between w-full py-1 text-left"
        >
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Страна
            {activeCountriesCount > 0 && (
              <span className="ml-1.5 inline-flex items-center justify-center w-5 h-5 text-xs font-medium bg-primary-100 text-primary-700 rounded-full normal-case">
                {activeCountriesCount}
              </span>
            )}
          </span>
          <ChevronIcon open={countriesOpen} />
        </button>
        {countriesOpen && (
          <div className="space-y-2 mt-3">
            {COUNTRIES.map((country) => (
              <label key={country.value} className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={filters.origin_country?.includes(country.value) || false}
                  onChange={() => handleCountryToggle(country.value)}
                  className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700 group-hover:text-gray-900">
                  {country.flag} {country.label}
                </span>
              </label>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
