# TASK — Integrate AI Normalization Agent (DeepSeek)
## Project: B2B Flower Market Platform
## AI Provider: DeepSeek API (deepseek-chat model)
## Scope: AI-assisted column mapping + attribute extraction + SKU suggestions
## Out of scope: AI changes to dictionary; auto-create SKUs; auto-confirm low confidence; AI for publishing

---

## 0) Goal

Integrate DeepSeek AI agent into the existing import/normalization pipeline to improve robustness against diverse supplier price lists.

AI must:
1) Detect/confirm **column mapping** when ambiguous (headers + sample rows)
2) Extract typed **attributes** from `raw_name` / row context
3) Suggest **top-N normalized SKUs** from DB (with confidence)

AI must NOT:
- modify dictionary rules or propose dictionary changes
- create new SKUs
- auto-confirm mappings below thresholds
- publish offers automatically

---

## 1) Agreed operating model (fixed)

### 1.1 Trigger conditions
AI runs only when:
- import_batch row_count <= 5000
AND at least one of the following:
- column mapping is ambiguous / unknown
- parser extracted missing critical fields (e.g., product_type/length/price) above some threshold
- normalization propose yields low confidence for many supplier_items

### 1.2 Confidence tiers (mandatory)
For each AI suggestion (column mapping, attributes, SKU candidate):
- confidence >= 0.90: **auto-apply**
- 0.70 <= confidence < 0.90: **apply + mark as AI-applied (reversible)**
- confidence < 0.70: **DO NOT apply** → push to Review Queue only

### 1.3 Deterministic-first principle
Existing deterministic pipeline always runs.
AI is an assisting layer, never a single point of failure.

If AI is down:
- import continues
- unresolved items stay in Review Queue / parse_events

---

## 2) AI Provider: DeepSeek

### 2.1 Configuration
```env
# .env
DEEPSEEK_API_KEY=sk-b07e5f952ac14b3a8580e15ca1cf2faf
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
AI_ENABLED=true
AI_MAX_ROWS=5000
```

### 2.2 DeepSeek specifics
- **Model**: `deepseek-chat` (cost-effective, good for structured extraction)
- **Pricing**: ~$0.14/1M input tokens, ~$0.28/1M output tokens (очень дёшево)
- **API**: OpenAI-compatible format
- **Context**: 64K tokens
- **Rate limits**: 60 RPM free tier

### 2.3 Cost estimate per import
| Rows | Input tokens | Output tokens | Cost |
|------|--------------|---------------|------|
| 100  | ~20K         | ~10K          | ~$0.006 |
| 500  | ~100K        | ~50K          | ~$0.03 |
| 2000 | ~400K        | ~200K         | ~$0.11 |
| 5000 | ~1M          | ~500K         | ~$0.28 |

---

## 3) Data contracts (strict JSON only)

AI input and output must be strictly structured JSON.

### 3.1 AI Input: ImportContext
```json
{
  "task": "extract_attributes",
  "supplier_id": "uuid",
  "import_batch_id": "uuid",
  "headers": ["Название", "Цена", "Кол-во"],
  "rows": [
    {
      "row_index": 0,
      "raw_name": "Роза Бабалу 50 см (Эквадор) FRAMA FLOWERS",
      "cells": ["Роза Бабалу 50 см (Эквадор) FRAMA FLOWERS", "150", "10"],
      "parser_extracted": {
        "flower_type": "Роза",
        "origin_country": null,
        "length_cm": 50
      }
    }
  ],
  "known_values": {
    "flower_types": ["Роза", "Гвоздика", "Хризантема", ...],
    "countries": ["Эквадор", "Колумбия", "Нидерланды", ...],
    "colors": ["белый", "красный", "розовый", ...]
  }
}
```

### 3.2 AI Output: NormalizationSuggestion
```json
{
  "column_mapping": [
    {"source_index": 0, "target_field": "raw_name", "confidence": 0.95},
    {"source_index": 1, "target_field": "price", "confidence": 0.90},
    {"source_index": 2, "target_field": "pack_qty", "confidence": 0.85}
  ],
  "row_suggestions": [
    {
      "row_index": 0,
      "extracted": {
        "flower_type": {"value": "Роза", "confidence": 0.98},
        "variety": {"value": "Бабалу", "confidence": 0.95},
        "origin_country": {"value": "Эквадор", "confidence": 0.92},
        "farm": {"value": "FRAMA FLOWERS", "confidence": 0.88},
        "length_cm": {"value": 50, "confidence": 0.99},
        "colors": {"value": [], "confidence": 0.70}
      },
      "needs_review": false,
      "rationale": "Стандартный формат: Тип Сорт Размер (Страна) Ферма"
    }
  ]
}
```

---

