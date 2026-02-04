import { useState, useRef, useEffect } from 'react';

interface Option {
  value: string | null;
  label: string;
}

interface EditableSelectProps {
  value: string | null | undefined;
  options: Option[];
  placeholder?: string;
  onSave: (value: string | null) => Promise<void>;
  className?: string;
  disabled?: boolean;
}

export default function EditableSelect({
  value,
  options,
  placeholder = '—',
  onSave,
  className = '',
  disabled = false,
}: EditableSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (saveStatus !== 'idle') {
      const timer = setTimeout(() => setSaveStatus('idle'), 1500);
      return () => clearTimeout(timer);
    }
  }, [saveStatus]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const handleSelect = async (newValue: string | null) => {
    if (newValue === value) {
      setIsOpen(false);
      return;
    }

    setIsSaving(true);
    setIsOpen(false);
    try {
      await onSave(newValue);
      setSaveStatus('success');
    } catch {
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  };

  const currentOption = options.find((opt) => opt.value === value);
  const displayValue = currentOption?.label || placeholder;

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div
        onClick={() => !disabled && !isSaving && setIsOpen(!isOpen)}
        className={`px-2 py-1 rounded cursor-pointer transition-all group flex items-center gap-1 ${
          disabled || isSaving ? 'cursor-default' : 'hover:bg-gray-100'
        }`}
      >
        <span className={!currentOption?.value ? 'text-gray-400' : ''}>
          {displayValue}
        </span>

        {!disabled && !isSaving && (
          <svg
            className={`w-3 h-3 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
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
        <div className="absolute z-20 top-full left-0 mt-1 min-w-[120px] bg-white border border-gray-200 rounded-lg shadow-lg py-1">
          {options.map((option) => (
            <div
              key={option.value ?? 'null'}
              onClick={() => handleSelect(option.value)}
              className={`px-3 py-2 cursor-pointer hover:bg-gray-100 text-sm ${
                option.value === value ? 'bg-primary-50 text-primary-700 font-medium' : ''
              }`}
            >
              {option.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
