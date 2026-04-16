"""Import service - orchestrates CSV import pipeline."""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.logging_config import get_logger
from apps.api.models import (
    ImportBatch,
    ParseEvent,
    ParseRun,
    RawRow,
)
from apps.api.models.product import Product
from packages.core.parsing import (
    detect_matrix_format,
    extract_length_cm,
    extract_matrix_columns,
    extract_origin_country,
    extract_pdf_text,
    parse_csv_content,
    parse_pdf_content,
    parse_xlsx_content,
    parse_price,
    normalize_name as normalize_name_rich,
)
from packages.core.ai.column_mapping import ai_detect_column_mapping
from packages.core.ai.text_extraction import ai_extract_price_from_text
from packages.core.parsing.attributes import extract_pack_qty
from packages.core.parsing.headers import normalize_headers
from packages.core.utils.stable_key import generate_stable_key

logger = get_logger(__name__)

PARSER_VERSION = "1.0.0-f1"  # Format F1: simple row table


class ImportService:
    """Service for importing CSV price lists."""

    def __init__(self, db: AsyncSession):
        """Initialize import service."""
        self.db = db

    async def import_file(
        self,
        supplier_id: UUID,
        filename: str,
        content: bytes,
    ) -> ImportBatch:
        """Import a price list file (CSV, PDF, or XLSX).

        Dispatches to the appropriate parser based on file extension.
        """
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if ext == "csv":
            return await self.import_csv(supplier_id, filename, content)
        elif ext == "pdf":
            return await self._import_pdf(supplier_id, filename, content)
        elif ext in ("xlsx", "xls"):
            return await self._import_xlsx(supplier_id, filename, content)
        else:
            raise ValueError(f"Unsupported file format: .{ext}")

    async def _import_pdf(
        self,
        supplier_id: UUID,
        filename: str,
        content: bytes,
    ) -> ImportBatch:
        """Import PDF price list for supplier.

        Uses the same 7-stage pipeline as import_csv() but parses via
        PyMuPDF's find_tables() instead of CSV reader.
        """
        logger.info("import_started", supplier_id=str(supplier_id), filename=filename, format="pdf")

        import_batch = ImportBatch(
            supplier_id=supplier_id,
            source_type="pdf",
            source_filename=filename,
            status="received",
            meta={"file_size": len(content)},
        )
        self.db.add(import_batch)
        await self.db.flush()

        try:
            # Try table extraction first
            rows = None
            ai_text_fallback = False
            try:
                rows = parse_pdf_content(content)
                logger.info("pdf_parsed", batch_id=str(import_batch.id), rows_count=len(rows))
            except ValueError as table_err:
                # Table extraction failed — try AI text extraction fallback
                logger.info(
                    "pdf_table_extraction_failed",
                    batch_id=str(import_batch.id),
                    error=str(table_err),
                )
                raw_text = extract_pdf_text(content)
                if raw_text.strip():
                    logger.info(
                        "pdf_ai_text_fallback_started",
                        batch_id=str(import_batch.id),
                        text_length=len(raw_text),
                    )
                    rows = await ai_extract_price_from_text(raw_text)
                    if rows:
                        ai_text_fallback = True
                        logger.info(
                            "pdf_ai_text_fallback_success",
                            batch_id=str(import_batch.id),
                            rows_count=len(rows),
                        )
                    else:
                        raise ValueError(
                            "PDF contains no extractable table data"
                        ) from table_err
                else:
                    raise ValueError(
                        "PDF contains no extractable text or table data"
                    ) from table_err

            raw_rows = []
            for row_data in rows:
                raw_row = RawRow(
                    import_batch_id=import_batch.id,
                    row_kind="data",
                    row_ref=f"row_{row_data['row_number']}",
                    raw_cells={"cells": row_data["cells"], "headers": row_data["headers"]},
                    raw_text=" | ".join(row_data["cells"]),
                )
                self.db.add(raw_row)
                raw_rows.append(raw_row)

            await self.db.flush()

            parse_run = ParseRun(
                import_batch_id=import_batch.id,
                parser_version=PARSER_VERSION + ("-ai-text" if ai_text_fallback else ""),
            )
            self.db.add(parse_run)
            await self.db.flush()

            summary = await self._process_rows(
                supplier_id=supplier_id,
                import_batch_id=import_batch.id,
                parse_run_id=parse_run.id,
                rows=rows,
                raw_rows=raw_rows,
            )

            if ai_text_fallback:
                summary["extraction_method"] = "ai_text_fallback"

            parse_run.finished_at = datetime.utcnow()
            parse_run.summary = summary
            import_batch.status = "parsed"
            await self.db.commit()

            logger.info("import_completed", batch_id=str(import_batch.id), summary=summary)
            return import_batch

        except Exception as e:
            import_batch.status = "failed"
            import_batch.meta["error"] = str(e)
            await self.db.commit()
            logger.error("import_failed", batch_id=str(import_batch.id), error=str(e))
            raise ValueError(f"Import failed: {str(e)}")

    async def _import_xlsx(
        self,
        supplier_id: UUID,
        filename: str,
        content: bytes,
    ) -> ImportBatch:
        """Import XLSX price list for supplier.

        Uses the same pipeline as _import_pdf() but parses via openpyxl.
        """
        logger.info("import_started", supplier_id=str(supplier_id), filename=filename, format="xlsx")

        import_batch = ImportBatch(
            supplier_id=supplier_id,
            source_type="xlsx",
            source_filename=filename,
            status="received",
            meta={"file_size": len(content)},
        )
        self.db.add(import_batch)
        await self.db.flush()

        try:
            rows = parse_xlsx_content(content)
            logger.info("xlsx_parsed", batch_id=str(import_batch.id), rows_count=len(rows))

            raw_rows = []
            for row_data in rows:
                raw_row = RawRow(
                    import_batch_id=import_batch.id,
                    row_kind="data",
                    row_ref=f"row_{row_data['row_number']}",
                    raw_cells={"cells": row_data["cells"], "headers": row_data["headers"]},
                    raw_text=" | ".join(row_data["cells"]),
                )
                self.db.add(raw_row)
                raw_rows.append(raw_row)

            await self.db.flush()

            parse_run = ParseRun(
                import_batch_id=import_batch.id,
                parser_version=PARSER_VERSION,
            )
            self.db.add(parse_run)
            await self.db.flush()

            summary = await self._process_rows(
                supplier_id=supplier_id,
                import_batch_id=import_batch.id,
                parse_run_id=parse_run.id,
                rows=rows,
                raw_rows=raw_rows,
            )

            parse_run.finished_at = datetime.utcnow()
            parse_run.summary = summary
            import_batch.status = "parsed"
            await self.db.commit()

            logger.info("import_completed", batch_id=str(import_batch.id), summary=summary)
            return import_batch

        except Exception as e:
            import_batch.status = "failed"
            import_batch.meta["error"] = str(e)
            await self.db.commit()
            logger.error("import_failed", batch_id=str(import_batch.id), error=str(e))
            raise ValueError(f"Import failed: {str(e)}")

    async def import_csv(
        self,
        supplier_id: UUID,
        filename: str,
        content: bytes,
    ) -> ImportBatch:
        """
        Import CSV price list for supplier.

        Pipeline stages:
        1. Create import_batch (status=received)
        2. Parse CSV and store raw_rows
        3. Create parse_run
        4. Process rows: create/update products directly
        5. Mark batch as parsed/failed
        """
        logger.info("import_started", supplier_id=str(supplier_id), filename=filename)

        # Stage 1: Create import batch
        import_batch = ImportBatch(
            supplier_id=supplier_id,
            source_type="csv",
            source_filename=filename,
            status="received",
            meta={"file_size": len(content)},
        )
        self.db.add(import_batch)
        await self.db.flush()

        try:
            # Stage 2: Parse CSV
            rows = parse_csv_content(content)
            logger.info("csv_parsed", batch_id=str(import_batch.id), rows_count=len(rows))

            # Store raw rows
            raw_rows = []
            for row_data in rows:
                raw_row = RawRow(
                    import_batch_id=import_batch.id,
                    row_kind="data",
                    row_ref=f"row_{row_data['row_number']}",
                    raw_cells={"cells": row_data["cells"], "headers": row_data["headers"]},
                    raw_text=" | ".join(row_data["cells"]),
                )
                self.db.add(raw_row)
                raw_rows.append(raw_row)

            await self.db.flush()

            # Stage 3: Create parse run
            parse_run = ParseRun(
                import_batch_id=import_batch.id,
                parser_version=PARSER_VERSION,
            )
            self.db.add(parse_run)
            await self.db.flush()

            # Stage 4: Process rows
            summary = await self._process_rows(
                supplier_id=supplier_id,
                import_batch_id=import_batch.id,
                parse_run_id=parse_run.id,
                rows=rows,
                raw_rows=raw_rows,
            )

            # Stage 5: Finalize parsing
            parse_run.finished_at = datetime.utcnow()
            parse_run.summary = summary
            import_batch.status = "parsed"

            await self.db.commit()

            logger.info(
                "import_completed",
                batch_id=str(import_batch.id),
                summary=summary,
            )

            return import_batch

        except Exception as e:
            import_batch.status = "failed"
            import_batch.meta["error"] = str(e)
            await self.db.commit()

            logger.error(
                "import_failed",
                batch_id=str(import_batch.id),
                error=str(e),
            )
            raise ValueError(f"Import failed: {str(e)}")

    async def parse_raw_rows(self, import_batch_id: UUID) -> Dict:
        """
        Re-parse an import batch from existing raw_rows in the database.

        Fetches raw_rows, creates a new ParseRun, and re-runs _process_rows.
        Used by the reparse admin endpoint.
        """
        # Fetch batch to get supplier_id
        batch_result = await self.db.execute(
            select(ImportBatch).where(ImportBatch.id == import_batch_id)
        )
        batch = batch_result.scalar_one_or_none()
        if not batch:
            raise ValueError(f"Import batch {import_batch_id} not found")

        # Fetch existing raw_rows
        raw_rows_result = await self.db.execute(
            select(RawRow)
            .where(RawRow.import_batch_id == import_batch_id)
            .order_by(RawRow.row_ref)
        )
        raw_rows = list(raw_rows_result.scalars().all())

        if not raw_rows:
            raise ValueError(f"No raw_rows found for batch {import_batch_id}")

        # Reconstruct parsed rows from raw_cells
        rows = []
        for raw_row in raw_rows:
            cells = raw_row.raw_cells.get("cells", [])
            headers = raw_row.raw_cells.get("headers", [])
            row_ref = raw_row.row_ref or ""
            # Extract row number from row_ref like "row_5"
            try:
                row_number = int(row_ref.replace("row_", ""))
            except (ValueError, AttributeError):
                row_number = 0

            rows.append({
                "row_number": row_number,
                "cells": cells,
                "headers": headers,
            })

        # Create new parse run
        parse_run = ParseRun(
            import_batch_id=import_batch_id,
            parser_version=PARSER_VERSION,
        )
        self.db.add(parse_run)
        await self.db.flush()

        logger.info(
            "reparse_processing",
            batch_id=str(import_batch_id),
            supplier_id=str(batch.supplier_id),
            rows_count=len(rows),
        )

        # Re-run processing
        summary = await self._process_rows(
            supplier_id=batch.supplier_id,
            import_batch_id=import_batch_id,
            parse_run_id=parse_run.id,
            rows=rows,
            raw_rows=raw_rows,
        )

        await self.db.commit()
        return summary

    async def _process_rows(
        self,
        supplier_id: UUID,
        import_batch_id: UUID,
        parse_run_id: UUID,
        rows: List[Dict],
        raw_rows: List[RawRow],
    ) -> Dict:
        """
        Process parsed rows: create/update products directly.

        Returns:
            Summary dict with counts
        """
        summary = {
            "rows_total": len(rows),
            "products_created": 0,
            "products_updated": 0,
            "parse_events_count": 0,
        }

        # Detect matrix format from first row headers
        is_matrix = False
        matrix_columns = []
        if rows:
            headers = rows[0].get("headers", [])
            is_matrix = detect_matrix_format(headers)
            if is_matrix:
                matrix_columns = extract_matrix_columns(headers)
                logger.info(
                    "matrix_format_detected",
                    columns_count=len(matrix_columns),
                    columns=matrix_columns,
                )

        # Resolve header map once for the entire file (keyword + AI fallback)
        resolved_header_map: Dict[str, int] | None = None
        if rows and not is_matrix:
            first_headers = rows[0].get("headers", [])
            resolved_header_map = normalize_headers(first_headers)

            # AI fallback: if name found but price missing, ask DeepSeek
            if "name" in resolved_header_map and "price" not in resolved_header_map:
                logger.info(
                    "ai_column_mapping_triggered",
                    headers=first_headers,
                    current_map=resolved_header_map,
                )
                # Collect sample data rows (up to 5, skipping empty)
                sample_rows = []
                for rd in rows[:10]:
                    cells = rd.get("cells", [])
                    if any(c.strip() for c in cells):
                        sample_rows.append(cells)
                    if len(sample_rows) >= 5:
                        break

                try:
                    ai_map = await ai_detect_column_mapping(first_headers, sample_rows)
                    if ai_map:
                        # Merge AI results into resolved map (AI fills gaps only)
                        for field, idx in ai_map.items():
                            if field not in resolved_header_map:
                                resolved_header_map[field] = idx
                        logger.info(
                            "ai_column_mapping_merged",
                            final_map=resolved_header_map,
                        )
                except Exception as e:
                    logger.warning("ai_column_mapping_call_failed", error=str(e))

        # Pre-scan: detect section headers for section_context support.
        # A section header is a row where the name column has text
        # but the price column is empty (e.g. "РОЗА ЭКВАДОР,,,,,,,,").
        section_map: Dict[int, str] = {}  # row_index -> section_context
        section_header_rows: set = set()  # indices of section header rows to skip
        if rows and not is_matrix:
            hmap = resolved_header_map or {}
            sec_name_idx = hmap.get("name")
            sec_price_idx = hmap.get("price")
            current_section: str | None = None

            for idx, rd in enumerate(rows):
                rc = rd.get("cells", [])
                has_name = (
                    sec_name_idx is not None
                    and sec_name_idx < len(rc)
                    and rc[sec_name_idx].strip()
                )
                has_price = (
                    sec_price_idx is not None
                    and sec_price_idx < len(rc)
                    and rc[sec_price_idx].strip()
                )
                if has_name and not has_price:
                    # This row is a section header — skip during processing
                    current_section = rc[sec_name_idx].strip()
                    section_header_rows.add(idx)
                else:
                    section_map[idx] = current_section or ""

        for row_idx, (row_data, raw_row) in enumerate(zip(rows, raw_rows)):
            # Skip section header rows (e.g. "Эквадор", "Израиль") — not actual items
            if row_idx in section_header_rows:
                continue
            try:
                if is_matrix and matrix_columns:
                    await self._process_matrix_row(
                        supplier_id=supplier_id,
                        import_batch_id=import_batch_id,
                        parse_run_id=parse_run_id,
                        row_data=row_data,
                        raw_row=raw_row,
                        matrix_columns=matrix_columns,
                        summary=summary,
                    )
                else:
                    await self._process_single_row(
                        supplier_id=supplier_id,
                        import_batch_id=import_batch_id,
                        parse_run_id=parse_run_id,
                        row_data=row_data,
                        raw_row=raw_row,
                        summary=summary,
                        section_context=section_map.get(row_idx) or None,
                        header_map_override=resolved_header_map,
                    )
            except Exception as e:
                # Log error but continue
                logger.warning(
                    "row_processing_failed",
                    raw_row_id=str(raw_row.id),
                    error=str(e),
                )
                await self._create_parse_event(
                    parse_run_id=parse_run_id,
                    raw_row_id=raw_row.id,
                    severity="error",
                    code="ROW_PROCESSING_FAILED",
                    message=f"Failed to process row: {str(e)}",
                )
                summary["parse_events_count"] += 1

        # Flush all pending changes so subsequent queries (AI enrichment)
        # can see updated last_import_batch_id on existing items
        await self.db.flush()

        return summary

    @staticmethod
    def _validate_offer(
        price_min: float | None,
        price_max: float | None,
        length_cm: int | None,
    ) -> tuple[str, str | None]:
        """Validate an offer candidate and return (validation, notes).

        Returns:
            ("ok", None) if valid,
            ("warning", "reason") if anomalous.
        """
        notes = []

        if price_min is not None and (price_min < 5 or price_min > 50_000):
            notes.append("price_anomaly")
        if price_max is not None and price_max > 50_000:
            notes.append("price_anomaly")

        if length_cm is not None and (length_cm < 15 or length_cm > 200):
            notes.append("length_anomaly")

        if notes:
            return "warning", ", ".join(notes)
        return "ok", None

    @staticmethod
    def _build_expanded_varieties(
        normalized,
        raw_name: str,
        section_context: str | None = None,
    ) -> list[tuple[object, str]]:
        """Expand a bundle into individual (normalized_result, synthetic_name) pairs.

        For each variety in the bundle, builds a synthetic name like
        "Роза спрей Лидия" and normalizes it independently.

        Returns:
            List of (NormalizedName, synthetic_name) tuples.
        """
        results = []
        flower_type = normalized.flower_type or ""
        subtype = normalized.flower_subtype or ""
        origin = normalized.origin_country

        for variety_name in normalized.bundle_varieties:
            # Strip type/subtype prefix if variety already starts with it
            # e.g. "Роза Аваланш" → "Аваланш" (type will be prepended below)
            vn = variety_name
            if flower_type:
                ft_lower = flower_type.lower()
                if vn.lower().startswith(ft_lower):
                    vn = vn[len(ft_lower):].strip()
                    # Also strip subtype if present after type
                    if subtype and vn.lower().startswith(subtype.lower()):
                        vn = vn[len(subtype):].strip()
            if not vn:
                vn = variety_name  # fallback to original if nothing left

            # Build synthetic name: "Роза спрей Лидия"
            parts = []
            if flower_type:
                parts.append(flower_type)
            if subtype:
                parts.append(subtype.lower())
            parts.append(vn)
            synthetic_name = " ".join(parts)

            # Normalize the synthetic name
            variety_norm = normalize_name_rich(synthetic_name, section_context=section_context)

            # Inherit origin country from parent if not detected
            if not variety_norm.origin_country and origin:
                variety_norm.origin_country = origin

            results.append((variety_norm, synthetic_name))

        return results

    async def _create_or_update_product(
        self,
        supplier_id: UUID,
        import_batch_id: UUID,
        title: str,
        raw_name: str,
        flower_type: str | None,
        variety: str | None,
        origin_country: str | None,
        color: str | None,
        length_cm: int | None,
        pack_type: str | None,
        pack_qty: int | None,
        price: Decimal,
        summary: Dict,
    ) -> Product:
        """Create or update a Product by stable key (supplier_id + raw_name + length + pack_type).

        Returns the Product instance.
        """
        stable_key = generate_stable_key(
            supplier_id=supplier_id,
            raw_name=raw_name,
            raw_group=f"{length_cm}_{pack_type}",
        )

        # Lookup existing product by raw_name match for same supplier
        result = await self.db.execute(
            select(Product).where(
                Product.supplier_id == supplier_id,
                Product.raw_name == raw_name,
                Product.length_cm == length_cm,
                Product.pack_type == pack_type,
            )
        )
        product = result.scalar_one_or_none()

        if product:
            # Update existing product
            product.title = title
            product.flower_type = flower_type or product.flower_type
            product.variety = variety or product.variety
            product.origin_country = origin_country or product.origin_country
            product.color = color or product.color
            product.pack_qty = pack_qty or product.pack_qty
            product.price = price
            product.import_batch_id = import_batch_id
            if product.status == "deleted":
                product.status = "active"
                product.is_active = True
            summary["products_updated"] += 1
        else:
            product = Product(
                supplier_id=supplier_id,
                title=title,
                flower_type=flower_type,
                variety=variety,
                origin_country=origin_country,
                color=color,
                length_cm=length_cm,
                pack_type=pack_type,
                pack_qty=pack_qty,
                price=price,
                currency="RUB",
                status="active",
                is_active=True,
                import_batch_id=import_batch_id,
                raw_name=raw_name,
            )
            self.db.add(product)
            await self.db.flush()
            summary["products_created"] += 1

        return product

    async def _process_single_row(
        self,
        supplier_id: UUID,
        import_batch_id: UUID,
        parse_run_id: UUID,
        row_data: Dict,
        raw_row: RawRow,
        summary: Dict,
        section_context: str | None = None,
        header_map_override: Dict[str, int] | None = None,
    ) -> None:
        """Process a single CSV row."""
        # Use pre-resolved header map or compute from row headers
        headers = row_data["headers"]
        cells = row_data["cells"]
        header_map = header_map_override if header_map_override is not None else normalize_headers(headers)

        # Extract required fields
        name_idx = header_map.get("name")
        price_idx = header_map.get("price")

        if name_idx is None or name_idx >= len(cells):
            await self._create_parse_event(
                parse_run_id=parse_run_id,
                raw_row_id=raw_row.id,
                severity="error",
                code="MISSING_NAME",
                message="Name column not found or empty",
            )
            summary["parse_events_count"] += 1
            return

        if price_idx is None or price_idx >= len(cells):
            await self._create_parse_event(
                parse_run_id=parse_run_id,
                raw_row_id=raw_row.id,
                severity="error",
                code="MISSING_PRICE",
                message="Price column not found or empty",
            )
            summary["parse_events_count"] += 1
            return

        raw_name = cells[name_idx].strip()
        raw_price = cells[price_idx].strip()

        if not raw_name:
            await self._create_parse_event(
                parse_run_id=parse_run_id,
                raw_row_id=raw_row.id,
                severity="error",
                code="EMPTY_NAME",
                message="Name is empty",
            )
            summary["parse_events_count"] += 1
            return

        # Parse price
        price_data = parse_price(raw_price)
        if price_data["error"] or price_data["price_min"] is None:
            await self._create_parse_event(
                parse_run_id=parse_run_id,
                raw_row_id=raw_row.id,
                severity="error",
                code="INVALID_PRICE",
                message=f"Invalid price: {price_data.get('error', 'unknown')}",
                payload={"raw_price": raw_price},
            )
            summary["parse_events_count"] += 1
            return

        # Extract pack_qty if column exists
        pack_qty = None
        pack_qty_idx = header_map.get("pack_qty")
        if pack_qty_idx is not None and pack_qty_idx < len(cells):
            pack_qty_str = cells[pack_qty_idx].strip()
            if pack_qty_str.isdigit():
                pack_qty = int(pack_qty_str)

        # Extract attributes using rich name normalizer
        normalized = normalize_name_rich(raw_name, section_context=section_context)

        # Use normalized values, falling back to legacy extraction
        length_cm = normalized.length_cm or extract_length_cm(raw_name)
        origin_country = normalized.origin_country or extract_origin_country(raw_name)
        if not pack_qty:
            pack_qty = extract_pack_qty(raw_name)

        # Build attributes with all extracted data and source tracking
        attributes = {
            "origin_country": origin_country,
            "colors": normalized.colors if normalized.colors else [],
            "flower_type": normalized.flower_type,
            "subtype": normalized.flower_subtype,  # кустовая, спрей, пионовидная
            "variety": normalized.variety,
            "farm": normalized.farm,
            "clean_name": normalized.clean_name,
        }
        if section_context:
            attributes["section_context"] = section_context

        # Build title from clean_name or raw_name
        title = normalized.clean_name or raw_name
        color = normalized.colors[0] if normalized.colors else None

        # Bundle auto-expansion: split into individual products
        if normalized.is_bundle_list and normalized.bundle_varieties:
            expanded = self._build_expanded_varieties(
                normalized, raw_name, section_context=section_context,
            )
            await self._create_parse_event(
                parse_run_id=parse_run_id,
                raw_row_id=raw_row.id,
                severity="info",
                code="BUNDLE_EXPANDED",
                message=f"Bundle auto-expanded: {len(expanded)} varieties from one row",
                payload={
                    "varieties": normalized.bundle_varieties,
                    "original": raw_name,
                },
            )
            summary["parse_events_count"] += 1

            for variety_norm, synthetic_name in expanded:
                v_length = variety_norm.length_cm or length_cm
                v_title = variety_norm.clean_name or synthetic_name
                v_color = (variety_norm.colors[0] if variety_norm.colors else None) or color
                await self._create_or_update_product(
                    supplier_id=supplier_id,
                    import_batch_id=import_batch_id,
                    title=v_title,
                    raw_name=synthetic_name,
                    flower_type=variety_norm.flower_type,
                    variety=variety_norm.variety,
                    origin_country=variety_norm.origin_country or origin_country,
                    color=v_color,
                    length_cm=v_length,
                    pack_type=None,
                    pack_qty=pack_qty,
                    price=Decimal(str(price_data["price_min"])),
                    summary=summary,
                )
            return

        # Create or update product
        await self._create_or_update_product(
            supplier_id=supplier_id,
            import_batch_id=import_batch_id,
            title=title,
            raw_name=raw_name,
            flower_type=normalized.flower_type,
            variety=normalized.variety,
            origin_country=origin_country,
            color=color,
            length_cm=length_cm,
            pack_type=None,
            pack_qty=pack_qty,
            price=Decimal(str(price_data["price_min"])),
            summary=summary,
        )

    async def _process_matrix_row(
        self,
        supplier_id: UUID,
        import_batch_id: UUID,
        parse_run_id: UUID,
        row_data: Dict,
        raw_row: RawRow,
        matrix_columns: List[tuple],
        summary: Dict,
    ) -> None:
        """
        Process a matrix format row — creates one Product per price column.

        Matrix format example:
            Наименование | 40 см Бак | 40 см Упак | 50 см Бак
            Роза         | 60        | 65         | 70

        Creates N Products (one per valid price column).
        """
        cells = row_data["cells"]

        raw_name = cells[0].strip() if cells else ""
        if not raw_name:
            await self._create_parse_event(
                parse_run_id=parse_run_id,
                raw_row_id=raw_row.id,
                severity="error",
                code="MISSING_NAME",
                message="Name column empty in matrix row",
            )
            summary["parse_events_count"] += 1
            return

        normalized = normalize_name_rich(raw_name)
        origin_country = normalized.origin_country or extract_origin_country(raw_name)
        title = normalized.clean_name or raw_name
        color = normalized.colors[0] if normalized.colors else None

        # Bundle auto-expansion for matrix format
        if normalized.is_bundle_list and normalized.bundle_varieties:
            expanded = self._build_expanded_varieties(normalized, raw_name)
            await self._create_parse_event(
                parse_run_id=parse_run_id,
                raw_row_id=raw_row.id,
                severity="info",
                code="BUNDLE_EXPANDED",
                message=f"Bundle auto-expanded (matrix): {len(expanded)} varieties from one row",
                payload={
                    "varieties": normalized.bundle_varieties,
                    "original": raw_name,
                },
            )
            summary["parse_events_count"] += 1

            # Each variety × each price column = N×M products
            for variety_norm, synthetic_name in expanded:
                v_title = variety_norm.clean_name or synthetic_name
                v_color = (variety_norm.colors[0] if variety_norm.colors else None) or color
                for col_idx, length_cm, pack_type in matrix_columns:
                    if col_idx >= len(cells):
                        continue
                    raw_price = cells[col_idx].strip()
                    if not raw_price:
                        continue
                    price_data = parse_price(raw_price)
                    if price_data["error"] or price_data["price_min"] is None:
                        continue
                    await self._create_or_update_product(
                        supplier_id=supplier_id,
                        import_batch_id=import_batch_id,
                        title=v_title,
                        raw_name=synthetic_name,
                        flower_type=variety_norm.flower_type,
                        variety=variety_norm.variety,
                        origin_country=variety_norm.origin_country or origin_country,
                        color=v_color,
                        length_cm=length_cm,
                        pack_type=pack_type,
                        pack_qty=None,
                        price=Decimal(str(price_data["price_min"])),
                        summary=summary,
                    )
            return

        # Non-bundle: one product per price column
        products_created = 0
        for col_idx, length_cm, pack_type in matrix_columns:
            if col_idx >= len(cells):
                continue

            raw_price = cells[col_idx].strip()
            if not raw_price:
                continue

            price_data = parse_price(raw_price)
            if price_data["error"] or price_data["price_min"] is None:
                await self._create_parse_event(
                    parse_run_id=parse_run_id,
                    raw_row_id=raw_row.id,
                    severity="warning",
                    code="MATRIX_PRICE_INVALID",
                    message=f"Invalid price in column {col_idx}: {raw_price}",
                    payload={"column_index": col_idx, "raw_price": raw_price},
                )
                summary["parse_events_count"] += 1
                continue

            await self._create_or_update_product(
                supplier_id=supplier_id,
                import_batch_id=import_batch_id,
                title=title,
                raw_name=raw_name,
                flower_type=normalized.flower_type,
                variety=normalized.variety,
                origin_country=origin_country,
                color=color,
                length_cm=length_cm,
                pack_type=pack_type,
                pack_qty=None,
                price=Decimal(str(price_data["price_min"])),
                summary=summary,
            )
            products_created += 1

        if products_created == 0:
            await self._create_parse_event(
                parse_run_id=parse_run_id,
                raw_row_id=raw_row.id,
                severity="warning",
                code="NO_VALID_PRICES",
                message=f"No valid prices found in matrix row for: {raw_name}",
            )
            summary["parse_events_count"] += 1

    async def _create_parse_event(
        self,
        parse_run_id: UUID,
        raw_row_id: Optional[UUID],
        severity: str,
        code: str,
        message: str,
        payload: Optional[Dict] = None,
    ) -> None:
        """Create a parse event."""
        event = ParseEvent(
            parse_run_id=parse_run_id,
            raw_row_id=raw_row_id,
            severity=severity,
            code=code,
            message=message,
            payload=payload or {},
        )
        self.db.add(event)

    async def get_import_summary(self, import_batch_id: UUID) -> Optional[Dict]:
        """Get import summary with counts."""
        result = await self.db.execute(
            select(ImportBatch).where(ImportBatch.id == import_batch_id)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            return None

        raw_rows_count = await self.db.scalar(
            select(func.count(RawRow.id)).where(RawRow.import_batch_id == import_batch_id)
        )

        products_count = await self.db.scalar(
            select(func.count(Product.id)).where(
                Product.import_batch_id == import_batch_id
            )
        )

        parse_events_count = await self.db.scalar(
            select(func.count(ParseEvent.id))
            .join(ParseRun)
            .where(ParseRun.import_batch_id == import_batch_id)
        )

        return {
            "batch_id": batch.id,
            "status": batch.status,
            "raw_rows_count": raw_rows_count or 0,
            "products_count": products_count or 0,
            "parse_events_count": parse_events_count or 0,
        }
