import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type { Order, OrderMetrics } from '../../types/order';
import type {
  SupplierItem,
  SupplierItemsParams,
  SupplierItemsResponse,
  OfferVariant,
} from '../../types/supplierItem';

// Update request types
export interface SupplierItemUpdateData {
  raw_name?: string;
  origin_country?: string | null;
  colors?: string[];
}

export interface OfferCandidateUpdateData {
  length_cm?: number | null;
  pack_type?: string | null;
  pack_qty?: number | null;
  price_min?: number | null;
  stock_qty?: number | null;
}

// AI Suggestion types
export interface AISuggestion {
  id: string;
  ai_run_id: string;
  suggestion_type: string;
  target_entity: string | null;
  target_id: string | null;
  field_name: string | null;
  suggested_value: { value: unknown };
  confidence: number;
  applied_status: string;
  applied_at: string | null;
  applied_by: string | null;
  created_at: string;
  item_raw_name: string | null;
  supplier_name: string | null;
}

export interface AISuggestionsResponse {
  items: AISuggestion[];
  total: number;
  page: number;
  per_page: number;
}

export interface AISuggestionsParams {
  status?: string;
  supplier_id?: string;
  page?: number;
  per_page?: number;
}

export interface AISuggestionActionResponse {
  id: string;
  applied_status: string;
  applied_at: string | null;
  message: string;
}

