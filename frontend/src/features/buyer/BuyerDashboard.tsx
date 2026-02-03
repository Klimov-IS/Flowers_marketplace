import { useState } from 'react';
import { useAppSelector } from '../../hooks/useAppSelector';
import { useAppDispatch } from '../../hooks/useAppDispatch';
import {
  updateQuantity,
  removeItem,
  clearSupplierCart,
} from './cartSlice';
import { useGetOrdersQuery } from './ordersApi';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import Badge from '../../components/ui/Badge';
import CheckoutModal from './CheckoutModal';

export default function BuyerDashboard() {
  const dispatch = useAppDispatch();
  const cart = useAppSelector((state) => state.cart);
  const user = useAppSelector((state) => state.auth.user);
  const [checkoutSupplier, setCheckoutSupplier] = useState<string | null>(null);

  // Fetch orders if user is authenticated
  const { data: ordersData } = useGetOrdersQuery(
    { buyer_id: user?.id || '', limit: 10 },
    { skip: !user?.id }
  );

  const calculateSupplierTotal = (supplierId: string) => {
    const supplier = cart.suppliers.find((s) => s.supplier_id === supplierId);
    if (!supplier) return 0;
    return supplier.items.reduce((sum, item) => sum + item.price * item.quantity, 0);
  };

  const handleQuantityChange = (
    supplierId: string,
    offerId: string,
    delta: number
  ) => {
    const supplier = cart.suppliers.find((s) => s.supplier_id === supplierId);
    const item = supplier?.items.find((i) => i.offer_id === offerId);
    if (item) {
      const newQuantity = item.quantity + delta;
      if (newQuantity > 0) {
        dispatch(updateQuantity({ supplier_id: supplierId, offer_id: offerId, quantity: newQuantity }));
      }
    }
  };

  const statusBadgeVariant = (status: string) => {
    switch (status) {
      case 'pending': return 'warning';
      case 'confirmed': return 'success';
      case 'rejected': return 'danger';
      case 'cancelled': return 'default';
      default: return 'default';
    }
  };

  const statusLabel = (status: string) => {
    switch (status) {
      case 'pending': return 'Ожидает';
      case 'confirmed': return 'Подтвержден';
      case 'rejected': return 'Отклонен';
      case 'cancelled': return 'Отменен';
      default: return status;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold mb-6">Личный кабинет покупателя</h1>

      {/* Cart Section */}
      <div className="mb-12">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-semibold">Корзина</h2>
          {cart.suppliers.length > 0 && (
            <p className="text-gray-600">
              {cart.suppliers.reduce(
                (sum, s) => sum + s.items.reduce((s2, i) => s2 + i.quantity, 0),
                0
              )}{' '}
              товаров
            </p>
          )}
        </div>

        {cart.suppliers.length === 0 ? (
          <Card className="p-12 text-center">
            <p className="text-gray-500 text-lg mb-4">Корзина пуста</p>
            <p className="text-gray-400">Добавьте товары из витрины</p>
          </Card>
        ) : (
          <div className="space-y-6">
            {cart.suppliers.map((supplier) => (
              <Card key={supplier.supplier_id} className="p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-xl font-semibold">{supplier.supplier_name}</h3>
                  <button
                    onClick={() =>
                      dispatch(clearSupplierCart(supplier.supplier_id))
                    }
                    className="text-red-600 hover:text-red-700 text-sm"
                  >
                    Очистить
                  </button>
                </div>

                <div className="space-y-4 mb-4">
                  {supplier.items.map((item) => (
                    <div
                      key={item.offer_id}
                      className="flex items-center justify-between border-b pb-4 last:border-b-0 last:pb-0"
                    >
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900">{item.name}</h4>
                        <p className="text-sm text-gray-600">
                          {item.price} ₽ / шт
                          {item.stock && (
                            <span className="ml-2 text-gray-400">
                              Остаток: {item.stock} шт
                            </span>
                          )}
                        </p>
                      </div>

                      <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() =>
                              handleQuantityChange(
                                supplier.supplier_id,
                                item.offer_id,
                                -1
                              )
                            }
                            className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center"
                          >
                            −
                          </button>
                          <span className="w-12 text-center font-medium">
                            {item.quantity}
                          </span>
                          <button
                            onClick={() =>
                              handleQuantityChange(
                                supplier.supplier_id,
                                item.offer_id,
                                1
                              )
                            }
                            className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center"
                          >
                            +
                          </button>
                        </div>

                        <div className="w-24 text-right font-semibold">
                          {(item.price * item.quantity).toLocaleString()} ₽
                        </div>

                        <button
                          onClick={() =>
                            dispatch(
                              removeItem({
                                supplier_id: supplier.supplier_id,
                                offer_id: item.offer_id,
                              })
                            )
                          }
                          className="text-red-600 hover:text-red-700"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex justify-between items-center pt-4 border-t">
                  <div className="text-lg">
                    <span className="text-gray-600">Итого:</span>
                    <span className="ml-2 text-2xl font-bold text-primary-600">
                      {calculateSupplierTotal(supplier.supplier_id).toLocaleString()} ₽
                    </span>
                  </div>
                  <Button onClick={() => setCheckoutSupplier(supplier.supplier_id)}>
                    Оформить заказ
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Order History */}
      <div>
        <h2 className="text-2xl font-semibold mb-4">История заказов</h2>

        {!user ? (
          <Card className="p-6 text-center text-gray-500">
            Войдите в систему чтобы увидеть историю заказов
          </Card>
        ) : ordersData?.orders.length === 0 ? (
          <Card className="p-6 text-center text-gray-500">
            У вас пока нет заказов
          </Card>
        ) : (
          <div className="space-y-4">
            {ordersData?.orders.map((order) => (
              <Card key={order.id} className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <h3 className="text-lg font-semibold">Заказ #{order.id.slice(0, 8)}</h3>
                      <Badge variant={statusBadgeVariant(order.status)}>
                        {statusLabel(order.status)}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">
                      {order.supplier?.name} • {new Date(order.created_at).toLocaleDateString('ru-RU')}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-primary-600">
                      {parseFloat(order.total_amount).toLocaleString()} ₽
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                      {order.items.length} {order.items.length === 1 ? 'товар' : 'товаров'}
                    </p>
                  </div>
                </div>

                {order.delivery_address && (
                  <div className="text-sm text-gray-600 mb-2">
                    📍 {order.delivery_address}
                  </div>
                )}

                {order.delivery_date && (
                  <div className="text-sm text-gray-600 mb-2">
                    📅 Доставка: {new Date(order.delivery_date).toLocaleDateString('ru-RU')}
                  </div>
                )}

                {order.rejection_reason && (
                  <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                    Причина отклонения: {order.rejection_reason}
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Checkout Modal */}
      {checkoutSupplier && (
        <CheckoutModal
          isOpen={!!checkoutSupplier}
          onClose={() => setCheckoutSupplier(null)}
          supplierId={checkoutSupplier}
        />
      )}
    </div>
  );
}
