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
} from '../supplierApi';
import { useAppSelector } from '../../../hooks/useAppSelector';
import type { FlatOfferVariant } from '../../../types/supplierItem';
import { getFlowerImage, getDefaultFlowerImage } from '../../../utils/flowerImages';

interface ProductDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** The variant that was clicked to open the modal */
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

export default function ProductDetailModal({
  isOpen,
  onClose,
  variant,
}: ProductDetailModalProps) {
  const user = useAppSelector((state) => state.auth.user);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);

  // Fetch all variants of this item
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

  const allVariants = variantsData?.items || [];
  // Use first variant data as item-level data (it's duplicated across all variants)
  const itemData = allVariants.length > 0 ? allVariants[0] : variant;

  const handleUpdateItem = async (field: string, value: ItemUpdateValue) => {
    const data: Record<string, unknown> = {};
    data[field] = value;
    await updateSupplierItem({ id: variant.item_id, data }).unwrap();
  };

  const handleUpdateVariant = async (
    variantId: string,
    field: string,
    value: string | number | null
  ) => {
    const data: Record<string, unknown> = {};
    data[field] = value;
    await updateOfferCandidate({ id: variantId, data }).unwrap();
  };

  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Show preview immediately
    const reader = new FileReader();
    reader.onload = (ev) => setPhotoPreview(ev.target?.result as string);
    reader.readAsDataURL(file);

    try {
      await uploadPhoto({ itemId: variant.item_id, file }).unwrap();
    } catch (error) {
      console.error('Failed to upload photo:', error);
      setPhotoPreview(null);
    }
  };

  // Determine the photo to show
  const photoUrl = photoPreview || itemData.photo_url;
  const fallbackImage = getFlowerImage(itemData.flower_type);

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <div className="flex items-start justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          {itemData.flower_type
            ? `${itemData.flower_type}${itemData.subtype ? ` ${itemData.subtype.toLowerCase()}` : ''}`
            : itemData.raw_name}
        </h3>
        <button
          onClick={onClose}
          className="p-1 text-gray-400 hover:text-gray-600 rounded"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="flex gap-6">
        {/* Left: Photo */}
        <div className="flex-shrink-0 w-48">
          <div
            className="relative group w-48 h-48 rounded-lg overflow-hidden bg-gray-100 border border-gray-200 cursor-pointer"
            onClick={() => fileInputRef.current?.click()}
          >
            <img
              src={photoUrl || fallbackImage}
              alt={itemData.flower_type || 'Фото товара'}
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.target as HTMLImageElement).src = getDefaultFlowerImage();
              }}
            />
            {/* Upload overlay */}
            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              {isUploading ? (
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white" />
              ) : (
                <div className="text-white text-center">
                  <svg className="w-8 h-8 mx-auto mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span className="text-xs">Загрузить фото</span>
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
          {!photoUrl && (
            <p className="text-xs text-gray-400 mt-2 text-center">
              Нажмите чтобы загрузить фото
            </p>
          )}
        </div>

        {/* Right: Item-level fields */}
        <div className="flex-1 min-w-0">
          <div className="grid grid-cols-2 gap-4">
            {/* Сорт */}
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

            {/* Страна */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Страна</label>
              <EditableSelect
                value={itemData.origin_country}
                options={COUNTRY_OPTIONS}
                onSave={async (val) => handleUpdateItem('origin_country', val)}
              />
            </div>

            {/* Цвета */}
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-500 mb-1">Цвета</label>
              <EditableColorSelect
                value={itemData.colors || []}
                onSave={async (colors) => handleUpdateItem('colors', colors)}
              />
            </div>

            {/* Raw name */}
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-500 mb-1">Исходное название</label>
              <p className="text-xs font-mono text-gray-500 bg-gray-50 px-2 py-1.5 rounded truncate" title={itemData.raw_name}>
                {itemData.raw_name}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Variants table */}
      <div className="mt-6">
        <h4 className="text-sm font-medium text-gray-700 mb-3">
          Варианты ({allVariants.length})
        </h4>
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr className="text-left text-xs text-gray-500">
                <th className="px-3 py-2 font-medium">Размер</th>
                <th className="px-3 py-2 font-medium">Упаковка</th>
                <th className="px-3 py-2 font-medium">Кол-во</th>
                <th className="px-3 py-2 font-medium">Цена</th>
                <th className="px-3 py-2 font-medium">Остаток</th>
                <th className="px-3 py-2 font-medium">Валидация</th>
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
                  <td className="px-3 py-2">
                    <EditableCell
                      value={v.stock}
                      type="number"
                      placeholder="—"
                      onSave={async (val) => handleUpdateVariant(v.variant_id, 'stock_qty', val)}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <ValidationBadge status={v.validation} />
                  </td>
                </tr>
              ))}
              {allVariants.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-4 text-center text-gray-400 text-sm">
                    Загрузка вариантов...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-4 flex justify-end">
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Закрыть
        </button>
      </div>
    </Modal>
  );
}

function ValidationBadge({ status }: { status: string }) {
  if (status === 'ok') {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-green-700 bg-green-50 px-1.5 py-0.5 rounded">
        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
        OK
      </span>
    );
  }
  if (status === 'warn') {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-yellow-700 bg-yellow-50 px-1.5 py-0.5 rounded">
        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
        Внимание
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs text-red-700 bg-red-50 px-1.5 py-0.5 rounded">
      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
      </svg>
      Ошибка
    </span>
  );
}
