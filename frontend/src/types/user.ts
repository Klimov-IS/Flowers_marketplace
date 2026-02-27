export type UserRole = 'buyer' | 'seller' | 'admin';

export interface User {
  id: string;
  name: string;
  email: string | null;
  phone?: string;
  role: UserRole;
  city_name?: string;
  // Extended supplier profile fields
  legal_name?: string;
  warehouse_address?: string;
  description?: string;
  min_order_amount?: number;
  avatar_url?: string;
  contact_person?: string;
  working_hours_from?: string;
  working_hours_to?: string;
}

// AuthState is now defined in authSlice.ts
