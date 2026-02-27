import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type { BaseQueryFn, FetchArgs, FetchBaseQueryError } from '@reduxjs/toolkit/query';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export interface LoginRequest {
  email: string;
  password: string;
  role: 'buyer' | 'supplier';
}

export interface RegisterBuyerRequest {
  name: string;
  email: string;
  phone: string;
  password: string;
  address?: string;
  city_id: string;
}

export interface RegisterSupplierRequest {
  name: string;
  email: string;
  phone: string;
  password: string;
  city_id?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserResponse {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  role: 'buyer' | 'supplier';
  status: string;
  city_name: string | null;
  // Extended supplier profile fields
  legal_name?: string | null;
  warehouse_address?: string | null;
  description?: string | null;
  min_order_amount?: number | null;
  avatar_url?: string | null;
  contact_person?: string | null;
  working_hours_from?: string | null;
  working_hours_to?: string | null;
}

export interface UpdateProfileRequest {
  name?: string;
  email?: string;
  phone?: string;
  city_name?: string;
  // Extended supplier profile fields
  legal_name?: string;
  warehouse_address?: string;
  description?: string;
  min_order_amount?: number;
  contact_person?: string;
  working_hours_from?: string;
  working_hours_to?: string;
}

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

// Wrapper that auto-refreshes token on 401
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
        const tokens = refreshResult.data as TokenResponse;
        localStorage.setItem('access_token', tokens.access_token);
        localStorage.setItem('refresh_token', tokens.refresh_token);
        // Retry the original request with new token
        result = await rawBaseQuery(args, api, extraOptions);
      } else {
        // Refresh failed — clear auth state
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

export const authApi = createApi({
  reducerPath: 'authApi',
  baseQuery: baseQueryWithReauth,
  endpoints: (builder) => ({
    login: builder.mutation<TokenResponse, LoginRequest>({
      query: (credentials) => ({
        url: '/auth/login',
        method: 'POST',
        body: credentials,
      }),
    }),

    registerBuyer: builder.mutation<TokenResponse, RegisterBuyerRequest>({
      query: (data) => ({
        url: '/auth/register/buyer',
        method: 'POST',
        body: data,
      }),
    }),

    registerSupplier: builder.mutation<TokenResponse, RegisterSupplierRequest>({
      query: (data) => ({
        url: '/auth/register/supplier',
        method: 'POST',
        body: data,
      }),
    }),

    refreshToken: builder.mutation<TokenResponse, { refresh_token: string }>({
      query: (data) => ({
        url: '/auth/refresh',
        method: 'POST',
        body: data,
      }),
    }),

    getCurrentUser: builder.query<UserResponse, void>({
      query: () => '/auth/me',
    }),

    updateProfile: builder.mutation<UserResponse, UpdateProfileRequest>({
      query: (data) => ({
        url: '/auth/me',
        method: 'PATCH',
        body: data,
      }),
    }),

    logout: builder.mutation<{ message: string }, void>({
      query: () => ({
        url: '/auth/logout',
        method: 'POST',
      }),
    }),
  }),
});

export const {
  useLoginMutation,
  useRegisterBuyerMutation,
  useRegisterSupplierMutation,
  useRefreshTokenMutation,
  useGetCurrentUserQuery,
  useUpdateProfileMutation,
  useLogoutMutation,
} = authApi;
