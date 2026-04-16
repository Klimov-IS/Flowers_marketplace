import { useRef, useState } from 'react';
import Modal from '../../../components/ui/Modal';
import Button from '../../../components/ui/Button';
import { useCreateSupplierItemMutation, useUploadItemPhotoMutation } from '../supplierApi';
import { useToast } from '../../../components/ui/Toast';

interface CreateItemModalProps {
  isOpen: boolean;
  onClose: () => void;
  supplierId: string;
}

export default function CreateItemModal({
  isOpen,
  onClose,
  supplierId,
}: CreateItemModalProps) {
  const [createItem, { isLoading }] = useCreateSupplierItemMutation();
  const [uploadPhoto] = useUploadItemPhotoMutation();
  const { showToast } = useToast();

  const [rawName, setRawName] = useState('');
  const [variety, setVariety] = useState('');
  const [price, setPrice] = useState('');
  const [lengthCm, setLengthCm] = useState('');
  const [color, setColor] = useState('');
  const [packType, setPackType] = useState('');
  const [packQty, setPackQty] = useState('');
  const [stockQty, setStockQty] = useState('');

  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!rawName.trim()) errs.rawName = 'Введите название';
    if (!price.trim() || isNaN(Number(price)) || Number(price) <= 0) {
      errs.price = 'Введите корректную цену';
    }
    if (!variety.trim()) errs.variety = 'Введите сорт';
    if (lengthCm && (isNaN(Number(lengthCm)) || Number(lengthCm) <= 0)) {
      errs.lengthCm = 'Введите корректную длину';
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhotoFile(file);

    const reader = new FileReader();
    reader.onload = (ev) => setPhotoPreview(ev.target?.result as string);
    reader.readAsDataURL(file);
  };

  const handleRemovePhoto = () => {
    setPhotoFile(null);
    setPhotoPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const resetForm = () => {
    setRawName('');
    setVariety('');
    setPrice('');
    setLengthCm('');
    setColor('');
    setPackType('');
    setPackQty('');
    setStockQty('');
    setPhotoFile(null);
    setPhotoPreview(null);
    setErrors({});
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    try {
      const result = await createItem({
        supplier_id: supplierId,
        raw_name: rawName.trim(),
        variety: variety.trim() || undefined,
        price: Number(price),
        length_cm: lengthCm ? Number(lengthCm) : undefined,
        color: color.trim() || undefined,
        pack_type: packType.trim() || undefined,
        pack_qty: packQty ? Number(packQty) : undefined,
        stock_qty: stockQty ? Number(stockQty) : undefined,
      }).unwrap();

      // Upload photo if selected
      if (photoFile && result.item_id) {
        try {
          await uploadPhoto({ itemId: result.item_id, file: photoFile }).unwrap();
        } catch (err) {
          console.error('Photo upload failed:', err);
          showToast('Карточка создана, но фото не загрузилось', 'error');
        }
      }

      resetForm();
      onClose();
    } catch (err) {
      console.error('Failed to create item:', err);
    }
  };

  const handleClose = () => {
    setErrors({});
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Новая карточка товара" size="lg">
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Photo + Name row */}
        <div className="flex gap-5">
          {/* Photo upload */}
          <div className="flex-shrink-0">
            <label className="block text-sm font-medium text-gray-700 mb-1">Фото</label>
            <div
              className="relative group w-28 h-28 rounded-xl overflow-hidden bg-gray-100 border-2 border-dashed border-gray-300 cursor-pointer hover:border-primary-400 transition-colors"
              onClick={() => fileInputRef.current?.click()}
            >
              {photoPreview ? (
                <>
                  <img
                    src={photoPreview}
                    alt="Preview"
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <span className="text-white text-xs font-medium">Заменить</span>
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-gray-400">
                  <svg className="w-6 h-6 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span className="text-xs">Загрузить</span>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={handlePhotoSelect}
              />
            </div>
            {photoPreview && (
              <button
                type="button"
                onClick={handleRemovePhoto}
                className="mt-1 text-xs text-gray-400 hover:text-red-500 transition-colors"
              >
                Удалить
              </button>
            )}
          </div>

          {/* Required fields */}
          <div className="flex-1 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Название *
              </label>
              <input
                type="text"
                value={rawName}
                onChange={(e) => setRawName(e.target.value)}
                placeholder="Роза Freedom"
                className={`w-full px-4 py-2 border rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all ${
                  errors.rawName ? 'border-red-500' : 'border-gray-200'
                }`}
              />
              {errors.rawName && <p className="mt-1 text-sm text-red-600">{errors.rawName}</p>}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Сорт *
                </label>
                <input
                  type="text"
                  value={variety}
                  onChange={(e) => setVariety(e.target.value)}
                  placeholder="Freedom"
                  className={`w-full px-4 py-2 border rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all ${
                    errors.variety ? 'border-red-500' : 'border-gray-200'
                  }`}
                />
                {errors.variety && <p className="mt-1 text-sm text-red-600">{errors.variety}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Цена (₽) *
                </label>
                <input
                  type="number"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder="120"
                  min="0"
                  step="0.01"
                  className={`w-full px-4 py-2 border rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all ${
                    errors.price ? 'border-red-500' : 'border-gray-200'
                  }`}
                />
                {errors.price && <p className="mt-1 text-sm text-red-600">{errors.price}</p>}
              </div>
            </div>
          </div>
        </div>

        {/* Optional fields */}
        <div>
          <p className="text-sm text-gray-500 mb-3">Дополнительные характеристики</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Длина (см)
              </label>
              <input
                type="number"
                value={lengthCm}
                onChange={(e) => setLengthCm(e.target.value)}
                placeholder="60"
                min="1"
                className={`w-full px-4 py-2 border rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all ${
                  errors.lengthCm ? 'border-red-500' : 'border-gray-200'
                }`}
              />
              {errors.lengthCm && <p className="mt-1 text-sm text-red-600">{errors.lengthCm}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Цвет
              </label>
              <input
                type="text"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                placeholder="Красный"
                className="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Упаковка
              </label>
              <input
                type="text"
                value={packType}
                onChange={(e) => setPackType(e.target.value)}
                placeholder="Пучок"
                className="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Кол-во в уп.
              </label>
              <input
                type="number"
                value={packQty}
                onChange={(e) => setPackQty(e.target.value)}
                placeholder="25"
                min="1"
                className="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
              />
            </div>
          </div>
        </div>

        {/* Stock */}
        <div className="w-1/2 sm:w-1/4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Наличие (шт.)
          </label>
          <input
            type="number"
            value={stockQty}
            onChange={(e) => setStockQty(e.target.value)}
            placeholder="100"
            min="0"
            className="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
          />
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-end pt-4 border-t">
          <Button type="button" variant="secondary" onClick={handleClose}>
            Отмена
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? 'Создание...' : 'Создать карточку'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
