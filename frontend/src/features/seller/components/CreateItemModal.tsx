import { useState } from 'react';
import Modal from '../../../components/ui/Modal';
import Button from '../../../components/ui/Button';
import { useCreateSupplierItemMutation } from '../supplierApi';

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

  const [rawName, setRawName] = useState('');
  const [variety, setVariety] = useState('');
  const [price, setPrice] = useState('');
  const [lengthCm, setLengthCm] = useState('');
  const [color, setColor] = useState('');
  const [packType, setPackType] = useState('');
  const [packQty, setPackQty] = useState('');
  const [stockQty, setStockQty] = useState('');

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    try {
      await createItem({
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

      // Reset form
      setRawName('');
      setVariety('');
      setPrice('');
      setLengthCm('');
      setColor('');
      setPackType('');
      setPackQty('');
      setStockQty('');
      setErrors({});
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
        {/* Required fields */}
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
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
