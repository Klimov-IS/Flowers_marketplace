import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';
import { authApi } from '../features/auth/authApi';
import { catalogApi } from '../features/catalog/catalogApi';
import { ordersApi } from '../features/buyer/ordersApi';
import { supplierApi } from '../features/seller/supplierApi';
import authReducer from '../features/auth/authSlice';
import cartReducer from '../features/buyer/cartSlice';
import filtersReducer from '../features/catalog/filtersSlice';

export const store = configureStore({
  reducer: {
    // RTK Query API slices
    [authApi.reducerPath]: authApi.reducer,
    [catalogApi.reducerPath]: catalogApi.reducer,
    [ordersApi.reducerPath]: ordersApi.reducer,
    [supplierApi.reducerPath]: supplierApi.reducer,

    // Regular reducers
    auth: authReducer,
    cart: cartReducer,
    filters: filtersReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(
      authApi.middleware,
      catalogApi.middleware,
      ordersApi.middleware,
      supplierApi.middleware
    ),
});

// Setup listeners for refetchOnFocus/refetchOnReconnect
setupListeners(store.dispatch);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
