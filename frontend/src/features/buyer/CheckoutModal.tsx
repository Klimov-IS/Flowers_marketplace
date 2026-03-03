import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAppSelector } from '../../hooks/useAppSelector';
import { useAppDispatch } from '../../hooks/useAppDispatch';
import { clearSupplierCart } from './cartSlice';
import { useCreateOrderMutation } from './ordersApi';
import Modal from '../../components/ui/Modal';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';

const checkoutSchema = z.object({
  delivery_address: z.string().optional(),
  delivery_date: z.string().optional(),
  notes: z.string().optional(),
});

type CheckoutFormData = z.infer<typeof checkoutSchema>;

interface CheckoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  supplierId: string;
}

export default function CheckoutModal({
  isOpen,
  onClose,
  supplierId,
}: CheckoutModalProps) {
  const dispatch = useAppDispatch();
  const cart = useAppSelector((state) => state.cart);
  const user = useAppSelector((state) => state.auth.user);
  const [createOrder, { isLoading }] = useCreateOrderMutation();
  const [deliveryType, setDeliveryType] = useState<'pickup' | 'delivery'>('delivery');
  const [addressError, setAddressError] = useState('');

  const supplier = cart.suppliers.find((s) => s.supplier_id === supplierId);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<CheckoutFormData>({
    resolver: zodResolver(checkoutSchema),
  });

  const onSubmit = async (data: CheckoutFormData) => {
    if (!user || !supplier) return;

    // Validate address for delivery
    if (deliveryType === 'delivery' && (!data.delivery_address || data.delivery_address.length < 5)) {
      setAddressError('Адрес должен содержать минимум 5 символов');
      return;
    }
    setAddressError('');

    try {
      await createOrder({
        buyer_id: user.id,
        items: supplier.items.map((item) => ({
          offer_id: item.offer_id,
          quantity: item.quantity,
        })),
        delivery_type: deliveryType,
        delivery_address: deliveryType === 'delivery' ? data.delivery_address : undefined,
        delivery_date: data.delivery_date,
        notes: data.notes,
      }).unwrap();

      dispatch(clearSupplierCart(supplierId));
      reset();
      onClose();

      alert('Заказ успешно создан!');
    } catch (error: unknown) {
      console.error('Failed to create order:', error);
      const detail = (error as { data?: { detail?: string } })?.data?.detail || '';
      if (detail.includes('not active')) {
        alert('Некоторые товары больше недоступны. Вернитесь в корзину — устаревшие товары будут удалены автоматически.');
      } else if (detail.includes('Buyer not found')) {
        alert('Ошибка аккаунта. Попробуйте перелогиниться.');
      } else if (detail) {
        alert(`Ошибка: ${detail}`);
      } else {
        alert('Ошибка при создании заказа. Проверьте подключение к API.');
      }
    }
  };

  const handleDeliveryTypeChange = (type: 'pickup' | 'delivery') => {
    setDeliveryType(type);
    setAddressError('');
  };

  if (!supplier) return null;

  const total = supplier.items.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0
  );

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Оформление заказа" size="lg">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Order Summary */}
        <div className="bg-gray-50 rounded-xl p-4">
          <h4 className="font-semibold mb-3">Ваш заказ из {supplier.supplier_name}</h4>
          <div className="space-y-2">
            {supplier.items.map((item) => (
              <div key={item.offer_id} className="flex justify-between text-sm">
                <span className="text-gray-700">
                  {item.name} × {item.quantity}
                </span>
                <span className="font-medium">
                  {(item.price * item.quantity).toLocaleString()} ₽
                </span>
              </div>
            ))}
          </div>
          <div className="mt-3 pt-3 border-t border-gray-300 flex justify-between font-bold text-lg">
            <span>Итого:</span>
            <span className="text-primary-600">{total.toLocaleString()} ₽</span>
          </div>
        </div>

        {/* Delivery Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Способ получения
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => handleDeliveryTypeChange('pickup')}
              className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${
                deliveryType === 'pickup'
                  ? 'border-primary-500 bg-primary-50 text-primary-700'
                  : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
              }`}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
              <span className="text-sm font-medium">Самовывоз</span>
            </button>
            <button
              type="button"
              onClick={() => handleDeliveryTypeChange('delivery')}
              className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${
                deliveryType === 'delivery'
                  ? 'border-primary-500 bg-primary-50 text-primary-700'
                  : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
              }`}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0" />
              </svg>
              <span className="text-sm font-medium">Доставка</span>
            </button>
          </div>
        </div>

        {/* Pickup info */}
        {deliveryType === 'pickup' && (
          <div className="bg-primary-50 border border-primary-200 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-primary-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <div>
                <p className="text-sm font-medium text-primary-800">Адрес самовывоза</p>
                {supplier.warehouse_address ? (
                  <p className="text-sm text-primary-700 mt-1">{supplier.warehouse_address}</p>
                ) : (
                  <p className="text-sm text-primary-600 mt-1">
                    Адрес будет указан в подтверждении заказа
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Delivery Form */}
        <div className="space-y-4">
          {deliveryType === 'delivery' && (
            <Input
              label="Адрес доставки *"
              placeholder="ул. Ленина, д. 10, офис 5"
              error={addressError || errors.delivery_address?.message}
              {...register('delivery_address')}
            />
          )}

          <Input
            label="Желаемая дата"
            type="date"
            error={errors.delivery_date?.message}
            {...register('delivery_date')}
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Комментарий к заказу
            </label>
            <textarea
              placeholder="Особые пожелания, время доставки..."
              className="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
              rows={3}
              {...register('notes')}
            />
            {errors.notes && (
              <p className="mt-1 text-sm text-red-600">{errors.notes.message}</p>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-end pt-4 border-t">
          <Button type="button" variant="secondary" onClick={onClose}>
            Отмена
          </Button>
          <Button type="submit" disabled={isLoading || !user}>
            {isLoading ? 'Оформление...' : 'Оформить заказ'}
          </Button>
        </div>

        {!user && (
          <p className="text-sm text-red-600 text-center">
            Войдите в систему чтобы оформить заказ
          </p>
        )}
      </form>
    </Modal>
  );
}
