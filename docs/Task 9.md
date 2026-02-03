# TASK 9 — Frontend Development (HTML Prototypes → Production SPA)

You are working in an existing repo where backend is complete (Tasks 1-3: Import, Normalization, Orders).
The API is fully functional and documented in `/docs/ADMIN_API.md`.

## Goal

Deliver frontend in **two phases**:

### **Phase 1: HTML Prototypes** (for design approval)
Create static HTML prototypes based on provided reference screenshots:
1. **Storefront** (Витрина) - Product catalog with filters and search
2. **Buyer Cabinet** (Кабинет покупателя) - Shopping cart + order history
3. **Seller Cabinet** (Кабинет продавца) - Price list upload + order management

**Purpose**: User reviews and approves design/UX before production development.

### **Phase 2: Production SPA** (after approval)
Build production-ready React application with:
- Full API integration (Tasks 1-3 endpoints)
- Authentication (Task 4 - JWT)
- State management
- Form validation
- Responsive design
- E2E tests

---

## References

User provided 5 reference screenshots in `/docs/Референсы/`:

1. **`screencapture-127-0-0-1-5501-index-html-2025-12-23-17_31_59.png`**
   - Storefront with hero section
   - Search bar + filters (product type, price, length, color)
   - Product grid with cards (image, price, "Add to cart" button)
   - Grid/list view toggle
   - Sorting dropdown

2. **`screencapture-127-0-0-1-5501-buyer-html-2025-12-23-18_19_20.png`**
   - Buyer cabinet with shopping cart
   - Cart grouped by suppliers ("База №1", "База №2")
   - Quantity controls (+/- buttons)
   - Total calculation per supplier + grand total
   - "Place order" button per supplier
   - Order history below (list with statuses: pending, confirmed, completed)
   - Order details expansion with delivery timeline
   - Statistics widget (total spent, orders count)

3. **`screencapture-127-0-0-1-5501-seller-html-2025-12-14-15_23_23.png`**
   - Seller cabinet with price list upload
   - Drag-and-drop zone for XLSX/CSV files
   - Normalization error editor (table with dropdown for SKU selection)
   - Statistics cards (products in catalog, pending review, active orders)
   - Quick stock update section
   - "Download full price list" button

4. **`screencapture-127-0-0-1-5501-index-html-2025-12-14-15_24_28.png`**
   - Alternative storefront design
   - Hero section: "Цветы оптом в Екатеринбурге"
   - Statistics: 50+ suppliers, 1000+ products, 0% commission
   - Category pills (Rose, Tulip, etc.)
   - Product cards in grid layout

5. **`screencapture-127-0-0-1-5501-buyer-html-2025-12-14-15_22_19 (1).png`**
   - Simplified buyer cabinet
   - Cart with fewer items
   - Order history with minimal details
   - "Upload purchase list" button

