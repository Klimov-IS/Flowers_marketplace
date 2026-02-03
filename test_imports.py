"""Quick test to verify imports work."""
import sys

print("Python version:", sys.version)
print("\nTesting imports...")

try:
    print("[OK] Importing FastAPI...")
    from fastapi import FastAPI

    print("[OK] Importing SQLAlchemy...")
    from sqlalchemy import select

    print("[OK] Importing Pydantic...")
    from pydantic import BaseModel

    print("[OK] Importing app models...")
    from apps.api.models import (
        Base,
        City,
        Supplier,
        ImportBatch,
        SupplierItem,
        OfferCandidate,
        NormalizedSKU,
        DictionaryEntry,
        SKUMapping,
        NormalizationTask,
        Offer,
    )

    print("[OK] Importing core normalization...")
    from packages.core.normalization import (
        normalize_tokens,
        detect_product_type,
        detect_variety,
        calculate_confidence,
    )

    print("[OK] Importing services...")
    from apps.api.services.dictionary_service import DictionaryService
    from apps.api.services.sku_service import SKUService

    print("\n[SUCCESS] ALL IMPORTS SUCCESSFUL!")

    # Quick test of functions
    print("\n--- Testing core functions ---")

    # Test normalize_tokens
    test_text = "Rose Explorer 60cm (Ecuador) 120rub"
    normalized = normalize_tokens(test_text)
    print(f"normalize_tokens: '{test_text}' -> '{normalized}'")

    # Test confidence calculation
    confidence = calculate_confidence(
        product_type_match=True,
        variety_match="exact",
        subtype_match=False,
    )
    print(f"calculate_confidence: {confidence}")

    print("\n[SUCCESS] FUNCTION TESTS PASSED!")
    print("\nNext steps:")
    print("1. Start PostgreSQL: cd infra && docker compose up -d")
    print("2. Run migrations: alembic upgrade head")
    print("3. Start API: uvicorn apps.api.main:app --reload")

except ImportError as e:
    print(f"\n[ERROR] Import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
