// FilterSidebar — desktop sidebar + mobile drawer for catalog filters

const COUNTRIES = [
  { value: 'Эквадор', label: 'Эквадор' },
  { value: 'Кения', label: 'Кения' },
  { value: 'Россия', label: 'Россия' },
  { value: 'Нидерланды', label: 'Нидерланды' },
  { value: 'Колумбия', label: 'Колумбия' },
  { value: 'Израиль', label: 'Израиль' },
  { value: 'Эфиопия', label: 'Эфиопия' },
  { value: 'Италия', label: 'Италия' },
];

const COLORS = [
  { name: 'Красный', bg: 'bg-red-500', extra: '' },
  { name: 'Белый', bg: 'bg-white', extra: 'border-2 border-gray-200' },
  { name: 'Розовый', bg: 'bg-pink-400', extra: '' },
  { name: 'Жёлтый', bg: 'bg-yellow-400', extra: '' },
  { name: 'Оранжевый', bg: 'bg-orange-500', extra: '' },
  { name: 'Фиолетовый', bg: 'bg-purple-500', extra: '' },
  { name: 'Синий', bg: 'bg-blue-500', extra: '' },
  { name: 'Зелёный', bg: 'bg-green-500', extra: '' },
  { name: 'Микс', bg: 'bg-gradient-to-br from-red-400 via-yellow-300 to-pink-400', extra: '' },
];

const LENGTHS = [40, 50, 60, 70, 80];

interface FilterSidebarProps {
  filters: {
    product_type?: string;
    origin_country?: string[];
    colors?: string[];
    in_stock?: boolean;
    length_min?: number;
    length_max?: number;
  };
  onFilterChange: (key: string, value: unknown) => void;
  onReset: () => void;
}

// ── Desktop Sidebar ─────────────────────────────────────────────────────────
export default function FilterSidebar({ filters, onFilterChange, onReset }: FilterSidebarProps) {
  return (
    <aside className="hidden lg:block w-64 shrink-0">
      <div className="sticky top-[140px] space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">Фильтры</h3>
          <button
            onClick={onReset}
            className="text-xs text-primary-600 hover:text-primary-700 font-medium transition-colors"
          >
            Сбросить всё
          </button>
        </div>

        <FilterSections filters={filters} onFilterChange={onFilterChange} />
      </div>
    </aside>
  );
}

