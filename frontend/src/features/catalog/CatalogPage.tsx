import { useState, useEffect, useCallback } from 'react';
import { useGetOffersQuery } from './catalogApi';
import { useAppSelector } from '../../hooks/useAppSelector';
import { useAppDispatch } from '../../hooks/useAppDispatch';
import {
  setSearchQuery,
  setProductType,
  setOriginCountry,
  setColors,
  setInStock,
  setLengthRange,
  setSortBy,
  setPage,
  resetFilters,
} from './filtersSlice';
import { addToCart } from '../buyer/cartSlice';
import { useDebounce } from '../../hooks/useDebounce';
import FilterSidebar, { MobileFilterDrawer } from './components/FilterSidebar';
import { getFlowerImage } from '../../utils/flowerImages';
import { formatTier } from '../../utils/catalogFormatters';
import type { OffersResponse, ProductFilters } from '../../types/product';
import type { AppDispatch } from '../../app/store';

function resolvePhotoUrl(url: string): string {
  const basePath = (import.meta.env.BASE_URL || '/').replace(/\/$/, '');
  let resolved = url;
  if (basePath && url.startsWith('/uploads')) {
    resolved = basePath + url;
  }
  return resolved;
}

// ── Constants ───────────────────────────────────────────────────────────────

const CATEGORIES = [
  { label: 'Все', value: undefined },
  { label: 'Розы', value: 'Роза' },
  { label: 'Тюльпаны', value: 'Тюльпан' },
  { label: 'Хризантемы', value: 'Хризантема' },
  { label: 'Гвоздики', value: 'Гвоздика' },
  { label: 'Герберы', value: 'Гербера' },
  { label: 'Лилии', value: 'Лилия' },
  { label: 'Гортензии', value: 'Гортензия' },
  { label: 'Эустома', value: 'Эустома' },
  { label: 'Зелень', value: 'Зелень' },
];

const SORT_OPTIONS = [
  { value: 'default', label: 'По популярности' },
  { value: 'price_asc', label: 'Цена: по возрастанию' },
  { value: 'price_desc', label: 'Цена: по убыванию' },
  { value: 'newest', label: 'Новинки' },
];

// ── SVG Icons ───────────────────────────────────────────────────────────────

function SearchIcon() {
  return (
    <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
    </svg>
  );
}

function FilterIcon() {
  return (
    <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75" />
    </svg>
  );
}

function CartIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007z" />
    </svg>
  );
}

function ChevronLeftIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

function ResetIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
    </svg>
  );
}

// ── Skeleton Loading ────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
      <div className="aspect-[4/5] bg-gray-200 animate-pulse" />
      <div className="p-4 space-y-3">
        <div className="h-4 bg-gray-200 rounded-lg animate-pulse w-3/4" />
        <div className="h-3 bg-gray-200 rounded-lg animate-pulse w-1/2" />
        <div className="h-7 bg-gray-200 rounded-lg animate-pulse w-1/3" />
        <div className="h-3 bg-gray-200 rounded-lg animate-pulse w-1/4" />
        <div className="h-8 bg-gray-200 rounded-lg animate-pulse w-full" />
        <div className="h-10 bg-gray-200 rounded-xl animate-pulse w-full" />
      </div>
    </div>
  );
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

// ── Pagination ──────────────────────────────────────────────────────────────

function CatalogPagination({
  data,
  filters,
  dispatch,
}: {
  data: OffersResponse | undefined;
  filters: ProductFilters;
  dispatch: AppDispatch;
}) {
  if (!data || data.total <= (filters.limit || 24)) return null;

  const perPage = filters.limit || 24;
  const totalPages = Math.ceil(data.total / perPage);
  const currentPage = Math.floor((filters.offset || 0) / perPage);

  const pages: (number | 'dots')[] = [];
  const visible = Array.from({ length: totalPages }, (_, i) => i)
    .filter((p) => p === 0 || p === totalPages - 1 || Math.abs(p - currentPage) <= 2);
  for (let i = 0; i < visible.length; i++) {
    if (i > 0 && visible[i] - visible[i - 1] > 1) {
      pages.push('dots');
    }
    pages.push(visible[i]);
  }

  return (
    <div className="flex items-center justify-center gap-1.5 mt-10">
      <button
        onClick={() => dispatch(setPage(currentPage - 1))}
        disabled={currentPage === 0}
        className="px-3 py-2 text-sm border border-gray-200 rounded-xl hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        <ChevronLeftIcon />
      </button>
      {pages.map((item, idx) =>
        item === 'dots' ? (
          <span key={`dots-${idx}`} className="px-1 text-gray-400">...</span>
        ) : (
          <button
            key={item}
            onClick={() => dispatch(setPage(item))}
            className={`w-9 h-9 text-sm rounded-xl font-medium ${
              item === currentPage
                ? 'bg-primary-500 text-white'
                : 'border border-gray-200 hover:bg-gray-50 transition-colors'
            }`}
          >
            {item + 1}
          </button>
        )
      )}
      <button
        onClick={() => dispatch(setPage(currentPage + 1))}
        disabled={currentPage >= totalPages - 1}
        className="px-3 py-2 text-sm border border-gray-200 rounded-xl hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        <ChevronRightIcon />
      </button>
    </div>
  );
}

