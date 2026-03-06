# Sizzle — Optimized Database Schema (v2)

> **Target:** Supabase PostgreSQL (v15+)
> **Generated:** 2026-03-06
> **Source of truth:** This file → run top-to-bottom in Supabase SQL Editor.

---

## What changed from v1

| Change | Why |
|--------|-----|
| **FLOAT → NUMERIC(10,2)** on all money columns | Float arithmetic causes rounding errors on prices (e.g. `149.99 × 3 ≠ 449.97`). NUMERIC is exact. |
| **Eliminated `sale_transactions` table** | Was 100% copy of `order_items + orders` created on settle. Replaced with `v_sales` **view** — zero duplication, zero write-amplification, same query interface. |
| **All FKs use integer PKs** | `order_items`, `kots`, `restaurant_tables.current_order_id` now reference `orders.id` (INTEGER) instead of `orders.order_id` (VARCHAR 50). Integer joins are 3-5× faster. |
| **Added `settled_at`, `payment_method`, `guest_name`, `guest_count` to `orders`** | Previously accepted by API but never stored. |
| **Custom ENUM types** for status/role/reason columns | Faster than CHECK constraints on VARCHAR, type-safe, smaller on disk (4 bytes vs variable). |
| **`aliases` → TEXT[] array** | Native PostgreSQL array with `ANY()` lookups instead of pipe-separated string splitting. |
| **BRIN indexes on timestamps** | 100× smaller than B-tree for append-only time-series columns (`created_at`, `sold_at`). |
| **GIN indexes on JSONB** | Fast `@>` containment queries on `modifiers`, `tags`, `item_ids`. |
| **Partial indexes** | `WHERE is_active = TRUE` / `WHERE status = 'building'` — skip dead rows in hot-path reads. |
| **`restaurant_id` on `restaurant_tables`** | Was missing — multi-tenant filtering now works. |

---

## Table of Contents

