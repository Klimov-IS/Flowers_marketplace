import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import type { ProductFilters } from '../../types/product';

interface FiltersState extends ProductFilters {
  sortBy: 'price_asc' | 'price_desc' | 'name';
}

const initialState: FiltersState = {
  q: '',
  product_type: undefined,
  length_cm: undefined,
  price_min: undefined,
  price_max: undefined,
  supplier_id: undefined,
  limit: 24,
  offset: 0,
  sortBy: 'price_asc',
};

const filtersSlice = createSlice({
  name: 'filters',
  initialState,
  reducers: {
    setSearchQuery: (state, action: PayloadAction<string>) => {
      state.q = action.payload;
      state.offset = 0; // Reset pagination
    },
    setProductType: (state, action: PayloadAction<string | undefined>) => {
      state.product_type = action.payload;
      state.offset = 0;
    },
    setPriceRange: (
      state,
      action: PayloadAction<{ min?: number; max?: number }>
    ) => {
      state.price_min = action.payload.min;
      state.price_max = action.payload.max;
      state.offset = 0;
    },
    setLengthFilter: (state, action: PayloadAction<number | undefined>) => {
      state.length_cm = action.payload;
      state.offset = 0;
    },
    setSupplierFilter: (state, action: PayloadAction<string | undefined>) => {
      state.supplier_id = action.payload;
      state.offset = 0;
    },
    setSortBy: (
      state,
      action: PayloadAction<'price_asc' | 'price_desc' | 'name'>
    ) => {
      state.sortBy = action.payload;
      state.offset = 0;
    },
    setPage: (state, action: PayloadAction<number>) => {
      state.offset = action.payload * (state.limit || 24);
    },
    resetFilters: (state) => {
      state.q = '';
      state.product_type = undefined;
      state.length_cm = undefined;
      state.price_min = undefined;
      state.price_max = undefined;
      state.supplier_id = undefined;
      state.offset = 0;
      state.sortBy = 'price_asc';
    },
  },
});

export const {
  setSearchQuery,
  setProductType,
  setPriceRange,
  setLengthFilter,
  setSupplierFilter,
  setSortBy,
  setPage,
  resetFilters,
} = filtersSlice.actions;

export default filtersSlice.reducer;
