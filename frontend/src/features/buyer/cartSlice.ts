import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';

export interface CartItem {
  product_id: string;
  offer_id: string;
  name: string;
  price: number;
  quantity: number;
  stock?: number;
  length_cm?: number;
}

export interface SupplierCart {
  supplier_id: string;
  supplier_name: string;
  items: CartItem[];
}

interface CartState {
  suppliers: SupplierCart[];
}

// Load cart from localStorage
const loadCart = (): SupplierCart[] => {
  try {
    const saved = localStorage.getItem('cart');
    return saved ? JSON.parse(saved) : [];
  } catch {
    return [];
  }
};

const initialState: CartState = {
  suppliers: loadCart(),
};

const cartSlice = createSlice({
  name: 'cart',
  initialState,
  reducers: {
    addToCart: (
      state,
      action: PayloadAction<{
        supplier_id: string;
        supplier_name: string;
        item: CartItem;
      }>
    ) => {
      const { supplier_id, supplier_name, item } = action.payload;

      let supplierGroup = state.suppliers.find(
        (s) => s.supplier_id === supplier_id
      );

      if (!supplierGroup) {
        supplierGroup = {
          supplier_id,
          supplier_name,
          items: [],
        };
        state.suppliers.push(supplierGroup);
      }

      const existingItem = supplierGroup.items.find(
        (i) => i.offer_id === item.offer_id
      );

      if (existingItem) {
        existingItem.quantity += item.quantity;
      } else {
        supplierGroup.items.push(item);
      }

      // Persist to localStorage
      localStorage.setItem('cart', JSON.stringify(state.suppliers));
    },

    updateQuantity: (
      state,
      action: PayloadAction<{
        supplier_id: string;
        offer_id: string;
        quantity: number;
      }>
    ) => {
      const { supplier_id, offer_id, quantity } = action.payload;
      const supplier = state.suppliers.find((s) => s.supplier_id === supplier_id);

      if (supplier) {
        const item = supplier.items.find((i) => i.offer_id === offer_id);
        if (item) {
          item.quantity = Math.max(1, quantity);
        }
      }

      localStorage.setItem('cart', JSON.stringify(state.suppliers));
    },

    removeItem: (
      state,
      action: PayloadAction<{ supplier_id: string; offer_id: string }>
    ) => {
      const { supplier_id, offer_id } = action.payload;
      const supplier = state.suppliers.find((s) => s.supplier_id === supplier_id);

      if (supplier) {
        supplier.items = supplier.items.filter((i) => i.offer_id !== offer_id);

        // Remove supplier group if empty
        if (supplier.items.length === 0) {
          state.suppliers = state.suppliers.filter(
            (s) => s.supplier_id !== supplier_id
          );
        }
      }

      localStorage.setItem('cart', JSON.stringify(state.suppliers));
    },

    clearSupplierCart: (state, action: PayloadAction<string>) => {
      state.suppliers = state.suppliers.filter(
        (s) => s.supplier_id !== action.payload
      );
      localStorage.setItem('cart', JSON.stringify(state.suppliers));
    },

    clearCart: (state) => {
      state.suppliers = [];
      localStorage.removeItem('cart');
    },
  },
});

export const {
  addToCart,
  updateQuantity,
  removeItem,
  clearSupplierCart,
  clearCart,
} = cartSlice.actions;

export default cartSlice.reducer;
