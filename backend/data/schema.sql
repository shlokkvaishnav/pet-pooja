-- =============================================================
-- Petpooja AI Copilot — Supabase PostgreSQL Schema
-- =============================================================
-- Run this in Supabase SQL Editor to create all tables.
-- Or let SQLAlchemy create them via Base.metadata.create_all()
-- =============================================================

-- Drop existing tables (in dependency order)
DROP TABLE IF EXISTS stock_logs CASCADE;
DROP TABLE IF EXISTS menu_item_ingredients CASCADE;
DROP TABLE IF EXISTS ingredients CASCADE;
DROP TABLE IF EXISTS combo_suggestions CASCADE;
DROP TABLE IF EXISTS kots CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS restaurant_tables CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS sale_transactions CASCADE;
DROP TABLE IF EXISTS shifts CASCADE;
DROP TABLE IF EXISTS menu_items CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS staff CASCADE;

-- ── Staff ───────────────────────────────────────

CREATE TABLE staff (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(150) NOT NULL,
    role        VARCHAR(30) NOT NULL DEFAULT 'waiter'
                CHECK (role IN ('waiter','cashier','manager','chef')),
    pin_hash    VARCHAR(128) NOT NULL,
    phone       VARCHAR(20),
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_staff_active ON staff (is_active);

-- ── Categories ──────────────────────────────────

CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) UNIQUE NOT NULL,
    name_hi     VARCHAR(100),
    display_order INTEGER DEFAULT 0,
    is_active   BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_categories_active ON categories (is_active);

-- ── Menu Items ──────────────────────────────────

