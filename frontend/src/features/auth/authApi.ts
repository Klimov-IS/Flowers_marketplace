import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

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
}

export const authApi = createApi({
  reducerPath: 'authApi',
  baseQuery: fetchBaseQuery({
    baseURL: API_BASE_URL,
    prepareHeaders: (headers) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
      return headers;
    },
  }),
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
  useLogoutMutation,
} = authApi;
