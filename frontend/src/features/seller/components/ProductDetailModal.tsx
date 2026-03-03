import { useRef, useState } from 'react';
import Modal from '../../../components/ui/Modal';
import EditableCell from './EditableCell';
import EditableSelect from './EditableSelect';
import EditableColorSelect from './EditableColorSelect';
import {
  useGetFlatItemsQuery,
  useUpdateSupplierItemMutation,
  useUpdateOfferCandidateMutation,
  useUploadItemPhotoMutation,
  useHideSupplierItemMutation,
  useRestoreSupplierItemMutation,
  useDuplicateSupplierItemMutation,
} from '../supplierApi';
import { useAppSelector } from '../../../hooks/useAppSelector';
import { useToast } from '../../../components/ui/Toast';
import type { FlatOfferVariant } from '../../../types/supplierItem';
import { getFlowerImage, getDefaultFlowerImage } from '../../../utils/flowerImages';

function resolvePhotoUrl(url: string): string {
  const basePath = (import.meta.env.BASE_URL || '/').replace(/\/$/, '');
  let resolved = url;
  if (basePath && url.startsWith('/uploads')) {
    resolved = basePath + url;
  }
  const sep = resolved.includes('?') ? '&' : '?';
  return `${resolved}${sep}v=${Date.now()}`;
}

interface ProductDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  variant: FlatOfferVariant;
}

const COUNTRY_OPTIONS = [
  { value: null, label: '—' },
  { value: 'Эквадор', label: 'Эквадор' },
  { value: 'Колумбия', label: 'Колумбия' },
  { value: 'Нидерланды', label: 'Нидерланды' },
  { value: 'Кения', label: 'Кения' },
  { value: 'Израиль', label: 'Израиль' },
  { value: 'Россия', label: 'Россия' },
  { value: 'Эфиопия', label: 'Эфиопия' },
  { value: 'Италия', label: 'Италия' },
];

const PACK_TYPE_OPTIONS = [
  { value: null, label: '—' },
  { value: 'бак', label: 'Бак' },
  { value: 'упак', label: 'Упаковка' },
  { value: 'шт', label: 'Штука' },
];

type ItemUpdateValue = string | number | string[] | null;

