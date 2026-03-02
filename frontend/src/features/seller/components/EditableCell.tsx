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

  // Sync external value changes
  useEffect(() => {
    if (!isFocused) {
      setEditValue(value?.toString() ?? '');
    }
  }, [value, isFocused]);

  // Clear save status after delay
  useEffect(() => {
    if (saveStatus !== 'idle') {
      const timer = setTimeout(() => setSaveStatus('idle'), 1500);
      return () => clearTimeout(timer);
    }
  }, [saveStatus]);

  const handleFocus = () => {
    if (disabled) return;
    setIsFocused(true);
    // Select all text on focus
    setTimeout(() => inputRef.current?.select(), 0);
  };

  const handleSave = async () => {
    setIsFocused(false);

    if (editValue === (value?.toString() ?? '')) {
      return; // No change
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
      inputRef.current?.blur(); // triggers handleSave via onBlur
    } else if (e.key === 'Escape') {
      setEditValue(value?.toString() ?? '');
      setIsFocused(false);
      inputRef.current?.blur();
    }
  };

  const isEmpty = value === null || value === undefined || value === '';

  // Status ring color
  const ringClass = saveStatus === 'success'
    ? 'ring-1 ring-green-400'
    : saveStatus === 'error'
      ? 'ring-1 ring-red-400'
      : isFocused
        ? 'ring-1 ring-primary-400 border-primary-400'
        : '';

  return (
    <div className={`relative ${className}`}>
      <input
        ref={inputRef}
        type={type}
        value={isFocused ? editValue : (isEmpty ? '' : (value?.toString() ?? ''))}
        placeholder={isFocused ? '' : placeholder}
        onChange={(e) => setEditValue(e.target.value)}
        onFocus={handleFocus}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        disabled={disabled || isSaving}
        min={type === 'number' ? 0 : undefined}
        step={type === 'number' ? 'any' : undefined}
        className={`w-full px-2 py-1 text-sm bg-transparent border border-transparent rounded-lg
          transition-all outline-none
          ${!disabled && !isSaving ? 'hover:border-gray-200 hover:bg-gray-50' : ''}
          ${ringClass}
          ${isSaving ? 'opacity-60' : ''}
          ${isEmpty && !isFocused ? 'text-gray-400' : 'text-gray-900'}
        `}
      />
      {/* Suffix display (only when not focused and has value) */}
      {!isFocused && !isEmpty && suffix && (
        <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-400 pointer-events-none">
          {suffix.trim()}
        </span>
      )}
      {/* Saving spinner */}
      {isSaving && (
        <div className="absolute right-2 top-1/2 -translate-y-1/2">
          <div className="w-3 h-3 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}
    </div>
  );
}