## 4) Data model changes (DB)

### 4.1 New tables

**Migration: `add_ai_tables.py`**

```sql
-- ai_runs: Track each AI invocation
CREATE TABLE ai_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id UUID NOT NULL REFERENCES suppliers(id),
    import_batch_id UUID REFERENCES import_batches(id),
    run_type VARCHAR(50) NOT NULL, -- 'column_mapping' | 'attribute_extraction' | 'combined'
    model_name VARCHAR(100) NOT NULL DEFAULT 'deepseek-chat',
    status VARCHAR(20) NOT NULL DEFAULT 'created', -- created|running|succeeded|failed|skipped
    row_count INTEGER,
    input_hash VARCHAR(64), -- SHA256 for caching
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost_usd NUMERIC(10, 6),
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ai_suggestions: Individual suggestions per row/field
CREATE TABLE ai_suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ai_run_id UUID NOT NULL REFERENCES ai_runs(id) ON DELETE CASCADE,
    suggestion_type VARCHAR(50) NOT NULL, -- 'column_mapping' | 'attribute' | 'sku_match'
    target_entity VARCHAR(50), -- 'supplier_item' | 'offer_candidate'
    target_id UUID, -- supplier_item_id or offer_candidate_id
    row_index INTEGER, -- for pre-entity suggestions
    field_name VARCHAR(50), -- 'flower_type', 'origin_country', etc.
    suggested_value JSONB NOT NULL,
    confidence NUMERIC(4, 3) NOT NULL, -- 0.000 to 1.000
    applied_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- pending|auto_applied|manual_applied|rejected|needs_review
    applied_at TIMESTAMP WITH TIME ZONE,
    applied_by VARCHAR(20), -- 'system' | 'seller' | 'admin'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_ai_runs_batch ON ai_runs(import_batch_id);
CREATE INDEX idx_ai_runs_status ON ai_runs(status);
CREATE INDEX idx_ai_suggestions_run ON ai_suggestions(ai_run_id);
CREATE INDEX idx_ai_suggestions_target ON ai_suggestions(target_entity, target_id);
CREATE INDEX idx_ai_suggestions_status ON ai_suggestions(applied_status);
```

### 4.2 Extend SupplierItem.attributes schema

```python
# Current
attributes = {
    "origin_country": "Эквадор",
    "colors": ["красный"],
    "flower_type": "Роза",
}

# Extended (with source tracking)
attributes = {
    "origin_country": "Эквадор",
    "colors": ["красный"],
    "flower_type": "Роза",
    # Metadata
    "_sources": {
        "origin_country": "ai",      # parser | ai | manual
        "colors": "manual",
        "flower_type": "parser"
    },
    "_confidences": {
        "origin_country": 0.92,
        "flower_type": 0.98
    },
    "_locked": ["colors"]  # Fields that won't be overwritten on re-import
}
```

---

## 5) Service layer implementation

### 5.1 AI Service (packages/core/ai/)

**File structure:**
```
packages/core/ai/
├── __init__.py
├── client.py          # DeepSeek API client
├── prompts.py         # System prompts for different tasks
├── schemas.py         # Pydantic models for I/O
├── service.py         # Main AIService class
└── utils.py           # Helpers (hashing, batching)
```

**`client.py`:**
```python
import httpx
from typing import Optional
import os

class DeepSeekClient:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.1,  # Low for deterministic extraction
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "response_format": response_format or {"type": "json_object"},
                },
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()
```

**`prompts.py`:**
```python
SYSTEM_PROMPT_EXTRACTION = """Ты AI-ассистент для нормализации данных о цветах.

Твоя задача: извлечь структурированные атрибуты из названий товаров.

Известные типы цветов: {flower_types}
Известные страны: {countries}
Известные цвета: {colors}

Правила:
1. Извлекай только то, что явно указано в названии
2. Если не уверен - ставь confidence < 0.70
3. Размер в см обычно указан как "50 см", "60cm", "50"
4. Страна часто в скобках: "(Эквадор)", "(Ecuador)"
5. Ферма обычно в конце ЗАГЛАВНЫМИ буквами
6. Сорт - это слово после типа цветка

Отвечай ТОЛЬКО валидным JSON в указанном формате."""

SYSTEM_PROMPT_COLUMN_MAPPING = """Ты AI-ассистент для определения структуры CSV/Excel файлов.

Определи какая колонка соответствует какому полю:
- raw_name: название товара (обязательно)
- price: цена (число)
- price_min, price_max: диапазон цен
- pack_qty: количество в упаковке
- length_cm: размер в см
- origin_country: страна происхождения
- stock_qty: остаток на складе

Отвечай ТОЛЬКО валидным JSON."""
```

