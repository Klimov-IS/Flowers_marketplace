// Note: getCountryFlag/getCountryName moved to inline since we now use Russian country names

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

export default function FilterSidebar({ filters, onFilterChange, onReset }: FilterSidebarProps) {
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

  // Note: handleColorToggle removed - colors filter hidden until data is available

  return (
    <aside className="w-64 flex-shrink-0 bg-white rounded-lg border border-gray-200 p-5 h-fit sticky top-24">
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

      {/* Product Type */}
      <div className="mb-5 pb-4 border-b border-gray-100">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Тип цветка
        </h3>
        <div className="space-y-2">
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
      </div>

      {/* Country */}
      <div className="mb-5 pb-4 border-b border-gray-100">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Страна
        </h3>
        <div className="space-y-2">
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
      </div>

      {/* Color filter hidden - no data in database yet */}
      {/* TODO: Enable when colors data is populated in supplier_items */}

      {/* Length and Price filters removed per user request */}
      {/* In Stock filter hidden - stock_qty is NULL for all offers in database */}
    </aside>
  );
}
