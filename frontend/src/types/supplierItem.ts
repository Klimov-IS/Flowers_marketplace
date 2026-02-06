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
  subtype?: string;      // кустовая, спрей, пионовидная
  variety?: string;
  origin_country?: string;
  colors?: string[];
  farm?: string;
  clean_name?: string;   // Чистое название: Тип + Субтип + Сорт
  _sources?: Record<string, 'ai' | 'manual' | 'parser'>;
  _confidences?: Record<string, number>;
  _locked?: string[];
  // Bundle detection
  is_bundle_list?: boolean;      // Multiple varieties in one row
  bundle_varieties?: string[];   // List of extracted variety names
  needs_review?: boolean;        // Requires manual review
  review_reason?: string;        // Reason for review (bundle_list_detected, garbage_text_detected)
  warnings?: string[];           // Parser warnings
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
  status: 'active' | 'ambiguous' | 'rejected' | 'hidden' | 'deleted';
  source_file: string | null;
  variants_count: number;
  variants: OfferVariant[];
  attributes?: ItemAttributes;
  possible_duplicate?: boolean;  // Items with same flower_type + variety
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
  status?: string[];
  // Additional filters
  origin_country?: (string | null)[];
  colors?: (string | null)[];
  price_min?: number;
  price_max?: number;
  length_min?: number;
  length_max?: number;
  stock_min?: number;
  stock_max?: number;
  // Sorting
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
}

// Sort state for table headers
export interface SortState {
  field: string | null;
  direction: 'asc' | 'desc' | null;
}

// ============================================================================
// Flat table types (1 row = 1 variant = 1 price)
// ============================================================================

export interface FlatOfferVariant {
  // OfferCandidate fields (unique per row)
  variant_id: string;
  length_cm: number | null;
  pack_type: string | null;
  pack_qty: number | null;
  price: string;
  stock: number | null;
  validation: 'ok' | 'warn' | 'error';

  // SupplierItem fields (duplicated for each variant)
  item_id: string;
  raw_name: string;
  flower_type: string | null;
  subtype: string | null;
  variety: string | null;
  origin_country: string | null;
  colors: string[];
  item_status: string;
  source_file: string | null;
  possible_duplicate: boolean;
}

export interface FlatItemsResponse {
  items: FlatOfferVariant[];
  total: number;
  page: number;
  per_page: number;
}

export interface FlatItemsParams {
  supplier_id: string;
  q?: string;
  page?: number;
  per_page?: number;
  status?: string[];
  origin_country?: (string | null)[];
  colors?: (string | null)[];
  price_min?: number;
  price_max?: number;
  length_min?: number;
  length_max?: number;
  stock_min?: number;
  stock_max?: number;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
}
