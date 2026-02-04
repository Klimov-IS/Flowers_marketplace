import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type { OffersResponse, ProductFilters } from '../../types/product';

// In development, Vite proxy handles /offers, /orders, /admin routes
// In production, set VITE_API_BASE_URL to the actual API URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const catalogApi = createApi({
  reducerPath: 'catalogApi',
  baseQuery: fetchBaseQuery({ baseUrl: API_BASE_URL }),
  tagTypes: ['Offers'],
  endpoints: (builder) => ({
    getOffers: builder.query<OffersResponse, ProductFilters>({
      query: (filters) => {
        const params = new URLSearchParams();

        if (filters.q) params.append('q', filters.q);
        if (filters.product_type) params.append('product_type', filters.product_type);
        if (filters.length_cm) params.append('length_cm', String(filters.length_cm));
        if (filters.length_min) params.append('length_min', String(filters.length_min));
        if (filters.length_max) params.append('length_max', String(filters.length_max));
        if (filters.price_min) params.append('price_min', String(filters.price_min));
        if (filters.price_max) params.append('price_max', String(filters.price_max));
        if (filters.supplier_id) params.append('supplier_id', filters.supplier_id);
        if (filters.limit) params.append('limit', String(filters.limit));
        if (filters.offset) params.append('offset', String(filters.offset));

        return `/offers?${params.toString()}`;
      },
      providesTags: ['Offers'],
    }),
  }),
});

export const { useGetOffersQuery } = catalogApi;
