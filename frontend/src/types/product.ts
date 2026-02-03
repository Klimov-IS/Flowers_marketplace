export interface Supplier {
  id: string;
  name: string;
}

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
}

export interface OffersResponse {
  offers: Offer[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProductFilters {
  q?: string;
  product_type?: string;
  length_cm?: number;
  length_min?: number;
  length_max?: number;
  price_min?: number;
  price_max?: number;
  supplier_id?: string;
  limit?: number;
  offset?: number;
}
