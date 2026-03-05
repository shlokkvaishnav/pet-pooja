"""
generate_synthetic_data.py — Supabase Synthetic Data Generator
================================================================
Generates 60 menu items across 6 categories and 180 days of
realistic sales data with co-occurrence patterns, then inserts
everything into the Supabase PostgreSQL database.

Usage:
    cd backend
    python data/generate_synthetic_data.py

Supports:
    --reset    Drop and recreate all tables first
    --days N   Number of days of history (default: 180)
"""

import json
import random
import sys
import uuid
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent dir so we can import database/models
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import engine, Base, SessionLocal
from models import Category, MenuItem, SaleTransaction


# ── Helpers ──────────────────────────────────────

def load_sample_menu() -> dict:
    """Load the base menu JSON."""
    menu_path = Path(__file__).parent / "sample_menu.json"
    with open(menu_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _utcnow():
    return datetime.now(timezone.utc)


# ── Phase 1: Categories ─────────────────────────

def seed_categories(db, categories_data: list) -> dict:
    """Insert categories, return name → id map."""
    cat_map = {}
    for idx, cat in enumerate(categories_data):
        obj = Category(
            name=cat["name"],
            name_hi=cat.get("name_hi", ""),
            display_order=idx,
            is_active=True,
        )
        db.add(obj)
        db.flush()
        cat_map[cat["name"]] = obj.id
    db.commit()
    return cat_map


# ── Phase 2: Menu Items ─────────────────────────

def seed_menu_items(db, items_data: list, cat_map: dict) -> list:
    """Insert menu items, return list of MenuItem objects."""
    items = []
    for item_data in items_data:
        obj = MenuItem(
            name=item_data["name"],
            name_hi=item_data.get("name_hi", ""),
            aliases=item_data.get("aliases", ""),
            category_id=cat_map.get(item_data["category"]),
            selling_price=item_data["selling_price"],
            food_cost=item_data["food_cost"],
            modifiers=item_data.get("modifiers", {}),
            is_veg=item_data.get("is_veg", True),
            is_available=True,
            is_bestseller="bestseller" in item_data.get("tags", []),
            tags=item_data.get("tags", []),
        )
        db.add(obj)
        db.flush()
        items.append(obj)
    db.commit()
    return items


# ── Phase 3: Synthetic Sales Data ───────────────

def _build_name_index(items: list) -> dict:
    return {item.name.lower(): item for item in items}


def _get_biryani_items(items: list) -> list:
    return [i for i in items if "biryani" in i.name.lower()]


def _get_cold_drink_items(items: list) -> list:
    cold_names = {"cold drink", "sweet lassi", "buttermilk", "jaljeera", "fresh lime soda"}
    return [i for i in items if i.name.lower() in cold_names]


def _pick_time_of_day() -> int:
    """Weighted hour: lunch 12–3, dinner 7–10, light otherwise."""
    weights = {
        11: 5, 12: 15, 13: 20, 14: 15, 15: 8,
        16: 3, 17: 4, 18: 6,
        19: 12, 20: 20, 21: 18, 22: 10,
    }
    hours = list(weights.keys())
    probs = list(weights.values())
    return random.choices(hours, weights=probs, k=1)[0]


def seed_sales(db, items: list, num_days: int = 180, base_orders_per_day: int = 110):
    """
    Generate realistic sales transactions:
    - 80–150 orders/day (base 110, ±35%)
    - Weekend 1.5× volume
    - Butter Naan + Dal Makhani co-occurrence ~70%
    - Cold Drink + any Biryani co-occurrence ~60%
    - Lunch (12–3) and dinner (7–10) spikes
    """
    order_types = ["dine_in", "takeaway", "delivery"]
    type_weights = [0.55, 0.25, 0.20]
    order_counter = 0

    name_idx = _build_name_index(items)
    biryani_items = _get_biryani_items(items)
    cold_drink_items = _get_cold_drink_items(items)

    butter_naan = name_idx.get("butter naan")
    dal_makhani = name_idx.get("dal makhani")

    # Popularity weights — aligned with BCG quadrant targets
    # BCG classifier uses margin_threshold=60% and popularity_threshold=0.4
    # Score = item_qty / max_qty, so items targeting "high pop" need >= 40% of max
    #
    # Target distribution:
    #   star      (margin>=60%, high pop)  — bestsellers with high margins
    #   plowhorse (margin<60%,  high pop)  — workhorses / cheap favourites
    #   puzzle    (margin>=60%, low pop)   — hidden stars
    #   dog       (margin<60%,  low pop)   — low margin, low traffic
    item_weights = []
    for item in items:
        margin = item.margin_pct
        if margin >= 60 and item.is_bestseller:
            # → star: high pop, high margin — heaviest weight
            weight = random.uniform(5.0, 7.0)
        elif margin >= 60 and not item.is_bestseller:
            # → puzzle: low pop, high margin — suppress sales
            weight = random.uniform(0.25, 0.55)
        elif margin < 60 and item.is_bestseller:
            # → plowhorse: high pop, low margin
            weight = random.uniform(4.0, 6.0)
        elif margin >= 40:
            # workhorses (40-60%) — most should become plowhorses (high pop)
            weight = random.uniform(3.0, 5.0)
        else:
            # dogs (<40% margin) — keep low pop
            weight = random.uniform(0.2, 0.5)
        item_weights.append(weight)

    total_weight = sum(item_weights)
    item_probs = [w / total_weight for w in item_weights]

    now = _utcnow()
    total_sales = 0
    batch = []
    BATCH_SIZE = 5000

    for day_offset in range(num_days):
        date = now - timedelta(days=day_offset)
        is_weekend = date.weekday() >= 5

        day_multiplier = 1.5 if is_weekend else 1.0
        day_orders = random.randint(
            int(base_orders_per_day * 0.75 * day_multiplier),
            int(base_orders_per_day * 1.35 * day_multiplier),
        )

        for _ in range(day_orders):
            order_counter += 1
            order_id = f"ORD-{order_counter:06d}"
            order_type = random.choices(order_types, weights=type_weights, k=1)[0]
            hour = _pick_time_of_day()

            num_items = random.randint(2, 5)
            ordered_items = set()

            base = random.choices(items, weights=item_probs, k=num_items)
            for item in base:
                ordered_items.add(item)

            # Co-occurrence 1: Butter Naan + Dal Makhani (70%)
            if butter_naan and dal_makhani:
                if random.random() < 0.70:
                    ordered_items.add(butter_naan)
                    ordered_items.add(dal_makhani)

            # Co-occurrence 2: Cold Drink + Biryani (60%)
            ordered_biryani = [i for i in ordered_items if i in biryani_items]
            if ordered_biryani and cold_drink_items:
                if random.random() < 0.60:
                    ordered_items.add(random.choice(cold_drink_items))
            elif biryani_items and cold_drink_items:
                if random.random() < 0.15:
                    ordered_items.add(random.choice(biryani_items))
                    ordered_items.add(random.choice(cold_drink_items))

            for item in ordered_items:
                qty = random.choices([1, 2, 3], weights=[0.70, 0.25, 0.05], k=1)[0]
                unit_price = item.selling_price * random.uniform(0.95, 1.0)

                sale = SaleTransaction(
                    item_id=item.id,
                    order_id=order_id,
                    quantity=qty,
                    unit_price=round(unit_price, 2),
                    total_price=round(unit_price * qty, 2),
                    order_type=order_type,
                    sold_at=date.replace(
                        hour=hour,
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59),
                    ),
                )
                batch.append(sale)
                total_sales += 1

            # Flush in batches to keep memory low
            if len(batch) >= BATCH_SIZE:
                db.bulk_save_objects(batch)
                db.flush()
                batch.clear()

        if day_offset % 30 == 29:
            if batch:
                db.bulk_save_objects(batch)
                db.flush()
                batch.clear()
            db.commit()
            print(f"   ... {day_offset + 1}/{num_days} days ({order_counter:,} orders, {total_sales:,} sales)")

    # Flush remaining
    if batch:
        db.bulk_save_objects(batch)
    db.commit()

    print(f"   Generated {order_counter:,} orders, {total_sales:,} sale transactions across {num_days} days")
    return order_counter, total_sales


