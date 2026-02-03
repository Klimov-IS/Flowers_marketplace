# Quick Test Guide - Task 2 Progress

## Prerequisites
- Docker Desktop must be running
- Python 3.12+ installed
- Dependencies installed: `pip install -r requirements.txt`

## Step-by-Step Test

### 1. Verify Imports
```bash
python test_imports.py
```
Expected: `[SUCCESS] ALL IMPORTS SUCCESSFUL!`

### 2. Start PostgreSQL
```bash
# Open Docker Desktop first!
cd infra
docker compose up -d
```

Wait 5 seconds for DB to be ready.

### 3. Apply Migrations
```bash
# From project root
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002, Add normalized layer tables
```

### 4. Start API Server
```bash
uvicorn apps.api.main:app --reload
```

API will be available at `http://localhost:8000`

### 5. Open API Documentation
Open browser: `http://localhost:8000/docs`

You should see new endpoints:
- `/admin/dictionary/bootstrap`
- `/admin/dictionary`
- `/admin/skus`

### 6. Test Dictionary Bootstrap (PowerShell/CMD)
```powershell
curl -X POST http://localhost:8000/admin/dictionary/bootstrap
```

Expected response:
```json
{
  "total": 35,
  "inserted": 35,
  "updated": 0
}
```

### 7. List Dictionary Entries
```powershell
curl http://localhost:8000/admin/dictionary?dict_type=product_type
```

You should see entries like "rose", "carnation", etc.

### 8. Create Test Normalized SKU
```powershell
curl -X POST http://localhost:8000/admin/skus `
  -H "Content-Type: application/json" `
  -d '{"product_type":"rose","title":"Rose Explorer","variety":"Explorer"}'
```

### 9. Search SKUs
```powershell
curl "http://localhost:8000/admin/skus?q=explorer"
```

### 10. Verify in Database (Optional)
```bash
# Connect to PostgreSQL
docker exec -it flower_market_db psql -U flower_user -d flower_market

# Check tables
\dt

# Check dictionary entries
SELECT dict_type, key, value FROM dictionary_entries LIMIT 10;

# Check normalized SKUs
SELECT id, product_type, title, variety FROM normalized_skus;

# Exit
\q
```

## ✅ Success Criteria

If all steps pass:
- ✅ All imports work
- ✅ Migrations applied successfully
- ✅ API starts without errors
- ✅ Dictionary bootstrap creates 35 entries
- ✅ Can create and query SKUs
- ✅ Swagger docs show all endpoints

## 🚧 What's Still TODO

The following features are implemented but NOT YET TESTED (need DB running):
- Dictionary CRUD (POST/PATCH)
- SKU search with filters
- Token normalization functions
- Confidence scoring

The following features are NOT YET IMPLEMENTED:
- Normalization Service (propose mappings)
- Normalization endpoints (propose, tasks, confirm)
- Publish Service
- Retail offers endpoint
- Tests

## 📋 Next Session Plan

1. Implement `NormalizationService.propose()`
2. Create normalization endpoints
3. Implement `PublishService`
4. Create offers endpoint
5. Write tests
6. Documentation

Estimated time: 6-8 hours
