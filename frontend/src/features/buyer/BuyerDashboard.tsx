import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAppSelector } from '../../hooks/useAppSelector';
import { useAppDispatch } from '../../hooks/useAppDispatch';
import {
  updateQuantity,
  removeItem,
  clearSupplierCart,
} from './cartSlice';
import { useGetOrdersQuery } from './ordersApi';
import CheckoutModal from './CheckoutModal';

/* ───── SVG icons ───── */
const TrashIcon = (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
  </svg>
);

const CheckIcon = (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const ClockIcon = (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const XCircleIcon = (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const ArrowLeftIcon = (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
    <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
  </svg>
);

const OrderCheckIcon = (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

/* ───── Status config ───── */
const AssembledIcon = (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
  </svg>
);

const statusConfig: Record<string, { icon: React.ReactNode; iconBg: string; badgeBg: string; label: string; dimCard?: boolean }> = {
  pending:   { icon: ClockIcon,     iconBg: 'bg-sky-50 text-sky-600',         badgeBg: 'bg-sky-100 text-sky-700',       label: 'Новый' },
  confirmed: { icon: CheckIcon,     iconBg: 'bg-primary-50 text-primary-600', badgeBg: 'bg-primary-100 text-primary-700', label: 'Подтверждён' },
  assembled: { icon: AssembledIcon, iconBg: 'bg-sky-50 text-sky-600',         badgeBg: 'bg-sky-100 text-sky-700',       label: 'Собран' },
  rejected:  { icon: XCircleIcon,   iconBg: 'bg-red-50 text-red-600',         badgeBg: 'bg-red-100 text-red-700',       label: 'Отклонён' },
  cancelled: { icon: XCircleIcon,   iconBg: 'bg-gray-100 text-gray-400',      badgeBg: 'bg-gray-100 text-gray-500',     label: 'Отменён', dimCard: true },
};

export default function BuyerDashboard() {
  const dispatch = useAppDispatch();
  const cart = useAppSelector((state) => state.cart);
  const user = useAppSelector((state) => state.auth.user);

  const [activeTab, setActiveTab] = useState<'cart' | 'orders'>('cart');
  const [checkoutSupplier, setCheckoutSupplier] = useState<string | null>(null);
  const [expandedOrder, setExpandedOrder] = useState<string | null>(null);

  const { data: ordersData } = useGetOrdersQuery(
    { buyer_id: user?.id || '', limit: 20 },
    { skip: !user?.id }
  );

  /* ───── Cart helpers ───── */
  const totalItems = cart.suppliers.reduce((sum, s) => sum + s.items.reduce((s2, i) => s2 + i.quantity, 0), 0);

  const calculateSupplierTotal = (supplierId: string) => {
    const supplier = cart.suppliers.find((s) => s.supplier_id === supplierId);
    if (!supplier) return 0;
    return supplier.items.reduce((sum, item) => sum + item.price * item.quantity, 0);
  };

  const grandTotal = cart.suppliers.reduce((sum, s) => sum + calculateSupplierTotal(s.supplier_id), 0);

  const handleQuantityChange = (supplierId: string, offerId: string, delta: number) => {
    const supplier = cart.suppliers.find((s) => s.supplier_id === supplierId);
    const item = supplier?.items.find((i) => i.offer_id === offerId);
    if (item) {
      const newQty = item.quantity + delta;
      if (newQty > 0) {
        dispatch(updateQuantity({ supplier_id: supplierId, offer_id: offerId, quantity: newQty }));
      }
    }
  };

  const getSupplierInitials = (name: string) => {
    const words = name.split(/\s+/);
    if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

  const orderCount = ordersData?.orders?.length || 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ───── Tabs ───── */}
      <div className="bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex gap-6">
            <button
              onClick={() => setActiveTab('cart')}
              className={`relative py-3.5 text-sm font-medium transition-colors ${
                activeTab === 'cart' ? 'text-primary-600 tab-active' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Корзина
              {totalItems > 0 && (
                <span className={`ml-1.5 px-1.5 py-0.5 rounded-full text-xs font-semibold ${
                  activeTab === 'cart' ? 'bg-primary-100 text-primary-700' : 'bg-gray-100 text-gray-600'
                }`}>
                  {totalItems}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('orders')}
              className={`relative py-3.5 text-sm font-medium transition-colors ${
                activeTab === 'orders' ? 'text-primary-600 tab-active' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Мои заказы
              {orderCount > 0 && (
                <span className={`ml-1.5 px-1.5 py-0.5 rounded-full text-xs font-semibold ${
                  activeTab === 'orders' ? 'bg-primary-100 text-primary-700' : 'bg-gray-100 text-gray-600'
                }`}>
                  {orderCount}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* ───── CART TAB ───── */}
      {activeTab === 'cart' && (
        <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {cart.suppliers.length === 0 ? (
            /* Empty cart */
            <div className="bg-white rounded-2xl shadow-sm p-12 text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 00-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 00-16.536-1.84M7.5 14.25L5.106 5.272M6 20.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm12.75 0a.75.75 0 11-1.5 0 .75.75 0 011.5 0z" />
                </svg>
              </div>
              <p className="text-gray-500 text-lg mb-2">Корзина пуста</p>
              <p className="text-gray-400 text-sm mb-6">Добавьте товары из каталога</p>
              <Link
                to="/catalog"
                className="inline-flex items-center gap-2 text-sm text-primary-600 hover:text-primary-700 font-medium transition-colors"
              >
                {ArrowLeftIcon}
                Перейти в каталог
              </Link>
            </div>
          ) : (
            <div className="grid lg:grid-cols-3 gap-6">
              {/* Cart items */}
              <div className="lg:col-span-2 space-y-4">
                {cart.suppliers.map((supplier) => (
                  <div key={supplier.supplier_id} className="bg-white rounded-2xl shadow-sm overflow-hidden">
                    {/* Supplier header */}
                    <div className="flex items-center justify-between px-5 py-3.5 bg-gray-50 border-b border-gray-100">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                          <span className="text-xs font-bold text-primary-700">
                            {getSupplierInitials(supplier.supplier_name)}
                          </span>
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-gray-900">{supplier.supplier_name}</div>
                          <div className="text-xs text-gray-500">{supplier.items.length} {supplier.items.length === 1 ? 'позиция' : 'позиций'}</div>
                        </div>
                      </div>
                      <button
                        onClick={() => dispatch(clearSupplierCart(supplier.supplier_id))}
                        className="text-xs text-red-500 hover:text-red-600 font-medium transition-colors"
                      >
                        Очистить
                      </button>
                    </div>

                    {/* Items */}
                    {supplier.items.map((item, idx) => (
                      <div
                        key={item.offer_id}
                        className={`px-5 py-4 hover:bg-gray-50/50 transition-colors ${
                          idx < supplier.items.length - 1 ? 'border-b border-gray-50' : ''
                        }`}
                      >
                        <div className="flex gap-4">
                          {/* Placeholder */}
                          <div className="w-16 h-16 bg-gray-100 rounded-xl flex items-center justify-center shrink-0">
                            <span className="text-2xl">&#127801;</span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <h4 className="text-sm font-semibold text-gray-900">{item.name}</h4>
                                <p className="text-xs text-gray-500 mt-0.5">
                                  {item.length_cm && `${item.length_cm} см · `}{item.price} ₽/шт
                                </p>
                              </div>
                              <button
                                onClick={() => dispatch(removeItem({ supplier_id: supplier.supplier_id, offer_id: item.offer_id }))}
                                className="p-1.5 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors shrink-0"
                              >
                                {TrashIcon}
                              </button>
                            </div>
                            <div className="flex items-center justify-between mt-3">
                              <div className="flex items-center gap-1.5">
                                <button
                                  onClick={() => handleQuantityChange(supplier.supplier_id, item.offer_id, -1)}
                                  className="w-7 h-7 rounded-lg bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-gray-600 text-sm transition-colors"
                                >
                                  −
                                </button>
                                <span className="w-12 text-center text-sm font-medium">{item.quantity}</span>
                                <button
                                  onClick={() => handleQuantityChange(supplier.supplier_id, item.offer_id, 1)}
                                  className="w-7 h-7 rounded-lg bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-gray-600 text-sm transition-colors"
                                >
                                  +
                                </button>
                                <span className="text-xs text-gray-500">шт</span>
                              </div>
                              <div className="text-right">
                                <div className="text-sm font-bold text-gray-900">
                                  {(item.price * item.quantity).toLocaleString()} ₽
                                </div>
                                <div className="text-xs text-gray-500">
                                  {item.quantity} шт × {item.price} ₽
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}

                    {/* Supplier subtotal */}
                    <div className="px-5 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
                      <span className="text-sm text-gray-500">Подытог по {supplier.supplier_name}</span>
                      <span className="text-sm font-bold text-gray-900">
                        {calculateSupplierTotal(supplier.supplier_id).toLocaleString()} ₽
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Sticky sidebar */}
              <div className="lg:col-span-1">
                <div className="sticky top-[80px]">
                  <div className="bg-white rounded-2xl shadow-sm p-5">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Итого заказа</h3>

                    <div className="space-y-2.5 mb-4">
                      {cart.suppliers.map((s) => (
                        <div key={s.supplier_id} className="flex justify-between text-sm">
                          <span className="text-gray-500">{s.supplier_name} ({s.items.length} поз.)</span>
                          <span className="text-gray-900 font-medium">
                            {calculateSupplierTotal(s.supplier_id).toLocaleString()} ₽
                          </span>
                        </div>
                      ))}
                      <div className="border-t border-gray-100 pt-2.5">
                        <div className="flex justify-between">
                          <span className="text-base font-semibold text-gray-900">Итого</span>
                          <span className="text-xl font-bold text-primary-600">{grandTotal.toLocaleString()} ₽</span>
                        </div>
                        <p className="text-xs text-gray-400 mt-1">
                          {cart.suppliers.reduce((n, s) => n + s.items.length, 0)} позиций, {totalItems} шт
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={() => setCheckoutSupplier(cart.suppliers[0]?.supplier_id || null)}
                      className="w-full bg-primary-500 hover:bg-primary-600 active:scale-[0.97] text-white font-semibold py-3.5 rounded-xl text-sm transition-all duration-150 flex items-center justify-center gap-2"
                    >
                      {OrderCheckIcon}
                      Оформить заказ
                    </button>

                    <p className="text-xs text-gray-400 text-center mt-3">
                      Заказы отправляются напрямую поставщикам. Оплата при получении.
                    </p>
                  </div>

                  <Link
                    to="/catalog"
                    className="flex items-center justify-center gap-2 text-sm text-primary-600 hover:text-primary-700 font-medium mt-4 transition-colors"
                  >
                    {ArrowLeftIcon}
                    Продолжить покупки
                  </Link>
                </div>
              </div>
            </div>
          )}
        </main>
      )}

      {/* ───── ORDERS TAB ───── */}
      {activeTab === 'orders' && (
        <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {!user ? (
            <div className="bg-white rounded-2xl shadow-sm p-12 text-center">
              <p className="text-gray-500">Войдите в систему, чтобы увидеть историю заказов</p>
            </div>
          ) : !ordersData?.orders?.length ? (
            <div className="bg-white rounded-2xl shadow-sm p-12 text-center">
              <p className="text-gray-500 text-lg mb-2">У вас пока нет заказов</p>
              <p className="text-gray-400 text-sm">Оформите первый заказ из каталога</p>
            </div>
          ) : (
            <div className="space-y-4">
              {ordersData.orders.map((order) => {
                const cfg = statusConfig[order.status] || statusConfig.pending;
                const isExpanded = expandedOrder === order.id;

                return (
                  <div
                    key={order.id}
                    className={`bg-white rounded-2xl shadow-sm overflow-hidden ${cfg.dimCard ? 'opacity-70' : ''}`}
                  >
                    {/* Order header */}
                    <button
                      onClick={() => setExpandedOrder(isExpanded ? null : order.id)}
                      className="w-full px-5 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-100 text-left hover:bg-gray-50/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${cfg.iconBg}`}>
                          {cfg.icon}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-gray-900">
                              Заказ #{order.id.slice(0, 8)}
                            </span>
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cfg.badgeBg}`}>
                              {cfg.label}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {new Date(order.created_at).toLocaleDateString('ru-RU')}
                            {order.supplier?.name && ` · ${order.supplier.name}`}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className={`text-lg font-bold ${cfg.dimCard ? 'text-gray-400 line-through' : 'text-gray-900'}`}>
                          {parseFloat(order.total_amount).toLocaleString()} ₽
                        </div>
                        <div className="text-xs text-gray-500">
                          {order.items.length} {order.items.length === 1 ? 'позиция' : 'позиций'}
                        </div>
                      </div>
                    </button>

                    {/* Expandable details */}
                    {isExpanded && (
                      <div className="px-5 py-3 bg-gray-50">
                        <div className="space-y-2">
                          {order.items.map((item) => (
                            <div key={item.id} className="flex justify-between text-sm">
                              <span className="text-gray-600">Позиция #{item.offer_id.slice(0, 8)}</span>
                              <span className="text-gray-900">
                                {item.quantity} шт — {parseFloat(item.total_price || '0').toLocaleString()} ₽
                              </span>
                            </div>
                          ))}
                        </div>

                        {order.delivery_address && (
                          <p className="text-xs text-gray-500 mt-3 pt-2 border-t border-gray-200">
                            Доставка: {order.delivery_address}
                          </p>
                        )}

                        {order.rejection_reason && (
                          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
                            Причина отклонения: {order.rejection_reason}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </main>
      )}

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
