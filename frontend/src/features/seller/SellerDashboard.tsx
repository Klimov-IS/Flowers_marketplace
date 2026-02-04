import { useState } from 'react';
import { useAppSelector } from '../../hooks/useAppSelector';
import {
  useGetSupplierOrdersQuery,
  useGetOrderMetricsQuery,
  useConfirmOrderMutation,
  useRejectOrderMutation,
} from './supplierApi';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import Badge from '../../components/ui/Badge';
import TabsNav from './components/TabsNav';
import AssortmentTab from './components/AssortmentTab';
import PriceListUpload from './PriceListUpload';
import RejectOrderModal from './RejectOrderModal';

type TabId = 'assortment' | 'orders' | 'upload';

export default function SellerDashboard() {
  const user = useAppSelector((state) => state.auth.user);
  const [activeTab, setActiveTab] = useState<TabId>('assortment');
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [rejectingOrder, setRejectingOrder] = useState<string | null>(null);

  // Fetch orders and metrics
  const { data: ordersData, isLoading: ordersLoading } = useGetSupplierOrdersQuery(
    { supplier_id: user?.id || '', status: statusFilter, limit: 50 },
    { skip: !user?.id || user.role !== 'seller' }
  );

  const { data: metrics } = useGetOrderMetricsQuery(user?.id || '', {
    skip: !user?.id || user.role !== 'seller',
  });

  const [confirmOrder, { isLoading: isConfirming }] = useConfirmOrderMutation();
  const [rejectOrder] = useRejectOrderMutation();

  const handleConfirm = async (orderId: string) => {
    if (!user) return;
    try {
      await confirmOrder({ supplier_id: user.id, order_id: orderId }).unwrap();
      alert('Заказ подтвержден!');
    } catch (error) {
      console.error('Failed to confirm order:', error);
      alert('Ошибка при подтверждении заказа');
    }
  };

  const handleReject = async (orderId: string, reason: string) => {
    if (!user) return;
    try {
      await rejectOrder({ supplier_id: user.id, order_id: orderId, reason }).unwrap();
      setRejectingOrder(null);
      alert('Заказ отклонен');
    } catch (error) {
      console.error('Failed to reject order:', error);
      alert('Ошибка при отклонении заказа');
    }
  };

  const statusBadgeVariant = (status: string) => {
    switch (status) {
      case 'pending':
        return 'warning';
      case 'confirmed':
        return 'success';
      case 'rejected':
        return 'danger';
      case 'cancelled':
        return 'default';
      default:
        return 'default';
    }
  };

  const statusLabel = (status: string) => {
    switch (status) {
      case 'pending':
        return 'Ожидает';
      case 'confirmed':
        return 'Подтвержден';
      case 'rejected':
        return 'Отклонен';
      case 'cancelled':
        return 'Отменен';
      default:
        return status;
    }
  };

  const statusFilters = [
    { value: undefined, label: 'Все' },
    { value: 'pending', label: 'Ожидают' },
    { value: 'confirmed', label: 'Подтверждены' },
    { value: 'rejected', label: 'Отклонены' },
  ];

  // Tabs configuration
  const tabs = [
    { id: 'assortment', label: 'Ассортимент' },
    {
      id: 'orders',
      label: 'Заказы',
      badge: metrics?.pending,
      badgeVariant: 'warning' as const,
    },
    { id: 'upload', label: 'Загрузка прайса' },
  ];

  if (!user || user.role !== 'seller') {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Card className="p-12 text-center">
          <p className="text-lg text-gray-600 mb-4">Доступ запрещен</p>
          <p className="text-gray-500">Войдите как продавец для доступа к этой странице</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold mb-6">Кабинет продавца</h1>

      {/* Metrics */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="p-6 text-center">
            <div className="text-4xl font-bold text-primary-600 mb-2">
              {metrics.total_orders}
            </div>
            <div className="text-gray-600">Всего заказов</div>
          </Card>
          <Card className="p-6 text-center">
            <div className="text-4xl font-bold text-orange-600 mb-2">
              {metrics.pending}
            </div>
            <div className="text-gray-600">Ожидают обработки</div>
          </Card>
          <Card className="p-6 text-center">
            <div className="text-4xl font-bold text-green-600 mb-2">
              {metrics.confirmed}
            </div>
            <div className="text-gray-600">Подтверждено</div>
          </Card>
          <Card className="p-6 text-center">
            <div className="text-4xl font-bold text-primary-600 mb-2">
              {parseFloat(metrics.total_revenue).toLocaleString()} ₽
            </div>
            <div className="text-gray-600">Общая выручка</div>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <TabsNav
        tabs={tabs}
        activeTab={activeTab}
        onTabChange={(tabId) => setActiveTab(tabId as TabId)}
      />

      {/* Tab Content */}
      {activeTab === 'assortment' && (
        <AssortmentTab supplierId={user.id} />
      )}

      {activeTab === 'upload' && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Загрузка прайс-листа</h2>
          <PriceListUpload />
        </div>
      )}

      {activeTab === 'orders' && (
        <div>
          {/* Status Filter Pills */}
          <div className="flex gap-2 mb-6">
            {statusFilters.map((filter) => (
              <button
                key={filter.label}
                onClick={() => setStatusFilter(filter.value)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                  statusFilter === filter.value
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {filter.label}
              </button>
            ))}
          </div>

          {ordersLoading ? (
            <Card className="p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            </Card>
          ) : !ordersData || ordersData.length === 0 ? (
            <Card className="p-12 text-center text-gray-500">
              <p className="text-lg mb-2">Заказов нет</p>
              <p className="text-sm">Входящие заказы появятся здесь</p>
            </Card>
          ) : (
            <div className="space-y-4">
              {ordersData.map((order) => (
                <Card key={order.id} className="p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold">
                          Заказ #{order.id.slice(0, 8)}
                        </h3>
                        <Badge variant={statusBadgeVariant(order.status)}>
                          {statusLabel(order.status)}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-600">
                        {order.buyer?.name} • {order.buyer?.phone}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        Создан: {new Date(order.created_at).toLocaleString('ru-RU')}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-primary-600">
                        {parseFloat(order.total_amount).toLocaleString()} ₽
                      </p>
                      <p className="text-sm text-gray-500 mt-1">
                        {order.items.length} позиций
                      </p>
                    </div>
                  </div>

                  {order.delivery_address && (
                    <div className="mb-3 text-sm text-gray-600">
                      Адрес: {order.delivery_address}
                    </div>
                  )}

                  {order.delivery_date && (
                    <div className="mb-3 text-sm text-gray-600">
                      Дата доставки:{' '}
                      {new Date(order.delivery_date).toLocaleDateString('ru-RU')}
                    </div>
                  )}

                  {order.notes && (
                    <div className="mb-4 p-3 bg-gray-50 rounded text-sm">
                      Комментарий: {order.notes}
                    </div>
                  )}

                  {order.status === 'pending' && (
                    <div className="flex gap-3 pt-4 border-t">
                      <Button
                        variant="success"
                        onClick={() => handleConfirm(order.id)}
                        disabled={isConfirming}
                      >
                        Подтвердить
                      </Button>
                      <Button
                        variant="danger"
                        onClick={() => setRejectingOrder(order.id)}
                      >
                        Отклонить
                      </Button>
                    </div>
                  )}

                  {order.status === 'rejected' && order.rejection_reason && (
                    <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                      Причина отклонения: {order.rejection_reason}
                    </div>
                  )}

                  {order.status === 'confirmed' && order.confirmed_at && (
                    <div className="mt-3 text-sm text-green-700">
                      Подтвержден:{' '}
                      {new Date(order.confirmed_at).toLocaleString('ru-RU')}
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Reject Order Modal */}
      {rejectingOrder && (
        <RejectOrderModal
          isOpen={!!rejectingOrder}
          onClose={() => setRejectingOrder(null)}
          onReject={(reason) => handleReject(rejectingOrder, reason)}
        />
      )}
    </div>
  );
}
