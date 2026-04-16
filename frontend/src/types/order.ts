import type { Supplier } from './product';

export interface Buyer {
  id: string;
  name: string;
  phone: string;
  email?: string;
}

export interface OrderItem {
  id: string;
  product_id?: string;
  offer_id?: string;
  normalized_sku_id?: string;
  product_name?: string;
  quantity: number;
  unit_price: string;
  total_price: string;
  notes?: string;
}

export interface Order {
  id: string;
  buyer_id: string;
  supplier_id: string;
  status: 'pending' | 'confirmed' | 'assembled' | 'shipped' | 'rejected' | 'cancelled';
  total_amount: string;
  currency: string;
  delivery_type?: 'pickup' | 'delivery';
  delivery_address: string;
  delivery_date?: string;
  notes?: string;
  created_at: string;
  confirmed_at?: string;
  rejected_at?: string;
  rejection_reason?: string;
  assembled_at?: string;
  shipped_at?: string;
  buyer?: Buyer;
  supplier?: Supplier;
  items: OrderItem[];
  items_count?: number;
}

export interface OrdersResponse {
  orders: Order[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateOrderRequest {
  buyer_id: string;
  items: {
    product_id?: string;
    offer_id?: string;
    quantity: number;
    notes?: string;
  }[];
  delivery_type?: 'pickup' | 'delivery';
  delivery_address?: string;
  delivery_date?: string;
  notes?: string;
}

export interface OrderMetrics {
  total_orders: number;
  pending: number;
  confirmed: number;
  assembled: number;
  shipped: number;
  rejected: number;
  cancelled: number;
  total_revenue: string;
}
