import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type { Order, OrderMetrics } from '../../types/order';

// In development, Vite proxy handles /offers, /orders, /admin routes
// In production, set VITE_API_BASE_URL to the actual API URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const supplierApi = createApi({
  reducerPath: 'supplierApi',
  baseQuery: fetchBaseQuery({ baseURL: API_BASE_URL }),
  tagTypes: ['SupplierOrders', 'ImportBatches', 'NormalizationTasks'],
  endpoints: (builder) => ({
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
  }),
});

export const {
  useGetSupplierOrdersQuery,
  useConfirmOrderMutation,
  useRejectOrderMutation,
  useGetOrderMetricsQuery,
  useUploadPriceListMutation,
} = supplierApi;