// ── Active Filter Chips ─────────────────────────────────────────────────────

function ActiveFilterChips({
  filters,
  dispatch,
}: {
  filters: ProductFilters & { sortBy?: string };
  dispatch: AppDispatch;
}) {
  const chips: { label: string; onRemove: () => void }[] = [];

  if (filters.origin_country?.length) {
    for (const c of filters.origin_country) {
      chips.push({
        label: c,
        onRemove: () => {
          const updated = filters.origin_country!.filter((x) => x !== c);
          dispatch(setOriginCountry(updated.length > 0 ? updated : undefined));
        },
      });
    }
  }

  if (filters.colors?.length) {
    for (const c of filters.colors) {
      chips.push({
        label: c,
        onRemove: () => {
          const updated = filters.colors!.filter((x) => x !== c);
          dispatch(setColors(updated.length > 0 ? updated : undefined));
        },
      });
    }
  }

  if (filters.length_min !== undefined || filters.length_max !== undefined) {
    const label = filters.length_min === filters.length_max
      ? `${filters.length_min} см`
      : filters.length_max === undefined
        ? `${filters.length_min}+ см`
        : `${filters.length_min}–${filters.length_max} см`;
    chips.push({
      label,
      onRemove: () => dispatch(setLengthRange({ min: undefined, max: undefined })),
    });
  }

  if (filters.in_stock) {
    chips.push({
      label: 'В наличии',
      onRemove: () => dispatch(setInStock(undefined)),
    });
  }

  if (chips.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mb-4">
      {chips.map((chip, i) => (
        <span
          key={`${chip.label}-${i}`}
          className="inline-flex items-center gap-1.5 px-3 py-1 bg-primary-50 text-primary-700 rounded-full text-xs font-medium"
        >
          {chip.label}
          <button onClick={chip.onRemove} className="hover:text-primary-900 transition-colors">
            <XIcon />
          </button>
        </span>
      ))}
      <button
        onClick={() => dispatch(resetFilters())}
        className="text-xs text-gray-500 hover:text-gray-700 font-medium px-2 transition-colors"
      >
        Сбросить все
      </button>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────────────────────────────

export default function CatalogPage() {
  const dispatch = useAppDispatch();
  const filters = useAppSelector((state) => state.filters);
  const [searchInput, setSearchInput] = useState(filters.q || '');
  const debouncedSearch = useDebounce(searchInput, 300);
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  useEffect(() => {
    dispatch(setSearchQuery(debouncedSearch));
  }, [debouncedSearch, dispatch]);

  const { data, isLoading, error } = useGetOffersQuery(filters);

  // ── Cart handlers ───────────────────────────────────────────────────────
  const handleAddToCart = (offerId: string) => {
    const offer = data?.offers.find((o) => o.id === offerId);
    if (!offer) return;

    const qty = quantities[offerId] || 1;
    const isPackSale = !!offer.pack_qty;
    const packQty = offer.pack_qty || 1;
    const actualQuantity = isPackSale ? qty * packQty : qty;
    const productName = offer.display_title || offer.sku.title;

    dispatch(
      addToCart({
        supplier_id: offer.supplier.id,
        supplier_name: offer.supplier.name,
        warehouse_address: offer.supplier.warehouse_address || undefined,
        item: {
          product_id: offer.sku.id,
          offer_id: offer.id,
          name: productName,
          price: offer.price_min,
          quantity: actualQuantity,
          stock: offer.stock_qty || undefined,
          length_cm: offer.length_cm || undefined,
        },
      })
    );

    setQuantities((prev) => ({ ...prev, [offerId]: 1 }));
  };

  const getQuantity = (offerId: string) => quantities[offerId] || 1;
  const setQuantity = (offerId: string, qty: number) => {
    setQuantities((prev) => ({ ...prev, [offerId]: Math.max(1, qty) }));
  };

  // ── Filter handlers ─────────────────────────────────────────────────────
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
        case 'in_stock':
          dispatch(setInStock(value as boolean | undefined));
          break;
        case 'length_range': {
          const range = value as { min?: number; max?: number };
          dispatch(setLengthRange(range));
          break;
        }
      }
    },
    [dispatch]
  );

  const handleResetFilters = useCallback(() => {
    dispatch(resetFilters());
    setSearchInput('');
  }, [dispatch]);

  // Active filter count for mobile badge
  const activeFilterCount =
    (filters.origin_country?.length || 0) +
    (filters.colors?.length || 0) +
    (filters.length_min !== undefined ? 1 : 0) +
    (filters.in_stock ? 1 : 0);

  return (
    <div className="bg-white min-h-screen">
      {/* ── Sticky Sub-Header: Search + Category Pills ──────────────── */}
      <div className="sticky top-16 z-40 bg-white/95 backdrop-blur-md border-b border-gray-100">
        {/* Search bar */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center gap-3">
            <div className="flex-1 relative">
              <SearchIcon />
              <input
                type="search"
                placeholder="Поиск по названию, сорту или поставщику..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-gray-100 border border-transparent rounded-xl text-sm placeholder:text-gray-400 focus:outline-none focus:bg-white focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition-all"
              />
            </div>
            {/* Mobile filter button */}
            <button
              onClick={() => setMobileFiltersOpen(true)}
              className="lg:hidden p-2.5 rounded-xl bg-gray-100 hover:bg-gray-200 transition-colors relative"
            >
              <FilterIcon />
              {activeFilterCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-primary-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                  {activeFilterCount}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Category pills */}
        <div className="border-t border-gray-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex gap-2 py-2.5 overflow-x-auto" style={{ scrollbarWidth: 'none' }}>
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.label}
                  onClick={() => dispatch(setProductType(cat.value))}
                  className={`shrink-0 px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
                    filters.product_type === cat.value
                      ? 'bg-primary-500 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Main Content ────────────────────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex gap-6">
          {/* Sidebar (desktop) */}
          <FilterSidebar
            filters={{
              product_type: filters.product_type,
              origin_country: filters.origin_country,
              colors: filters.colors,
              in_stock: filters.in_stock,
              length_min: filters.length_min,
              length_max: filters.length_max,
            }}
            onFilterChange={handleFilterChange}
            onReset={handleResetFilters}
          />

          {/* Products area */}
          <div className="flex-1 min-w-0">
            {/* Results bar */}
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-gray-500">
                Найдено{' '}
                <span className="font-semibold text-gray-900">{data?.total || 0}</span>{' '}
                товаров
              </p>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500 hidden sm:inline">Сортировка:</span>
                <select
                  value={filters.sortBy}
                  onChange={(e) => dispatch(setSortBy(e.target.value))}
                  className="text-sm border border-gray-200 rounded-xl px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all cursor-pointer"
                >
                  {SORT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Active filter chips */}
            <ActiveFilterChips filters={filters} dispatch={dispatch} />

            {/* Loading state */}
            {isLoading && <SkeletonGrid />}

            {/* Error state */}
            {error && (
              <div className="bg-white rounded-2xl shadow-sm p-6 text-center text-red-600">
                Ошибка загрузки данных. Проверьте подключение к API.
              </div>
            )}

            {/* Empty state */}
            {data && data.offers.length === 0 && !isLoading && (
              <div className="bg-white rounded-2xl shadow-sm p-12 sm:p-16 text-center">
                <div className="text-6xl mb-4">&#128270;</div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Ничего не найдено</h3>
                <p className="text-sm text-gray-500 mb-6 max-w-md mx-auto">
                  Попробуйте изменить фильтры или поисковый запрос. Возможно, товар временно отсутствует.
                </p>
                <button
                  onClick={handleResetFilters}
                  className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 active:scale-[0.97] text-white font-medium px-6 py-2.5 rounded-xl text-sm transition-all duration-150"
                >
                  <ResetIcon />
                  Сбросить фильтры
                </button>
              </div>
            )}

            {/* Products grid */}
            {!isLoading && data && data.offers.length > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-4">
                {data.offers.map((offer) => {
                  const tierInfo = formatTier(offer.tier_min_qty, offer.tier_max_qty);
                  const isPackSale = !!offer.pack_qty;
                  const packQty = offer.pack_qty || 1;
                  const pricePerUnit = Number(offer.price_min) || 0;
                  const packPrice = isPackSale ? pricePerUnit * packQty : null;
                  const unitLabel = isPackSale ? 'упак.' : 'шт';
                  const quantity = getQuantity(offer.id);
                  const totalQty = isPackSale ? quantity * packQty : quantity;
                  const totalPrice = totalQty * pricePerUnit;

                  // Metadata line: "60 см · Эквадор"
                  const metaParts: string[] = [];
                  if (offer.length_cm) metaParts.push(`${offer.length_cm} см`);
                  if (offer.origin_country) metaParts.push(offer.origin_country);
                  const metaLine = metaParts.join(' · ');

                  return (
                    <div
                      key={offer.id}
                      className="bg-white rounded-2xl shadow-sm hover:shadow-md transition-shadow duration-200 overflow-hidden group flex flex-col"
                    >
                      {/* Image */}
                      <div className="relative overflow-hidden">
                        <div className="aspect-[4/5] bg-gray-100 overflow-hidden flex items-end justify-center">
                          <img
                            src={offer.photo_url ? resolvePhotoUrl(offer.photo_url) : getFlowerImage(offer.sku.product_type)}
                            alt={offer.display_title || offer.sku.title}
                            className={`transition-transform duration-300 group-hover:scale-105 ${offer.photo_url ? 'w-full h-full object-cover' : 'max-w-full max-h-full object-contain'}`}
                            loading="lazy"
                            onError={(e) => {
                              (e.target as HTMLImageElement).src = getFlowerImage(offer.sku.product_type);
                            }}
                          />
                        </div>
                      </div>

                      {/* Content */}
                      <div className="p-3 sm:p-4 flex flex-col flex-1">
                        <h3 className="font-semibold text-gray-900 text-sm sm:text-base line-clamp-2 mb-1">
                          {offer.display_title || offer.sku.title}
                        </h3>
                        {metaLine && (
                          <p className="text-xs text-gray-500 mb-3">{metaLine}</p>
                        )}

                        <div className="mt-auto">
                          {/* Price block */}
                          <div className="mb-2">
                            <div className="flex items-baseline gap-1">
                              <span className="text-xl sm:text-2xl font-bold text-primary-600">
                                {pricePerUnit} &#8381;
                              </span>
                              <span className="text-xs text-gray-400">/ шт</span>
                            </div>
                            {packPrice && (
                              <p className="text-xs text-gray-500">
                                = {packPrice.toLocaleString('ru-RU')} &#8381; / упак. {packQty} шт
                              </p>
                            )}
                            {tierInfo && (
                              <p className="text-xs text-primary-600 font-medium mt-0.5">{tierInfo}</p>
                            )}
                          </div>

                          {/* Supplier */}
                          <p className="text-[11px] text-gray-400 mb-2">{offer.supplier.name}</p>

                          {/* Quantity controls */}
                          <div className="flex items-center gap-1.5 mb-2">
                            <button
                              onClick={() => setQuantity(offer.id, getQuantity(offer.id) - 1)}
                              className="w-7 h-7 rounded-lg bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-gray-600 transition-colors text-sm font-medium"
                            >
                              &minus;
                            </button>
                            <input
                              type="number"
                              min="1"
                              value={quantity}
                              onChange={(e) => setQuantity(offer.id, parseInt(e.target.value) || 1)}
                              className="w-12 text-center border border-gray-200 rounded-lg py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
                            />
                            <button
                              onClick={() => setQuantity(offer.id, getQuantity(offer.id) + 1)}
                              className="w-7 h-7 rounded-lg bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-gray-600 transition-colors text-sm font-medium"
                            >
                              +
                            </button>
                            <span className="text-xs text-gray-500">{unitLabel}</span>
                          </div>

                          {/* Total */}
                          <p className="text-xs text-gray-600 mb-2.5">
                            {isPackSale ? (
                              <>Итого: {totalQty} шт &times; {pricePerUnit} &#8381; = <span className="font-semibold text-gray-900">{totalPrice.toLocaleString('ru-RU')} &#8381;</span></>
                            ) : (
                              <>Итого: <span className="font-semibold text-gray-900">{totalPrice.toLocaleString('ru-RU')} &#8381;</span></>
                            )}
                          </p>

                          {/* Add to cart */}
                          <button
                            onClick={() => handleAddToCart(offer.id)}
                            className="w-full bg-primary-500 hover:bg-primary-600 active:scale-[0.97] text-white font-medium py-2.5 rounded-xl text-sm transition-all duration-150 flex items-center justify-center gap-2"
                          >
                            <CartIcon />
                            В корзину
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Pagination */}
            <CatalogPagination data={data} filters={filters} dispatch={dispatch} />
          </div>
        </div>
      </main>

      {/* ── Mobile Filter Drawer ────────────────────────────────────── */}
      <MobileFilterDrawer
        open={mobileFiltersOpen}
        onClose={() => setMobileFiltersOpen(false)}
        filters={{
          product_type: filters.product_type,
          origin_country: filters.origin_country,
          colors: filters.colors,
          in_stock: filters.in_stock,
          length_min: filters.length_min,
          length_max: filters.length_max,
        }}
        onFilterChange={handleFilterChange}
        onReset={handleResetFilters}
        totalCount={data?.total || 0}
      />
    </div>
  );
}
