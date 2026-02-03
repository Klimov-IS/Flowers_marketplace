# TASK 3 — Order Flow (Retail → Supplier) + Order Management (MVP)

You are working in an existing repo where Task 1 (Import) and Task 2 (Normalization & Publishing) are completed.
Published offers are available via GET /offers endpoint. Suppliers and retailers exist in the database.

## Goal

Implement minimal order flow for MVP:
1) Retail buyer creates order from published offers
2) Order is split by supplier (one order = one supplier for MVP)
3) Supplier can view incoming orders
4) Supplier can confirm/reject order with simple status workflow
5) Retail buyer can view their order history and current status
6) Admin can view all orders and basic metrics

No payments, no delivery integration, no complex workflow. Just data flow and status tracking.

## Scope (must implement)

### A) Database Schema (Migration 003)

Add tables:
- `buyers` - Retail buyers (name, phone, email, address, city_id, status)
- `orders` - Orders (buyer_id, supplier_id, status, total_amount, currency, delivery_address, delivery_date, notes, created_at, confirmed_at, rejected_at, rejection_reason)
- `order_items` - Order line items (order_id, offer_id, normalized_sku_id, quantity, unit_price, total_price, notes)

**Enums**:
- order_status: pending, confirmed, rejected, cancelled
- buyer_status: active, blocked, pending_verification

**Indexes**:
- orders: (buyer_id, created_at), (supplier_id, status, created_at), (status)
- order_items: (order_id), (offer_id)

**Constraints**:
- orders.total_amount must be positive
- order_items.quantity must be positive
- order_items.unit_price must be non-negative

---

### B) Buyer Management (Minimal)

**Endpoints**:

#### Create Buyer
- `POST /admin/buyers`
- Body: `{ "name": "...", "phone": "...", "email": "...", "address": "...", "city_id": "uuid" }`
- Returns: buyer object

#### List Buyers
- `GET /admin/buyers`
- Query params: `status`, `city_id`, `limit`, `offset`
- Returns: paginated list

#### Get Buyer
- `GET /admin/buyers/{buyer_id}`
- Returns: buyer details

**Notes**:
- MVP: No buyer self-registration (admin creates)
- MVP: No authentication (use buyer_id in requests)
- Production: Add JWT auth + buyer self-service

---

### C) Order Creation (Retail API)

**Endpoint**: `POST /orders`

**Request body**:
```json
{
  "buyer_id": "uuid",
  "supplier_id": "uuid",
  "items": [
    {
      "offer_id": "uuid",
      "quantity": 10,
      "notes": "Optional item notes"
    }
  ],
  "delivery_address": "ул. Ленина 1, кв. 10",
  "delivery_date": "2025-01-15",
  "notes": "Доставка с 9 до 12"
}
```

**Validation**:
- All offer_ids must exist and be active (is_active=true)
- All offers must belong to the same supplier (single-supplier order)
- Buyer must exist and be active
- Delivery date must be today or future
- Quantities must be positive

**Behavior**:
1. Validate buyer exists and is active
2. Fetch offers by IDs
3. Verify all offers belong to same supplier
4. Verify all offers are active
5. Calculate line item totals (unit_price * quantity)
6. Calculate order total_amount (sum of line items)
7. Create order with status='pending'
8. Create order_items
9. Return order with items

**Response** (200 OK):
```json
{
  "id": "uuid",
  "buyer_id": "uuid",
  "supplier_id": "uuid",
  "status": "pending",
  "total_amount": 1500.00,
  "currency": "RUB",
  "delivery_address": "ул. Ленина 1, кв. 10",
  "delivery_date": "2025-01-15",
  "notes": "Доставка с 9 до 12",
  "created_at": "2025-01-12T10:00:00Z",
  "items": [
    {
      "id": "uuid",
      "offer_id": "uuid",
      "normalized_sku_id": "uuid",
      "quantity": 10,
      "unit_price": 120.00,
      "total_price": 1200.00,
      "sku_title": "Rose Explorer"
    }
  ]
}
```

**Status codes**:
- 200: Created
- 400: Validation error (offers from different suppliers, inactive offers, etc.)
- 404: Buyer or offers not found
- 500: Internal error