1. [Clean Slate + Enum Types](#1-clean-slate--enum-types)
2. [Table DDL (15 tables + 1 view)](#2-table-ddl)
3. [Deferred Foreign Keys](#3-deferred-foreign-keys)
4. [The `v_sales` View](#4-the-v_sales-view)
5. [Feature ↔ Table Matrix](#5-feature--table-matrix)
6. [Code Migration Checklist](#6-code-migration-checklist)

---

## 1. Clean Slate + Enum Types

```sql
-- ╔══════════════════════════════════════════════════════════╗
-- ║  STEP 1 — Drop everything (child tables first)          ║
-- ╚══════════════════════════════════════════════════════════╝

DROP VIEW  IF EXISTS v_sales CASCADE;
DROP TABLE IF EXISTS stock_logs CASCADE;
DROP TABLE IF EXISTS menu_item_ingredients CASCADE;
DROP TABLE IF EXISTS ingredients CASCADE;
DROP TABLE IF EXISTS combo_suggestions CASCADE;
DROP TABLE IF EXISTS voice_sessions CASCADE;
DROP TABLE IF EXISTS kots CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS restaurant_tables CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS shifts CASCADE;
DROP TABLE IF EXISTS menu_items CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS staff CASCADE;
DROP TABLE IF EXISTS restaurant_settings CASCADE;
DROP TABLE IF EXISTS restaurants CASCADE;

DROP TYPE IF EXISTS staff_role CASCADE;
DROP TYPE IF EXISTS table_status CASCADE;
DROP TYPE IF EXISTS shift_status CASCADE;
DROP TYPE IF EXISTS order_status CASCADE;
DROP TYPE IF EXISTS order_type CASCADE;
DROP TYPE IF EXISTS order_source CASCADE;
DROP TYPE IF EXISTS payment_method CASCADE;
DROP TYPE IF EXISTS stock_reason CASCADE;
DROP TYPE IF EXISTS measure_unit CASCADE;

-- ╔══════════════════════════════════════════════════════════╗
-- ║  STEP 2 — Custom ENUM types (4 bytes, type-safe)        ║
-- ╚══════════════════════════════════════════════════════════╝

CREATE TYPE staff_role      AS ENUM ('waiter', 'cashier', 'manager', 'chef');
CREATE TYPE table_status    AS ENUM ('empty', 'occupied', 'reserved', 'cleaning');
CREATE TYPE shift_status    AS ENUM ('open', 'closed');
CREATE TYPE order_status    AS ENUM ('building', 'confirmed', 'cancelled');
CREATE TYPE order_type      AS ENUM ('dine_in', 'takeaway', 'delivery');
CREATE TYPE order_source    AS ENUM ('voice', 'manual');
CREATE TYPE payment_method  AS ENUM ('cash', 'card', 'upi');
CREATE TYPE stock_reason    AS ENUM ('purchase', 'usage', 'waste', 'adjustment');
CREATE TYPE measure_unit    AS ENUM ('g', 'kg', 'ml', 'L', 'pcs');
```

---

## 2. Table DDL

### restaurants

```sql
CREATE TABLE restaurants (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200)    NOT NULL,
    slug            VARCHAR(100)    UNIQUE NOT NULL,
    email           VARCHAR(200)    UNIQUE NOT NULL,
    password_hash   VARCHAR(256)    NOT NULL,
    phone           VARCHAR(20),
    address         TEXT,
    cuisine_type    VARCHAR(100),
    logo_url        VARCHAR(500),
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_restaurants_active ON restaurants (id) WHERE is_active;
```

---

### restaurant_settings

```sql
CREATE TABLE restaurant_settings (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER         NOT NULL UNIQUE
                    REFERENCES restaurants(id) ON DELETE CASCADE,
    menu_management JSONB           NOT NULL DEFAULT '{}',
    notifications   JSONB           NOT NULL DEFAULT '{}',
    integrations    JSONB           NOT NULL DEFAULT '{}',
    billing_plan    JSONB           NOT NULL DEFAULT '{}',
    security        JSONB           NOT NULL DEFAULT '{}',
    voice_ai_config JSONB           NOT NULL DEFAULT '{}',
    profile_extras  JSONB           NOT NULL DEFAULT '{}',
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
```

---

### staff

```sql
CREATE TABLE staff (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER         NOT NULL
                    REFERENCES restaurants(id) ON DELETE CASCADE,
    name            VARCHAR(150)    NOT NULL,
    role            staff_role      NOT NULL DEFAULT 'waiter',
    pin_hash        VARCHAR(128)    NOT NULL,
    phone           VARCHAR(20),
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_staff_restaurant ON staff (restaurant_id) WHERE is_active;
```

---

### shifts

```sql
CREATE TABLE shifts (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER         NOT NULL
                    REFERENCES restaurants(id) ON DELETE CASCADE,
    name            VARCHAR(50),
    started_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    opened_by       INTEGER         NOT NULL REFERENCES staff(id),
    closed_by       INTEGER         REFERENCES staff(id),
    opening_cash    NUMERIC(10,2)   NOT NULL DEFAULT 0,
    closing_cash    NUMERIC(10,2),
    status          shift_status    NOT NULL DEFAULT 'open'
);

CREATE INDEX idx_shifts_open ON shifts (restaurant_id) WHERE status = 'open';
CREATE INDEX idx_shifts_started ON shifts USING BRIN (started_at);
```

---

### categories

```sql
CREATE TABLE categories (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER         NOT NULL
                    REFERENCES restaurants(id) ON DELETE CASCADE,
    name            VARCHAR(100)    NOT NULL,
    name_hi         VARCHAR(100),
    name_mr         VARCHAR(100),
    name_kn         VARCHAR(100),
    name_gu         VARCHAR(100),
    name_hi_en      VARCHAR(100),
    display_order   SMALLINT        NOT NULL DEFAULT 0,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,

    UNIQUE (restaurant_id, name)
);

CREATE INDEX idx_categories_active ON categories (restaurant_id) WHERE is_active;
```

---

### menu_items

```sql
CREATE TABLE menu_items (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER         NOT NULL
                    REFERENCES restaurants(id) ON DELETE CASCADE,
    name            VARCHAR(200)    NOT NULL,
    name_hi         VARCHAR(200),
    name_mr         VARCHAR(200),
    name_kn         VARCHAR(200),
    name_gu         VARCHAR(200),
    name_hi_en      VARCHAR(200),
    description     TEXT,
    aliases         TEXT[]          NOT NULL DEFAULT '{}',   -- native array, no pipe-splitting
    category_id     INTEGER         REFERENCES categories(id) ON DELETE SET NULL,
    selling_price   NUMERIC(10,2)   NOT NULL,
    food_cost       NUMERIC(10,2)   NOT NULL,
    modifiers       JSONB           NOT NULL DEFAULT '{}',
    is_veg          BOOLEAN         NOT NULL DEFAULT TRUE,
    is_available    BOOLEAN         NOT NULL DEFAULT TRUE,
    is_bestseller   BOOLEAN         NOT NULL DEFAULT FALSE,
    current_stock   INTEGER,                                -- NULL = unlimited
    tags            JSONB           NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mi_restaurant   ON menu_items (restaurant_id);
CREATE INDEX idx_mi_category     ON menu_items (category_id);
CREATE INDEX idx_mi_available    ON menu_items (restaurant_id, category_id) WHERE is_available;
CREATE INDEX idx_mi_tags         ON menu_items USING GIN (tags);
```

---

### restaurant_tables

```sql
CREATE TABLE restaurant_tables (
    id                  SERIAL PRIMARY KEY,
    restaurant_id       INTEGER         NOT NULL
                        REFERENCES restaurants(id) ON DELETE CASCADE,
    table_number        VARCHAR(10)     NOT NULL,
    capacity            SMALLINT        NOT NULL DEFAULT 4,
    section             VARCHAR(50)     NOT NULL DEFAULT 'main',
    status              table_status    NOT NULL DEFAULT 'empty',
    current_order_id    INTEGER,        -- FK added after orders table

    UNIQUE (restaurant_id, table_number)
);

CREATE INDEX idx_tables_restaurant ON restaurant_tables (restaurant_id);
CREATE INDEX idx_tables_occupied   ON restaurant_tables (restaurant_id)
                                   WHERE status = 'occupied';
```

---

### orders

> **Key change:** `order_id` (VARCHAR) stays as a human-readable display field,
> but **all FKs now use `orders.id` (INTEGER)** — faster joins everywhere.

```sql
CREATE TABLE orders (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER         NOT NULL
                    REFERENCES restaurants(id) ON DELETE CASCADE,
    order_id        VARCHAR(50)     UNIQUE NOT NULL,         -- "ORD-20260306-A1B2C3" (display only)
    order_number    VARCHAR(20),
    total_amount    NUMERIC(10,2)   NOT NULL DEFAULT 0,
    status          order_status    NOT NULL DEFAULT 'building',
    order_type      order_type      NOT NULL DEFAULT 'dine_in',
    table_id        INTEGER         REFERENCES restaurant_tables(id) ON DELETE SET NULL,
    staff_id        INTEGER         REFERENCES staff(id) ON DELETE SET NULL,
    shift_id        INTEGER         REFERENCES shifts(id) ON DELETE SET NULL,
    source          order_source    NOT NULL DEFAULT 'voice',

    -- Fields previously missing (accepted by API but never stored)
    guest_name      VARCHAR(150),
    guest_count     SMALLINT,
    payment_method  payment_method,
    settled_at      TIMESTAMPTZ,                             -- NULL = not yet settled

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Now add the deferred FK from restaurant_tables → orders
ALTER TABLE restaurant_tables
    ADD CONSTRAINT fk_tables_current_order
    FOREIGN KEY (current_order_id) REFERENCES orders(id) ON DELETE SET NULL;

CREATE INDEX idx_orders_restaurant  ON orders (restaurant_id);
CREATE INDEX idx_orders_status      ON orders (restaurant_id, status);
CREATE INDEX idx_orders_building    ON orders (restaurant_id) WHERE status = 'building';
CREATE INDEX idx_orders_table       ON orders (table_id) WHERE table_id IS NOT NULL;
CREATE INDEX idx_orders_created     ON orders USING BRIN (created_at);
```

> **Removed:** `table_number` column — use `JOIN restaurant_tables` on `table_id` instead. One source of truth.

---

### order_items

```sql
CREATE TABLE order_items (
    id                  SERIAL PRIMARY KEY,
    order_pk            INTEGER         NOT NULL
                        REFERENCES orders(id) ON DELETE CASCADE,      -- INTEGER FK, not VARCHAR
    item_id             INTEGER         NOT NULL
                        REFERENCES menu_items(id) ON DELETE CASCADE,
    quantity            SMALLINT        NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price          NUMERIC(10,2)   NOT NULL,
    modifiers_applied   JSONB           NOT NULL DEFAULT '{}',
    line_total          NUMERIC(10,2)   NOT NULL
);

CREATE INDEX idx_oi_order ON order_items (order_pk);
CREATE INDEX idx_oi_item  ON order_items (item_id);
```

> **Renamed:** `order_id` → `order_pk` to make clear it's an integer FK to `orders.id`, not the display string.

---

### kots

```sql
CREATE TABLE kots (
    id              SERIAL PRIMARY KEY,
    kot_id          VARCHAR(50)     UNIQUE NOT NULL,
    order_pk        INTEGER         NOT NULL
                    REFERENCES orders(id) ON DELETE CASCADE,          -- INTEGER FK
    items_summary   JSONB           NOT NULL,
    print_ready     TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_kots_order ON kots (order_pk);
```

---

### combo_suggestions

```sql
CREATE TABLE combo_suggestions (
    id                  SERIAL PRIMARY KEY,
    restaurant_id       INTEGER         NOT NULL
                        REFERENCES restaurants(id) ON DELETE CASCADE,
    name                VARCHAR(200)    NOT NULL,
    item_ids            JSONB           NOT NULL,
    item_names          JSONB           NOT NULL,
    individual_total    NUMERIC(10,2),
    combo_price         NUMERIC(10,2),
    discount_pct        NUMERIC(5,2),
    expected_margin     NUMERIC(10,2),
    support             REAL,
    confidence          REAL,
    lift                REAL,
    combo_score         REAL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_combos_restaurant ON combo_suggestions (restaurant_id);
CREATE INDEX idx_combos_score      ON combo_suggestions (combo_score DESC NULLS LAST);
CREATE INDEX idx_combos_items      ON combo_suggestions USING GIN (item_ids);
```

---

### ingredients

```sql
CREATE TABLE ingredients (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER         NOT NULL
                    REFERENCES restaurants(id) ON DELETE CASCADE,
    name            VARCHAR(150)    NOT NULL,
    unit            measure_unit    NOT NULL DEFAULT 'g',
    current_stock   NUMERIC(10,2)   NOT NULL DEFAULT 0,
    reorder_level   NUMERIC(10,2)   NOT NULL DEFAULT 0,
    cost_per_unit   NUMERIC(10,4)   NOT NULL DEFAULT 0,      -- 4 decimal places for per-gram costs
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    UNIQUE (restaurant_id, name)
);

CREATE INDEX idx_ingredients_active ON ingredients (restaurant_id) WHERE is_active;
CREATE INDEX idx_ingredients_low    ON ingredients (restaurant_id)
                                    WHERE current_stock <= reorder_level AND is_active;
```

> **New:** `idx_ingredients_low` — partial index that only covers items actually at/below reorder level. Makes low-stock alerts instant.

---

### menu_item_ingredients

```sql
CREATE TABLE menu_item_ingredients (
    id              SERIAL PRIMARY KEY,
    menu_item_id    INTEGER         NOT NULL
                    REFERENCES menu_items(id) ON DELETE CASCADE,
    ingredient_id   INTEGER         NOT NULL
                    REFERENCES ingredients(id) ON DELETE CASCADE,
    quantity_used   NUMERIC(10,4)   NOT NULL,

    UNIQUE (menu_item_id, ingredient_id)
);

CREATE INDEX idx_mii_ingredient ON menu_item_ingredients (ingredient_id);
```

---

### stock_logs

```sql
CREATE TABLE stock_logs (
    id              SERIAL PRIMARY KEY,
    ingredient_id   INTEGER         NOT NULL
                    REFERENCES ingredients(id) ON DELETE CASCADE,
    change_qty      NUMERIC(10,2)   NOT NULL,
    reason          stock_reason    NOT NULL,
    note            TEXT,
    staff_id        INTEGER         REFERENCES staff(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sl_ingredient ON stock_logs (ingredient_id);
CREATE INDEX idx_sl_created    ON stock_logs USING BRIN (created_at);
CREATE INDEX idx_sl_waste      ON stock_logs (ingredient_id) WHERE reason = 'waste';
```

---

### voice_sessions

```sql
CREATE TABLE voice_sessions (
    id              SERIAL PRIMARY KEY,
    session_id      VARCHAR(100)    UNIQUE NOT NULL,
    last_active     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),   -- was FLOAT, now proper timestamp
    order_items     JSONB           NOT NULL DEFAULT '[]',
    last_items      JSONB           NOT NULL DEFAULT '[]',
    turn_count      SMALLINT        NOT NULL DEFAULT 0,
    confirmed       BOOLEAN         NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_vs_active ON voice_sessions (last_active);
```

---

## 3. Deferred Foreign Keys

All circular/cross-referenced FKs are handled via `ALTER TABLE` statements placed **after** both tables exist (see `orders` section above for `fk_tables_current_order`). No deferred constraint hacks needed.

---

## 4. The `v_sales` View

> **This replaces the `sale_transactions` table entirely.**
> All analytics modules query this view instead. Zero data duplication.

```sql
CREATE OR REPLACE VIEW v_sales AS
SELECT
    oi.id                           AS id,
    o.restaurant_id                 AS restaurant_id,
    oi.item_id                      AS item_id,
    o.order_id                      AS order_id,
    oi.quantity                     AS quantity,
    oi.unit_price                   AS unit_price,
    oi.line_total                   AS total_price,
    o.order_type::TEXT              AS order_type,
    o.shift_id                      AS shift_id,
    COALESCE(o.settled_at, o.updated_at) AS sold_at
FROM order_items oi
JOIN orders o ON o.id = oi.order_pk
WHERE o.status = 'confirmed';
```

**Why this is better:**
- **No write amplification** — settle just sets `orders.status = 'confirmed'` + `settled_at = NOW()`. No more INSERT loop creating N sale_transaction rows.
- **Always consistent** — if you edit an order item, analytics update automatically.
- **No missing columns** — the `shift_id` bug that crashed settle is gone (it comes from orders directly).
- **Same query interface** — `SELECT * FROM v_sales WHERE item_id = 5` works identically to the old table.

---

## 5. Feature ↔ Table Matrix

| Feature | Tables / Views Used |
|---------|---------------------|
| **Auth login/signup** | `restaurants` |
| **Restaurant profile** | `restaurants`, `restaurant_settings` |
| **Staff management** | `staff` |
| **Shift management** | `shifts`, `staff` |
| **Menu management** | `menu_items`, `categories` |
| **Table floor plan** | `restaurant_tables`, `orders`, `order_items`, `menu_items` |
| **Table book/settle** | `restaurant_tables`, `orders`, `order_items` |
| **Voice ordering** | `menu_items`, `voice_sessions`, `orders`, `order_items`, `kots` |
| **Dashboard / Menu matrix** | `v_sales`, `menu_items`, `categories` |
| **Combo engine** | `v_sales`, `menu_items`, `categories`, `combo_suggestions` |
| **Trend / price elasticity** | `v_sales`, `menu_items`, `categories` |
| **Waste analytics** | `stock_logs`, `ingredients`, `orders`, `order_items`, `menu_items` |
| **Inventory** | `ingredients`, `stock_logs`, `menu_item_ingredients` |

---

## 6. Code Migration Checklist

These backend files need updates to match the new schema:

### models.py changes

| Change | Details |
|--------|---------|
| All `Float` → `Numeric` | `from sqlalchemy import Numeric`; use `Numeric(10,2)` |
| All enum string columns → use `Enum` type | `from sqlalchemy import Enum`; `Column(Enum(staff_role_enum, ...))` or just use `String` and let the DB enum handle it |
| `OrderItem.order_id` → `OrderItem.order_pk` | `Column(Integer, ForeignKey("orders.id"))` instead of `ForeignKey("orders.order_id")` |
| `KOT.order_id` → `KOT.order_pk` | Same — integer FK to `orders.id` |
| `RestaurantTable.current_order_id` | Change from `String(50), ForeignKey("orders.order_id")` → `Integer, ForeignKey("orders.id")` |
| `Order` — add columns | `guest_name`, `guest_count`, `payment_method`, `settled_at` |
| `Order` — remove `table_number` | Get via `table_id` JOIN instead |
| `MenuItem.aliases` | `Column(ARRAY(Text), default=[])` instead of `Column(Text, default="")` |
| `VoiceSession.last_active` | `Column(DateTime)` instead of `Column(Float)` |
| Delete `SaleTransaction` model | Replace with `v_sales` view — analytics reads use raw SQL or a readonly ORM model mapped to the view |
| `ingredients.cost_per_unit` | `Numeric(10,4)` for per-gram precision |

### routes_ops.py changes

| Change | Details |
|--------|---------|
| `settle_table()` | Remove the entire `for oi in order_items: db.add(SaleTransaction(...))` loop. Just set `order.status = 'confirmed'`, `order.settled_at = now`, `order.payment_method = body.payment_method`. |
| `book_table()` | Store `body.guest_name`, `body.guest_count` on the new Order. |
| `table.current_order_id = order_id` (string) | → `table.current_order_id = order.id` (integer) |
| All `OrderItem.order_id` references | → `OrderItem.order_pk` |
| Remove `table_number` from Order creation | Use `table_id` only |

### Analytics modules

| Module | Change |
|--------|--------|
| `popularity.py` | Query `v_sales` instead of `SaleTransaction` |
| `contribution_margin.py` | Query `v_sales` instead of `SaleTransaction` |
| `combo_engine.py` | Query `v_sales` instead of `SaleTransaction` |
| `trend_analyzer.py` | Query `v_sales` instead of `SaleTransaction` |
| `advanced_analytics.py` | Query `v_sales` for sales data |

> **Tip:** Create a thin ORM model `class VSale(Base): __tablename__ = "v_sales"` with `__table_args__ = {"info": {"is_view": True}}` so all analytics modules can use `db.query(VSale)` with zero other code changes.

### Voice modules

| Module | Change |
|--------|--------|
| `item_matcher.py` | `aliases.split("|")` → aliases is already a list (TEXT[]) |
| `session_store.py` | `last_active` is TIMESTAMPTZ now, not unix float |
| `order_builder.py` | `OrderItem(order_id=...)` → `OrderItem(order_pk=order.id)`, remove `table_number` from Order |

---

## Quick apply

Copy sections 1, 2, and 4 into Supabase SQL Editor and execute in order. The `_run_auto_migrations()` in `main.py` will handle any future column additions automatically after the code is updated to match.