**`service.py`:**
```python
class AIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = DeepSeekClient()
        self.enabled = os.getenv("AI_ENABLED", "false").lower() == "true"
        self.max_rows = int(os.getenv("AI_MAX_ROWS", "5000"))

    async def process_import_batch(
        self,
        import_batch_id: UUID,
        supplier_id: UUID,
        rows: list[dict],
        headers: list[str],
    ) -> AIRunResult:
        """Main entry point for AI processing."""

        if not self.enabled:
            return AIRunResult(status="skipped", reason="AI disabled")

        if len(rows) > self.max_rows:
            return AIRunResult(status="skipped", reason=f"Too many rows: {len(rows)}")

        # Create AI run record
        ai_run = AIRun(
            supplier_id=supplier_id,
            import_batch_id=import_batch_id,
            run_type="combined",
            status="running",
            row_count=len(rows),
            started_at=datetime.utcnow(),
        )
        self.db.add(ai_run)
        await self.db.flush()

        try:
            # Step 1: Column mapping (if needed)
            column_mapping = await self._extract_column_mapping(headers, rows[:10])

            # Step 2: Attribute extraction (batch)
            suggestions = await self._extract_attributes_batch(rows, ai_run.id)

            # Step 3: Apply suggestions based on confidence
            applied_count = await self._apply_suggestions(suggestions)

            ai_run.status = "succeeded"
            ai_run.finished_at = datetime.utcnow()

            return AIRunResult(
                status="succeeded",
                ai_run_id=ai_run.id,
                suggestions_count=len(suggestions),
                applied_count=applied_count,
            )

        except Exception as e:
            ai_run.status = "failed"
            ai_run.error_message = str(e)
            ai_run.finished_at = datetime.utcnow()
            raise
```

### 5.2 Integration into ImportService

**`apps/api/services/import_service.py` changes:**

```python
# Add after deterministic parsing
async def _run_ai_enrichment(
    self,
    import_batch_id: UUID,
    supplier_id: UUID,
    supplier_items: list[SupplierItem],
) -> None:
    """Run AI enrichment for items with missing attributes."""

    # Filter items that need AI help
    items_needing_ai = [
        item for item in supplier_items
        if not item.attributes.get("flower_type")
        or not item.attributes.get("origin_country")
    ]

    if not items_needing_ai:
        logger.info("ai_skipped", reason="all_items_complete")
        return

    ai_service = AIService(self.db)
    result = await ai_service.process_import_batch(
        import_batch_id=import_batch_id,
        supplier_id=supplier_id,
        rows=[{"raw_name": item.raw_name, "id": str(item.id)} for item in items_needing_ai],
        headers=[],
    )

    logger.info("ai_enrichment_complete", **result.dict())
```

---

## 6) API Endpoints

### 6.1 Admin endpoints

**`apps/api/routers/ai.py`:**

```python
router = APIRouter(prefix="/admin/ai", tags=["AI"])

@router.post("/imports/{import_batch_id}/run")
async def start_ai_run(
    import_batch_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AIRunResponse:
    """Manually trigger AI processing for an import batch."""
    ...

@router.get("/runs/{ai_run_id}")
async def get_ai_run(
    ai_run_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AIRunDetailResponse:
    """Get AI run details and statistics."""
    ...

@router.get("/imports/{import_batch_id}/suggestions")
async def get_suggestions(
    import_batch_id: UUID,
    status: Optional[str] = Query(None),  # pending|needs_review|applied
    db: AsyncSession = Depends(get_db),
) -> list[AISuggestionResponse]:
    """Get AI suggestions for review."""
    ...

@router.post("/suggestions/{suggestion_id}/apply")
async def apply_suggestion(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AISuggestionResponse:
    """Manually apply an AI suggestion."""
    ...

@router.post("/suggestions/{suggestion_id}/reject")
async def reject_suggestion(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AISuggestionResponse:
    """Reject an AI suggestion."""
    ...

@router.post("/suggestions/bulk-apply")
async def bulk_apply_suggestions(
    suggestion_ids: list[UUID],
    db: AsyncSession = Depends(get_db),
) -> BulkApplyResponse:
    """Apply multiple suggestions at once."""
    ...
```

---

## 7) UI Integration (Seller Cabinet)

### 7.1 Import result with AI status

After upload, show:
```
Импорт завершён
├── Всего строк: 219
├── Распознано парсером: 180 (82%)
├── Дообработано AI: 35 (16%)
│   ├── Автоприменено (>90%): 28
│   └── На проверку (<90%): 7
└── Ошибки: 4 (2%)

[Открыть очередь проверки (7)]
```

### 7.2 Review Queue page

New page: `/seller/review-queue`

