# Sprint 4 — Frontend Integration & Production Readiness

**Дата**: 2026-02-03
**Статус**: Planning
**Длительность**: 2 недели

---

## Цель спринта

Подготовить MVP к пилоту с реальными поставщиками:
- Интегрировать React-frontend с backend API
- Добавить базовую авторизацию
- Создать UI для поставщиков (загрузка прайсов)
- Расширить словарь нормализации

---

## Задачи

### 4.1 Git Repository Setup (Priority: Critical)

**Проблема**: Git инициализирован в `C:/Users/79025`, не в папке проекта.

**Задачи**:
- [ ] Удалить привязку к родительскому репозиторию
- [ ] Инициализировать git в папке проекта
- [ ] Сделать initial commit всех файлов
- [ ] Создать remote репозиторий (GitHub/GitLab)
- [ ] Push initial commit

**Команды**:
```bash
cd "c:\Users\79025\Desktop\проекты\Маркетплейс"
git init
git add .
git commit -m "Initial commit: MVP Phase 1-3 complete"
```

---

### 4.2 Frontend-Backend Integration (Priority: High)

**Текущее состояние**: React-app существует, но не связан с API.

**Задачи**:
- [ ] Настроить API proxy в Vite config
- [ ] Реализовать API client (axios/fetch wrapper)
- [ ] Подключить catalog API к CatalogPage
- [ ] Подключить orders API к CheckoutModal
- [ ] Добавить error handling и loading states

**Файлы**:
- `frontend/vite.config.ts` — proxy setup
- `frontend/src/api/client.ts` — API wrapper
- `frontend/src/features/catalog/catalogApi.ts` — catalog hooks
- `frontend/src/features/buyer/ordersApi.ts` — orders hooks

**Definition of Done**:
- [ ] Buyer может видеть реальные офферы из БД
- [ ] Buyer может оформить заказ через UI
- [ ] Ошибки API отображаются пользователю

---

### 4.3 Supplier Dashboard (Priority: High)

**Текущее состояние**: Только API endpoints, нет UI.

**Задачи**:
- [ ] Страница загрузки CSV прайса
- [ ] Отображение статуса импорта (progress, errors)
- [ ] Список входящих заказов
- [ ] Кнопки Confirm/Reject заказа
- [ ] Базовая статистика (заказы, выручка)

**Файлы**:
- `frontend/src/features/seller/PriceListUpload.tsx` — расширить
- `frontend/src/features/seller/OrdersTable.tsx` — новый
- `frontend/src/features/seller/SellerDashboard.tsx` — интеграция

**Definition of Done**:
- [ ] Поставщик может загрузить CSV через UI
- [ ] Поставщик видит ошибки парсинга
- [ ] Поставщик может обработать заказы

---

### 4.4 Basic Authentication (Priority: Medium)

**Текущее состояние**: Нет авторизации, buyer_id в request body.

**Задачи**:
- [ ] JWT auth middleware (FastAPI)
- [ ] Login/Register endpoints
- [ ] Frontend auth flow (login page, token storage)
- [ ] Protected routes (buyer vs supplier)
- [ ] Refresh token logic

**Файлы**:
- `apps/api/auth/` — новый модуль
- `apps/api/routers/auth.py` — login/register endpoints
- `frontend/src/features/auth/` — login flow

**Definition of Done**:
- [ ] Buyer/Supplier могут залогиниться
- [ ] API endpoints проверяют JWT
- [ ] Refresh token работает

---

### 4.5 Dictionary Expansion (Priority: Medium)

**Текущее состояние**: Базовый словарь ~35 записей.

**Задачи**:
- [ ] Добавить популярные сорта роз (50+ varieties)
- [ ] Добавить сезонные цветы
- [ ] Добавить синонимы на русском/английском
- [ ] Добавить regex правила для специфичных форматов
- [ ] Тестирование на реальных прайсах

**Файлы**:
- `apps/api/data/dictionary_seed.py` — расширить
- `data/samples/` — добавить реальные примеры прайсов

**Definition of Done**:
- [ ] 80%+ позиций нормализуются автоматически
- [ ] Тесты на реальных данных проходят

---

### 4.6 Production Hardening (Priority: Low)

**Задачи**:
- [ ] CORS configuration (whitelist domains)
- [ ] Rate limiting (slowapi)
- [ ] Request validation (size limits)
- [ ] Health check improvements
- [ ] Migrate to FastAPI lifespan (deprecation fix)

**Файлы**:
- `apps/api/main.py` — CORS, lifespan
- `apps/api/middleware/` — rate limiting

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
- [ ] Git репозиторий настроен правильно
- [ ] Remote repository создан
- [ ] Initial commit сделан
