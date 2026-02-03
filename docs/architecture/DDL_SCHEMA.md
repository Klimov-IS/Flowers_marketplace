-- =========================================================
-- 0) Extensions
-- =========================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid(), digest()
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- trigram indexes for fast text search

-- =========================================================
-- 1) Helper: updated_at trigger
-- =========================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================================================
-- 2) ENUM Types (idempotent)
-- =========================================================
DO $$ BEGIN
  CREATE TYPE supplier_status AS ENUM ('pending', 'active', 'blocked');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE buyer_status AS ENUM ('pending', 'active', 'blocked');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE import_batch_status AS ENUM ('received', 'parsed', 'published', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE source_type AS ENUM ('csv', 'xlsx', 'pdf', 'image', 'api', 'other');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE raw_row_kind AS ENUM ('data', 'header', 'group', 'comment', 'empty');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE parse_severity AS ENUM ('info', 'warn', 'error');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE supplier_item_status AS ENUM ('active', 'ambiguous', 'rejected');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE validation_status AS ENUM ('ok', 'warn', 'error');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE price_type AS ENUM ('fixed', 'range');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE availability_type AS ENUM ('unknown', 'in_stock', 'preorder');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE mapping_method AS ENUM ('rule', 'manual', 'semantic');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE mapping_status AS ENUM ('proposed', 'confirmed', 'rejected');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE task_status AS ENUM ('open', 'in_progress', 'done');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE order_status AS ENUM ('draft', 'sent', 'accepted', 'rejected', 'partial', 'completed', 'canceled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE order_supplier_status AS ENUM ('sent', 'accepted', 'rejected', 'partial');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =========================================================
-- 3) GEO (MVP minimal) — one-city focus supported
-- =========================================================
CREATE TABLE IF NOT EXISTS cities (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL,
  country     text NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (name)
);

CREATE TRIGGER trg_cities_updated_at
BEFORE UPDATE ON cities
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================================================
-- 4) Parties: suppliers / buyers
-- =========================================================
CREATE TABLE IF NOT EXISTS suppliers (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  city_id     uuid NULL REFERENCES cities(id) ON DELETE SET NULL,
  name        text NOT NULL,
  status      supplier_status NOT NULL DEFAULT 'pending',
  contacts    jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (name)
);

CREATE TRIGGER trg_suppliers_updated_at
BEFORE UPDATE ON suppliers
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS buyers (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  city_id     uuid NULL REFERENCES cities(id) ON DELETE SET NULL,
  name        text NOT NULL,
  status      buyer_status NOT NULL DEFAULT 'pending',
  contacts    jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (name)
);

