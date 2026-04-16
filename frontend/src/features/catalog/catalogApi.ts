import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type { ProductsResponse, ProductFilters } from '../../types/product';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const catalogApi = createApi({
  reducerPath: 'catalogApi',
  baseQuery: fetchBaseQuery({ baseUrl: API_BASE_URL }),
  tagTypes: ['Products'],
  endpoints: (builder) => ({
    getProducts: builder.query<ProductsResponse, ProductFilters>({
      query: (filters) => {
        const params = new URLSearchParams();

        if (filters.q) params.append('q', filters.q);
        // product_type from filtersSlice maps to flower_type on the API
        const flowerType = filters.flower_type || filters.product_type;
        if (flowerType) params.append('flower_type', flowerType);
        if (filters.variety) params.append('variety', filters.variety);
        if (filters.length_min) params.append('length_min', String(filters.length_min));
        if (filters.length_max) params.append('length_max', String(filters.length_max));
        if (filters.price_min) params.append('price_min', String(filters.price_min));
        if (filters.price_max) params.append('price_max', String(filters.price_max));
        if (filters.supplier_id) params.append('supplier_id', filters.supplier_id);
        if (filters.color) params.append('color', filters.color);
        if (filters.in_stock !== undefined) params.append('in_stock', String(filters.in_stock));
        if (filters.sort_by) params.append('sort_by', filters.sort_by);
        if (filters.limit) params.append('limit', String(filters.limit));
        if (filters.offset) params.append('offset', String(filters.offset));

        return `/products?${params.toString()}`;
      },
      providesTags: ['Products'],
    }),
  }),
});

export const { useGetProductsQuery } = catalogApi;
