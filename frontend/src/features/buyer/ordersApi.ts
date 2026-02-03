import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type {
  Order,
  OrdersResponse,
  CreateOrderRequest,
} from '../../types/order';

// In development, Vite proxy handles /offers, /orders, /admin routes
// In production, set VITE_API_BASE_URL to the actual API URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const ordersApi = createApi({
  reducerPath: 'ordersApi',
  baseQuery: fetchBaseQuery({ baseURL: API_BASE_URL }),
  tagTypes: ['Orders'],
  endpoints: (builder) => ({
    getOrders: builder.query<
      OrdersResponse,
      {
        buyer_id?: string;
        supplier_id?: string;
        status?: string;
        limit?: number;
        offset?: number;
      }
    >({
      query: (params) => {
        const searchParams = new URLSearchParams();
        if (params.buyer_id) searchParams.append('buyer_id', params.buyer_id);
        if (params.supplier_id) searchParams.append('supplier_id', params.supplier_id);
        if (params.status) searchParams.append('status', params.status);
        if (params.limit) searchParams.append('limit', String(params.limit));
        if (params.offset) searchParams.append('offset', String(params.offset));

        return `/orders?${searchParams.toString()}`;
      },
      providesTags: ['Orders'],
    }),

    getOrderById: builder.query<Order, string>({
      query: (id) => `/orders/${id}`,
      providesTags: (result, error, id) => [{ type: 'Orders', id }],
    }),

    createOrder: builder.mutation<Order, CreateOrderRequest>({
      query: (body) => ({
        url: '/orders',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Orders'],
    }),
  }),
});

export const {
  useGetOrdersQuery,
  useGetOrderByIdQuery,
  useCreateOrderMutation,
} = ordersApi;
