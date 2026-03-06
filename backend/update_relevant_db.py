"""
update_relevant_db.py
=====================
Safe database maintenance for analytics/ops correctness.

Important:
- This script NEVER writes to `restaurant_tables`.
- It only updates business data needed for dashboard accuracy.

Usage:
  python update_relevant_db.py --dry-run
  python update_relevant_db.py --apply
"""

from __future__ import annotations

import argparse
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import SessionLocal
from models import (
    Restaurant,
    Category,
    MenuItem,
    Staff,
    Shift,
    Order,
    OrderItem,
    SaleTransaction,
    ComboSuggestion,
)


TARGET_TABLES = [
    "categories",
    "menu_items",
    "staff",
    "shifts",
    "orders",
    "order_items",
    "sale_transactions",
    "combo_suggestions",
]


def _default_restaurant_id(db: Session) -> int | None:
    first = db.query(Restaurant).order_by(Restaurant.id.asc()).first()
    return first.id if first else None


def _stats_line(stats: dict[str, int]) -> str:
    return " | ".join(f"{k}: {v}" for k, v in stats.items() if v > 0) or "no changes"


def run_maintenance(db: Session, apply: bool = False) -> dict[str, int]:
    stats: dict[str, int] = defaultdict(int)
    rid_default = _default_restaurant_id(db)

    # 1) Backfill missing restaurant_id on core tables (excluding restaurant_tables intentionally).
    if rid_default is not None:
        for model, label in (
            (Category, "categories_restaurant_id"),
            (MenuItem, "menu_items_restaurant_id"),
            (Staff, "staff_restaurant_id"),
            (Shift, "shifts_restaurant_id"),
            (Order, "orders_restaurant_id"),
            (ComboSuggestion, "combo_suggestions_restaurant_id"),
        ):
            rows = db.query(model).filter(model.restaurant_id.is_(None)).all()
            for row in rows:
                row.restaurant_id = rid_default
                stats[label] += 1

    # 2) Fix order_items line_total.
    items = db.query(OrderItem).all()
    for oi in items:
        qty = oi.quantity or 0
        unit_price = oi.unit_price or 0
        expected = float(qty * unit_price)
        if oi.line_total is None or abs((oi.line_total or 0) - expected) > 0.01:
            oi.line_total = expected
            stats["order_items_line_total"] += 1

    # 3) Recompute order total_amount from order_items.
    sums = (
        db.query(OrderItem.order_id, func.coalesce(func.sum(OrderItem.line_total), 0.0))
        .group_by(OrderItem.order_id)
        .all()
    )
    order_total_map = {order_id: float(total) for order_id, total in sums}
    orders = db.query(Order).all()
    for o in orders:
        expected_total = order_total_map.get(o.order_id, 0.0)
        if o.total_amount is None or abs((o.total_amount or 0.0) - expected_total) > 0.01:
            o.total_amount = expected_total
            stats["orders_total_amount"] += 1

    # 4) Ensure sale transaction prices and totals are valid.
    menu_price_map = {
        mid: float(price or 0.0)
        for mid, price in db.query(MenuItem.id, MenuItem.selling_price).all()
    }
    menu_rid_map = {
        mid: rid
        for mid, rid in db.query(MenuItem.id, MenuItem.restaurant_id).all()
    }

    sales = db.query(SaleTransaction).all()
    for s in sales:
        if (s.unit_price or 0) <= 0 and s.item_id in menu_price_map:
            s.unit_price = menu_price_map[s.item_id]
            stats["sale_unit_price"] += 1

        expected_total = float((s.quantity or 0) * (s.unit_price or 0))
        if s.total_price is None or abs((s.total_price or 0.0) - expected_total) > 0.01:
            s.total_price = expected_total
            stats["sale_total_price"] += 1

        if s.restaurant_id is None:
            s.restaurant_id = menu_rid_map.get(s.item_id) or rid_default
            if s.restaurant_id is not None:
                stats["sale_restaurant_id"] += 1

    # 5) Ensure order_number fallback exists.
    for o in orders:
        if not o.order_number:
            suffix = (o.order_id or "").split("-")[-1] or str(o.id)
            o.order_number = f"ORD-{suffix}"
            stats["orders_order_number"] += 1

    if apply:
        db.commit()
    else:
        db.rollback()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Update relevant DB data without touching restaurant_tables.")
    mode = parser.add_mutually_exclusive_group(required=False)
    mode.add_argument("--apply", action="store_true", help="Apply changes (commit).")
    mode.add_argument("--dry-run", action="store_true", help="Preview changes only (default).")
    args = parser.parse_args()

    apply = bool(args.apply)

    db = SessionLocal()
    try:
        stats = run_maintenance(db, apply=apply)
        print("Mode:", "APPLY" if apply else "DRY-RUN")
        print("Target tables:", ", ".join(TARGET_TABLES))
        print("Excluded table:", "restaurant_tables")
        print("Changes:", _stats_line(stats))
    finally:
        db.close()


if __name__ == "__main__":
    main()