CREATE TRIGGER trg_buyers_updated_at
BEFORE UPDATE ON buyers
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================================================
-- 5) Import + RAW layer
-- =========================================================
CREATE TABLE IF NOT EXISTS import_batches (
  id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_id             uuid NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
  source_type             source_type NOT NULL DEFAULT 'other',
  source_filename         text NULL,
  declared_effective_date date NULL,
  status                  import_batch_status NOT NULL DEFAULT 'received',
  imported_at             timestamptz NOT NULL DEFAULT now(),
  meta                    jsonb NOT NULL DEFAULT '{}'::jsonb, -- any extra: file hash, uploader, etc.
  created_at              timestamptz NOT NULL DEFAULT now(),
  updated_at              timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_import_batches_updated_at
BEFORE UPDATE ON import_batches
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS raw_rows (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  import_batch_id  uuid NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
  row_kind         raw_row_kind NOT NULL DEFAULT 'data',
  row_ref          text NULL,           -- sheet/page/row or cell address
  raw_cells        jsonb NOT NULL DEFAULT '{}'::jsonb, -- raw cells as array/object
  raw_text         text NULL,           -- concatenated for debug/search
  created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS parse_runs (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  import_batch_id  uuid NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
  parser_version   text NOT NULL,
  started_at       timestamptz NOT NULL DEFAULT now(),
  finished_at      timestamptz NULL,
  summary          jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS parse_events (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  parse_run_id uuid NOT NULL REFERENCES parse_runs(id) ON DELETE CASCADE,
  raw_row_id   uuid NULL REFERENCES raw_rows(id) ON DELETE SET NULL,
  severity     parse_severity NOT NULL DEFAULT 'info',
  code         text NOT NULL,
  message      text NOT NULL,
  payload      jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 6) PARSED layer: supplier items + offer candidates
-- =========================================================
CREATE TABLE IF NOT EXISTS supplier_items (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_id     uuid NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
  -- stable_key is set by ETL (e.g., digest of normalized name/group + supplier)
  stable_key      text NULL,
  last_import_batch_id uuid NULL REFERENCES import_batches(id) ON DELETE SET NULL,

  raw_name        text NOT NULL,
  raw_group       text NULL,
  name_norm       text NULL,     -- normalized text for matching; can be set by ETL
  attributes      jsonb NOT NULL DEFAULT '{}'::jsonb,

  status          supplier_item_status NOT NULL DEFAULT 'active',

  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT supplier_items_stable_key_unique
    UNIQUE (supplier_id, stable_key)
);

CREATE TRIGGER trg_supplier_items_updated_at
BEFORE UPDATE ON supplier_items
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS offer_candidates (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_item_id uuid NOT NULL REFERENCES supplier_items(id) ON DELETE CASCADE,
  import_batch_id  uuid NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
  raw_row_id       uuid NULL REFERENCES raw_rows(id) ON DELETE SET NULL,

  length_cm        integer NULL CHECK (length_cm IS NULL OR length_cm > 0),
  pack_type        text NULL,                 -- "бак"/"упак"/etc (dictionary-driven)
  pack_qty         integer NULL CHECK (pack_qty IS NULL OR pack_qty > 0),

  price_type       price_type NOT NULL DEFAULT 'fixed',
  price_min        numeric(12,2) NOT NULL CHECK (price_min >= 0),
  price_max        numeric(12,2) NULL CHECK (price_max IS NULL OR price_max >= 0),
  currency         char(3) NOT NULL DEFAULT 'RUB',

  tier_min_qty     integer NULL CHECK (tier_min_qty IS NULL OR tier_min_qty >= 0),
  tier_max_qty     integer NULL CHECK (tier_max_qty IS NULL OR tier_max_qty >= 0),

  availability     availability_type NOT NULL DEFAULT 'unknown',
  stock_qty        integer NULL CHECK (stock_qty IS NULL OR stock_qty >= 0),

  validation       validation_status NOT NULL DEFAULT 'ok',
  validation_notes text NULL,

  created_at       timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT offer_candidates_price_min_le_max
    CHECK (price_max IS NULL OR price_min <= price_max),

  CONSTRAINT offer_candidates_tier_min_le_max
    CHECK (
      (tier_min_qty IS NULL AND tier_max_qty IS NULL)
      OR (tier_min_qty IS NOT NULL AND tier_max_qty IS NOT NULL AND tier_min_qty <= tier_max_qty)
    )
);

-- =========================================================
-- 7) NORMALIZED layer: SKU + dictionary + mapping + tasks
-- =========================================================
CREATE TABLE IF NOT EXISTS normalized_skus (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_type  text NOT NULL,   -- rose/carnation/greens/packaging/... (dictionary-driven)
  variety       text NULL,
  color         text NULL,
  title         text NOT NULL,
  -- generated search vector (simple config; can switch to russian later)
  search_tsv    tsvector GENERATED ALWAYS AS (
    to_tsvector('simple',
      coalesce(product_type,'') || ' ' ||
      coalesce(variety,'')      || ' ' ||
      coalesce(color,'')        || ' ' ||
      coalesce(title,'')
    )
  ) STORED,

  meta          jsonb NOT NULL DEFAULT '{}'::jsonb,

  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_normalized_skus_updated_at
BEFORE UPDATE ON normalized_skus
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS dictionary_entries (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  dict_type   text NOT NULL,           -- product_type/color/variety/country/pack_type/regex_rule/...
  key         text NOT NULL,
  value       text NOT NULL,
  synonyms    text[] NULL,
  rules       jsonb NOT NULL DEFAULT '{}'::jsonb,  -- regex/replace/extract patterns
  status      text NOT NULL DEFAULT 'active',      -- active/deprecated
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (dict_type, key)
);

CREATE TRIGGER trg_dictionary_entries_updated_at
BEFORE UPDATE ON dictionary_entries
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS sku_mappings (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_item_id uuid NOT NULL REFERENCES supplier_items(id) ON DELETE CASCADE,
  normalized_sku_id uuid NOT NULL REFERENCES normalized_skus(id) ON DELETE CASCADE,

  method           mapping_method NOT NULL DEFAULT 'rule',
  confidence       numeric(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),
  status           mapping_status NOT NULL DEFAULT 'proposed',

  decided_by       uuid NULL,     -- link to auth.users if you add later
  decided_at       timestamptz NULL,
  notes            text NULL,

  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_sku_mappings_updated_at
BEFORE UPDATE ON sku_mappings
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Only ONE confirmed mapping per supplier_item (partial unique index)
CREATE UNIQUE INDEX IF NOT EXISTS ux_sku_mappings_one_confirmed_per_item
ON sku_mappings (supplier_item_id)
WHERE status = 'confirmed';

CREATE TABLE IF NOT EXISTS normalization_tasks (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_item_id uuid NOT NULL REFERENCES supplier_items(id) ON DELETE CASCADE,

  reason           text NOT NULL, -- unknown_product/ambiguous/needs_dictionary/...
  priority         integer NOT NULL DEFAULT 100,
  status           task_status NOT NULL DEFAULT 'open',
  assigned_to      uuid NULL,

  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_normalization_tasks_updated_at
BEFORE UPDATE ON normalization_tasks
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================================================
-- 8) PUBLISHED layer: offers + delivery rules
-- =========================================================
CREATE TABLE IF NOT EXISTS supplier_delivery_rules (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_id     uuid NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
  city_id         uuid NULL REFERENCES cities(id) ON DELETE SET NULL,

  delivery_zone   jsonb NOT NULL DEFAULT '{}'::jsonb, -- later can migrate to PostGIS
  min_order_amount numeric(12,2) NULL CHECK (min_order_amount IS NULL OR min_order_amount >= 0),
  min_order_qty   integer NULL CHECK (min_order_qty IS NULL OR min_order_qty >= 0),
  delivery_windows jsonb NOT NULL DEFAULT '{}'::jsonb,
  notes           text NULL,

  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_supplier_delivery_rules_updated_at
BEFORE UPDATE ON supplier_delivery_rules
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS offers (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_id     uuid NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
  normalized_sku_id uuid NOT NULL REFERENCES normalized_skus(id) ON DELETE CASCADE,
  source_import_batch_id uuid NULL REFERENCES import_batches(id) ON DELETE SET NULL,

  length_cm       integer NULL CHECK (length_cm IS NULL OR length_cm > 0),
  pack_type       text NULL,
  pack_qty        integer NULL CHECK (pack_qty IS NULL OR pack_qty > 0),

  price_type      price_type NOT NULL DEFAULT 'fixed',
  price_min       numeric(12,2) NOT NULL CHECK (price_min >= 0),
  price_max       numeric(12,2) NULL CHECK (price_max IS NULL OR price_max >= 0),
  currency        char(3) NOT NULL DEFAULT 'RUB',

  tier_min_qty    integer NULL CHECK (tier_min_qty IS NULL OR tier_min_qty >= 0),
  tier_max_qty    integer NULL CHECK (tier_max_qty IS NULL OR tier_max_qty >= 0),

  availability    availability_type NOT NULL DEFAULT 'unknown',
  stock_qty       integer NULL CHECK (stock_qty IS NULL OR stock_qty >= 0),

  is_active       boolean NOT NULL DEFAULT true,
  published_at    timestamptz NOT NULL DEFAULT now(),

  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT offers_price_min_le_max
    CHECK (price_max IS NULL OR price_min <= price_max),

  CONSTRAINT offers_tier_min_le_max
    CHECK (
      (tier_min_qty IS NULL AND tier_max_qty IS NULL)
      OR (tier_min_qty IS NOT NULL AND tier_max_qty IS NOT NULL AND tier_min_qty <= tier_max_qty)
    )
);

CREATE TRIGGER trg_offers_updated_at
BEFORE UPDATE ON offers
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================================================
-- 9) Orders (MVP)
-- =========================================================
CREATE TABLE IF NOT EXISTS orders (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  buyer_id    uuid NOT NULL REFERENCES buyers(id) ON DELETE CASCADE,
  city_id     uuid NULL REFERENCES cities(id) ON DELETE SET NULL,
  status      order_status NOT NULL DEFAULT 'draft',
  notes       text NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_orders_updated_at
BEFORE UPDATE ON orders
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS order_supplier_links (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id    uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  supplier_id uuid NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
  status      order_supplier_status NOT NULL DEFAULT 'sent',
  supplier_notes text NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (order_id, supplier_id)
);

CREATE TRIGGER trg_order_supplier_links_updated_at
BEFORE UPDATE ON order_supplier_links
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS order_lines (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id    uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  offer_id    uuid NOT NULL REFERENCES offers(id) ON DELETE RESTRICT,

  qty         integer NOT NULL CHECK (qty > 0),
  unit_price  numeric(12,2) NOT NULL CHECK (unit_price >= 0),
  line_amount numeric(12,2) NOT NULL CHECK (line_amount >= 0),

  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS order_events (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id    uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  entity_type text NOT NULL CHECK (entity_type IN ('order', 'order_supplier_link')),
  entity_id   uuid NOT NULL, -- points to orders.id or order_supplier_links.id (soft FK)
  from_status text NULL,
  to_status   text NOT NULL,
  payload     jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 10) Indexes (performance)
-- =========================================================

-- suppliers / buyers
CREATE INDEX IF NOT EXISTS ix_suppliers_city_status ON suppliers (city_id, status);
CREATE INDEX IF NOT EXISTS ix_buyers_city_status ON buyers (city_id, status);

-- imports
CREATE INDEX IF NOT EXISTS ix_import_batches_supplier_time ON import_batches (supplier_id, imported_at DESC);
CREATE INDEX IF NOT EXISTS ix_raw_rows_batch_kind ON raw_rows (import_batch_id, row_kind);
CREATE INDEX IF NOT EXISTS ix_parse_runs_batch_time ON parse_runs (import_batch_id, started_at DESC);
CREATE INDEX IF NOT EXISTS ix_parse_events_run_sev ON parse_events (parse_run_id, severity);

-- raw text debug search (optional but handy)
CREATE INDEX IF NOT EXISTS gin_raw_rows_raw_text_trgm
ON raw_rows USING gin (raw_text gin_trgm_ops);

-- supplier_items matching/search
CREATE INDEX IF NOT EXISTS ix_supplier_items_supplier_status ON supplier_items (supplier_id, status);
CREATE INDEX IF NOT EXISTS gin_supplier_items_raw_name_trgm
ON supplier_items USING gin (raw_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS gin_supplier_items_name_norm_trgm
ON supplier_items USING gin (name_norm gin_trgm_ops);

-- offer candidates
CREATE INDEX IF NOT EXISTS ix_offer_candidates_item_batch ON offer_candidates (supplier_item_id, import_batch_id);
CREATE INDEX IF NOT EXISTS ix_offer_candidates_batch_validation ON offer_candidates (import_batch_id, validation);

-- normalized_skus search
CREATE INDEX IF NOT EXISTS gin_normalized_skus_search_tsv
ON normalized_skus USING gin (search_tsv);
CREATE INDEX IF NOT EXISTS ix_normalized_skus_product_type ON normalized_skus (product_type);

-- dictionary
CREATE INDEX IF NOT EXISTS ix_dictionary_entries_type_status ON dictionary_entries (dict_type, status);
CREATE INDEX IF NOT EXISTS gin_dictionary_entries_synonyms ON dictionary_entries USING gin (synonyms);

-- mappings
CREATE INDEX IF NOT EXISTS ix_sku_mappings_item_status ON sku_mappings (supplier_item_id, status);
CREATE INDEX IF NOT EXISTS ix_sku_mappings_sku_status ON sku_mappings (normalized_sku_id, status);

-- offers (search & filters)
CREATE INDEX IF NOT EXISTS ix_offers_active_sku_price
ON offers (is_active, normalized_sku_id, price_min);
CREATE INDEX IF NOT EXISTS ix_offers_supplier_active
ON offers (supplier_id, is_active);
CREATE INDEX IF NOT EXISTS ix_offers_filters
ON offers (normalized_sku_id, length_cm, pack_type, pack_qty);

-- orders
CREATE INDEX IF NOT EXISTS ix_orders_buyer_time ON orders (buyer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_order_supplier_links_order ON order_supplier_links (order_id);
CREATE INDEX IF NOT EXISTS ix_order_lines_order ON order_lines (order_id);
CREATE INDEX IF NOT EXISTS ix_order_events_order_time ON order_events (order_id, created_at DESC);

-- =========================================================
-- End of DDL
-- =========================================================