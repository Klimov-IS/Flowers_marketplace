import { useState, useRef, useEffect } from 'react';

interface EditableColorSelectProps {
  value: string[];
  onSave: (colors: string[]) => Promise<void>;
  className?: string;
  disabled?: boolean;
}

// Colors with their display names and hex codes for preview
const COLOR_OPTIONS = [
  { value: 'белый', label: 'Белый', hex: '#FFFFFF', border: true },
  { value: 'кремовый', label: 'Кремовый', hex: '#FFFDD0' },
  { value: 'желтый', label: 'Желтый', hex: '#FFD700' },
  { value: 'оранжевый', label: 'Оранжевый', hex: '#FF8C00' },
  { value: 'персиковый', label: 'Персиковый', hex: '#FFDAB9' },
  { value: 'коралловый', label: 'Коралловый', hex: '#FF7F50' },
  { value: 'розовый', label: 'Розовый', hex: '#FFB6C1' },
  { value: 'пудровый', label: 'Пудровый', hex: '#E8CCD7' },
  { value: 'красный', label: 'Красный', hex: '#DC143C' },
  { value: 'бордовый', label: 'Бордовый', hex: '#8B0000' },
  { value: 'лавандовый', label: 'Лавандовый', hex: '#E6E6FA' },
  { value: 'сиреневый', label: 'Сиреневый', hex: '#C8A2C8' },
  { value: 'лиловый', label: 'Лиловый', hex: '#B666D2' },
  { value: 'фиолетовый', label: 'Фиолетовый', hex: '#8B008B' },
  { value: 'синий', label: 'Синий', hex: '#4169E1' },
  { value: 'зеленый', label: 'Зеленый', hex: '#228B22' },
  { value: 'биколор', label: 'Биколор', hex: 'linear-gradient(135deg, #FFB6C1 50%, #FFFFFF 50%)' },
  { value: 'микс', label: 'Микс', hex: 'linear-gradient(135deg, #FF6B6B, #4ECDC4, #45B7D1, #96CEB4)' },
];

export default function EditableColorSelect({
  value = [],
  onSave,
  className = '',
  disabled = false,
}: EditableColorSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedColors, setSelectedColors] = useState<string[]>(value);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSelectedColors(value);
  }, [value]);

  useEffect(() => {
    if (saveStatus !== 'idle') {
      const timer = setTimeout(() => setSaveStatus('idle'), 1500);
      return () => clearTimeout(timer);
    }
  }, [saveStatus]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        if (isOpen) {
          handleSave();
        }
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen, selectedColors]);

  const handleSave = async () => {
    setIsOpen(false);

    // Check if changed
    const sortedNew = [...selectedColors].sort();
    const sortedOld = [...value].sort();
    if (JSON.stringify(sortedNew) === JSON.stringify(sortedOld)) {
      return;
    }

    setIsSaving(true);
    try {
      await onSave(selectedColors);
      setSaveStatus('success');
    } catch {
      setSaveStatus('error');
      setSelectedColors(value); // Revert on error
    } finally {
      setIsSaving(false);
    }
  };

  const toggleColor = (color: string) => {
    setSelectedColors((prev) => {
      if (prev.includes(color)) {
        return prev.filter((c) => c !== color);
      } else {
        return [...prev, color];
      }
    });
  };

  const getColorStyle = (option: (typeof COLOR_OPTIONS)[0]) => {
    if (option.hex.startsWith('linear')) {
      return { background: option.hex };
    }
    return { backgroundColor: option.hex };
  };

  // Display selected colors as small squares
  const renderSelectedColors = () => {
    if (selectedColors.length === 0) {
      return <span className="text-gray-400">—</span>;
    }

    return (
      <div className="flex gap-0.5 flex-wrap">
        {selectedColors.map((color) => {
          const option = COLOR_OPTIONS.find((o) => o.value === color);
          if (!option) return null;
          return (
            <div
              key={color}
              className={`w-4 h-4 rounded ${option.border ? 'border border-gray-300' : ''}`}
              style={getColorStyle(option)}
              title={option.label}
            />
          );
        })}
      </div>
    );
  };

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div
        onClick={() => !disabled && !isSaving && setIsOpen(!isOpen)}
        className={`px-2 py-1 rounded cursor-pointer transition-all group flex items-center gap-1 ${
          disabled || isSaving ? 'cursor-default' : 'hover:bg-gray-100'
        }`}
      >
        {renderSelectedColors()}

        {!disabled && !isSaving && (
          <span className="ml-1 text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity">
            ✎
          </span>
        )}

        {isSaving && (
          <div className="w-3 h-3 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
        )}

        {saveStatus === 'success' && (
          <span className="text-green-500 text-xs">✓</span>
        )}
        {saveStatus === 'error' && (
          <span className="text-red-500 text-xs">✗</span>
        )}
      </div>

      {isOpen && (
        <div className="absolute z-20 top-full left-0 mt-1 min-w-[200px] bg-white border border-gray-200 rounded-lg shadow-lg p-2">
          <div className="text-xs text-gray-500 mb-2 px-1">Выберите цвета:</div>
          <div className="grid grid-cols-3 gap-1">
            {COLOR_OPTIONS.map((option) => (
              <div
                key={option.value}
                onClick={() => toggleColor(option.value)}
                className={`flex items-center gap-1.5 px-2 py-1.5 rounded cursor-pointer text-sm transition-colors ${
                  selectedColors.includes(option.value)
                    ? 'bg-primary-50 ring-1 ring-primary-300'
                    : 'hover:bg-gray-100'
                }`}
              >
                <div
                  className={`w-4 h-4 rounded flex-shrink-0 ${option.border ? 'border border-gray-300' : ''}`}
                  style={getColorStyle(option)}
                />
                <span className="text-xs truncate">{option.label}</span>
              </div>
            ))}
          </div>
          <div className="mt-2 pt-2 border-t border-gray-100 flex justify-between items-center">
            <button
              onClick={() => setSelectedColors([])}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              Очистить
            </button>
            <button
              onClick={handleSave}
              className="px-3 py-1 text-xs bg-primary-500 text-white rounded hover:bg-primary-600"
            >
              Готово
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
