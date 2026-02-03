export type UserRole = 'buyer' | 'seller' | 'admin';

export interface User {
  id: string;
  name: string;
  email: string | null;
  phone?: string;
  role: UserRole;
}

// AuthState is now defined in authSlice.ts
