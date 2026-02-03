# Integration Tests

Integration tests require a running PostgreSQL database.

## Prerequisites

1. Start PostgreSQL with Docker Compose:
```bash
cd infra
docker compose up -d
```

2. Run migrations:
```bash
alembic upgrade head
```

## Running Tests

Run all integration tests:
```bash
pytest tests/integration/ -v
```

Run specific test:
```bash
pytest tests/integration/test_normalization_propose.py::test_normalization_propose_flow -v
```

## Test Coverage

### test_normalization_propose.py
- `test_normalization_propose_flow`: Complete propose flow with idempotency check
- `test_normalization_propose_by_batch`: Filtering by import_batch_id
- `test_normalization_propose_no_candidates`: Behavior when no normalized SKUs exist
- `test_normalization_error_handling`: Validation and error cases

## Notes

- Tests use transaction rollback for cleanup (no database pollution)
- Each test creates its own test data (city, supplier, CSV import)
- Dictionary is bootstrapped for each test
- Tests verify both correctness and idempotency
