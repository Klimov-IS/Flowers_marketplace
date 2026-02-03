# Sprint 4 — Frontend Integration & Production Readiness

**Дата**: 2026-02-03
**Статус**: ✅ COMPLETED
**Длительность**: 1 день (ускоренный спринт)

---

## Цель спринта

Подготовить MVP к пилоту с реальными поставщиками:
- Интегрировать React-frontend с backend API
- Добавить базовую авторизацию
- Создать UI для поставщиков (загрузка прайсов)
- Расширить словарь нормализации

---

## Задачи

### 4.1 Git Repository Setup (Priority: Critical) ✅ DONE

**Проблема**: Git инициализирован в `C:/Users/79025`, не в папке проекта.

**Задачи**:
- [x] Удалить привязку к родительскому репозиторию
- [x] Инициализировать git в папке проекта
- [x] Сделать initial commit всех файлов
- [x] Создать remote репозиторий (GitHub/GitLab)
- [x] Push initial commit

**Результат**:
- Repository: https://github.com/Klimov-IS/Flowers_marketplace
- Initial commit: 172 files, 33,739 lines
- Branch: main

---

### 4.2 Frontend-Backend Integration (Priority: High) ✅ DONE

**Задачи**:
- [x] Настроить API proxy в Vite config
- [x] Реализовать API client (axios/fetch wrapper)
- [x] Подключить catalog API к CatalogPage
- [x] Подключить orders API к CheckoutModal
- [x] Добавить error handling и loading states

**Изменения**:
- `frontend/vite.config.ts` — добавлен proxy для /offers, /orders, /admin, /buyers
- `frontend/src/utils/api.ts` — axios client с interceptors (уже был)
- `frontend/src/features/catalog/catalogApi.ts` — RTK Query (уже был)
- `frontend/src/features/buyer/ordersApi.ts` — RTK Query (уже был)

**Definition of Done**:
- [x] Buyer может видеть реальные офферы из БД
- [x] Buyer может оформить заказ через UI
- [x] Ошибки API отображаются пользователю

---

### 4.3 Supplier Dashboard (Priority: High) ✅ DONE

**Задачи**:
- [x] Страница загрузки CSV прайса
- [x] Отображение статуса импорта (progress, errors)
- [x] Список входящих заказов
- [x] Кнопки Confirm/Reject заказа
- [x] Базовая статистика (заказы, выручка)

**Реализованные компоненты**:
- `frontend/src/features/seller/PriceListUpload.tsx` — drag-and-drop upload, progress display
- `frontend/src/features/seller/SellerDashboard.tsx` — полный dashboard с метриками
- `frontend/src/features/seller/RejectOrderModal.tsx` — модальное окно отклонения
- `frontend/src/features/seller/supplierApi.ts` — RTK Query (orders, metrics, upload)

**Definition of Done**:
- [x] Поставщик может загрузить CSV через UI
- [x] Поставщик видит ошибки парсинга
- [x] Поставщик может обработать заказы

---

### 4.4 Basic Authentication (Priority: Medium) ✅ DONE

**Задачи**:
- [x] JWT auth middleware (FastAPI)
- [x] Login/Register endpoints
- [x] Frontend auth flow (login page, token storage)
- [x] Protected routes (buyer vs supplier)
- [x] Refresh token logic

**Реализовано**:
- `apps/api/auth/` — модуль с JWT, password hashing, dependencies
- `apps/api/routers/auth.py` — /auth/login, /auth/register/buyer, /auth/register/supplier, /auth/refresh, /auth/me
- `frontend/src/features/auth/authApi.ts` — RTK Query для auth
- `frontend/src/features/auth/authSlice.ts` — обновлен для JWT
- `frontend/src/features/auth/LoginPage.tsx` — реальный логин
- Migration 004: password_hash + email для buyers/suppliers

**Definition of Done**:
- [x] Buyer/Supplier могут залогиниться
- [x] API endpoints проверяют JWT (get_current_user dependency)
- [x] Refresh token работает

---

### 4.5 Dictionary Expansion (Priority: Medium) ✅ DONE

**Текущее состояние**: Расширен с ~35 до ~115 записей.

**Задачи**:
- [x] Добавить популярные сорта роз (50+ varieties)
- [x] Добавить сезонные цветы
- [x] Добавить синонимы на русском/английском
- [x] Добавить regex правила для специфичных форматов
- [ ] Тестирование на реальных прайсах (отложено)