---

### D) Order List (Retail API)

**Endpoint**: `GET /orders`

**Query params**:
- `buyer_id` (required for retail): Filter by buyer
- `status` (optional): Filter by status
- `supplier_id` (optional): Filter by supplier
- `limit` (default 50, max 200): Max results
- `offset` (default 0): Pagination

**Response** (200 OK):
```json
{
  "orders": [
    {
      "id": "uuid",
      "supplier": {
        "id": "uuid",
        "name": "Flower Base Moscow"
      },
      "status": "pending",
      "total_amount": 1500.00,
      "currency": "RUB",
      "delivery_date": "2025-01-15",
      "created_at": "2025-01-12T10:00:00Z",
      "items_count": 3
    }
  ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

**Notes**:
- Joined with supplier for name
- Ordered by created_at DESC
- Items count for preview

---

### E) Order Details (Retail API)

**Endpoint**: `GET /orders/{order_id}`

**Query params**:
- `buyer_id` (optional): Verify buyer owns this order

**Response** (200 OK):
```json
{
  "id": "uuid",
  "buyer": {
    "id": "uuid",
    "name": "Retail Shop A",
    "phone": "+79001234567"
  },
  "supplier": {
    "id": "uuid",
    "name": "Flower Base Moscow",
    "phone": "+79007654321"
  },
  "status": "confirmed",
  "total_amount": 1500.00,
  "currency": "RUB",
  "delivery_address": "ул. Ленина 1, кв. 10",
  "delivery_date": "2025-01-15",
  "notes": "Доставка с 9 до 12",
  "created_at": "2025-01-12T10:00:00Z",
  "confirmed_at": "2025-01-12T11:00:00Z",
  "items": [
    {
      "id": "uuid",
      "offer": {
        "id": "uuid",
        "length_cm": 60,
        "pack_qty": 10
      },
      "sku": {
        "id": "uuid",
        "product_type": "rose",
        "variety": "Explorer",
        "title": "Rose Explorer"
      },
      "quantity": 10,
      "unit_price": 120.00,
      "total_price": 1200.00,
      "notes": null
    }
  ]
}
```

---

### F) Supplier Order List (Supplier API)

**Endpoint**: `GET /suppliers/{supplier_id}/orders`

**Query params**:
- `status` (optional): Filter by status
- `limit` (default 50, max 200): Max results
- `offset` (default 0): Pagination

**Response** (200 OK):
```json
{
  "orders": [
    {
      "id": "uuid",
      "buyer": {
        "id": "uuid",
        "name": "Retail Shop A",
        "phone": "+79001234567"
      },
      "status": "pending",
      "total_amount": 1500.00,
      "delivery_date": "2025-01-15",
      "created_at": "2025-01-12T10:00:00Z",
      "items_count": 3
    }
  ],
  "total": 25,
  "limit": 50,
  "offset": 0
}
```

**Notes**:
- Ordered by created_at DESC
- Pending orders first (can add custom ordering)

---

### G) Confirm Order (Supplier API)

**Endpoint**: `POST /suppliers/{supplier_id}/orders/{order_id}/confirm`

**Request body** (optional):
```json
{
  "notes": "Confirmed. Ready for delivery on time."
}
```

**Validation**:
- Order must belong to this supplier
- Order status must be 'pending'
- Cannot confirm already confirmed/rejected/cancelled order

**Behavior**:
1. Verify order belongs to supplier
2. Verify status == 'pending'
3. Update order:
   - status = 'confirmed'
   - confirmed_at = now()
   - notes = append supplier notes
4. Return updated order

**Response** (200 OK):
```json
{
  "id": "uuid",
  "status": "confirmed",
  "confirmed_at": "2025-01-12T11:00:00Z",
  "notes": "Updated notes..."
}
```

**Status codes**:
- 200: Confirmed
- 400: Invalid status transition
- 404: Order not found or doesn't belong to supplier
- 500: Internal error

---

### H) Reject Order (Supplier API)

**Endpoint**: `POST /suppliers/{supplier_id}/orders/{order_id}/reject`

**Request body**:
```json
{
  "rejection_reason": "Out of stock for Rose Explorer"
}
```

**Validation**:
- Order must belong to this supplier
- Order status must be 'pending' or 'confirmed' (can reject confirmed orders before delivery)
- rejection_reason required

**Behavior**:
1. Verify order belongs to supplier
2. Verify status in ['pending', 'confirmed']
3. Update order:
   - status = 'rejected'
   - rejected_at = now()
   - rejection_reason = provided reason
4. Return updated order

**Response** (200 OK):
```json
{
  "id": "uuid",
  "status": "rejected",
  "rejected_at": "2025-01-12T11:00:00Z",
  "rejection_reason": "Out of stock for Rose Explorer"
}
```

---

### I) Admin Order Management

**Endpoint**: `GET /admin/orders`

**Query params**:
- `status` (optional): Filter by status
- `buyer_id` (optional): Filter by buyer
- `supplier_id` (optional): Filter by supplier
- `date_from` / `date_to` (optional): Filter by created_at
- `limit` (default 50, max 500): Max results
- `offset` (default 0): Pagination

**Response** (200 OK):
```json
{
  "orders": [
    {
      "id": "uuid",
      "buyer": {"id": "uuid", "name": "Retail Shop A"},
      "supplier": {"id": "uuid", "name": "Flower Base Moscow"},
      "status": "confirmed",
      "total_amount": 1500.00,
      "delivery_date": "2025-01-15",
      "created_at": "2025-01-12T10:00:00Z",
      "items_count": 3
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

**Endpoint**: `GET /admin/orders/{order_id}`

Returns full order details (same as retail detail endpoint but without buyer_id check).

---

### J) Order Metrics (Admin API)

**Endpoint**: `GET /admin/metrics/orders`

**Query params**:
- `date_from` / `date_to` (optional): Date range

**Response** (200 OK):
```json
{
  "total_orders": 150,
  "by_status": {
    "pending": 25,
    "confirmed": 100,
    "rejected": 20,
    "cancelled": 5
  },
  "total_amount": 225000.00,
  "average_order_amount": 1500.00,
  "top_suppliers": [
    {
      "supplier_id": "uuid",
      "supplier_name": "Flower Base Moscow",
      "orders_count": 50,
      "total_amount": 75000.00
    }
  ],
  "top_buyers": [
    {
      "buyer_id": "uuid",
      "buyer_name": "Retail Shop A",
      "orders_count": 20,
      "total_amount": 30000.00
    }
  ]
}
```

---

## Non-goals (explicitly do NOT implement)

❌ Payments and invoicing
❌ Delivery tracking
❌ Complex order workflow (just 4 statuses)
❌ Order editing/modification
❌ Multi-supplier orders in one request
❌ Shopping cart persistence
❌ Order notifications (email/SMS)
❌ Buyer authentication (use buyer_id for now)
❌ Inventory/stock management
❌ Order approval workflow

---

## Required Tests

### Unit Tests
**File**: `tests/unit/test_order_validation.py`

Test cases (minimum 5):
1. Validate single-supplier constraint (all offers from same supplier)
2. Validate active offers only
3. Validate positive quantities
4. Calculate order totals correctly
5. Validate status transitions (pending → confirmed/rejected)

### Integration Tests
**File**: `tests/integration/test_order_flow.py`

Test scenarios:
1. **Create order** - Happy path
   - Create buyer
   - Create order with 2 items
   - Assert: order created, items created, total calculated

2. **List orders (retail)** - Filter by buyer
   - Create 2 orders for buyer A
   - Create 1 order for buyer B
   - GET /orders?buyer_id=A
   - Assert: Returns 2 orders for buyer A

3. **Supplier order list**
   - Create orders for supplier S1 and S2
   - GET /suppliers/S1/orders
   - Assert: Returns only S1 orders

4. **Confirm order**
   - Create order (status=pending)
   - POST /suppliers/{id}/orders/{id}/confirm
   - Assert: status=confirmed, confirmed_at set

5. **Reject order**
   - Create order (status=pending)
   - POST /suppliers/{id}/orders/{id}/reject
   - Assert: status=rejected, rejection_reason set

6. **Mixed supplier offers** - Validation error
   - Try to create order with offers from 2 different suppliers
   - Assert: 400 Bad Request

7. **Inactive offers** - Validation error
   - Try to create order with inactive offer (is_active=false)
   - Assert: 400 Bad Request

8. **Order metrics**
   - Create 5 orders (3 confirmed, 2 rejected)
   - GET /admin/metrics/orders
   - Assert: Correct counts and totals

---

## Documentation

### Update `docs/ADMIN_API.md`
Add new sections:
- Buyer Management (3 endpoints)
- Order Management (5+ endpoints)
- Order Metrics (1 endpoint)

### Update `README.md`
Add Task 3 quickstart:
```bash
# 1. Create buyer
curl -X POST http://localhost:8000/admin/buyers \
  -H "Content-Type: application/json" \
  -d '{"name": "Retail Shop A", "phone": "+79001234567", ...}'

# 2. Create order
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "buyer_id": "uuid",
    "supplier_id": "uuid",
    "items": [{"offer_id": "uuid", "quantity": 10}],
    "delivery_address": "...",
    "delivery_date": "2025-01-15"
  }'

# 3. Supplier views orders
curl http://localhost:8000/suppliers/{id}/orders

# 4. Supplier confirms order
curl -X POST http://localhost:8000/suppliers/{id}/orders/{order_id}/confirm
```

---

## Database Migration Strategy

**Migration 003**: `20250113_add_orders`

Create tables:
- buyers
- orders
- order_items

Add enums:
- order_status
- buyer_status

Add indexes and constraints as specified above.

---

## Implementation Notes

### 1. Order Totals Calculation
Calculate dynamically from order_items:
```python
# At order creation:
for item in items:
    offer = fetch_offer(item.offer_id)
    item.unit_price = offer.price_min  # Use min price
    item.total_price = item.unit_price * item.quantity

order.total_amount = sum(item.total_price for item in items)
```

### 2. Status Transitions
Valid transitions:
- pending → confirmed
- pending → rejected
- confirmed → rejected (before delivery)
- Any → cancelled (buyer cancels)

Invalid transitions:
- confirmed → pending
- rejected → confirmed
- rejected → pending

### 3. Single-Supplier Constraint
MVP: One order = one supplier

Validation:
```python
offer_ids = [item.offer_id for item in request.items]
offers = fetch_offers(offer_ids)
supplier_ids = {offer.supplier_id for offer in offers}

if len(supplier_ids) > 1:
    raise ValidationError("All offers must be from the same supplier")
```

Future: Support multi-supplier orders (split into multiple orders or order groups).

### 4. Price Snapshot
Order items store `unit_price` at order creation time.
This prevents price changes from affecting historical orders.

### 5. No Inventory Check
MVP: Orders can be created even if stock is unavailable.
Supplier can reject order if out of stock.

Future: Add real-time stock validation.

---

## Definition of Done

- [x] Migration 003 creates buyers, orders, order_items tables
- [x] Buyer CRUD endpoints work
- [x] POST /orders creates order with validation
- [x] GET /orders lists orders for buyer
- [x] GET /orders/{id} returns order details
- [x] GET /suppliers/{id}/orders lists supplier orders
- [x] POST /suppliers/{id}/orders/{id}/confirm works
- [x] POST /suppliers/{id}/orders/{id}/reject works
- [x] GET /admin/orders lists all orders with filters
- [x] GET /admin/metrics/orders returns correct metrics
- [x] Unit tests pass (order validation)
- [x] Integration tests pass (8 scenarios)
- [x] ADMIN_API.md updated
- [x] README.md updated with Task 3 quickstart
- [x] No scope creep (no payments, no delivery, no complex workflow)

---

## Output format for your response

1) Plan (order flow architecture + endpoints breakdown)
2) Implementation notes (key decisions: totals calculation, status transitions, single-supplier constraint)
3) Files created/changed (list migrations, models, services, routers, tests, docs)
4) Commands to run (migration, tests, curl examples)
5) DoD checklist results
