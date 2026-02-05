import { useState, useEffect, useCallback } from 'react';
import { useGetOffersQuery } from './catalogApi';
import { useAppSelector } from '../../hooks/useAppSelector';
import { useAppDispatch } from '../../hooks/useAppDispatch';
import {
  setSearchQuery,
  setProductType,
  setLengthRange,
  setPriceRange,
  setOriginCountry,
  setColors,
  setInStock,
  resetFilters,
} from './filtersSlice';
import { addToCart } from '../buyer/cartSlice';
import { useDebounce } from '../../hooks/useDebounce';
import Card from '../../components/ui/Card';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';
import FilterSidebar from './components/FilterSidebar';
import { getFlowerImage, getDefaultFlowerImage } from '../../utils/flowerImages';
import {
  getCountryFlag,
  getCountryName,
  formatPackInfo,
  formatTier,
  formatColors,
} from '../../utils/catalogFormatters';

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

  // Handler for FilterSidebar
  const handleFilterChange = useCallback(
    (key: string, value: unknown) => {
      switch (key) {
        case 'product_type':
          dispatch(setProductType(value as string | undefined));
          break;
        case 'origin_country':
          dispatch(setOriginCountry(value as string[] | undefined));
          break;
        case 'colors':
          dispatch(setColors(value as string[] | undefined));
          break;
        case 'length_min':
          dispatch(setLengthRange({ min: value as number | undefined, max: filters.length_max }));
          break;
        case 'length_max':
          dispatch(setLengthRange({ min: filters.length_min, max: value as number | undefined }));
          break;
        case 'price_min':
          dispatch(setPriceRange({ min: value as number | undefined, max: filters.price_max }));
          break;
        case 'price_max':
          dispatch(setPriceRange({ min: filters.price_min, max: value as number | undefined }));
          break;
        case 'in_stock':
          dispatch(setInStock(value as boolean | undefined));
          break;
      }
    },
    [dispatch, filters.length_min, filters.length_max, filters.price_min, filters.price_max]
  );

  const handleResetFilters = useCallback(() => {
    dispatch(resetFilters());
    setSearchInput('');
  }, [dispatch]);

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

      {/* Main Layout: Sidebar + Content */}
      <div className="flex gap-6">
        {/* Sidebar Filters */}
        <FilterSidebar
          filters={{
            product_type: filters.product_type,
            origin_country: filters.origin_country,
            colors: filters.colors,
            length_min: filters.length_min,
            length_max: filters.length_max,
            price_min: filters.price_min,
            price_max: filters.price_max,
            in_stock: filters.in_stock,
          }}
          onFilterChange={handleFilterChange}
          onReset={handleResetFilters}
        />

        {/* Products Area */}
        <div className="flex-1 min-w-0">
          {/* Search Bar */}
          <div className="mb-4">
            <Input
              type="search"
              placeholder="Поиск по названию, сорту или поставщику..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full"
            />
          </div>

          {/* Results Count */}
          <div className="mb-4">
            <p className="text-gray-600">
              {isLoading ? 'Загрузка...' : `Найдено: ${data?.total || 0} товаров`}
            </p>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            </div>
          )}

          {/* Error State */}
          {error && (
            <Card className="p-6 text-center text-red-600">
              Ошибка загрузки данных. Проверьте подключение к API.
            </Card>
          )}

          {/* Empty State */}
          {data && data.offers.length === 0 && (
            <Card className="p-12 text-center text-gray-500">
              <p className="text-lg">Товары не найдены</p>
              <p className="mt-2">Попробуйте изменить фильтры или поисковый запрос</p>
            </Card>
          )}

          {/* Products Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data?.offers.map((offer) => {
          const packInfo = formatPackInfo(offer.pack_type, offer.pack_qty);
          const tierInfo = formatTier(offer.tier_min_qty, offer.tier_max_qty);
          const colorsText = formatColors(offer.colors);

          return (
            <Card key={offer.id} className="p-4 flex flex-col h-full">
              {/* Image Block */}
              <div className="aspect-square bg-gray-100 rounded-lg mb-3 overflow-hidden flex items-end justify-center">
                <img
                  src={getFlowerImage(offer.sku.product_type)}
                  alt={offer.display_title || offer.sku.title}
                  className="max-w-full max-h-full object-contain"
                  loading="lazy"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = getDefaultFlowerImage();
                  }}
                />
              </div>

              {/* Content Block */}
              <div className="flex-grow">
                {/* Country */}
                {offer.origin_country && (
                  <p className="text-xs text-gray-500 mb-1">
                    <span className="mr-1">{getCountryFlag(offer.origin_country)}</span>
                    {getCountryName(offer.origin_country)}
                  </p>
                )}

                {/* Title */}
                <h3 className="font-semibold text-gray-900 mb-1 line-clamp-2 min-h-[2.5rem]">
                  {offer.display_title || offer.sku.title}
                </h3>

                {/* Colors */}
                {colorsText && (
                  <p className="text-sm text-gray-600 mb-1 truncate">{colorsText}</p>
                )}

                {/* Length & Pack */}
                <p className="text-xs text-gray-500 mb-2">
                  {offer.length_cm && <span>{offer.length_cm} см</span>}
                  {offer.length_cm && packInfo && <span className="mx-1">·</span>}
                  {packInfo && <span>{packInfo}</span>}
                  {!offer.length_cm && !packInfo && <span>—</span>}
                </p>
              </div>

              {/* Footer Block - pinned to bottom */}
              <div className="mt-auto pt-3 border-t border-gray-100">
                {/* Price Block - compact with aligned metrics */}
                <div className="flex justify-between items-start mb-2 min-h-[44px]">
                  <span className="text-2xl font-bold text-primary-600">
                    {offer.price_min} ₽
                  </span>
                  <div className="text-right">
                    <p className="text-xs text-gray-500">
                      {offer.stock_qty ? `Ост: ${offer.stock_qty}` : '—'}
                    </p>
                    {tierInfo && (
                      <p className="text-[10px] text-green-600">{tierInfo}</p>
                    )}
                  </div>
                </div>

                {/* Supplier */}
                <p className="text-xs text-gray-400 mb-2">{offer.supplier.name}</p>

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
              </div>
            </Card>
          );
        })}
          </div>
        </div>
      </div>
    </div>
  );
}
