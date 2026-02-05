import { getCountryFlag, getCountryName } from '../../../utils/catalogFormatters';

// Product types with Russian labels
const PRODUCT_TYPES = [
  { value: 'rose', label: 'Роза' },
  { value: 'carnation', label: 'Гвоздика' },
  { value: 'gypsophila', label: 'Гипсофила' },
  { value: 'ruscus', label: 'Рускус' },
  { value: 'alstroemeria', label: 'Альстромерия' },
  { value: 'eucalyptus', label: 'Эвкалипт' },
  { value: 'protea', label: 'Протея' },
];

// Countries
const COUNTRIES = ['EC', 'NL', 'CO', 'KE', 'RU'];

// Colors with swatches
const COLORS = [
  { value: 'белый', color: '#ffffff' },
  { value: 'красный', color: '#e53935' },
  { value: 'розовый', color: '#ec407a' },
  { value: 'жёлтый', color: '#fdd835' },
  { value: 'оранжевый', color: '#ff9800' },
  { value: 'зелёный', color: '#43a047' },
];

interface FilterSidebarProps {
  filters: {
    product_type?: string;
    origin_country?: string[];
    colors?: string[];
    length_min?: number;
    length_max?: number;
    price_min?: number;
    price_max?: number;
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

  const handleColorToggle = (color: string) => {
    const current = filters.colors || [];
    const updated = current.includes(color)
      ? current.filter((c) => c !== color)
      : [...current, color];
    onFilterChange('colors', updated.length > 0 ? updated : undefined);
  };

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
            <label key={country} className="flex items-center gap-2 cursor-pointer group">
              <input
                type="checkbox"
                checked={filters.origin_country?.includes(country) || false}
                onChange={() => handleCountryToggle(country)}
                className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700 group-hover:text-gray-900">
                {getCountryFlag(country)} {getCountryName(country)}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Color */}
      <div className="mb-5 pb-4 border-b border-gray-100">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Цвет
        </h3>
        <div className="grid grid-cols-3 gap-2">
          {COLORS.map((color) => (
            <button
              key={color.value}
              onClick={() => handleColorToggle(color.value)}
              className={`flex flex-col items-center gap-1 p-2 rounded-md border transition-colors ${
                filters.colors?.includes(color.value)
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-transparent hover:bg-gray-50'
              }`}
            >
              <span
                className="w-6 h-6 rounded-full border border-gray-300"
                style={{ backgroundColor: color.color }}
              />
              <span className="text-[10px] text-gray-600">{color.value}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Length */}
      <div className="mb-5 pb-4 border-b border-gray-100">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Длина, см
        </h3>
        <div className="flex items-center gap-2">
          <input
            type="number"
            placeholder="от"
            value={filters.length_min || ''}
            onChange={(e) => onFilterChange('length_min', e.target.value ? Number(e.target.value) : undefined)}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-primary-500 focus:border-primary-500"
          />
          <span className="text-gray-400">—</span>
          <input
            type="number"
            placeholder="до"
            value={filters.length_max || ''}
            onChange={(e) => onFilterChange('length_max', e.target.value ? Number(e.target.value) : undefined)}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
      </div>

      {/* Price */}
      <div className="mb-5 pb-4 border-b border-gray-100">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Цена, ₽
        </h3>
        <div className="flex items-center gap-2">
          <input
            type="number"
            placeholder="от"
            value={filters.price_min || ''}
            onChange={(e) => onFilterChange('price_min', e.target.value ? Number(e.target.value) : undefined)}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-primary-500 focus:border-primary-500"
          />
          <span className="text-gray-400">—</span>
          <input
            type="number"
            placeholder="до"
            value={filters.price_max || ''}
            onChange={(e) => onFilterChange('price_max', e.target.value ? Number(e.target.value) : undefined)}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
      </div>

      {/* In Stock Toggle */}
      <div>
        <label className="flex items-center gap-3 cursor-pointer">
          <div className="relative">
            <input
              type="checkbox"
              checked={filters.in_stock || false}
              onChange={(e) => onFilterChange('in_stock', e.target.checked || undefined)}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-gray-200 rounded-full peer peer-checked:bg-primary-600 transition-colors" />
            <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
          </div>
          <span className="text-sm text-gray-700">Только в наличии</span>
        </label>
      </div>
    </aside>
  );
}
