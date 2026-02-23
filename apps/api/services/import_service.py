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
    NormalizedSKU,
    OfferCandidate,
    ParseEvent,
    ParseRun,
    RawRow,
    SKUMapping,
    SupplierItem,
)
from apps.api.services.ai_enrichment_service import run_ai_enrichment_for_batch
from apps.api.services.publish_service import PublishService
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
from packages.core.utils.stable_key import generate_stable_key, normalize_name

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

            try:
                ai_result = await run_ai_enrichment_for_batch(
                    db=self.db,
                    supplier_id=supplier_id,
                    import_batch_id=import_batch.id,
                )
                summary["ai_enrichment"] = ai_result
            except Exception as e:
                logger.warning("ai_enrichment_error", batch_id=str(import_batch.id), error=str(e))
                summary["ai_enrichment"] = {"status": "error", "error": str(e)}

            try:
                mapping_result = await self._auto_create_sku_mappings(
                    supplier_id=supplier_id,
                    import_batch_id=import_batch.id,
                )
                summary["auto_mappings"] = mapping_result
            except Exception as e:
                logger.warning("auto_mappings_error", batch_id=str(import_batch.id), error=str(e))
                summary["auto_mappings"] = {"status": "error", "error": str(e)}

            parse_run.finished_at = datetime.utcnow()
            parse_run.summary = summary
            import_batch.status = "parsed"
            await self.db.commit()

            logger.info("import_completed", batch_id=str(import_batch.id), summary=summary)

            try:
                publish_service = PublishService(self.db)
                publish_result = await publish_service.publish_supplier_offers(supplier_id)
                await self.db.commit()
            except Exception as e:
                logger.warning("auto_publish_error", batch_id=str(import_batch.id), error=str(e))

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

            try:
                ai_result = await run_ai_enrichment_for_batch(
                    db=self.db,
                    supplier_id=supplier_id,
                    import_batch_id=import_batch.id,
                )
                summary["ai_enrichment"] = ai_result
            except Exception as e:
                logger.warning("ai_enrichment_error", batch_id=str(import_batch.id), error=str(e))
                summary["ai_enrichment"] = {"status": "error", "error": str(e)}

            try:
                mapping_result = await self._auto_create_sku_mappings(
                    supplier_id=supplier_id,
                    import_batch_id=import_batch.id,
                )
                summary["auto_mappings"] = mapping_result
            except Exception as e:
                logger.warning("auto_mappings_error", batch_id=str(import_batch.id), error=str(e))
                summary["auto_mappings"] = {"status": "error", "error": str(e)}

            parse_run.finished_at = datetime.utcnow()
            parse_run.summary = summary
            import_batch.status = "parsed"
            await self.db.commit()

            logger.info("import_completed", batch_id=str(import_batch.id), summary=summary)

            try:
                publish_service = PublishService(self.db)
                publish_result = await publish_service.publish_supplier_offers(supplier_id)
                await self.db.commit()
            except Exception as e:
                logger.warning("auto_publish_error", batch_id=str(import_batch.id), error=str(e))

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
        4. Process rows: create/update supplier_items and offer_candidates
        5. Mark batch as parsed/failed

        Args:
            supplier_id: Supplier UUID
            filename: Original filename
            content: CSV file bytes

        Returns:
            Import batch

        Raises:
            ValueError: If import fails
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

            # Stage 4.5: AI Enrichment (optional, runs if AI is enabled)
            try:
                ai_result = await run_ai_enrichment_for_batch(
                    db=self.db,
                    supplier_id=supplier_id,
                    import_batch_id=import_batch.id,
                )
                summary["ai_enrichment"] = ai_result
                logger.info(
                    "ai_enrichment_result",
                    batch_id=str(import_batch.id),
                    status=ai_result.get("status"),
                    auto_applied=ai_result.get("auto_applied", 0),
                    needs_review=ai_result.get("needs_review", 0),
                )
            except Exception as e:
                # AI enrichment failure should not fail the import
                logger.warning(
                    "ai_enrichment_error",
                    batch_id=str(import_batch.id),
                    error=str(e),
                )
                summary["ai_enrichment"] = {"status": "error", "error": str(e)}

            # Stage 5: Auto-create SKU mappings for new supplier items
            try:
                mapping_result = await self._auto_create_sku_mappings(
                    supplier_id=supplier_id,
                    import_batch_id=import_batch.id,
                )
                summary["auto_mappings"] = mapping_result
                logger.info(
                    "auto_mappings_created",
                    batch_id=str(import_batch.id),
                    skus_created=mapping_result.get("skus_created", 0),
                    mappings_created=mapping_result.get("mappings_created", 0),
                )
            except Exception as e:
                logger.warning(
                    "auto_mappings_error",
                    batch_id=str(import_batch.id),
                    error=str(e),
                )
                summary["auto_mappings"] = {"status": "error", "error": str(e)}

            # Stage 6: Finalize parsing
            parse_run.finished_at = datetime.utcnow()
            parse_run.summary = summary
            import_batch.status = "parsed"

            await self.db.commit()

            logger.info(
                "import_completed",
                batch_id=str(import_batch.id),
                summary=summary,
            )

            # Stage 7: Auto-publish offers
            try:
                publish_service = PublishService(self.db)
                publish_result = await publish_service.publish_supplier_offers(supplier_id)
                await self.db.commit()
                logger.info(
                    "auto_publish_completed",
                    batch_id=str(import_batch.id),
                    offers_created=publish_result.get("offers_created", 0),
                    offers_deactivated=publish_result.get("offers_deactivated", 0),
                )
            except Exception as e:
                logger.warning(
                    "auto_publish_error",
                    batch_id=str(import_batch.id),
                    error=str(e),
                )
                # Don't fail the import if publish fails

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

    async def _process_rows(
        self,
        supplier_id: UUID,
        import_batch_id: UUID,
        parse_run_id: UUID,
        rows: List[Dict],
        raw_rows: List[RawRow],
    ) -> Dict:
        """
        Process parsed rows: create supplier_items and offer_candidates.

        Args:
            supplier_id: Supplier UUID
            import_batch_id: Import batch UUID
            parse_run_id: Parse run UUID
            rows: Parsed CSV rows
            raw_rows: Corresponding RawRow models

        Returns:
            Summary dict with counts
        """
        summary = {
            "rows_total": len(rows),
            "supplier_items_created": 0,
            "supplier_items_updated": 0,
            "offer_candidates_created": 0,
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

    async def _create_bundle_items(
        self,
        supplier_id: UUID,
        import_batch_id: UUID,
        raw_row: RawRow,
        raw_name: str,
        expanded: list[tuple[object, str]],
        summary: Dict,
    ) -> list:
        """Create SupplierItem records for each expanded bundle variety.

        Returns list of (supplier_item, variety_norm) tuples for OfferCandidate creation.
        """
        items = []
        for variety_norm, synthetic_name in expanded:
            # Build attributes for this variety
            attrs = {
                "origin_country": variety_norm.origin_country,
                "colors": variety_norm.colors or [],
                "flower_type": variety_norm.flower_type,
                "subtype": variety_norm.flower_subtype,
                "variety": variety_norm.variety,
                "farm": variety_norm.farm,
                "clean_name": variety_norm.clean_name,
                "origin": "bundle_expansion",
                "bundle_source": raw_name,
            }
            attrs = {k: v for k, v in attrs.items() if v is not None}
            sources = {k: "parser" for k in attrs.keys()}
            attrs["_sources"] = sources

            name_norm = normalize_name(synthetic_name)
            stable_key = generate_stable_key(
                supplier_id=supplier_id,
                raw_name=synthetic_name,
                raw_group=None,
            )

            # Create or update SupplierItem
            result = await self.db.execute(
                select(SupplierItem).where(
                    SupplierItem.supplier_id == supplier_id,
                    SupplierItem.stable_key == stable_key,
                )
            )
            supplier_item = result.scalar_one_or_none()

            if supplier_item:
                supplier_item.last_import_batch_id = import_batch_id
                supplier_item.raw_name = synthetic_name
                supplier_item.name_norm = name_norm
                if supplier_item.status == "deleted":
                    supplier_item.status = "active"
                    supplier_item.deleted_at = None

                # Merge attributes preserving manual edits
                existing_attrs = supplier_item.attributes or {}
                locked_fields = existing_attrs.get("_locked", [])
                existing_sources = existing_attrs.get("_sources", {})
                merged = dict(attrs)
                merged_sources = dict(sources)
                for field in locked_fields:
                    if field in existing_attrs:
                        merged[field] = existing_attrs[field]
                        merged_sources[field] = existing_sources.get(field, "manual")
                for field, source in existing_sources.items():
                    if source == "manual" and field in existing_attrs and field not in locked_fields:
                        merged[field] = existing_attrs[field]
                        merged_sources[field] = "manual"
                merged["_sources"] = merged_sources
                merged["_locked"] = locked_fields
                supplier_item.attributes = merged
                summary["supplier_items_updated"] += 1
            else:
                supplier_item = SupplierItem(
                    supplier_id=supplier_id,
                    stable_key=stable_key,
                    last_import_batch_id=import_batch_id,
                    raw_name=synthetic_name,
                    raw_group=None,
                    name_norm=name_norm,
                    attributes=attrs,
                    status="active",
                )
                self.db.add(supplier_item)
                await self.db.flush()
                summary["supplier_items_created"] += 1

            items.append((supplier_item, variety_norm))

        return items

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

        # Bundle auto-expansion: split into individual items
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

            items = await self._create_bundle_items(
                supplier_id, import_batch_id, raw_row, raw_name, expanded, summary,
            )
            for supplier_item, variety_norm in items:
                v_length = variety_norm.length_cm or length_cm
                validation, validation_notes = self._validate_offer(
                    price_data["price_min"], price_data["price_max"], v_length,
                )
                offer_candidate = OfferCandidate(
                    supplier_item_id=supplier_item.id,
                    import_batch_id=import_batch_id,
                    raw_row_id=raw_row.id,
                    length_cm=v_length,
                    pack_type=None,
                    pack_qty=pack_qty,
                    price_type=price_data["price_type"],
                    price_min=price_data["price_min"],
                    price_max=price_data["price_max"],
                    currency="RUB",
                    tier_min_qty=None,
                    tier_max_qty=None,
                    availability="unknown",
                    stock_qty=None,
                    validation=validation,
                    validation_notes=validation_notes,
                )
                self.db.add(offer_candidate)
                summary["offer_candidates_created"] += 1
            return

        # Non-bundle warnings
        if normalized.warnings:
            attributes["warnings"] = normalized.warnings
            if any("garbage" in w for w in normalized.warnings):
                attributes["needs_review"] = True
                attributes["review_reason"] = "garbage_text_detected"

        # Remove None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        # Add source tracking metadata
        sources = {k: "parser" for k in attributes.keys()}
        attributes["_sources"] = sources

        # Generate stable key
        name_norm = normalize_name(raw_name)
        stable_key = generate_stable_key(
            supplier_id=supplier_id,
            raw_name=raw_name,
            raw_group=None,  # F1 format has no groups
        )

        # Create or update supplier_item
        result = await self.db.execute(
            select(SupplierItem).where(
                SupplierItem.supplier_id == supplier_id,
                SupplierItem.stable_key == stable_key,
            )
        )
        supplier_item = result.scalar_one_or_none()

        if supplier_item:
            # Update existing - preserve locked fields and manual changes
            supplier_item.last_import_batch_id = import_batch_id
            supplier_item.raw_name = raw_name
            supplier_item.name_norm = name_norm

            # Restore to active if was deleted (re-import should reactivate)
            if supplier_item.status == "deleted":
                supplier_item.status = "active"
                supplier_item.deleted_at = None

            # Merge attributes: preserve locked fields and manual sources
            existing_attrs = supplier_item.attributes or {}
            locked_fields = existing_attrs.get("_locked", [])
            existing_sources = existing_attrs.get("_sources", {})

            # Start with new parser attributes
            merged = dict(attributes)
            merged_sources = dict(sources)

            # Preserve locked fields from existing
            for field in locked_fields:
                if field in existing_attrs:
                    merged[field] = existing_attrs[field]
                    merged_sources[field] = existing_sources.get(field, "manual")

            # Preserve manually edited fields (source=manual)
            for field, source in existing_sources.items():
                if source == "manual" and field in existing_attrs and field not in locked_fields:
                    merged[field] = existing_attrs[field]
                    merged_sources[field] = "manual"

            merged["_sources"] = merged_sources
            merged["_locked"] = locked_fields
            supplier_item.attributes = merged
            summary["supplier_items_updated"] += 1
        else:
            # Create new
            supplier_item = SupplierItem(
                supplier_id=supplier_id,
                stable_key=stable_key,
                last_import_batch_id=import_batch_id,
                raw_name=raw_name,
                raw_group=None,
                name_norm=name_norm,
                attributes=attributes,
                status="active",
            )
            self.db.add(supplier_item)
            await self.db.flush()
            summary["supplier_items_created"] += 1

        # Create offer_candidate
        validation, validation_notes = self._validate_offer(
            price_data["price_min"], price_data["price_max"], length_cm,
        )
        offer_candidate = OfferCandidate(
            supplier_item_id=supplier_item.id,
            import_batch_id=import_batch_id,
            raw_row_id=raw_row.id,
            length_cm=length_cm,
            pack_type=None,  # F1 format doesn't have pack_type in MVP
            pack_qty=pack_qty,
            price_type=price_data["price_type"],
            price_min=price_data["price_min"],
            price_max=price_data["price_max"],
            currency="RUB",
            tier_min_qty=None,
            tier_max_qty=None,
            availability="unknown",
            stock_qty=None,
            validation=validation,
            validation_notes=validation_notes,
        )
        self.db.add(offer_candidate)
        summary["offer_candidates_created"] += 1

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
        Process a matrix format row - one product with multiple price columns.

        Matrix format example:
            Наименование | 40 см Бак | 40 см Упак | 50 см Бак
            Роза         | 60        | 65         | 70

        Creates one SupplierItem and multiple OfferCandidates.
        """
        cells = row_data["cells"]

        # First column is product name
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

        # Extract attributes using rich name normalizer
        normalized = normalize_name_rich(raw_name)
        origin_country = normalized.origin_country or extract_origin_country(raw_name)

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

            items = await self._create_bundle_items(
                supplier_id, import_batch_id, raw_row, raw_name, expanded, summary,
            )

            # Create OfferCandidates: each variety × each price column
            for supplier_item, variety_norm in items:
                candidates_created = 0
                for col_idx, length_cm, pack_type in matrix_columns:
                    if col_idx >= len(cells):
                        continue
                    raw_price = cells[col_idx].strip()
                    if not raw_price:
                        continue
                    price_data = parse_price(raw_price)
                    if price_data["error"] or price_data["price_min"] is None:
                        continue
                    validation, validation_notes = self._validate_offer(
                        price_data["price_min"], price_data["price_max"], length_cm,
                    )
                    offer_candidate = OfferCandidate(
                        supplier_item_id=supplier_item.id,
                        import_batch_id=import_batch_id,
                        raw_row_id=raw_row.id,
                        length_cm=length_cm,
                        pack_type=pack_type,
                        pack_qty=None,
                        price_type=price_data["price_type"],
                        price_min=price_data["price_min"],
                        price_max=price_data["price_max"],
                        currency="RUB",
                        tier_min_qty=None,
                        tier_max_qty=None,
                        availability="unknown",
                        stock_qty=None,
                        validation=validation,
                        validation_notes=validation_notes,
                    )
                    self.db.add(offer_candidate)
                    candidates_created += 1
                summary["offer_candidates_created"] += candidates_created
            return

        # Non-bundle warnings
        if normalized.warnings:
            attributes["warnings"] = normalized.warnings
            if any("garbage" in w for w in normalized.warnings):
                attributes["needs_review"] = True
                attributes["review_reason"] = "garbage_text_detected"

        # Remove None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        # Add source tracking metadata
        sources = {k: "parser" for k in attributes.keys()}
        attributes["_sources"] = sources

        # Generate stable key and create/update SupplierItem
        name_norm = normalize_name(raw_name)
        stable_key = generate_stable_key(
            supplier_id=supplier_id,
            raw_name=raw_name,
            raw_group=None,
        )

        result = await self.db.execute(
            select(SupplierItem).where(
                SupplierItem.supplier_id == supplier_id,
                SupplierItem.stable_key == stable_key,
            )
        )
        supplier_item = result.scalar_one_or_none()

        if supplier_item:
            supplier_item.last_import_batch_id = import_batch_id
            supplier_item.raw_name = raw_name
            if supplier_item.status == "deleted":
                supplier_item.status = "active"
                supplier_item.deleted_at = None
            supplier_item.name_norm = name_norm

            existing_attrs = supplier_item.attributes or {}
            locked_fields = existing_attrs.get("_locked", [])
            existing_sources = existing_attrs.get("_sources", {})
            merged = dict(attributes)
            merged_sources = dict(sources)
            for field in locked_fields:
                if field in existing_attrs:
                    merged[field] = existing_attrs[field]
                    merged_sources[field] = existing_sources.get(field, "manual")
            for field, source in existing_sources.items():
                if source == "manual" and field in existing_attrs and field not in locked_fields:
                    merged[field] = existing_attrs[field]
                    merged_sources[field] = "manual"
            merged["_sources"] = merged_sources
            merged["_locked"] = locked_fields
            supplier_item.attributes = merged
            summary["supplier_items_updated"] += 1
        else:
            supplier_item = SupplierItem(
                supplier_id=supplier_id,
                stable_key=stable_key,
                last_import_batch_id=import_batch_id,
                raw_name=raw_name,
                raw_group=None,
                name_norm=name_norm,
                attributes=attributes,
                status="active",
            )
            self.db.add(supplier_item)
            await self.db.flush()
            summary["supplier_items_created"] += 1

        # Create OfferCandidate for each non-empty price column
        candidates_created = 0
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

            validation, validation_notes = self._validate_offer(
                price_data["price_min"], price_data["price_max"], length_cm,
            )
            offer_candidate = OfferCandidate(
                supplier_item_id=supplier_item.id,
                import_batch_id=import_batch_id,
                raw_row_id=raw_row.id,
                length_cm=length_cm,
                pack_type=pack_type,
                pack_qty=None,
                price_type=price_data["price_type"],
                price_min=price_data["price_min"],
                price_max=price_data["price_max"],
                currency="RUB",
                tier_min_qty=None,
                tier_max_qty=None,
                availability="unknown",
                stock_qty=None,
                validation=validation,
                validation_notes=validation_notes,
            )
            self.db.add(offer_candidate)
            candidates_created += 1

        summary["offer_candidates_created"] += candidates_created

        if candidates_created == 0:
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

    async def _auto_create_sku_mappings(
        self,
        supplier_id: UUID,
        import_batch_id: UUID,
    ) -> Dict:
        """
        Auto-create SKU mappings for supplier items from import batch.

        For each supplier_item without a confirmed mapping:
        1. Find or create NormalizedSKU based on flower_type + variety
        2. Create SKUMapping with status='confirmed'

        Args:
            supplier_id: Supplier UUID
            import_batch_id: Import batch UUID

        Returns:
            Dict with counts: skus_created, mappings_created, skipped
        """
        from decimal import Decimal

        result = {
            "skus_created": 0,
            "mappings_created": 0,
            "skipped": 0,
        }

        # Find supplier items from this batch without confirmed mappings
        stmt = (
            select(SupplierItem)
            .outerjoin(
                SKUMapping,
                (SKUMapping.supplier_item_id == SupplierItem.id)
                & (SKUMapping.status == "confirmed"),
            )
            .where(
                SupplierItem.supplier_id == supplier_id,
                SupplierItem.last_import_batch_id == import_batch_id,
                SKUMapping.id.is_(None),  # No confirmed mapping
            )
        )
        items_result = await self.db.execute(stmt)
        supplier_items = items_result.scalars().all()

        for item in supplier_items:
            attrs = item.attributes or {}
            flower_type = attrs.get("flower_type")
            variety = attrs.get("variety")

            if not flower_type:
                # Can't create SKU without flower_type
                result["skipped"] += 1
                continue

            # Find or create NormalizedSKU
            sku_stmt = select(NormalizedSKU).where(
                NormalizedSKU.product_type == flower_type,
                NormalizedSKU.variety == variety,
            )
            sku_result = await self.db.execute(sku_stmt)
            sku = sku_result.scalar_one_or_none()

            if not sku:
                # Create new NormalizedSKU
                title_parts = [flower_type]
                if variety:
                    title_parts.append(variety)
                title = " ".join(title_parts)

                sku = NormalizedSKU(
                    product_type=flower_type,
                    variety=variety,
                    color=None,
                    title=title,
                    meta={},
                )
                self.db.add(sku)
                await self.db.flush()
                result["skus_created"] += 1

            # Create confirmed mapping
            mapping = SKUMapping(
                supplier_item_id=item.id,
                normalized_sku_id=sku.id,
                method="rule",
                confidence=Decimal("0.900"),
                status="confirmed",
            )
            self.db.add(mapping)
            result["mappings_created"] += 1

        await self.db.flush()
        return result

    async def get_import_summary(self, import_batch_id: UUID) -> Optional[Dict]:
        """
        Get import summary with counts.

        Args:
            import_batch_id: Import batch UUID

        Returns:
            Summary dict or None if not found
        """
        # Get import batch
        result = await self.db.execute(
            select(ImportBatch).where(ImportBatch.id == import_batch_id)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            return None

        # Count raw rows
        raw_rows_count = await self.db.scalar(
            select(func.count(RawRow.id)).where(RawRow.import_batch_id == import_batch_id)
        )

        # Count supplier items
        supplier_items_count = await self.db.scalar(
            select(func.count(SupplierItem.id)).where(
                SupplierItem.last_import_batch_id == import_batch_id
            )
        )

        # Count offer candidates
        offer_candidates_count = await self.db.scalar(
            select(func.count(OfferCandidate.id)).where(
                OfferCandidate.import_batch_id == import_batch_id
            )
        )

        # Count parse events
        parse_events_count = await self.db.scalar(
            select(func.count(ParseEvent.id))
            .join(ParseRun)
            .where(ParseRun.import_batch_id == import_batch_id)
        )

        return {
            "batch_id": batch.id,
            "status": batch.status,
            "raw_rows_count": raw_rows_count or 0,
            "supplier_items_count": supplier_items_count or 0,
            "offer_candidates_count": offer_candidates_count or 0,
            "parse_events_count": parse_events_count or 0,
        }
