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
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState<string>(value?.toString() ?? '');
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  useEffect(() => {
    setEditValue(value?.toString() ?? '');
  }, [value]);

  useEffect(() => {
    if (saveStatus !== 'idle') {
      const timer = setTimeout(() => setSaveStatus('idle'), 1500);
      return () => clearTimeout(timer);
    }
  }, [saveStatus]);

  const handleClick = () => {
    if (!disabled && !isEditing) {
      setIsEditing(true);
    }
  };

  const handleSave = async () => {
    if (editValue === (value?.toString() ?? '')) {
      setIsEditing(false);
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
      setIsEditing(false);
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
      handleSave();
    } else if (e.key === 'Escape') {
      setEditValue(value?.toString() ?? '');
      setIsEditing(false);
    }
  };

  const handleBlur = () => {
    handleSave();
  };

  const displayValue = value !== null && value !== undefined ? `${value}${suffix}` : placeholder;

  if (isEditing) {
    return (
      <div className="relative">
        <input
          ref={inputRef}
          type={type}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          disabled={isSaving}
          className={`w-full px-2 py-1 text-sm border border-primary-500 rounded focus:outline-none focus:ring-1 focus:ring-primary-500 ${
            isSaving ? 'bg-gray-100' : 'bg-white'
          } ${className}`}
          min={type === 'number' ? 0 : undefined}
          step={type === 'number' ? 'any' : undefined}
        />
        {isSaving && (
          <div className="absolute right-2 top-1/2 -translate-y-1/2">
            <div className="w-3 h-3 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      onClick={handleClick}
      className={`px-2 py-1 rounded cursor-pointer transition-all group relative ${
        disabled ? 'cursor-default' : 'hover:bg-gray-100'
      } ${className}`}
    >
      <span className={value === null || value === undefined ? 'text-gray-400' : ''}>
        {displayValue}
      </span>

      {!disabled && (
        <span className="ml-1 text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity">
          ✎
        </span>
      )}

      {saveStatus === 'success' && (
        <span className="absolute -right-1 -top-1 text-green-500 text-xs">✓</span>
      )}
      {saveStatus === 'error' && (
        <span className="absolute -right-1 -top-1 text-red-500 text-xs">✗</span>
      )}
    </div>
  );
}
