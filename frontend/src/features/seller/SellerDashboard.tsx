import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAppSelector } from '../../hooks/useAppSelector';
import { useAppDispatch } from '../../hooks/useAppDispatch';
import { setUser } from '../auth/authSlice';
import { useUpdateProfileMutation } from '../auth/authApi';
import {
  useGetSupplierOrdersQuery,
  useGetOrderMetricsQuery,
  useConfirmOrderMutation,
  useRejectOrderMutation,
  useAssembleOrderMutation,
} from './supplierApi';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import { useToast } from '../../components/ui/Toast';
import AssortmentTab from './components/AssortmentTab';
import RejectOrderModal from './RejectOrderModal';
import PriceListUpload from './PriceListUpload';
import ImportHistory from './components/ImportHistory';

type TabId = 'assortment' | 'upload' | 'orders' | 'profile';

/* ───── SVG Icons ───── */
const BoxIcon = (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
  </svg>
);
const UploadIcon = (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
  </svg>
);
const ClipboardIcon = (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
  </svg>
);
const UserIcon = (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
  </svg>
);
const CameraIcon = (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.04l-.821 1.315z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z" />
  </svg>
);

/* ───── Order status config ───── */
const ClockSvg = (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);
const CheckSvg = (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);
const PackageSvg = (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
  </svg>
);
const XCircleSvg = (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const statusConfig: Record<string, { icon: React.ReactNode; iconBg: string; badgeBg: string; borderColor: string; label: string; dimCard?: boolean }> = {
  pending:   { icon: ClockSvg,   iconBg: 'bg-amber-50 text-amber-600',     badgeBg: 'bg-amber-100 text-amber-700',       borderColor: 'border-l-amber-400',   label: 'Новый' },
  confirmed: { icon: CheckSvg,   iconBg: 'bg-primary-50 text-primary-600', badgeBg: 'bg-primary-100 text-primary-700',   borderColor: 'border-l-primary-400', label: 'Подтверждён' },
  assembled: { icon: PackageSvg, iconBg: 'bg-sky-50 text-sky-600',         badgeBg: 'bg-sky-100 text-sky-700',           borderColor: 'border-l-sky-400',     label: 'Собран' },
  rejected:  { icon: XCircleSvg, iconBg: 'bg-red-50 text-red-600',         badgeBg: 'bg-red-100 text-red-700',           borderColor: 'border-l-red-400',     label: 'Отклонён' },
  cancelled: { icon: XCircleSvg, iconBg: 'bg-gray-100 text-gray-400',      badgeBg: 'bg-gray-100 text-gray-500',         borderColor: 'border-l-gray-300',    label: 'Отменён', dimCard: true },
};

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export default function SellerDashboard() {
  const user = useAppSelector((state) => state.auth.user);
  const dispatch = useAppDispatch();
  const { showToast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabFromUrl = searchParams.get('tab') as TabId | null;
  const [activeTab, setActiveTab] = useState<TabId>(
    tabFromUrl && ['assortment', 'upload', 'orders', 'profile'].includes(tabFromUrl) ? tabFromUrl : 'assortment'
  );
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [rejectingOrder, setRejectingOrder] = useState<string | null>(null);
  const [expandedOrder, setExpandedOrder] = useState<string | null>(null);

  // Profile form state
  const [profileName, setProfileName] = useState(user?.name || '');
  const [profileEmail, setProfileEmail] = useState(user?.email || '');
  const [profilePhone, setProfilePhone] = useState(user?.phone || '');
  const [profileCity, setProfileCity] = useState(user?.city_name || '');
  const [profileLegalName, setProfileLegalName] = useState(user?.legal_name || '');
  const [profileContactPerson, setProfileContactPerson] = useState(user?.contact_person || '');
  const [profileWarehouseAddress, setProfileWarehouseAddress] = useState(user?.warehouse_address || '');
  const [profileDescription, setProfileDescription] = useState(user?.description || '');
  const [profileWorkFrom, setProfileWorkFrom] = useState(user?.working_hours_from || '');
  const [profileWorkTo, setProfileWorkTo] = useState(user?.working_hours_to || '');
  const [profileMinOrder, setProfileMinOrder] = useState(user?.min_order_amount?.toString() || '');
  const [updateProfile, { isLoading: isSavingProfile }] = useUpdateProfileMutation();
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const avatarInputRef = useRef<HTMLInputElement>(null);

  // Sync form when user changes
  useEffect(() => {
    if (user) {
      setProfileName(user.name);
      setProfileEmail(user.email || '');
      setProfilePhone(user.phone || '');
      setProfileCity(user.city_name || '');
      setProfileLegalName(user.legal_name || '');
      setProfileContactPerson(user.contact_person || '');
      setProfileWarehouseAddress(user.warehouse_address || '');
      setProfileDescription(user.description || '');
      setProfileWorkFrom(user.working_hours_from || '');
      setProfileWorkTo(user.working_hours_to || '');
      setProfileMinOrder(user.min_order_amount?.toString() || '');
    }
  }, [user]);

  const handleSaveProfile = async () => {
    if (!user) return;
    try {
      const result = await updateProfile({
        name: profileName || undefined,
        email: profileEmail || undefined,
        phone: profilePhone || undefined,
        city_name: profileCity || undefined,
        legal_name: profileLegalName || undefined,
        contact_person: profileContactPerson || undefined,
        warehouse_address: profileWarehouseAddress || undefined,
        description: profileDescription || undefined,
        working_hours_from: profileWorkFrom || undefined,
        working_hours_to: profileWorkTo || undefined,
        min_order_amount: profileMinOrder ? parseFloat(profileMinOrder) : undefined,
      }).unwrap();

      dispatch(setUser({
        ...user,
        name: result.name,
        email: result.email,
        phone: result.phone || undefined,
        city_name: result.city_name || undefined,
        legal_name: result.legal_name || undefined,
        contact_person: result.contact_person || undefined,
        warehouse_address: result.warehouse_address || undefined,
        description: result.description || undefined,
        working_hours_from: result.working_hours_from || undefined,
        working_hours_to: result.working_hours_to || undefined,
        min_order_amount: result.min_order_amount || undefined,
        avatar_url: result.avatar_url || undefined,
      }));
      showToast('Профиль сохранён', 'success');
    } catch (error: any) {
      const detail = error?.data?.detail;
      showToast(typeof detail === 'string' ? detail : 'Ошибка сохранения профиля', 'error');
    }
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !user) return;

    setIsUploadingAvatar(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const token = localStorage.getItem('access_token');
      const res = await fetch(`${API_BASE}/auth/me/avatar`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();

      dispatch(setUser({ ...user, avatar_url: data.avatar_url }));
      showToast('Аватар обновлён', 'success');
    } catch {
      showToast('Ошибка загрузки аватара', 'error');
    } finally {
      setIsUploadingAvatar(false);
    }
  };

  // Sync tab from URL
  useEffect(() => {
    const tab = searchParams.get('tab') as TabId | null;
    if (tab && ['assortment', 'upload', 'orders', 'profile'].includes(tab)) {
      setActiveTab(tab);
    }
  }, [searchParams]);

  // Fetch orders and metrics
  const { data: ordersData, isLoading: ordersLoading } = useGetSupplierOrdersQuery(
    { supplier_id: user?.id || '', status: statusFilter, limit: 50 },
    { skip: !user?.id || user.role !== 'seller' }
  );

  const { data: orderMetrics } = useGetOrderMetricsQuery(user?.id || '', {
    skip: !user?.id || user.role !== 'seller',
  });

  const [confirmOrder, { isLoading: isConfirming }] = useConfirmOrderMutation();
  const [rejectOrder] = useRejectOrderMutation();
  const [assembleOrder, { isLoading: isAssembling }] = useAssembleOrderMutation();

  const handleConfirm = async (orderId: string) => {
    if (!user) return;
    try {
      await confirmOrder({ supplier_id: user.id, order_id: orderId }).unwrap();
      showToast('Заказ подтверждён', 'success');
    } catch {
      showToast('Ошибка при подтверждении заказа', 'error');
    }
  };

  const handleReject = async (orderId: string, reason: string) => {
    if (!user) return;
    try {
      await rejectOrder({ supplier_id: user.id, order_id: orderId, reason }).unwrap();
      setRejectingOrder(null);
      showToast('Заказ отклонён', 'success');
    } catch {
      showToast('Ошибка при отклонении заказа', 'error');
    }
  };

  const handleAssemble = async (orderId: string) => {
    if (!user) return;
    try {
      await assembleOrder({ supplier_id: user.id, order_id: orderId }).unwrap();
      showToast('Заказ собран', 'success');
    } catch {
      showToast('Ошибка при сборке заказа', 'error');
    }
  };

  // Tabs configuration
  const tabs = [
    { id: 'assortment', label: 'Ассортимент', icon: BoxIcon },
    { id: 'upload', label: 'Загрузка прайса', icon: UploadIcon },
    {
      id: 'orders',
      label: 'Заказы',
      icon: ClipboardIcon,
      badge: orderMetrics?.pending,
    },
    { id: 'profile', label: 'Профиль', icon: UserIcon },
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

  const getInitials = (name: string) => name.slice(0, 2).toUpperCase();

  const resetProfileForm = () => {
    if (!user) return;
    setProfileName(user.name);
    setProfileEmail(user.email || '');
    setProfilePhone(user.phone || '');
    setProfileCity(user.city_name || '');
    setProfileLegalName(user.legal_name || '');
    setProfileContactPerson(user.contact_person || '');
    setProfileWarehouseAddress(user.warehouse_address || '');
    setProfileDescription(user.description || '');
    setProfileWorkFrom(user.working_hours_from || '');
    setProfileWorkTo(user.working_hours_to || '');
    setProfileMinOrder(user.min_order_amount?.toString() || '');
  };

  return (
    <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Кабинет продавца</h1>

      {/* Tab Navigation */}
      <div className="bg-white border-b border-gray-100 rounded-t-2xl mb-6">
        <nav className="flex gap-1 px-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id as TabId);
                setSearchParams({ tab: tab.id }, { replace: true });
              }}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors relative ${
                activeTab === tab.id
                  ? 'text-primary-600 tab-active'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.icon}
              {tab.label}
              {tab.badge !== undefined && tab.badge > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-xs font-bold rounded-full bg-amber-100 text-amber-700">
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* ═══════════ ASSORTMENT TAB ═══════════ */}
      {activeTab === 'assortment' && (
        <AssortmentTab supplierId={user.id} />
      )}

      {/* ═══════════ UPLOAD TAB ═══════════ */}
      {activeTab === 'upload' && (
        <div className="grid lg:grid-cols-2 gap-6">
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Загрузка прайс-листа</h3>
            <PriceListUpload showHistory={false} />
            <div className="mt-6 p-4 bg-sky-50 border border-sky-200 rounded-xl">
              <h4 className="text-sm font-semibold text-sky-800 mb-2">Подсказки по формату</h4>
              <ul className="text-sm text-sky-700 space-y-1">
                <li>• Первая строка — заголовки: Название, Сорт, Цвет, Длина, Цена, Упаковка</li>
                <li>• Цена указывается за штуку в рублях</li>
                <li>• Длина стебля — число в сантиметрах</li>
                <li>• Один файл на одну загрузку</li>
              </ul>
            </div>
          </Card>
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">История загрузок</h3>
            <ImportHistory supplierId={user.id} compact />
          </Card>
        </div>
      )}

      {/* ═══════════ ORDERS TAB ═══════════ */}
      {activeTab === 'orders' && (
        <div>
          {/* Stats Pills */}
          {orderMetrics && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <div className="bg-white rounded-2xl p-4 shadow-sm">
                <p className="text-sm text-gray-500">Новые</p>
                <p className="text-2xl font-bold text-amber-600">{orderMetrics.pending}</p>
              </div>
              <div className="bg-white rounded-2xl p-4 shadow-sm">
                <p className="text-sm text-gray-500">Подтверждённые</p>
                <p className="text-2xl font-bold text-primary-600">{orderMetrics.confirmed}</p>
              </div>
              <div className="bg-white rounded-2xl p-4 shadow-sm">
                <p className="text-sm text-gray-500">Собранные</p>
                <p className="text-2xl font-bold text-sky-600">{orderMetrics.assembled}</p>
              </div>
              <div className="bg-white rounded-2xl p-4 shadow-sm">
                <p className="text-sm text-gray-500">За месяц</p>
                <p className="text-2xl font-bold text-gray-900">
                  {parseFloat(orderMetrics.total_revenue || '0').toLocaleString()} ₽
                </p>
              </div>
            </div>
          )}

          {/* Status Filter Pills */}
          <div className="flex gap-2 mb-6 flex-wrap">
            {[
              { value: undefined, label: 'Все' },
              { value: 'pending', label: 'Новые' },
              { value: 'confirmed', label: 'Подтверждённые' },
              { value: 'assembled', label: 'Собранные' },
              { value: 'rejected', label: 'Отклонённые' },
            ].map((filter) => (
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
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto" />
            </Card>
          ) : !ordersData || ordersData.length === 0 ? (
            <Card className="p-12 text-center text-gray-500">
              <p className="text-lg mb-2">Заказов нет</p>
              <p className="text-sm">Входящие заказы появятся здесь</p>
            </Card>
          ) : (
            <div className="space-y-4">
              {ordersData.map((order) => {
                const cfg = statusConfig[order.status] || statusConfig.pending;
                const isExpanded = expandedOrder === order.id;

                return (
                  <div
                    key={order.id}
                    className={`bg-white rounded-2xl shadow-sm overflow-hidden border-l-4 ${cfg.borderColor} ${cfg.dimCard ? 'opacity-70' : ''}`}
                  >
                    {/* Order header — clickable */}
                    <button
                      onClick={() => setExpandedOrder(isExpanded ? null : order.id)}
                      className="w-full px-5 py-4 flex items-center gap-4 text-left hover:bg-gray-50/50 transition-colors"
                    >
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${cfg.iconBg}`}>
                        {cfg.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="font-semibold text-gray-900">#{order.id.slice(0, 4)}</span>
                          <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${cfg.badgeBg}`}>
                            {cfg.label}
                          </span>
                        </div>
                        <p className="text-sm text-gray-500">
                          {new Date(order.created_at).toLocaleString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                          {order.buyer && ` · ${order.buyer.name}`}
                        </p>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <p className={`text-lg font-bold ${order.status === 'cancelled' ? 'line-through text-gray-400' : 'text-gray-900'}`}>
                          {parseFloat(order.total_amount).toLocaleString()} ₽
                        </p>
                        <p className="text-xs text-gray-500">{order.items_count || order.items?.length || 0} позиций</p>
                      </div>
                      <svg className={`w-5 h-5 text-gray-400 transition-transform flex-shrink-0 ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>

                    {/* Expandable details */}
                    {isExpanded && (
                      <div className="px-5 py-4 bg-gray-50 border-t border-gray-100">
                        {order.items && order.items.length > 0 && (
                          <div className="mb-4">
                            <h4 className="text-sm font-medium text-gray-700 mb-2">Позиции заказа</h4>
                            <div className="space-y-1.5">
                              {order.items.map((item) => (
                                <div key={item.id} className="flex justify-between text-sm">
                                  <span className="text-gray-600">
                                    Позиция #{item.offer_id.slice(0, 8)} — {item.quantity} шт × {parseFloat(item.unit_price).toLocaleString()} ₽
                                  </span>
                                  <span className="font-medium text-gray-900">
                                    {parseFloat(item.total_price).toLocaleString()} ₽
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {order.delivery_address && (
                          <p className="text-sm text-gray-600 mb-1">
                            <span className="font-medium">Адрес:</span> {order.delivery_address}
                          </p>
                        )}
                        {order.delivery_date && (
                          <p className="text-sm text-gray-600 mb-1">
                            <span className="font-medium">Дата доставки:</span>{' '}
                            {new Date(order.delivery_date).toLocaleDateString('ru-RU')}
                          </p>
                        )}
                        {order.notes && (
                          <div className="mt-2 p-3 bg-white rounded-xl text-sm text-gray-700 border border-gray-200">
                            {order.notes}
                          </div>
                        )}

                        {order.buyer && (
                          <div className="mt-3 flex items-center gap-2 text-sm text-gray-600">
                            <span className="font-medium">Покупатель:</span>
                            {order.buyer.name}
                            {order.buyer.phone && (
                              <a href={`tel:${order.buyer.phone}`} className="text-primary-600 hover:underline ml-1">
                                {order.buyer.phone}
                              </a>
                            )}
                          </div>
                        )}

                        {order.status === 'rejected' && order.rejection_reason && (
                          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
                            Причина отклонения: {order.rejection_reason}
                          </div>
                        )}

                        {order.status === 'assembled' && (
                          <div className="mt-3 text-sm text-sky-700">
                            Ожидает самовывоза покупателем
                          </div>
                        )}

                        {order.status === 'cancelled' && (
                          <div className="mt-3 text-sm text-gray-500">
                            Заказ отменён
                          </div>
                        )}

                        {/* Action buttons */}
                        <div className="flex gap-3 mt-4 pt-3 border-t border-gray-200">
                          {order.status === 'pending' && (
                            <>
                              <Button variant="success" size="sm" onClick={() => handleConfirm(order.id)} disabled={isConfirming}>
                                Подтвердить
                              </Button>
                              {order.buyer?.phone && (
                                <a href={`tel:${order.buyer.phone}`} className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-xl hover:bg-gray-50">
                                  Связаться
                                </a>
                              )}
                              <Button variant="danger" size="sm" onClick={() => setRejectingOrder(order.id)}>
                                Отклонить
                              </Button>
                            </>
                          )}
                          {order.status === 'confirmed' && (
                            <>
                              <button
                                onClick={() => handleAssemble(order.id)}
                                disabled={isAssembling}
                                className="inline-flex items-center px-4 py-1.5 text-sm font-medium text-white bg-sky-500 hover:bg-sky-600 rounded-xl transition-colors disabled:opacity-50"
                              >
                                Собран
                              </button>
                              {order.buyer?.phone && (
                                <a href={`tel:${order.buyer.phone}`} className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-xl hover:bg-gray-50">
                                  Связаться
                                </a>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ═══════════ PROFILE TAB ═══════════ */}
      {activeTab === 'profile' && (
        <div className="space-y-6">
          {/* Avatar + Company name header */}
          <Card className="p-6">
            <div className="flex items-center gap-6">
              <div className="relative group">
                <div className="w-20 h-20 rounded-2xl bg-primary-100 flex items-center justify-center text-primary-700 text-2xl font-bold overflow-hidden">
                  {user.avatar_url ? (
                    <img src={`${API_BASE}${user.avatar_url}`} alt="" className="w-full h-full object-cover" />
                  ) : (
                    getInitials(user.name)
                  )}
                </div>
                <button
                  onClick={() => avatarInputRef.current?.click()}
                  disabled={isUploadingAvatar}
                  className="absolute inset-0 bg-black/40 rounded-2xl flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                >
                  <span className="text-white">{CameraIcon}</span>
                </button>
                <input
                  ref={avatarInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleAvatarUpload}
                  className="hidden"
                />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">{user.name}</h2>
                <p className="text-sm text-gray-500">Нажмите на аватар для загрузки логотипа</p>
              </div>
            </div>
          </Card>

          {/* Company info form */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">Информация о компании</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Название компании</label>
                <input type="text" value={profileName} onChange={(e) => setProfileName(e.target.value)}
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Юридическое название</label>
                <input type="text" value={profileLegalName} onChange={(e) => setProfileLegalName(e.target.value)} placeholder='ООО «Флора Плюс»'
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Контактное лицо</label>
                <input type="text" value={profileContactPerson} onChange={(e) => setProfileContactPerson(e.target.value)} placeholder="Иванов Пётр Сергеевич"
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Телефон</label>
                <input type="tel" value={profilePhone} onChange={(e) => setProfilePhone(e.target.value)} placeholder="+7 (999) 123-45-67"
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input type="email" value={profileEmail} onChange={(e) => setProfileEmail(e.target.value)}
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Город</label>
                <input type="text" value={profileCity} onChange={(e) => setProfileCity(e.target.value)} placeholder="Москва"
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all" />
              </div>
            </div>

            <div className="mt-5">
              <label className="block text-sm font-medium text-gray-700 mb-1">Адрес склада / самовывоза</label>
              <input type="text" value={profileWarehouseAddress} onChange={(e) => setProfileWarehouseAddress(e.target.value)} placeholder="г. Москва, ул. Цветочная, д. 15, стр. 2"
                className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all" />
            </div>

            <div className="mt-5">
              <label className="block text-sm font-medium text-gray-700 mb-1">Описание компании</label>
              <textarea value={profileDescription} onChange={(e) => setProfileDescription(e.target.value)} placeholder="Расскажите о вашей компании..." rows={3}
                className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all resize-none" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Время работы с</label>
                <input type="time" value={profileWorkFrom} onChange={(e) => setProfileWorkFrom(e.target.value)}
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Время работы до</label>
                <input type="time" value={profileWorkTo} onChange={(e) => setProfileWorkTo(e.target.value)}
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Минимальный заказ, ₽</label>
                <input type="number" value={profileMinOrder} onChange={(e) => setProfileMinOrder(e.target.value)} placeholder="3000"
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all" />
                <p className="mt-1 text-xs text-gray-400">Оставьте пустым, если ограничений нет</p>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-8 pt-6 border-t border-gray-100">
              <Button variant="secondary" onClick={resetProfileForm}>Отмена</Button>
              <Button onClick={handleSaveProfile} disabled={isSavingProfile}>
                {isSavingProfile ? 'Сохранение...' : 'Сохранить'}
              </Button>
            </div>
          </Card>

          {/* Danger zone */}
          <Card className="p-6 border-2 border-red-200">
            <h3 className="text-lg font-semibold text-red-700 mb-2">Опасная зона</h3>
            <p className="text-sm text-gray-600 mb-4">
              Удаление аккаунта необратимо. Все данные, включая историю заказов и ассортимент, будут удалены.
            </p>
            <Button variant="danger" size="sm">Удалить аккаунт</Button>
          </Card>
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
