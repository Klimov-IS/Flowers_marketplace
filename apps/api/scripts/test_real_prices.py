"""Test script for real price list imports.

This script tests the parsing of real price lists from docs/Прайсы/
without requiring a database connection.

Usage:
    python -m apps.api.scripts.test_real_prices
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from packages.core.parsing import parse_csv_content, normalize_headers, parse_price


def test_price_file(filepath: Path) -> dict:
    """Test parsing a single price file.

    Returns:
        Dictionary with test results
    """
    print(f"\n{'='*60}")
    print(f"Testing: {filepath.name}")
    print("=" * 60)

    content = filepath.read_bytes()

    try:
        rows = parse_csv_content(content)
    except ValueError as e:
        print(f"ERROR: Failed to parse CSV: {e}")
        return {"file": filepath.name, "error": str(e), "rows": 0, "valid": 0}

    print(f"Total rows parsed: {len(rows)}")

    if rows:
        headers = rows[0]["headers"]
        print(f"Headers detected: {headers[:5]}...")  # Show first 5 headers

        header_map = normalize_headers(headers)
        print(f"Header mapping: {header_map}")

    # Count valid prices
    valid = 0
    errors = []
    examples = []

    for row in rows:
        cells = row["cells"]
        header_map = normalize_headers(row["headers"])

        name_idx = header_map.get("name")
        price_idx = header_map.get("price")

        if name_idx is None:
            errors.append(f"Row {row['row_number']}: No name column found")
            continue

        if price_idx is None:
            errors.append(f"Row {row['row_number']}: No price column found")
            continue

        name = cells[name_idx] if name_idx < len(cells) else ""
        price = cells[price_idx] if price_idx < len(cells) else ""

        # Skip group headers (rows without price)
        if not price.strip():
            continue

        result = parse_price(price)

        if result["error"]:
            errors.append(f"Row {row['row_number']}: {name[:30]} | {price} -> {result['error']}")
        else:
            valid += 1
            if len(examples) < 10:
                examples.append(f"  + {name[:40]}: {result['price_min']} RUB")

    print(f"\nValid prices: {valid}/{len(rows)}")
    print(f"Success rate: {valid/len(rows)*100:.1f}%" if rows else "N/A")

    if examples:
        print("\nExamples of parsed items:")
        for ex in examples:
            print(ex)

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors[:10]:  # Show first 10 errors
            print(f"  - {e}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")

    return {
        "file": filepath.name,
        "rows": len(rows),
        "valid": valid,
        "errors": len(errors),
        "success_rate": valid / len(rows) * 100 if rows else 0,
    }


def main():
    """Run tests on all price files."""
    prices_dir = project_root / "docs" / "Прайсы"

    if not prices_dir.exists():
        print(f"ERROR: Price directory not found: {prices_dir}")
        sys.exit(1)

    csv_files = list(prices_dir.glob("*.csv"))
    print(f"Found {len(csv_files)} CSV files in {prices_dir}")

    results = []
    for f in csv_files:
        # Skip matrix format (not supported yet)
        if "Мой прайс" in f.name:
            print(f"\nSkipping matrix format: {f.name}")
            continue

        result = test_price_file(f)
        results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'File':<45} {'Rows':>6} {'Valid':>6} {'Rate':>8}")
    print("-" * 60)
    for r in results:
        print(f"{r['file'][:44]:<45} {r['rows']:>6} {r['valid']:>6} {r['success_rate']:>7.1f}%")

    total_rows = sum(r["rows"] for r in results)
    total_valid = sum(r["valid"] for r in results)
    overall_rate = total_valid / total_rows * 100 if total_rows else 0

    print("-" * 60)
    print(f"{'TOTAL':<45} {total_rows:>6} {total_valid:>6} {overall_rate:>7.1f}%")


if __name__ == "__main__":
    main()