// ── Shared Filter Sections (used by both desktop sidebar and mobile drawer) ─
function FilterSections({
  filters,
  onFilterChange,
}: {
  filters: FilterSidebarProps['filters'];
  onFilterChange: FilterSidebarProps['onFilterChange'];
}) {
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

  const handleLengthToggle = (length: number) => {
    // Use length_min/length_max for the selected length range
    const isSelected = isLengthSelected(length, filters.length_min, filters.length_max);
    if (isSelected) {
      // If deselecting, reset length filters
      onFilterChange('length_range', { min: undefined, max: undefined });
    } else {
      if (length >= 80) {
        onFilterChange('length_range', { min: 80, max: undefined });
      } else {
        onFilterChange('length_range', { min: length, max: length });
      }
    }
  };

  return (
    <>
      {/* Country */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-3">Страна происхождения</h4>
        <div className="space-y-2">
          {COUNTRIES.map((country) => (
            <label key={country.value} className="flex items-center gap-2.5 cursor-pointer group">
              <input
                type="checkbox"
                checked={filters.origin_country?.includes(country.value) || false}
                onChange={() => handleCountryToggle(country.value)}
                className="w-4 h-4 rounded border-gray-300 text-primary-500 focus:ring-primary-500/20 transition"
              />
              <span className="text-sm text-gray-600 group-hover:text-gray-900 transition-colors">
                {country.label}
              </span>
            </label>
          ))}
        </div>
      </div>

      <div className="border-t border-gray-100" />

      {/* Color */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-3">Цвет</h4>
        <div className="flex flex-wrap gap-2">
          {COLORS.map((color) => {
            const isSelected = filters.colors?.includes(color.name) || false;
            return (
              <button
                key={color.name}
                onClick={() => handleColorToggle(color.name)}
                className={`w-8 h-8 rounded-full ${color.bg} ${color.extra} transition-all hover:scale-110 ${
                  isSelected ? 'ring-2 ring-offset-2 ring-primary-500' : ''
                }`}
                title={color.name}
              />
            );
          })}
        </div>
      </div>

      <div className="border-t border-gray-100" />

      {/* Stem length */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-3">Длина стебля</h4>
        <div className="space-y-2">
          {LENGTHS.map((length) => {
            const selected = isLengthSelected(length, filters.length_min, filters.length_max);
            return (
              <label key={length} className="flex items-center gap-2.5 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={selected}
                  onChange={() => handleLengthToggle(length)}
                  className="w-4 h-4 rounded border-gray-300 text-primary-500 focus:ring-primary-500/20 transition"
                />
                <span className="text-sm text-gray-600 group-hover:text-gray-900 transition-colors">
                  {length >= 80 ? '80+ см' : `${length} см`}
                </span>
              </label>
            );
          })}
        </div>
      </div>

      <div className="border-t border-gray-100" />

      {/* In stock toggle */}
      <label className="flex items-center justify-between cursor-pointer">
        <span className="text-sm font-medium text-gray-700">Только в наличии</span>
        <div className="relative">
          <input
            type="checkbox"
            checked={filters.in_stock || false}
            onChange={(e) => onFilterChange('in_stock', e.target.checked || undefined)}
            className="sr-only peer"
          />
          <div className="block w-10 h-6 bg-gray-200 peer-checked:bg-primary-500 rounded-full cursor-pointer transition-colors" />
          <div className="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-sm peer-checked:translate-x-4 transition-transform cursor-pointer" />
        </div>
      </label>
    </>
  );
}

function isLengthSelected(
  length: number,
  lengthMin: number | undefined,
  lengthMax: number | undefined
): boolean {
  if (length >= 80) {
    return lengthMin === 80 && lengthMax === undefined;
  }
  return lengthMin === length && lengthMax === length;
}

// ── Mobile Filter Drawer ────────────────────────────────────────────────────
export function MobileFilterDrawer({
  open,
  onClose,
  filters,
  onFilterChange,
  onReset,
  totalCount,
}: {
  open: boolean;
  onClose: () => void;
  filters: FilterSidebarProps['filters'];
  onFilterChange: FilterSidebarProps['onFilterChange'];
  onReset: () => void;
  totalCount: number;
}) {
  return (
    <>
      {/* Overlay */}
      <div
        className={`fixed inset-0 bg-black/40 z-50 transition-opacity duration-300 ${
          open ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        className={`fixed bottom-0 left-0 right-0 z-50 bg-white rounded-t-3xl shadow-2xl max-h-[85vh] overflow-y-auto transition-transform duration-300 ${
          open ? 'translate-y-0' : 'translate-y-full'
        }`}
      >
        {/* Handle */}
        <div className="sticky top-0 bg-white rounded-t-3xl pt-3 pb-2 px-6 border-b border-gray-100 z-10">
          <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-3" />
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Фильтры</h3>
            <button onClick={onClose} className="p-2 rounded-lg hover:bg-gray-100 transition-colors">
              <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          <FilterSections filters={filters} onFilterChange={onFilterChange} />
        </div>

        {/* Bottom actions */}
        <div className="sticky bottom-0 bg-white border-t border-gray-100 p-4 flex gap-3">
          <button
            onClick={onReset}
            className="flex-1 py-3 border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Сбросить
          </button>
          <button
            onClick={onClose}
            className="flex-1 py-3 bg-primary-500 hover:bg-primary-600 text-white rounded-xl text-sm font-medium transition-colors"
          >
            Показать {totalCount} товаров
          </button>
        </div>
      </div>
    </>
  );
}
