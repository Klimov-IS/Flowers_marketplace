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
  delivery_address: z.string().min(5, 'Адрес должен содержать минимум 5 символов'),
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
  const [createOrder, { isLoading, isSuccess }] = useCreateOrderMutation();

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

    try {
      await createOrder({
        buyer_id: user.id,
        items: supplier.items.map((item) => ({
          offer_id: item.offer_id,
          quantity: item.quantity,
        })),
        delivery_address: data.delivery_address,
        delivery_date: data.delivery_date,
        notes: data.notes,
      }).unwrap();

      // Clear cart for this supplier
      dispatch(clearSupplierCart(supplierId));
      reset();
      onClose();

      alert('Заказ успешно создан!');
    } catch (error) {
      console.error('Failed to create order:', error);
      alert('Ошибка при создании заказа. Проверьте подключение к API.');
    }
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
        <div className="bg-gray-50 rounded-lg p-4">
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

        {/* Delivery Form */}
        <div className="space-y-4">
          <Input
            label="Адрес доставки *"
            placeholder="ул. Ленина, д. 10, офис 5"
            error={errors.delivery_address?.message}
            {...register('delivery_address')}
          />

          <Input
            label="Желаемая дата доставки"
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
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
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