**Реализовано**:
- `apps/api/data/dictionary_seed.py` — расширен до 115+ записей:
  - 29 типов продуктов (rose, tulip, peony, hydrangea, lily, gerbera, etc.)
  - 50+ сортов роз с цветами (Freedom, Red Naomi, Avalanche, Mondial, Explorer, etc.)
  - 12 цветов с русскими/английскими синонимами
  - 10 стран-производителей (Ecuador, Colombia, Netherlands, Kenya, Russia, etc.)
  - 4 типа упаковки
  - 9 стоп-слов
  - 12 regex правил для специфичных форматов

**Definition of Done**:
- [x] Словарь расширен до 100+ записей
- [x] Покрыты все основные типы цветов
- [x] Добавлены популярные сорта роз

---

### 4.6 Production Hardening (Priority: Low) ✅ DONE

**Задачи**:
- [x] CORS configuration (whitelist domains)
- [x] Rate limiting (in-memory middleware)
- [ ] Request validation (size limits) — отложено
- [ ] Health check improvements — отложено
- [x] Migrate to FastAPI lifespan (deprecation fix)

**Реализовано**:
- `apps/api/main.py`:
  - Migrated from `@app.on_event()` to `lifespan` context manager
  - CORS origins configurable via `CORS_ORIGINS` env variable
  - Added simple in-memory rate limiting middleware (opt-in)
- `apps/api/config.py`:
  - Added `cors_origins` setting (comma-separated list or "*")
  - Added `rate_limit_enabled`, `rate_limit_requests`, `rate_limit_window`
- `.env.example` — documented new settings

---

## Метрики успеха спринта

| Метрика | Target |
|---------|--------|
| Frontend pages working | 5+ |
| API endpoints with auth | 80% |
| Dictionary entries | 100+ |
| Auto-normalization rate | 80% |
| Test coverage | Maintain current |

---

## Риски

| Риск | Mitigation |
|------|------------|
| Реальные прайсы сложнее тестовых | Собрать 5+ реальных примеров до начала |
| JWT усложнит тестирование | Добавить dev bypass для тестов |
| Frontend интеграция долгая | Начать с minimal viable UI |

---

## Зависимости

- **Task 4.1** (Git) — делаем первым, блокирует всё
- **Task 4.2** (Frontend) — можно параллельно с 4.4
- **Task 4.3** (Supplier UI) — зависит от 4.2
- **Task 4.4** (Auth) — можно параллельно с 4.2
- **Task 4.5** (Dictionary) — независимый
- **Task 4.6** (Hardening) — в конце спринта

---

## Timeline

```
Week 1:
├── Day 1-2: Git setup + Initial commit
├── Day 3-4: Frontend-Backend integration (catalog)
└── Day 5-7: Supplier dashboard + Orders UI

Week 2:
├── Day 1-3: Authentication layer
├── Day 4-5: Dictionary expansion
└── Day 6-7: Testing + Hardening
```

---

## Команда

- **Backend**: FastAPI, SQLAlchemy, JWT
- **Frontend**: React, TypeScript, Redux Toolkit
- **DevOps**: Docker, PostgreSQL, git

---

## Checklist перед стартом

- [x] Code review завершён
- [x] Текущий статус документирован
- [x] Git репозиторий настроен правильно
- [x] Remote repository создан
- [x] Initial commit сделан

**Статус**: Sprint 4 IN PROGRESS (2026-02-03)

### Progress Summary
- ✅ Task 4.1: Git Setup — DONE
- ✅ Task 4.2: Frontend-Backend Integration — DONE (was already implemented!)
- ✅ Task 4.3: Supplier Dashboard — DONE (was already implemented!)
- ✅ Task 4.4: Authentication — DONE (JWT + password auth)
- ✅ Task 4.5: Dictionary Expansion — DONE (35 → 115+ entries)
- ✅ Task 4.6: Production Hardening — DONE (lifespan, CORS, rate limiting)

**Commits:**
1. Initial commit (172 files, 33,739 lines)
2. Add Vite proxy configuration
3. Add JWT authentication backend and frontend
4. Expand dictionary seed (115+ entries)
5. Production hardening (lifespan, CORS, rate limiting)

---

## 🎉 Sprint 4 COMPLETED

**Дата завершения**: 2026-02-03

Все основные задачи Sprint 4 выполнены:
- Проект под контролем версий (GitHub)
- Frontend и Backend интегрированы
- JWT авторизация работает
- Словарь нормализации расширен
- API готов к production (CORS, rate limiting, lifespan)
