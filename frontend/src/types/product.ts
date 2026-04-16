export interface Supplier {
  id: string;
  name: string;
  warehouse_address?: string | null;
}

// ── New product types (flat, no joins) ──

export interface CatalogProduct {
  id: string;
  supplier: Supplier;
  title: string;
  flower_type: string | null;
  variety: string | null;
  length_cm: number | null;
  color: string | null;
  origin_country: string | null;
  pack_type: string | null;
  pack_qty: number | null;
  photo_url: string | null;
  price: number;
  currency: string;
  stock_qty: number | null;
  created_at: string;
}

export interface ProductsResponse {
  products: CatalogProduct[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProductFilters {
  q?: string;
  product_type?: string;  // kept for backward compat with filtersSlice
  flower_type?: string;
  variety?: string;
  length_cm?: number;
  length_min?: number;
  length_max?: number;
  price_min?: number;
  price_max?: number;
  supplier_id?: string;
  color?: string;
  origin_country?: string[];
  colors?: string[];
  in_stock?: boolean;
  sort_by?: string;
  limit?: number;
  offset?: number;
}

// ── Legacy types (kept for backward compat) ──

export interface NormalizedSKU {
  id: string;
  product_type: string;
  variety: string | null;
  title: string;
  color?: string | null;
}

export interface Offer {
  id: string;
  supplier: Supplier;
  sku: NormalizedSKU;
  display_title: string | null;
  length_cm: number | null;
  pack_type: string | null;
  pack_qty: number | null;
  price_type: string;
  price_min: number;
  price_max: number | null;
  currency: string;
  tier_min_qty: number | null;
  tier_max_qty: number | null;
  availability: string;
  stock_qty: number | null;
  published_at: string;
  origin_country: string | null;
  colors: string[];
  photo_url: string | null;
}

export interface OffersResponse {
  offers: Offer[];
  total: number;
  limit: number;
  offset: number;
}
