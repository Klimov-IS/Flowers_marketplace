/**
 * Types for Supplier Items (Seller Cabinet)
 */

export interface OfferVariant {
  id: string;
  length_cm: number | null;
  pack_type: string | null;
  pack_qty: number | null;
  price: string;
  price_max: string | null;
  stock: number | null;
  validation: 'ok' | 'warn' | 'error';
}

export interface ItemAttributes {
  flower_type?: string;
  variety?: string;
  origin_country?: string;
  colors?: string[];
  farm?: string;
  _sources?: Record<string, 'ai' | 'manual' | 'parser'>;
  _confidences?: Record<string, number>;
  _locked?: string[];
}

export interface SupplierItem {
  id: string;
  raw_name: string;
  origin_country: string | null;
  colors: string[];
  length_min: number | null;
  length_max: number | null;
  price_min: string | null;
  price_max: string | null;
  stock_total: number;
  status: 'active' | 'ambiguous' | 'rejected';
  source_file: string | null;
  variants_count: number;
  variants: OfferVariant[];
  attributes?: ItemAttributes;
}

export interface SupplierItemsResponse {
  items: SupplierItem[];
  total: number;
  page: number;
  per_page: number;
}

export interface SupplierItemsParams {
  supplier_id: string;
  q?: string;
  page?: number;
  per_page?: number;
}