**Design Notes from References**:
- Color scheme: Purple gradient (#6366F1 to #8B5CF6), green (#10B981), orange (#F59E0B)
- Typography: Clean sans-serif (likely Inter or SF Pro)
- Layout: Cards with shadows, rounded corners (8px-12px)
- Buttons: Primary (blue #3B82F6), secondary (gray), success (green)
- Spacing: Generous whitespace, 16px-24px gaps

---

## Phase 1: HTML Prototypes

### Scope (must implement)

#### A) Project Structure

```
frontend/
├── prototypes/
│   ├── index.html           # Storefront
│   ├── buyer.html           # Buyer cabinet
│   ├── seller.html          # Seller cabinet
│   ├── assets/
│   │   ├── styles.css       # Common styles
│   │   ├── main.js          # Interactions (cart, filters)
│   │   ├── mock-data.js     # Hardcoded mock data
│   │   └── images/
│   │       └── placeholder.svg
│   └── README.md            # How to run
└── .gitignore
```

#### B) Technology Stack (Phase 1)

- **HTML5** - Semantic markup
- **CSS3** - Custom styles (no preprocessors)
- **Tailwind CSS** - Utility-first framework (CDN for prototypes)
- **Vanilla JavaScript** - No frameworks
- **Mock Data** - Hardcoded JSON in `mock-data.js`

**Why Tailwind CSS?**
- References use Tailwind-style classes
- Rapid prototyping
- Easy to migrate to React (Tailwind works with React)

#### C) Storefront (index.html)

**URL**: `http://localhost:5500/index.html` (via Live Server)

**Sections**:

1. **Header / Navigation**
   - Logo: "Цветочный B2B"
   - Nav links: "Витрина", "Кабинет покупателя", "Кабинет продавца"
   - Auth buttons: "Войти", "Регистрация" (disabled in prototype)

2. **Hero Section**
   - Gradient background (purple to pink)
   - Heading: "Самый быстрый поиск и закупка цветов для вашего бизнеса"
   - Subtitle: "Единая платформа для поставщиков и флористов. Найдите лучшие предложения за 5 минут."
   - CTA button: "СМОТРЕТЬ КАТАЛОГ" (smooth scroll to catalog)

3. **Statistics Bar**
   - 3 cards: "50+ Поставщиков", "1000+ Сортов цветов", "0% Комиссия"

4. **Search & Filters**
   - Search input: "Умный поиск по названию, сорту или поставщику..."
   - Product type filter: Pills/chips (Все, Роза, Тюльпаны, Пионы, Гортензия, Хризантема, Лилия)
   - Advanced filters (collapsible):
     - Price range: Slider or min/max inputs (0 - ∞)
     - Length: Checkboxes (40см, 50см, 60см, 70см, 80см)
     - Color: Checkboxes (Красный, Желтый, Белый, Розовый, Сиреневый)
   - "Reset filters" button

5. **Toolbar**
   - Results count: "Найдено: 13 товаров"
   - Sort dropdown: "Цена: по возрастанию", "Цена: по убыванию", "База: все"
   - View toggle: Grid / List icons

6. **Product Grid**
   - Card layout (4 columns on desktop, 2 on tablet, 1 on mobile)
   - Each card:
     - Product image (placeholder if none)
     - Product name: "Роза Красная 40 см"
     - Supplier: "База №1" (small gray text)
     - Rating: 5.2 км (distance icon)
     - Stock: "~15 мин" (delivery time icon)
     - Price: **"120 ₽"** /шт. (large bold)
     - Stock badge: "Остаток: 180" (green badge)
     - Quantity controls: "-" [input] "+" buttons
     - "В корзину" button (blue, primary)

7. **Pagination**
   - Simple prev/next or numbered pages

8. **Footer**
   - Copyright
   - Links (optional)

**Mock Data** (10-15 products):
```json
{
  "products": [
    {
      "id": "1",
      "name": "Роза Красная 40 см",
      "supplier": "База №1",
      "supplier_id": "s1",
      "price": 120,
      "currency": "RUB",
      "unit": "шт",
      "stock": 180,
      "length_cm": 40,
      "product_type": "rose",
      "color": "red",
      "image": "placeholder.svg",
      "distance_km": 5.2,
      "delivery_time_min": 15
    },
    // ... more products
  ]
}
```

**Interactions (JavaScript)**:
- Filter products by type (click pills)
- Sort by price
- Add to cart (increment quantity, store in `localStorage`)
- Update cart badge in header

#### D) Buyer Cabinet (buyer.html)

**URL**: `http://localhost:5500/buyer.html`

**Sections**:

1. **Header**
   - Same as index.html
   - Active tab: "Кабинет покупателя"

2. **Page Title**
   - "Личный кабинет покупателя"
   - Subtitle: "Мульти-корзина и управление заказами"

3. **Cart Section ("Корзина")**
   - Upload purchase list button (top right): "Загрузить список покупок" (disabled in prototype)
   - Cart items grouped by supplier:
     - **База №1** (supplier name as subheading)
       - Product card:
         - Thumbnail + name: "Роза Красная 40 см"
         - Unit price: "120 ₽ / шт" + Stock: "Остаток: 180 шт"
         - Quantity controls: "-" [50] "+"
         - Total: "6 000 ₽"
         - Remove button (X icon)
     - Footer for Base №1:
       - "Товаров: 2" + "Расстояние: 5.2 км" + "Время в пути: ~15 мин"
       - **"Итого: 8 550 ₽"** (large bold)
       - **"Оформить заказ"** button (blue, primary)

     - **База №2** (repeat structure)
       - Different products
       - Warning banner: "Бонусная программа" (orange banner with promo text)

   - If cart empty: Empty state with "Корзина пуста" message

4. **Order History ("История заказов")**
   - List of orders (cards)
   - Each order card:
     - Header: "Заказ #1234" + Status badge (color-coded: orange=pending, green=confirmed, gray=completed)
     - Supplier: "База №1"
     - Date: "15.01.2024, 14:30"
     - Total: "8 550 ₽"
     - Contact: "Телефон: +7 (999) 123-4567" (clickable)
     - Actions: "Оформить заказ" button (if pending) / "Детали" button (view details)
     - If order expanded:
       - Delivery timeline (vertical stepper):
         - ✅ "Заказ принят" (14.01.2024, 14:30)
         - ✅ "Сборка заказа" (14.01.2024, 16:45)
         - 🔵 "В пути" (Ожидается: 15.01.2024, 17:00)
         - ⏸ "Доставлен" (Ожидается: 16.01.2024, 10:00)
       - "Заказ в пути у вас" text + delivery countdown
       - "Расстояние: 5.2 км • Время: ~18 мин"

5. **Statistics Widget** (optional, bottom)
   - 3 cards:
     - "Общая сумма": "9 450 ₽"
     - "Ваша экономия": "0 ₽" (green badge)
     - "Количество заказов": "2 шт."

**Mock Data** (cart + orders):
```json
{
  "cart": [
    { "supplier_id": "s1", "supplier_name": "База №1", "items": [...] },
    { "supplier_id": "s2", "supplier_name": "База №2", "items": [...] }
  ],
  "orders": [
    {
      "id": "1234",
      "supplier": "База №1",
      "status": "pending",
      "date": "15.01.2024, 14:30",
      "total": 8550,
      "phone": "+7 (999) 123-4567",
      "timeline": [...]
    },
    ...
  ]
}
```

**Interactions**:
- Update cart quantities (+/-)
- Remove items from cart
- "Place order" button → show success modal (mock)
- Expand/collapse order details
- Filter orders by status (tabs: Все, В обработке, Выполнены)

#### E) Seller Cabinet (seller.html)

**URL**: `http://localhost:5500/seller.html`

**Sections**:

1. **Header**
   - Same as index.html
   - Active tab: "Кабинет продавца"

2. **Page Title**
   - "Личный кабинет продавца"
   - Subtitle: "Управление прайс-листами и остатками"

3. **Price List Upload**
   - Heading: "Загрузка прайс-листа"
   - Description: "Загрузите файл (XLSX, CSV, TXT) вашим прайс-листом. Система автоматически нормализует товары и создаст каталог за < 1 минуту."
   - Drag-and-drop zone:
     - Upload icon
     - "Перетащите файл сюда или выберите файл"
     - "Поддерживаются форматы: XLSX, CSV, TXT"
   - "Загрузить прайс-лист" button (blue, primary)

4. **Normalization Error Editor**
   - Heading: "Редактор ошибок нормализации"
   - Description: "Товары, которые не удалось автоматически распознать. Привяжите их к нормализованному SKU вручную."
   - Table:
     - Columns: "Supplier Item", "Normalized SKU" (dropdown), "Apply" button
     - Example row:
       - "Rose Yel. 40cm" →
       - Dropdown: "Выберите нормализованный SKU" (options: "Rose Yellow 40cm", "Rose Pink 40cm", ...)
       - "Применить" button (gray)

5. **Statistics**
   - 3 cards:
     - "156 Товаров в каталоге"
     - "12 Требуют обработки"
     - "3 Активных заказов"

6. **Quick Stock Update**
   - Heading: "Быстрое обновление остатков"
   - Description: "Обновите остатки для популярных товаров"
   - List:
     - Product card:
       - "Роза Красная 40 см"
       - Current stock: "Текущий остаток: 180 шт"
       - Input: "Новый ост" (number input)
       - "Обновить" button (blue, small)

7. **Incoming Orders Section** (below fold)
   - Heading: "Входящие заказы"
   - Filter tabs: Все, Ожидают, Подтверждены, Отклонены
   - Table:
     - Columns: Order ID, Buyer, Date, Total, Status, Actions
     - Example row:
       - "#1234", "Retail Shop A", "15.01.2024, 14:30", "8 550 ₽", "Ожидает" (orange badge)
       - Actions: "Подтвердить" (green button), "Отклонить" (red button)
   - Click "Reject" → Modal with reason textarea

8. **Footer**
   - "Загрузить полный прайс-лист" button (dark gray, secondary)

**Mock Data**:
```json
{
  "stats": {
    "products_count": 156,
    "pending_review": 12,
    "active_orders": 3
  },
  "normalization_errors": [
    { "supplier_item": "Rose Yel. 40cm", "normalized_sku_id": null },
    ...
  ],
  "stock_updates": [
    { "product": "Роза Красная 40 см", "current_stock": 180 },
    ...
  ],
  "orders": [
    {
      "id": "1234",
      "buyer": "Retail Shop A",
      "date": "15.01.2024, 14:30",
      "total": 8550,
      "status": "pending"
    },
    ...
  ]
}
```

**Interactions**:
- Drag-and-drop file upload (show progress bar, then success message)
- Dropdown select SKU in normalization editor
- Update stock (show success toast)
- Confirm/reject order (show modal)
- Filter orders by status (tabs)

---

### Deliverables (Phase 1)

1. **`frontend/prototypes/index.html`** - Storefront (fully interactive)
2. **`frontend/prototypes/buyer.html`** - Buyer cabinet (cart + orders)
3. **`frontend/prototypes/seller.html`** - Seller cabinet (uploads + orders)
4. **`frontend/prototypes/assets/styles.css`** - Common styles (variables, utilities)
5. **`frontend/prototypes/assets/main.js`** - Core interactions (cart, filters, modals)
6. **`frontend/prototypes/assets/mock-data.js`** - Mock JSON data
7. **`frontend/prototypes/README.md`** - How to run prototypes locally

---

### Technical Requirements (Phase 1)

**Browser Support**:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile responsive (min width 320px)

**Responsive Breakpoints**:
- Mobile: 320px - 640px (1 column)
- Tablet: 641px - 1024px (2 columns)
- Desktop: 1025px+ (4 columns)

**Accessibility**:
- Semantic HTML5 tags (`<header>`, `<nav>`, `<main>`, `<section>`, `<article>`)
- ARIA labels for buttons/icons
- Keyboard navigation (tab, enter, space)
- Focus states for interactive elements

**Performance**:
- Page load < 1s (all assets < 500KB total)
- No external dependencies except Tailwind CDN
- Lazy load images if many products

**Code Quality**:
- Clean, readable HTML (indentation, comments)
- BEM naming for custom CSS classes
- ESLint-compliant JavaScript (no globals except `window.App`)

---

### Definition of Done (Phase 1)

- [x] 3 HTML files created (index, buyer, seller)
- [x] Matches reference screenshots (layout, colors, spacing)
- [x] All interactive elements work (cart, filters, modals)
- [x] Responsive on mobile/tablet/desktop
- [x] Mock data loads correctly
- [x] README with run instructions (Live Server or `python -m http.server`)
- [x] User reviews and approves design/UX

---

## Phase 2: Production SPA (after Phase 1 approval)

### Scope (must implement)

#### A) Technology Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite (fast dev server, optimized builds)
- **Routing**: React Router v6
- **State Management**: Redux Toolkit + RTK Query
- **UI Library**: Tailwind CSS + Headless UI
- **Forms**: React Hook Form + Zod validation
- **HTTP Client**: Axios (configured with interceptors)
- **Testing**: Vitest + React Testing Library + Playwright (E2E)
- **Linting**: ESLint + Prettier
- **Package Manager**: pnpm (fast, disk-efficient)

**Why React?**
- Popular, large ecosystem
- Good TypeScript support
- Easy to find developers
- Integrates well with existing backend

**Why Redux Toolkit?**
- Centralized state management
- RTK Query for API caching
- DevTools for debugging

#### B) Project Structure

```
frontend/
├── prototypes/          # Phase 1 (keep for reference)
├── public/
│   ├── favicon.ico
│   └── images/
├── src/
│   ├── app/
│   │   ├── store.ts            # Redux store
│   │   └── api.ts              # RTK Query API slice
│   ├── features/
│   │   ├── auth/               # Authentication (Task 4)
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── authSlice.ts
│   │   │   └── authApi.ts
│   │   ├── catalog/            # Storefront
│   │   │   ├── CatalogPage.tsx
│   │   │   ├── ProductCard.tsx
│   │   │   ├── Filters.tsx
│   │   │   └── catalogApi.ts
│   │   ├── buyer/              # Buyer cabinet
│   │   │   ├── BuyerDashboard.tsx
│   │   │   ├── Cart.tsx
│   │   │   ├── OrderHistory.tsx
│   │   │   ├── cartSlice.ts
│   │   │   └── buyerApi.ts
│   │   ├── seller/             # Seller cabinet
│   │   │   ├── SellerDashboard.tsx
│   │   │   ├── PriceListUpload.tsx
│   │   │   ├── OrderManagement.tsx
│   │   │   └── sellerApi.ts
│   │   └── admin/              # Admin panel (optional)
│   ├── components/             # Shared UI components
│   │   ├── Layout.tsx
│   │   ├── Header.tsx
│   │   ├── Button.tsx
│   │   ├── Modal.tsx
│   │   ├── Input.tsx
│   │   └── ...
│   ├── hooks/                  # Custom hooks
│   │   ├── useAuth.ts
│   │   ├── useCart.ts
│   │   └── useDebounce.ts
│   ├── types/                  # TypeScript types
│   │   ├── product.ts
│   │   ├── order.ts
│   │   └── user.ts
│   ├── utils/                  # Utilities
│   │   ├── api.ts              # Axios instance
│   │   ├── formatters.ts
│   │   └── validators.ts
│   ├── App.tsx                 # Root component
│   ├── main.tsx                # Entry point
│   ├── router.tsx              # Routes config
│   └── index.css               # Tailwind imports
├── tests/
│   ├── e2e/                    # Playwright tests
│   │   ├── catalog.spec.ts
│   │   ├── buyer-flow.spec.ts
│   │   └── seller-flow.spec.ts
│   └── unit/                   # Vitest tests
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── .eslintrc.json
└── README.md
```

#### C) API Integration

Map frontend features to backend endpoints (from Tasks 1-3):

**Catalog (GET /offers)**:
- Filters: product_type, price_min, price_max, length_cm, supplier_id
- Search: q parameter
- Pagination: limit, offset

**Cart**:
- Stored in Redux (localStorage persistence)
- Calculate totals client-side

**Orders**:
- Create: POST /orders (buyer_id, items, delivery_address, notes)
- List: GET /orders?buyer_id={id}&status={status}
- Details: GET /orders/{order_id}

**Supplier Orders**:
- List: GET /admin/suppliers/{id}/orders
- Confirm: POST /admin/suppliers/{id}/orders/{order_id}/confirm
- Reject: POST /admin/suppliers/{id}/orders/{order_id}/reject

**Buyers** (admin):
- Create: POST /admin/buyers
- List: GET /admin/buyers

**Suppliers** (admin):
- Upload: POST /admin/suppliers/{id}/imports/csv

**Normalization** (admin):
- Propose: POST /admin/normalization/propose
- Tasks: GET /admin/normalization/tasks
- Confirm: POST /admin/normalization/confirm

#### D) Authentication Flow (Task 4 integration)

**When Task 4 is complete**:
- Login: POST /auth/login → JWT token
- Register: POST /auth/register
- Refresh: POST /auth/refresh
- Logout: Clear token

**Token Storage**:
- Store JWT in `localStorage` (or httpOnly cookie if backend supports)
- Add token to Axios headers via interceptor

**Protected Routes**:
- Buyer cabinet: Requires role=buyer
- Seller cabinet: Requires role=seller
- Admin panel: Requires role=admin

**Fallback (Phase 2 before Task 4)**:
- Use mock auth (hardcoded user in Redux)
- Pass buyer_id/supplier_id in API calls

#### E) Key Features

**Storefront**:
- Product grid with infinite scroll (or pagination)
- Real-time search (debounced, 300ms)
- Multi-select filters (product type, color, length)
- Price range slider
- Sort by price/name
- Add to cart with quantity
- View toggle (grid/list)

**Buyer Cabinet**:
- Multi-supplier cart (grouped)
- Cart persistence (localStorage)
- Checkout flow:
  1. Review cart
  2. Enter delivery address + date
  3. Confirm order
  4. Success message with order ID
- Order history with filters (status, date range)
- Order details modal with timeline
- Reorder functionality (add past order to cart)

**Seller Cabinet**:
- File upload (XLSX/CSV) with drag-and-drop
- Upload progress bar (real-time via polling or websocket)
- Parse results table (success count, error count)
- Normalization task list (pending review)
- Manual mapping UI (dropdown with autocomplete)
- Stock update form (bulk or individual)
- Incoming orders table with filters
- Confirm/reject modal with reason textarea
- Order metrics dashboard (charts with Recharts)

**Admin Panel** (optional, Phase 2):
- Manage buyers (CRUD)
- Manage suppliers (CRUD)
- View all orders
- Global metrics dashboard

#### F) State Management

**Redux Slices**:
- `authSlice`: User, token, role
- `cartSlice`: Cart items, totals (persisted to localStorage)
- `filtersSlice`: Active filters, search query (URL sync)

**RTK Query APIs**:
- `catalogApi`: GET /offers
- `ordersApi`: POST /orders, GET /orders, GET /orders/{id}
- `suppliersApi`: Supplier CRUD, upload, orders
- `buyersApi`: Buyer CRUD
- `normalizationApi`: Propose, tasks, confirm

**Why RTK Query?**
- Auto-generated hooks (`useGetOffersQuery`)
- Caching + invalidation
- Loading/error states
- Optimistic updates

#### G) Form Validation

Use **Zod schemas** for type-safe validation:

```ts
// Order creation form
const orderSchema = z.object({
  buyer_id: z.string().uuid(),
  items: z.array(
    z.object({
      offer_id: z.string().uuid(),
      quantity: z.number().int().min(1),
    })
  ).min(1),
  delivery_address: z.string().min(5),
  delivery_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  notes: z.string().optional(),
});
```

**React Hook Form integration**:
```tsx
const { register, handleSubmit, formState: { errors } } = useForm({
  resolver: zodResolver(orderSchema),
});
```

#### H) Testing

**Unit Tests** (Vitest + React Testing Library):
- Component rendering
- User interactions (click, type)
- State updates
- API mock responses

**E2E Tests** (Playwright):
1. **Catalog flow**:
   - Open storefront
   - Apply filters
   - Search for "rose"
   - Add 2 products to cart
   - Verify cart badge count

2. **Buyer order flow**:
   - Login as buyer
   - Add products to cart
   - Go to checkout
   - Fill delivery form
   - Place order
   - Verify order in history

3. **Seller order flow**:
   - Login as seller
   - View incoming orders
   - Confirm one order
   - Verify status updated

**Coverage Target**: 80%+ for critical paths

#### I) Performance Optimization

- Code splitting (React.lazy)
- Image lazy loading
- Debounced search
- Virtualized lists for long product grids (react-window)
- Production build < 500KB gzipped
- Lighthouse score > 90

#### J) Deployment

**Static Hosting** (Vercel/Netlify):
- `pnpm run build` → `dist/` folder
- Deploy to Vercel with automatic CI/CD
- Environment variables via `.env.production`

**API Base URL**:
- Development: `http://localhost:8000`
- Production: `https://api.flower-b2b.com` (example)

---

### Deliverables (Phase 2)

1. **React application** (fully functional, production-ready)
2. **API integration** (all backend endpoints connected)
3. **Authentication** (JWT if Task 4 done, else mock)
4. **Tests** (unit + E2E, > 80% coverage)
5. **Documentation**:
   - `README.md` (setup, run, build, deploy)
   - `docs/FRONTEND_ARCHITECTURE.md` (state flow, API mapping)
6. **Deployment** (Vercel/Netlify link + instructions)

---

### Definition of Done (Phase 2)

- [x] React app builds without errors
- [x] All pages match approved prototypes (Phase 1)
- [x] All API endpoints integrated and working
- [x] Authentication flow works (JWT or mock)
- [x] Forms validate correctly (Zod schemas)
- [x] Cart persists across sessions (localStorage)
- [x] Orders can be created and viewed
- [x] Seller can upload files and manage orders
- [x] Responsive on mobile/tablet/desktop
- [x] Tests pass (unit + E2E)
- [x] Lighthouse score > 90
- [x] Production build deployed
- [x] README updated with setup instructions

---

## Non-goals (explicitly do NOT implement)

❌ **Backend development** (already done in Tasks 1-3)
❌ **Authentication backend** (will be Task 4)
❌ **Payments** (will be Task 5)
❌ **Notifications** (will be Task 6, email/SMS)
❌ **Mobile app** (native iOS/Android)
❌ **Admin analytics dashboard** (beyond basic metrics)
❌ **Multi-language support** (Russian only for MVP)
❌ **SEO optimization** (no SSR, just client-side SPA)
❌ **Real-time features** (websockets for live orders)

---

## Timeline Estimate

**Phase 1 (HTML Prototypes)**:
- index.html: 4-6 hours
- buyer.html: 4-6 hours
- seller.html: 4-6 hours
- Styles + interactions: 3-4 hours
- Testing + polish: 2-3 hours
- **Total: 17-25 hours** (~3-4 days)

**Phase 2 (Production SPA)**:
- Project setup + routing: 3-4 hours
- Catalog page + filters: 8-10 hours
- Buyer cabinet (cart + orders): 10-12 hours
- Seller cabinet (upload + orders): 10-12 hours
- Authentication integration: 4-6 hours
- Testing (unit + E2E): 8-10 hours
- Polish + responsive: 4-6 hours
- Deployment + docs: 3-4 hours
- **Total: 50-64 hours** (~1.5-2 weeks)

**Overall: 67-89 hours** (~2-3 weeks full-time)

---

## Commands to Run

### Phase 1: HTML Prototypes

```bash
# Clone repo and navigate to prototypes
cd frontend/prototypes

# Option 1: Use Live Server (VS Code extension)
# Right-click index.html → "Open with Live Server"

# Option 2: Use Python simple server
python -m http.server 5500

# Option 3: Use Node.js http-server
npx http-server -p 5500

# Open browser
open http://localhost:5500/index.html
```

### Phase 2: Production SPA

```bash
# Navigate to frontend root
cd frontend

# Install dependencies
pnpm install

# Run dev server
pnpm run dev
# → http://localhost:5173

# Run tests
pnpm run test            # Unit tests (Vitest)
pnpm run test:e2e        # E2E tests (Playwright)

# Lint
pnpm run lint

# Build for production
pnpm run build
# → dist/ folder

# Preview production build
pnpm run preview
# → http://localhost:4173
```

---

## Output format for your response

After creating files:

1) **Plan** - Phase 1 vs Phase 2 breakdown
2) **Implementation notes** - Key decisions (Tailwind vs custom CSS, Redux vs Context, etc.)
3) **Files created** - List all HTML/CSS/JS files (Phase 1) or React components (Phase 2)
4) **Commands to run** - How to view prototypes or start dev server
5) **DoD checklist** - Mark completed items

---

## Next Steps (after Task 9 completion)

1. **Task 4 - Authentication** (JWT backend + frontend integration)
2. **Task 5 - Payments** (Yandex.Checkout integration)
3. **Task 6 - Notifications** (Email/SMS for order status)
4. **Task 7 - Inventory** (Real-time stock sync)
5. **Task 8 - Analytics** (Dashboard for sellers/admin)
6. **Task 10 - Mobile App** (React Native or Flutter)

---

**USER ACTION REQUIRED**:
1. Review this specification
2. Approve to proceed with **Phase 1 (HTML Prototypes)**
3. After prototypes: Review in browser, give feedback
4. After approval: Proceed to **Phase 2 (Production SPA)**
