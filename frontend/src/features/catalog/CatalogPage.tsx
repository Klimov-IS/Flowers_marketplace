import { useState, useEffect } from 'react';
import { useGetOffersQuery } from './catalogApi';
import { useAppSelector } from '../../hooks/useAppSelector';
import { useAppDispatch } from '../../hooks/useAppDispatch';
import { setSearchQuery, setProductType, resetFilters } from './filtersSlice';
import { addToCart } from '../buyer/cartSlice';
import { useDebounce } from '../../hooks/useDebounce';
import Card from '../../components/ui/Card';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';
import { getFlowerImage, getDefaultFlowerImage } from '../../utils/flowerImages';

export default function CatalogPage() {
  const dispatch = useAppDispatch();
  const filters = useAppSelector((state) => state.filters);
  const [searchInput, setSearchInput] = useState(filters.q || '');
  const debouncedSearch = useDebounce(searchInput, 300);
  const [quantities, setQuantities] = useState<Record<string, number>>({});

  // Update search filter when debounced value changes
  useEffect(() => {
    dispatch(setSearchQuery(debouncedSearch));
  }, [debouncedSearch, dispatch]);

  const { data, isLoading, error } = useGetOffersQuery(filters);

  const productTypes = [
    { value: undefined, label: 'Все' },
    { value: 'rose', label: 'Розы' },
    { value: 'tulip', label: 'Тюльпаны' },
    { value: 'peony', label: 'Пионы' },
    { value: 'hydrangea', label: 'Гортензия' },
    { value: 'chrysanthemum', label: 'Хризантема' },
  ];

  const handleAddToCart = (offerId: string) => {
    const offer = data?.offers.find((o) => o.id === offerId);
    if (!offer) return;

    const quantity = quantities[offerId] || 1;
    // Use display_title for clean name, fallback to sku.title
    const productName = offer.display_title || offer.sku.title;

    dispatch(
      addToCart({
        supplier_id: offer.supplier.id,
        supplier_name: offer.supplier.name,
        item: {
          product_id: offer.sku.id,
          offer_id: offer.id,
          name: productName,
          price: offer.price_min,
          quantity,
          stock: offer.stock_qty || undefined,
          length_cm: offer.length_cm || undefined,
        },
      })
    );

    // Reset quantity after adding
    setQuantities((prev) => ({ ...prev, [offerId]: 1 }));
    alert(`Добавлено в корзину: ${productName} (${quantity} шт)`);
  };

  const getQuantity = (offerId: string) => quantities[offerId] || 1;

  const setQuantity = (offerId: string, qty: number) => {
    setQuantities((prev) => ({ ...prev, [offerId]: Math.max(1, qty) }));
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-primary-600 to-purple-600 rounded-lg p-12 text-white mb-8">
        <h1 className="text-4xl font-bold mb-4">
          Самый быстрый поиск и закупка цветов для вашего бизнеса
        </h1>
        <p className="text-xl opacity-90">
          Единая платформа для поставщиков и флористов. Найдите лучшие предложения за 5 минут.
        </p>
      </div>

      {/* Search & Filters */}
      <Card className="p-6 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <Input
              type="search"
              placeholder="Поиск по названию, сорту или поставщику..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
          </div>
          <Button variant="secondary" onClick={() => dispatch(resetFilters())}>
            Сбросить фильтры
          </Button>
        </div>

        {/* Product Type Pills */}
        <div className="flex flex-wrap gap-2 mt-4">
          {productTypes.map((type) => (
            <button
              key={type.label}
              onClick={() => dispatch(setProductType(type.value))}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                filters.product_type === type.value
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {type.label}
            </button>
          ))}
        </div>
      </Card>

      {/* Results */}
      <div className="mb-4">
        <p className="text-gray-600">
          {isLoading ? 'Загрузка...' : `Найдено: ${data?.total || 0} товаров`}
        </p>
      </div>

      {/* Products Grid */}
      {isLoading && (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
        </div>
      )}

      {error && (
        <Card className="p-6 text-center text-red-600">
          Ошибка загрузки данных. Проверьте подключение к API.
        </Card>
      )}

      {data && data.offers.length === 0 && (
        <Card className="p-12 text-center text-gray-500">
          <p className="text-lg">Товары не найдены</p>
          <p className="mt-2">Попробуйте изменить фильтры или поисковый запрос</p>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {data?.offers.map((offer) => (
          <Card key={offer.id} className="p-4">
            <div className="aspect-square bg-gray-100 rounded-lg mb-4 overflow-hidden">
              <img
                src={getFlowerImage(offer.sku.product_type)}
                alt={offer.display_title || offer.sku.title}
                className="w-full h-full object-cover"
                loading="lazy"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = getDefaultFlowerImage();
                }}
              />
            </div>
            <h3 className="font-semibold text-gray-900 mb-1">
              {offer.display_title || offer.sku.title}
            </h3>
            <p className="text-sm text-gray-600 mb-2">{offer.supplier.name}</p>

            {offer.length_cm && (
              <p className="text-xs text-gray-500 mb-2">Длина: {offer.length_cm} см</p>
            )}

            <div className="flex justify-between items-center mb-3">
              <span className="text-2xl font-bold text-primary-600">
                {offer.price_min} ₽
              </span>
              {offer.stock_qty && (
                <span className="text-xs text-gray-500">Остаток: {offer.stock_qty}</span>
              )}
            </div>

            {/* Quantity Controls */}
            <div className="flex items-center gap-2 mb-3">
              <button
                onClick={() => setQuantity(offer.id, getQuantity(offer.id) - 1)}
                className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center text-gray-700"
              >
                −
              </button>
              <input
                type="number"
                min="1"
                value={getQuantity(offer.id)}
                onChange={(e) => setQuantity(offer.id, parseInt(e.target.value) || 1)}
                className="w-16 text-center border border-gray-300 rounded px-2 py-1"
              />
              <button
                onClick={() => setQuantity(offer.id, getQuantity(offer.id) + 1)}
                className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center text-gray-700"
              >
                +
              </button>
            </div>

            <Button
              className="w-full"
              size="sm"
              onClick={() => handleAddToCart(offer.id)}
            >
              В корзину
            </Button>
          </Card>
        ))}
      </div>
    </div>
  );
}