CREATE TABLE menu_items (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    name_hi         VARCHAR(200),
    description     TEXT,
    aliases         TEXT DEFAULT '',          -- pipe-separated: "pnr tikka|panir tikka"
    category_id     INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    selling_price   FLOAT NOT NULL,
    food_cost       FLOAT NOT NULL,
    modifiers       JSONB DEFAULT '{}',       -- {"spice_level": [...], "size": [...]}
    is_veg          BOOLEAN DEFAULT TRUE,
    is_available    BOOLEAN DEFAULT TRUE,
    is_bestseller   BOOLEAN DEFAULT FALSE,
    current_stock   INTEGER,                  -- NULL = unlimited
    tags            JSONB DEFAULT '[]',       -- ["spicy", "chef-special"]
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_menu_items_category ON menu_items (category_id);
CREATE INDEX idx_menu_items_available ON menu_items (is_available);
CREATE INDEX idx_menu_items_bestseller ON menu_items (is_bestseller);

-- ── Sale Transactions (historical order data for analytics) ──

CREATE TABLE sale_transactions (
    id          SERIAL PRIMARY KEY,
    item_id     INTEGER NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
    order_id    VARCHAR(50) NOT NULL,
    quantity    INTEGER DEFAULT 1,
    unit_price  FLOAT NOT NULL,
    total_price FLOAT NOT NULL,
    order_type  VARCHAR(20) DEFAULT 'dine_in',   -- dine_in | takeaway | delivery
    shift_id    INTEGER REFERENCES shifts(id),
    sold_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sales_item ON sale_transactions (item_id);
CREATE INDEX idx_sales_order ON sale_transactions (order_id);
CREATE INDEX idx_sales_sold_at ON sale_transactions (sold_at);

-- ── Shifts ──────────────────────────────────────

CREATE TABLE shifts (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(50),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    opened_by       INTEGER NOT NULL REFERENCES staff(id),
    closed_by       INTEGER REFERENCES staff(id),
    opening_cash    FLOAT DEFAULT 0.0,
    closing_cash    FLOAT,
    status          VARCHAR(10) DEFAULT 'open'
                    CHECK (status IN ('open','closed'))
);

CREATE INDEX idx_shifts_status ON shifts (status);
CREATE INDEX idx_shifts_started ON shifts (started_at DESC);

-- ── Orders (voice/manual orders) ────────────────

CREATE TABLE orders (
    id              SERIAL PRIMARY KEY,
    order_id        VARCHAR(50) UNIQUE NOT NULL,
    order_number    VARCHAR(20),
    total_amount    FLOAT DEFAULT 0.0,
    status          VARCHAR(20) DEFAULT 'building',  -- building | confirmed | cancelled
    order_type      VARCHAR(20) DEFAULT 'dine_in',
    table_number    VARCHAR(10),
    table_id        INTEGER REFERENCES restaurant_tables(id),
    staff_id        INTEGER REFERENCES staff(id),
    shift_id        INTEGER REFERENCES shifts(id),
    source          VARCHAR(20) DEFAULT 'voice',     -- voice | manual
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_orders_status ON orders (status);
CREATE INDEX idx_orders_created ON orders (created_at DESC);
CREATE INDEX idx_orders_shift ON orders (shift_id);
CREATE INDEX idx_orders_staff ON orders (staff_id);

-- ── Restaurant Tables ───────────────────────────

CREATE TABLE restaurant_tables (
    id                  SERIAL PRIMARY KEY,
    table_number        VARCHAR(10) UNIQUE NOT NULL,
    capacity            INTEGER NOT NULL DEFAULT 4,
    section             VARCHAR(50) DEFAULT 'main',   -- main | patio | private | bar
    status              VARCHAR(20) DEFAULT 'empty'
                        CHECK (status IN ('empty','occupied','reserved','cleaning')),
    current_order_id    VARCHAR(50) REFERENCES orders(order_id)
);

CREATE INDEX idx_tables_status ON restaurant_tables (status);

-- ── Order Items ─────────────────────────────────

CREATE TABLE order_items (
    id                  SERIAL PRIMARY KEY,
    order_id            VARCHAR(50) NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    item_id             INTEGER NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
    quantity            INTEGER DEFAULT 1,
    unit_price          FLOAT NOT NULL,
    modifiers_applied   JSONB DEFAULT '{}',
    line_total          FLOAT NOT NULL
);

CREATE INDEX idx_order_items_order ON order_items (order_id);

-- ── KOT (Kitchen Order Tickets) ─────────────────

CREATE TABLE kots (
    id              SERIAL PRIMARY KEY,
    kot_id          VARCHAR(50) UNIQUE NOT NULL,    -- KOT-YYYYMMDD-XXXX
    order_id        VARCHAR(50) NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    items_summary   JSONB NOT NULL,                 -- [{name, qty, modifiers}]
    print_ready     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_kots_order ON kots (order_id);

-- ── Combo Suggestions (generated by FP-Growth) ──

CREATE TABLE combo_suggestions (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    item_ids            JSONB NOT NULL,             -- [1, 5, 12]
    item_names          JSONB NOT NULL,             -- ["Paneer Tikka", "Naan"]
    individual_total    FLOAT,
    combo_price         FLOAT,
    discount_pct        FLOAT,
    expected_margin     FLOAT,
    support             FLOAT,
    confidence          FLOAT,
    lift                FLOAT,
    combo_score         FLOAT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── Ingredients ─────────────────────────────────

CREATE TABLE ingredients (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(150) UNIQUE NOT NULL,
    unit            VARCHAR(20) NOT NULL DEFAULT 'g',   -- g | kg | ml | L | pcs
    current_stock   FLOAT NOT NULL DEFAULT 0.0,
    reorder_level   FLOAT NOT NULL DEFAULT 0.0,
    cost_per_unit   FLOAT NOT NULL DEFAULT 0.0,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ingredients_active ON ingredients (is_active);

-- ── Menu-Item ↔ Ingredient (recipe / BOM) ───────

CREATE TABLE menu_item_ingredients (
    id              SERIAL PRIMARY KEY,
    menu_item_id    INTEGER NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
    ingredient_id   INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    quantity_used   FLOAT NOT NULL   -- per 1 serving, in ingredient's unit
);

CREATE INDEX idx_mii_item ON menu_item_ingredients (menu_item_id);
CREATE INDEX idx_mii_ingredient ON menu_item_ingredients (ingredient_id);

-- ── Stock Logs (audit trail for inventory changes) ──

CREATE TABLE stock_logs (
    id              SERIAL PRIMARY KEY,
    ingredient_id   INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    change_qty      FLOAT NOT NULL,             -- positive = add, negative = deduct
    reason          VARCHAR(30) NOT NULL
                    CHECK (reason IN ('purchase','usage','waste','adjustment')),
    note            TEXT,
    staff_id        INTEGER REFERENCES staff(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_stocklogs_ingredient ON stock_logs (ingredient_id);
CREATE INDEX idx_stocklogs_reason ON stock_logs (reason);
CREATE INDEX idx_stocklogs_created ON stock_logs (created_at DESC);

-- ── Enable Row-Level Security (optional, recommended) ──

-- ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE menu_items ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE sale_transactions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE kots ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE combo_suggestions ENABLE ROW LEVEL SECURITY;

-- ── Done ──
SELECT 'Schema created successfully' AS status;