Features:
- List of items with AI suggestions
- Show confidence badges (green >90%, yellow 70-90%, red <70%)
- Actions: Apply / Reject / Edit manually
- Bulk actions: Apply all >80%, Reject all <50%

### 7.3 AssortmentTable enhancement

Show AI source indicator:
```tsx
{item.attributes._sources?.flower_type === 'ai' && (
  <span className="ml-1 text-xs bg-blue-100 text-blue-600 px-1 rounded">
    AI {Math.round(item.attributes._confidences?.flower_type * 100)}%
  </span>
)}
```

---

## 8) Implementation Plan

### Phase 0: Preparation (1-2 дня)
- [x] Сохранить DeepSeek API key в .env
- [ ] Создать миграцию для ai_runs и ai_suggestions таблиц
- [ ] Расширить SupplierItem.attributes схему (_sources, _confidences, _locked)
- [ ] Добавить source tracking в PATCH endpoint

### Phase 1: AI Service Core (2-3 дня)
- [ ] Создать `packages/core/ai/` модуль
- [ ] Реализовать DeepSeekClient
- [ ] Написать промпты для extraction
- [ ] Создать AIService с базовой логикой
- [ ] Unit тесты для AI service

### Phase 2: Pipeline Integration (1-2 дня)
- [ ] Интегрировать AI в ImportService (после парсера)
- [ ] Добавить confidence tier логику
- [ ] Реализовать применение suggestions
- [ ] Integration тест: import → AI → suggestions

### Phase 3: API & Review Queue (2-3 дня)
- [ ] Создать `/admin/ai/` роутер
- [ ] Реализовать endpoints для suggestions
- [ ] Создать Review Queue страницу в Seller Cabinet
- [ ] Добавить AI индикаторы в AssortmentTable

### Phase 4: Polish & Testing (1-2 дня)
- [ ] Добавить кэширование по input_hash
- [ ] Добавить rate limiting
- [ ] Добавить метрики и логирование
- [ ] E2E тесты
- [ ] Документация

---

## 9) Acceptance Criteria (Definition of Done)

Feature is done when:

1. [ ] Import pipeline still works without AI (AI_ENABLED=false)
2. [ ] For imports <= 5000 rows, AI run can be started and completes
3. [ ] Column mapping AI can resolve ambiguous formats
4. [ ] Row extraction AI fills missing attributes with confidence
5. [ ] Auto-apply works for confidence >= 0.90
6. [ ] Suggestions with confidence < 0.70 go to Review Queue only
7. [ ] Review Queue UI allows apply/reject suggestions
8. [ ] All AI actions are auditable (ai_runs + ai_suggestions)
9. [ ] Source tracking shows parser/ai/manual in UI
10. [ ] Basic tests exist:
    - [ ] Unit test: confidence tier logic
    - [ ] Unit test: DeepSeek client mock
    - [ ] Integration test: AI run lifecycle
    - [ ] Integration test: import with AI disabled

---

## 10) Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| DeepSeek API down | Low | Medium | Graceful fallback, import continues |
| Slow response (>30s) | Medium | Low | Timeout + retry, async processing |
| Wrong extractions | Medium | Medium | Confidence tiers, manual review |
| Cost overrun | Low | Low | Row limit (5000), caching |
| Rate limiting | Low | Low | Batch requests, exponential backoff |

---

## 11) Files to create/modify

### New files:
```
packages/core/ai/__init__.py
packages/core/ai/client.py
packages/core/ai/prompts.py
packages/core/ai/schemas.py
packages/core/ai/service.py
packages/core/ai/utils.py
apps/api/routers/ai.py
apps/api/models/ai.py
alembic/versions/xxx_add_ai_tables.py
frontend/src/features/seller/pages/ReviewQueuePage.tsx
frontend/src/features/seller/components/AISuggestionCard.tsx
frontend/src/features/seller/components/ConfidenceBadge.tsx
```

### Modified files:
```
apps/api/services/import_service.py  # Add AI enrichment call
apps/api/routers/admin.py            # Include AI router
apps/api/main.py                     # Register AI router
frontend/src/features/seller/supplierApi.ts  # Add AI endpoints
frontend/src/features/seller/components/AssortmentTable.tsx  # Add AI indicators
frontend/src/App.tsx                 # Add ReviewQueue route
.env                                 # Add DEEPSEEK_* vars (done)
.env.example                         # Add DEEPSEEK_* template
```

---

## 12) Estimated timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 0 | 1-2 дня | DB готова, source tracking |
| Phase 1 | 2-3 дня | AI service работает локально |
| Phase 2 | 1-2 дня | AI интегрирован в импорт |
| Phase 3 | 2-3 дня | Review Queue UI готов |
| Phase 4 | 1-2 дня | Тесты, документация |
| **Total** | **7-12 дней** | **Полная интеграция AI** |

---