// In development, Vite proxy handles /offers, /orders, /admin routes
// In production, set VITE_API_BASE_URL to the actual API URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const supplierApi = createApi({
  reducerPath: 'supplierApi',
  baseQuery: fetchBaseQuery({ baseUrl: API_BASE_URL }),
  tagTypes: ['SupplierOrders', 'ImportBatches', 'NormalizationTasks', 'SupplierItems', 'AISuggestions'],
  endpoints: (builder) => ({
    // Supplier Items (Assortment)
    getSupplierItems: builder.query<SupplierItemsResponse, SupplierItemsParams>({
      query: ({
        supplier_id,
        q,
        page,
        per_page,
        status,
        origin_country,
        colors,
        price_min,
        price_max,
        length_min,
        length_max,
        stock_min,
        stock_max,
      }) => {
        const params = new URLSearchParams();
        if (q) params.append('q', q);
        if (page) params.append('page', String(page));
        if (per_page) params.append('per_page', String(per_page));
        if (status && status.length > 0) {
          status.forEach(s => params.append('status', s));
        }
        // Country filter
        if (origin_country && origin_country.length > 0) {
          origin_country.forEach(c => {
            if (c === null) {
              params.append('origin_country', '__null__');
            } else {
              params.append('origin_country', c);
            }
          });
        }
        // Color filter
        if (colors && colors.length > 0) {
          colors.forEach(c => {
            if (c === null) {
              params.append('colors', '__null__');
            } else {
              params.append('colors', c);
            }
          });
        }
        // Range filters
        if (price_min !== undefined) params.append('price_min', String(price_min));
        if (price_max !== undefined) params.append('price_max', String(price_max));
        if (length_min !== undefined) params.append('length_min', String(length_min));
        if (length_max !== undefined) params.append('length_max', String(length_max));
        if (stock_min !== undefined) params.append('stock_min', String(stock_min));
        if (stock_max !== undefined) params.append('stock_max', String(stock_max));

        const queryString = params.toString();
        return `/admin/suppliers/${supplier_id}/items${queryString ? `?${queryString}` : ''}`;
      },
      providesTags: ['SupplierItems'],
    }),

    getSupplierOrders: builder.query<
      Order[],
      { supplier_id: string; status?: string; limit?: number; offset?: number }
    >({
      query: ({ supplier_id, status, limit, offset }) => {
        const params = new URLSearchParams();
        if (status) params.append('status', status);
        if (limit) params.append('limit', String(limit));
        if (offset) params.append('offset', String(offset));

        return `/admin/suppliers/${supplier_id}/orders?${params.toString()}`;
      },
      providesTags: ['SupplierOrders'],
    }),

    confirmOrder: builder.mutation<
      { order_id: string; status: string; confirmed_at: string },
      { supplier_id: string; order_id: string }
    >({
      query: ({ supplier_id, order_id }) => ({
        url: `/admin/suppliers/${supplier_id}/orders/confirm`,
        method: 'POST',
        body: { order_id },
      }),
      invalidatesTags: ['SupplierOrders'],
    }),

    rejectOrder: builder.mutation<
      {
        order_id: string;
        status: string;
        rejected_at: string;
        rejection_reason: string;
      },
      { supplier_id: string; order_id: string; reason: string }
    >({
      query: ({ supplier_id, order_id, reason }) => ({
        url: `/admin/suppliers/${supplier_id}/orders/reject`,
        method: 'POST',
        body: { order_id, reason },
      }),
      invalidatesTags: ['SupplierOrders'],
    }),

    getOrderMetrics: builder.query<OrderMetrics, string>({
      query: (supplier_id) => `/admin/suppliers/${supplier_id}/orders/metrics`,
    }),

    uploadPriceList: builder.mutation<
      {
        batch_id: string;
        status: string;
        total_rows: number;
        success_rows: number;
        error_rows: number;
      },
      { supplier_id: string; file: File; description?: string }
    >({
      query: ({ supplier_id, file, description }) => {
        const formData = new FormData();
        formData.append('file', file);
        if (description) formData.append('description', description);

        return {
          url: `/admin/suppliers/${supplier_id}/imports/csv`,
          method: 'POST',
          body: formData,
        };
      },
      invalidatesTags: ['ImportBatches'],
    }),

    // Update Supplier Item (for editable table)
    updateSupplierItem: builder.mutation<
      SupplierItem,
      { id: string; data: SupplierItemUpdateData }
    >({
      query: ({ id, data }) => ({
        url: `/admin/supplier-items/${id}`,
        method: 'PATCH',
        body: data,
      }),
      invalidatesTags: ['SupplierItems'],
    }),

    // Update Offer Candidate / Variant (for editable table)
    updateOfferCandidate: builder.mutation<
      OfferVariant,
      { id: string; data: OfferCandidateUpdateData }
    >({
      query: ({ id, data }) => ({
        url: `/admin/offer-candidates/${id}`,
        method: 'PATCH',
        body: data,
      }),
      invalidatesTags: ['SupplierItems'],
    }),

    // AI Suggestions endpoints
    getAISuggestions: builder.query<AISuggestionsResponse, AISuggestionsParams>({
      query: ({ status, supplier_id, page, per_page }) => {
        const params = new URLSearchParams();
        if (status) params.append('status', status);
        if (supplier_id) params.append('supplier_id', supplier_id);
        if (page) params.append('page', String(page));
        if (per_page) params.append('per_page', String(per_page));

        const queryString = params.toString();
        return `/admin/ai/suggestions${queryString ? `?${queryString}` : ''}`;
      },
      providesTags: ['AISuggestions'],
    }),

    acceptAISuggestion: builder.mutation<AISuggestionActionResponse, string>({
      query: (suggestionId) => ({
        url: `/admin/ai/suggestions/${suggestionId}/accept`,
        method: 'PATCH',
      }),
      invalidatesTags: ['AISuggestions', 'SupplierItems'],
    }),

    rejectAISuggestion: builder.mutation<AISuggestionActionResponse, string>({
      query: (suggestionId) => ({
        url: `/admin/ai/suggestions/${suggestionId}/reject`,
        method: 'PATCH',
      }),
      invalidatesTags: ['AISuggestions'],
    }),

    // Item actions (delete, hide, restore)
    deleteSupplierItem: builder.mutation<
      { id: string; status: string; message: string },
      string
    >({
      query: (itemId) => ({
        url: `/admin/supplier-items/${itemId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['SupplierItems'],
    }),

    hideSupplierItem: builder.mutation<
      { id: string; status: string; message: string },
      string
    >({
      query: (itemId) => ({
        url: `/admin/supplier-items/${itemId}/hide`,
        method: 'POST',
      }),
      invalidatesTags: ['SupplierItems'],
    }),

    restoreSupplierItem: builder.mutation<
      { id: string; status: string; message: string },
      string
    >({
      query: (itemId) => ({
        url: `/admin/supplier-items/${itemId}/restore`,
        method: 'POST',
      }),
      invalidatesTags: ['SupplierItems'],
    }),

    // Bulk actions
    bulkDeleteItems: builder.mutation<
      { affected_count: number; status: string; message: string },
      string[]
    >({
      query: (itemIds) => ({
        url: `/admin/supplier-items/bulk-delete`,
        method: 'POST',
        body: { item_ids: itemIds },
      }),
      invalidatesTags: ['SupplierItems'],
    }),

    bulkHideItems: builder.mutation<
      { affected_count: number; status: string; message: string },
      string[]
    >({
      query: (itemIds) => ({
        url: `/admin/supplier-items/bulk-hide`,
        method: 'POST',
        body: { item_ids: itemIds },
      }),
      invalidatesTags: ['SupplierItems'],
    }),

    bulkRestoreItems: builder.mutation<
      { affected_count: number; status: string; message: string },
      string[]
    >({
      query: (itemIds) => ({
        url: `/admin/supplier-items/bulk-restore`,
        method: 'POST',
        body: { item_ids: itemIds },
      }),
      invalidatesTags: ['SupplierItems'],
    }),
  }),
});

export const {
  useGetSupplierItemsQuery,
  useGetSupplierOrdersQuery,
  useConfirmOrderMutation,
  useRejectOrderMutation,
  useGetOrderMetricsQuery,
  useUploadPriceListMutation,
  useUpdateSupplierItemMutation,
  useUpdateOfferCandidateMutation,
  useGetAISuggestionsQuery,
  useAcceptAISuggestionMutation,
  useRejectAISuggestionMutation,
  // Item actions
  useDeleteSupplierItemMutation,
  useHideSupplierItemMutation,
  useRestoreSupplierItemMutation,
  // Bulk actions
  useBulkDeleteItemsMutation,
  useBulkHideItemsMutation,
  useBulkRestoreItemsMutation,
} = supplierApi;