# ── Main ─────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic data for Petpooja")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables")
    parser.add_argument("--days", type=int, default=180, help="Days of order history (default: 180)")
    args = parser.parse_args()

    print("🌱 Generating synthetic data for Supabase...")
    print("=" * 60)

    if args.reset:
        print("⚠️  Dropping all tables...")
        Base.metadata.drop_all(bind=engine)

    # Create tables (idempotent — safe to run multiple times)
    Base.metadata.create_all(bind=engine)
    print("✅ Tables verified/created on Supabase")

    db = SessionLocal()

    try:
        # Check if data already exists
        existing = db.query(MenuItem).count()
        if existing > 0 and not args.reset:
            print(f"⚠️  Database already has {existing} menu items.")
            print("   Use --reset to drop and recreate. Skipping seed.")
            return

        # Load menu
        menu_data = load_sample_menu()

        # Seed categories
        print("📁 Seeding categories...")
        cat_map = seed_categories(db, menu_data["categories"])
        print(f"   {len(cat_map)} categories created")

        # Seed menu items
        print("🍽️  Seeding menu items...")
        items = seed_menu_items(db, menu_data["items"], cat_map)
        print(f"   {len(items)} menu items created")

        # Verify CM% distribution
        stars = sum(1 for i in items if i.margin_pct >= 65 and i.is_bestseller)
        hidden = sum(1 for i in items if i.margin_pct >= 65 and not i.is_bestseller)
        workhorses = sum(1 for i in items if 40 <= i.margin_pct < 65)
        dogs = sum(1 for i in items if i.margin_pct < 40)
        print(f"   CM% Distribution → Stars: {stars}, Hidden Stars: {hidden}, Workhorses: {workhorses}, Dogs: {dogs}")

        # Seed sales transactions
        print(f"📊 Generating {args.days} days of sales data...")
        n_orders, n_sales = seed_sales(db, items, num_days=args.days, base_orders_per_day=110)

        print("=" * 60)
        print("✅ Supabase database populated successfully!")
        print(f"   Categories:          {len(cat_map)}")
        print(f"   Menu items:          {len(items)}")
        print(f"   Orders:              ~{n_orders:,}")
        print(f"   Sale transactions:   ~{n_sales:,}")
        print(f"   Days of history:     {args.days}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
