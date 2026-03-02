import { useState, useRef, useEffect } from 'react';

interface EditableCellProps {
  value: string | number | null | undefined;
  type?: 'text' | 'number';
  suffix?: string;
  placeholder?: string;
  onSave: (value: string | number | null) => Promise<void>;
  className?: string;
  disabled?: boolean;
}

export default function EditableCell({
  value,
  type = 'text',
  suffix = '',
  placeholder = '—',
  onSave,
  className = '',
  disabled = false,
}: EditableCellProps) {
  const [isFocused, setIsFocused] = useState(false);
  const [editValue, setEditValue] = useState<string>(value?.toString() ?? '');
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isFocused) {
      setEditValue(value?.toString() ?? '');
    }
  }, [value, isFocused]);

  useEffect(() => {
    if (saveStatus !== 'idle') {
      const timer = setTimeout(() => setSaveStatus('idle'), 1500);
      return () => clearTimeout(timer);
    }
  }, [saveStatus]);

  const handleFocus = () => {
    if (disabled) return;
    setIsFocused(true);
    setTimeout(() => inputRef.current?.select(), 0);
  };

  const handleSave = async () => {
    setIsFocused(false);

    if (editValue === (value?.toString() ?? '')) {
      return;
    }

    setIsSaving(true);
    try {
      let saveValue: string | number | null;
      if (type === 'number') {
        saveValue = editValue === '' ? null : parseFloat(editValue);
        if (saveValue !== null && isNaN(saveValue)) {
          throw new Error('Invalid number');
        }
      } else {
        saveValue = editValue || null;
      }
      await onSave(saveValue);
      setSaveStatus('success');
    } catch {
      setSaveStatus('error');
      setEditValue(value?.toString() ?? '');
    } finally {
      setIsSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      inputRef.current?.blur();
    } else if (e.key === 'Escape') {
      setEditValue(value?.toString() ?? '');
      setIsFocused(false);
      inputRef.current?.blur();
    }
  };

  // For number type: filter out non-numeric characters
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (type === 'number') {
      // Allow digits, dot, comma, minus
      const raw = e.target.value.replace(',', '.');
      if (raw === '' || raw === '-' || /^-?\d*\.?\d*$/.test(raw)) {
        setEditValue(raw);
      }
    } else {
      setEditValue(e.target.value);
    }
  };

  const isEmpty = value === null || value === undefined || value === '';

  const ringClass = saveStatus === 'success'
    ? 'ring-1 ring-green-400'
    : saveStatus === 'error'
      ? 'ring-1 ring-red-400'
      : isFocused
        ? 'ring-1 ring-primary-400 border-primary-400'
        : '';

  // Display value with suffix when not focused
  const displayValue = isEmpty ? '' : (value?.toString() ?? '');

  return (
    <div className={`relative ${className}`}>
      <input
        ref={inputRef}
        type="text"
        inputMode={type === 'number' ? 'decimal' : 'text'}
        value={isFocused ? editValue : displayValue}
        placeholder={isFocused ? '' : placeholder}
        onChange={handleChange}
        onFocus={handleFocus}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        disabled={disabled || isSaving}
        className={`w-full px-2 py-1 text-sm bg-transparent border border-transparent rounded-lg
          transition-all outline-none
          ${!disabled && !isSaving ? 'hover:border-gray-200 hover:bg-gray-50' : ''}
          ${ringClass}
          ${isSaving ? 'opacity-60' : ''}
          ${isEmpty && !isFocused ? 'text-gray-400' : 'text-gray-900'}
          ${suffix ? 'pr-8' : ''}
        `}
      />
      {/* Suffix — always visible when value exists */}
      {!isEmpty && suffix && (
        <span className={`absolute right-2 top-1/2 -translate-y-1/2 text-xs pointer-events-none ${
          isFocused ? 'text-gray-300' : 'text-gray-400'
        }`}>
          {suffix.trim()}
        </span>
      )}
      {isSaving && (
        <div className="absolute right-2 top-1/2 -translate-y-1/2">
          <div className="w-3 h-3 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}
    </div>
  );
}