// ── Toggle Switch ─────────────────────────────────────────────────────────────
function ToggleSwitch({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (val: boolean) => Promise<void>;
  disabled?: boolean;
}) {
  const [loading, setLoading] = useState(false);

  const handleToggle = async () => {
    if (disabled || loading) return;
    setLoading(true);
    try {
      await onChange(!checked);
    } catch (err) {
      console.error('Toggle failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={handleToggle}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
        checked ? 'bg-primary-500' : 'bg-gray-300'
      } ${disabled || loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow-sm transition-transform ${
          checked ? 'translate-x-[18px]' : 'translate-x-[3px]'
        }`}
      />
      {loading && (
        <span className="absolute inset-0 flex items-center justify-center">
          <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
        </span>
      )}
    </button>
  );
}

// ── Status Badge ──────────────────────────────────────────────────────────────
const STATUS_CONFIG: Record<string, { label: string; cls: string }> = {
  active: { label: 'Активен', cls: 'bg-green-100 text-green-700' },
  ambiguous: { label: 'Модерация', cls: 'bg-yellow-100 text-yellow-700' },
  hidden: { label: 'Скрыто', cls: 'bg-gray-100 text-gray-500' },
};

function StatusBadge({
  status,
  onHide,
  onRestore,
}: {
  status: string;
  onHide: () => void;
  onRestore: () => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const cfg = STATUS_CONFIG[status] || { label: status, cls: 'bg-gray-100 text-gray-600' };
  const canToggle = status === 'active' || status === 'hidden' || status === 'ambiguous';

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => canToggle && setIsOpen(!isOpen)}
        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium transition-all ${cfg.cls} ${
          canToggle ? 'cursor-pointer hover:ring-1 hover:ring-gray-300' : 'cursor-default'
        }`}
      >
        {cfg.label}
        {canToggle && (
          <svg className="w-3 h-3 opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-1 z-50 min-w-[150px] bg-white border border-gray-200 rounded-xl shadow-lg py-1">
          {status === 'active' && (
            <button
              type="button"
              onClick={() => { setIsOpen(false); onHide(); }}
              className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
            >
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
              </svg>
              Скрыть
            </button>
          )}
          {(status === 'hidden' || status === 'ambiguous') && (
            <button
              type="button"
              onClick={() => { setIsOpen(false); onRestore(); }}
              className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
            >
              <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              Восстановить
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main Modal ────────────────────────────────────────────────────────────────
export default function ProductDetailModal({
  isOpen,
  onClose,
  variant,
}: ProductDetailModalProps) {
  const user = useAppSelector((state) => state.auth.user);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const { showToast } = useToast();

  const { data: variantsData } = useGetFlatItemsQuery(
    {
      supplier_id: user?.id || '',
      item_id: variant.item_id,
      per_page: 100,
      status: ['active', 'hidden'],
    },
    { skip: !isOpen || !user?.id }
  );

  const [updateSupplierItem] = useUpdateSupplierItemMutation();
  const [updateOfferCandidate] = useUpdateOfferCandidateMutation();
  const [uploadPhoto, { isLoading: isUploading }] = useUploadItemPhotoMutation();
  const [hideSupplierItem] = useHideSupplierItemMutation();
  const [restoreSupplierItem] = useRestoreSupplierItemMutation();
  const [duplicateSupplierItem] = useDuplicateSupplierItemMutation();

  const allVariants = variantsData?.items || [];
  const itemData = allVariants.length > 0 ? allVariants[0] : variant;
  // Use fresh variant data from refetched query instead of stale prop
  const currentVariant = allVariants.find(v => v.variant_id === variant.variant_id) || variant;

  const handleUpdateItem = async (field: string, value: ItemUpdateValue) => {
    try {
      const data: Record<string, unknown> = {};
      data[field] = value;
      await updateSupplierItem({ id: variant.item_id, data }).unwrap();
    } catch (err) {
      console.error('Failed to update item:', field, value, err);
      showToast('Ошибка сохранения', 'error');
      throw err;
    }
  };

  const handleUpdateVariant = async (
    variantId: string,
    field: string,
    value: string | number | null
  ) => {
    try {
      const data: Record<string, unknown> = {};
      data[field] = value;
      await updateOfferCandidate({ id: variantId, data }).unwrap();
    } catch (err) {
      console.error('Failed to update variant:', variantId, field, value, err);
      showToast('Ошибка сохранения', 'error');
      throw err;
    }
  };

  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadStatus('idle');

    // Show local preview immediately
    const reader = new FileReader();
    reader.onload = (ev) => setPhotoPreview(ev.target?.result as string);
    reader.readAsDataURL(file);

    try {
      const result = await uploadPhoto({ itemId: variant.item_id, file }).unwrap();
      console.log('Photo uploaded:', result);
      setUploadStatus('success');
      showToast('Фото обновлено', 'success');
      setTimeout(() => setUploadStatus('idle'), 2000);
    } catch (err) {
      console.error('Photo upload failed:', err);
      setPhotoPreview(null);
      setUploadStatus('error');
      showToast('Ошибка загрузки фото', 'error');
      setTimeout(() => setUploadStatus('idle'), 3000);
    }

    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleHide = async () => {
    try {
      await hideSupplierItem(variant.item_id).unwrap();
      showToast('Позиция скрыта', 'success');
    } catch {
      showToast('Ошибка при скрытии', 'error');
    }
  };

  const handleRestore = async () => {
    try {
      await restoreSupplierItem(variant.item_id).unwrap();
      showToast('Позиция восстановлена', 'success');
    } catch {
      showToast('Ошибка при восстановлении', 'error');
    }
  };

  const handleDuplicate = async () => {
    try {
      await duplicateSupplierItem(variant.item_id).unwrap();
      showToast('Карточка дублирована', 'success');
      onClose();
    } catch {
      showToast('Ошибка при дублировании', 'error');
    }
  };

  const savedPhotoUrl = itemData.photo_url ? resolvePhotoUrl(itemData.photo_url) : null;
  const photoUrl = photoPreview || savedPhotoUrl;
  const fallbackImage = getFlowerImage(itemData.flower_type);

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      {/* Header: name + status badge */}
      <div className="flex items-start justify-between gap-4 mb-5">
        <div className="flex-1 min-w-0">
          <EditableCell
            value={itemData.raw_name}
            type="text"
            placeholder="Название товара"
            onSave={async (val) => {
              if (val) await handleUpdateItem('raw_name', val as string);
            }}
            className="text-lg font-semibold text-gray-900"
          />
          <div className="flex items-center gap-2 text-xs text-gray-400 mt-1 px-2">
            <span className="font-mono">{variant.item_id.slice(0, 8)}</span>
            {itemData.flower_type && (
              <>
                <span>&middot;</span>
                <span>{itemData.flower_type}{itemData.subtype ? ` ${itemData.subtype.toLowerCase()}` : ''}</span>
              </>
            )}
          </div>
        </div>
        <StatusBadge
          status={itemData.item_status}
          onHide={handleHide}
          onRestore={handleRestore}
        />
      </div>

      {/* Photo + fields row */}
      <div className="flex gap-6">
        {/* Photo */}
        <div className="flex-shrink-0">
          <div
            className="relative group w-60 h-60 rounded-2xl overflow-hidden bg-gray-100 border border-gray-200 cursor-pointer"
            onClick={() => fileInputRef.current?.click()}
          >
            <img
              src={photoUrl || fallbackImage}
              alt={itemData.raw_name}
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.target as HTMLImageElement).src = getDefaultFlowerImage();
              }}
            />
            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              {isUploading ? (
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white" />
              ) : (
                <div className="text-white text-center">
                  <svg className="w-8 h-8 mx-auto mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span className="text-xs font-medium">Загрузить фото</span>
                </div>
              )}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={handlePhotoUpload}
            />
          </div>
          {uploadStatus === 'success' && (
            <p className="text-xs text-green-600 mt-2 text-center flex items-center justify-center gap-1">
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Фото сохранено
            </p>
          )}
          {uploadStatus === 'error' && (
            <p className="text-xs text-red-600 mt-2 text-center">Ошибка загрузки</p>
          )}
        </div>

        {/* Fields */}
        <div className="flex-1 min-w-0 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Сорт</label>
            <EditableCell
              value={itemData.variety || ''}
              type="text"
              placeholder="Не указан"
              onSave={async (val) => handleUpdateItem('variety', val)}
              className="text-sm font-medium text-gray-900"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Страна</label>
            <EditableSelect
              value={itemData.origin_country}
              options={COUNTRY_OPTIONS}
              onSave={async (val) => handleUpdateItem('origin_country', val)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Цвета</label>
            <EditableColorSelect
              value={itemData.colors || []}
              onSave={async (colors) => handleUpdateItem('colors', colors)}
            />
          </div>
        </div>
      </div>

      {/* Characteristics section */}
      <div className="mt-6">
        <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Характеристики
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 bg-gray-50 rounded-xl p-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Длина</label>
            <EditableCell
              value={currentVariant.length_cm}
              type="number"
              placeholder="—"
              suffix=" см"
              onSave={async (val) => handleUpdateVariant(currentVariant.variant_id, 'length_cm', val)}
              className="text-sm font-medium"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Цена</label>
            <EditableCell
              value={currentVariant.price ? parseFloat(currentVariant.price) : null}
              type="number"
              placeholder="—"
              suffix=" ₽"
              onSave={async (val) => handleUpdateVariant(currentVariant.variant_id, 'price_min', val)}
              className="text-sm font-semibold"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Упаковка</label>
            <EditableSelect
              value={currentVariant.pack_type}
              options={PACK_TYPE_OPTIONS}
              onSave={async (val) => handleUpdateVariant(currentVariant.variant_id, 'pack_type', val)}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Кол-во в уп.</label>
            <EditableCell
              value={currentVariant.pack_qty}
              type="number"
              placeholder="—"
              onSave={async (val) => handleUpdateVariant(currentVariant.variant_id, 'pack_qty', val)}
              className="text-sm font-medium"
            />
          </div>
        </div>

        {/* Stock toggle */}
        <div className="flex items-center gap-3 mt-4 px-1">
          <ToggleSwitch
            checked={(currentVariant.stock ?? 0) > 0}
            onChange={async (val) => {
              await handleUpdateVariant(currentVariant.variant_id, 'stock_qty', val ? 999 : 0);
            }}
          />
          <span className="text-sm text-gray-700">
            {(currentVariant.stock ?? 0) > 0 ? 'Есть в наличии' : 'Нет в наличии'}
          </span>
        </div>
      </div>

      {/* Variants table (only if multiple) */}
      {allVariants.length > 1 && (
        <div className="mt-6">
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Все варианты ({allVariants.length})
          </h4>
          <div className="border border-gray-200 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr className="text-left text-xs text-gray-500">
                  <th className="px-3 py-2 font-medium">Размер</th>
                  <th className="px-3 py-2 font-medium">Упаковка</th>
                  <th className="px-3 py-2 font-medium">Кол-во</th>
                  <th className="px-3 py-2 font-medium">Цена</th>
                  <th className="px-3 py-2 font-medium text-center">Наличие</th>
                </tr>
              </thead>
              <tbody>
                {allVariants.map((v) => (
                  <tr
                    key={v.variant_id}
                    className={`border-b border-gray-100 hover:bg-gray-50 ${
                      v.variant_id === variant.variant_id ? 'bg-primary-50/50' : ''
                    }`}
                  >
                    <td className="px-3 py-2">
                      <EditableCell
                        value={v.length_cm}
                        type="number"
                        placeholder="—"
                        suffix=" см"
                        onSave={async (val) => handleUpdateVariant(v.variant_id, 'length_cm', val)}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <EditableSelect
                        value={v.pack_type}
                        options={PACK_TYPE_OPTIONS}
                        onSave={async (val) => handleUpdateVariant(v.variant_id, 'pack_type', val)}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <EditableCell
                        value={v.pack_qty}
                        type="number"
                        placeholder="—"
                        onSave={async (val) => handleUpdateVariant(v.variant_id, 'pack_qty', val)}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <EditableCell
                        value={v.price ? parseFloat(v.price) : null}
                        type="number"
                        placeholder="—"
                        suffix=" ₽"
                        onSave={async (val) => handleUpdateVariant(v.variant_id, 'price_min', val)}
                        className="font-medium"
                      />
                    </td>
                    <td className="px-3 py-2 text-center">
                      <ToggleSwitch
                        checked={(v.stock ?? 0) > 0}
                        onChange={async (val) => {
                          await handleUpdateVariant(v.variant_id, 'stock_qty', val ? 999 : 0);
                        }}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-6 flex justify-end gap-3 pt-4 border-t border-gray-100">
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
        >
          Закрыть
        </button>
        <button
          onClick={handleDuplicate}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-primary-700 bg-primary-50 border border-primary-200 rounded-xl hover:bg-primary-100 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          Дублировать
        </button>
      </div>
    </Modal>
  );
}
