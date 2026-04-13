import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type { BaseQueryFn, FetchArgs, FetchBaseQueryError } from '@reduxjs/toolkit/query';
import type {
  Order,
  OrdersResponse,
  CreateOrderRequest,
} from '../../types/order';

// In development, Vite proxy handles /offers, /orders, /admin routes
// In production, set VITE_API_BASE_URL to the actual API URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const rawBaseQuery = fetchBaseQuery({
  baseUrl: API_BASE_URL,
  prepareHeaders: (headers) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    return headers;
  },
});

const baseQueryWithReauth: BaseQueryFn<string | FetchArgs, unknown, FetchBaseQueryError> = async (
  args,
  api,
  extraOptions,
) => {
  let result = await rawBaseQuery(args, api, extraOptions);

  if (result.error && result.error.status === 401) {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      const refreshResult = await rawBaseQuery(
        { url: '/auth/refresh', method: 'POST', body: { refresh_token: refreshToken } },
        api,
        extraOptions,
      );

      if (refreshResult.data) {
        const tokens = refreshResult.data as { access_token: string; refresh_token: string };
        localStorage.setItem('access_token', tokens.access_token);
        localStorage.setItem('refresh_token', tokens.refresh_token);
        result = await rawBaseQuery(args, api, extraOptions);
      } else {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        const basePath = import.meta.env.VITE_BASE_PATH || '/';
        window.location.href = basePath + 'login';
      }
    }
  }

  return result;
};

export const ordersApi = createApi({
  reducerPath: 'ordersApi',
  baseQuery: baseQueryWithReauth,
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
      providesTags: (_result, _error, id) => [{ type: 'Orders', id }],
    }),

    createOrder: builder.mutation<Order, CreateOrderRequest>({
      query: (body) => ({
        url: '/orders',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Orders'],
    }),

    validateCart: builder.mutation<
      { valid: string[]; invalid: string[] },
      { offer_ids: string[] }
    >({
      query: (body) => ({
        url: '/orders/validate-cart',
        method: 'POST',
        body,
      }),
    }),
  }),
});

export const {
  useGetOrdersQuery,
  useGetOrderByIdQuery,
  useCreateOrderMutation,
  useValidateCartMutation,
} = ordersApi;
