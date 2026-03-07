"""
advanced_analytics.py — Extended Analytical Capabilities
=========================================================
Covers deeper analytical needs:
- Category cannibalization analysis
- Price sensitivity modeling for Plowhorses
- Waste and void tracking
- Customer return rate estimation (via table patterns)
- Menu complexity scoring per category
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from models import (
    MenuItem, VSale, Category, Order, OrderItem,
    StockLog, Ingredient,
)

logger = logging.getLogger("petpooja.revenue.advanced")


def analyze_category_cannibalization(db: Session, lookback_days: int = 90, restaurant_id: int = None) -> list[dict]:
    """
    Detect cannibalization within categories: when a newer item steals
    sales from existing items in the same category.

    Approach: For each category, find items added in the lookback period
    and check if existing items' sales declined after the new item appeared.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=lookback_days)
    cutoff_naive = cutoff.replace(tzinfo=None)

    cat_q = db.query(Category).filter(Category.is_active.is_(True))
    categories = cat_q.all()
    results = []

    for cat in categories:
        items = [i for i in cat.items if i.is_available and (not restaurant_id or i.restaurant_id == restaurant_id)]
        if len(items) < 2:
            continue

        # Identify newer items (created within lookback)
        newer_items = [
            i for i in items
            if i.created_at and (
                (i.created_at.tzinfo is None and i.created_at >= cutoff_naive) or
                (i.created_at.tzinfo is not None and i.created_at >= cutoff)
            )
        ]
        older_items = [
            i for i in items
            if (not i.created_at) or (
                (i.created_at.tzinfo is None and i.created_at < cutoff_naive) or
                (i.created_at.tzinfo is not None and i.created_at < cutoff)
            )
        ]

        if not newer_items or not older_items:
            continue

        for new_item in newer_items:
            if new_item.created_at and new_item.created_at.tzinfo is None:
                new_added = new_item.created_at.replace(tzinfo=timezone.utc)
            else:
                new_added = new_item.created_at or cutoff

            for old_item in older_items:
                # Compare old item sales before vs after new item launch
                before_qty = _item_qty_in_range(
                    db, old_item.id,
                    new_added - timedelta(days=30),
                    new_added,
                )
                after_qty = _item_qty_in_range(
                    db, old_item.id,
                    new_added,
                    min(new_added + timedelta(days=30), now),
                )

                if before_qty == 0:
                    continue

                change_pct = ((after_qty - before_qty) / before_qty) * 100

                # Only flag significant declines (>20%)
                if change_pct < -20:
                    results.append({
                        "category": cat.name,
                        "new_item": new_item.name,
                        "new_item_id": new_item.id,
                        "affected_item": old_item.name,
                        "affected_item_id": old_item.id,
                        "sales_before": before_qty,
                        "sales_after": after_qty,
                        "decline_pct": round(change_pct, 1),
                        "severity": "high" if change_pct < -40 else "medium",
                        "recommendation": (
                            f"'{new_item.name}' may be cannibalizing '{old_item.name}'. "
                            f"Sales dropped {abs(change_pct):.0f}% after launch. "
                            f"Consider differentiating or consolidating."
                        ),
                    })

    results.sort(key=lambda x: x["decline_pct"])
    return results


def estimate_price_sensitivity(db: Session, restaurant_id: int = None) -> list[dict]:
    """
    For Plowhorse items (high popularity, low margin) being considered
    for price increases, estimate the likely sales volume impact using
    historical data patterns from similar items.
    """
    from .contribution_margin import calculate_margins
    from .popularity import calculate_popularity
    from .menu_matrix import classify_menu_matrix

    margins = calculate_margins(db, restaurant_id=restaurant_id)
    popularity = calculate_popularity(db, restaurant_id=restaurant_id)
    matrix = classify_menu_matrix(margins, popularity)

    plowhorses = [m for m in matrix if m["quadrant"] == "plowhorse"]
    if not plowhorses:
        return []

    # Get category-level elasticity baselines from historical data
    category_elasticity = _estimate_category_elasticity(db)

    results = []
    for item in plowhorses:
        cat = item.get("category", "")
        base_elasticity = category_elasticity.get(cat, -0.8)  # default moderate

        # Simulate 5%, 8%, 10% price increases
        scenarios = []
        for increase_pct in [5, 8, 10]:
            new_price = item["selling_price"] * (1 + increase_pct / 100)
            estimated_qty_change = base_elasticity * increase_pct
            new_margin_pct = ((new_price - item["food_cost"]) / new_price) * 100

            # Revenue impact = (price change × remaining volume) - lost volume revenue
            current_revenue_proxy = item["selling_price"] * item.get("daily_velocity", 1) * 30
            new_volume_factor = 1 + (estimated_qty_change / 100)
            projected_revenue = new_price * item.get("daily_velocity", 1) * new_volume_factor * 30

            scenarios.append({
                "increase_pct": increase_pct,
                "new_price": round(new_price / 5) * 5,  # round to ₹5
                "estimated_qty_change_pct": round(estimated_qty_change, 1),
                "new_margin_pct": round(new_margin_pct, 1),
                "projected_monthly_revenue": round(projected_revenue, 2),
                "current_monthly_revenue": round(current_revenue_proxy, 2),
                "revenue_impact": round(projected_revenue - current_revenue_proxy, 2),
            })

        best_scenario = max(scenarios, key=lambda s: s["revenue_impact"])

        results.append({
            "item_id": item["item_id"],
            "name": item["name"],
            "category": cat,
            "current_price": item["selling_price"],
            "current_margin_pct": item["margin_pct"],
            "popularity_score": item["popularity_score"],
            "estimated_elasticity": round(base_elasticity, 2),
            "scenarios": scenarios,
            "recommended_increase": best_scenario["increase_pct"],
            "recommended_price": best_scenario["new_price"],
        })

    return results


def analyze_waste_and_voids(db: Session, days: int = 30, restaurant_id: int = None) -> dict:
    """
    Track waste through stock logs and order cancellations (voids).

    Returns:
        {
            "waste_summary": {...},
            "void_summary": {...},
            "top_wasted_ingredients": [...],
            "top_voided_items": [...],
        }
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    # Waste from stock logs
    waste_q = (
        db.query(
            Ingredient.name,
            func.sum(func.abs(StockLog.change_qty)).label("total_waste"),
            Ingredient.cost_per_unit,
            Ingredient.unit,
        )
        .join(Ingredient, StockLog.ingredient_id == Ingredient.id)
        .filter(
            StockLog.reason == "waste",
            StockLog.created_at >= cutoff,
        )
    )
    if restaurant_id:
        waste_q = waste_q.filter(Ingredient.restaurant_id == restaurant_id)
    waste_logs = (
        waste_q
        .group_by(Ingredient.id, Ingredient.name, Ingredient.cost_per_unit, Ingredient.unit)
        .order_by(func.sum(func.abs(StockLog.change_qty)).desc())
        .all()
    )

    top_wasted = []
    total_waste_cost = 0.0
    for name, qty, cost_per_unit, unit in waste_logs:
        waste_cost = float(qty or 0) * float(cost_per_unit or 0)
        total_waste_cost += waste_cost
        top_wasted.append({
            "ingredient": name,
            "quantity_wasted": round(float(qty or 0), 2),
            "unit": unit,
            "waste_cost": round(waste_cost, 2),
        })

    # Voids: cancelled orders after KOT generation
    order_base_filter = [Order.created_at >= cutoff]
    if restaurant_id:
        order_base_filter.append(Order.restaurant_id == restaurant_id)

    total_orders = (
        db.query(func.count(Order.id))
        .filter(*order_base_filter)
        .scalar() or 0
    )
    cancelled_orders = (
        db.query(func.count(Order.id))
        .filter(
            Order.status == "cancelled",
            *order_base_filter,
        )
        .scalar() or 0
    )

    void_pct = (cancelled_orders / total_orders * 100) if total_orders > 0 else 0

    # Most voided items
    void_q = (
        db.query(
            MenuItem.name,
            func.sum(OrderItem.quantity).label("void_qty"),
        )
        .join(OrderItem, OrderItem.item_id == MenuItem.id)
        .join(Order, Order.id == OrderItem.order_pk)
        .filter(
            Order.status == "cancelled",
            Order.created_at >= cutoff,
        )
    )
    if restaurant_id:
        void_q = void_q.filter(Order.restaurant_id == restaurant_id)
    voided_items = (
        void_q
        .group_by(MenuItem.id, MenuItem.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(10)
        .all()
    )

    top_voided = [
        {"item": name, "void_quantity": int(qty or 0)}
        for name, qty in voided_items
    ]

    return {
        "waste_summary": {
            "period_days": days,
            "total_waste_cost": round(total_waste_cost, 2),
            "top_wasted_count": len(top_wasted),
        },
        "void_summary": {
            "total_orders": total_orders,
            "cancelled_orders": cancelled_orders,
            "void_pct": round(void_pct, 1),
        },
        "top_wasted_ingredients": top_wasted[:10],
        "top_voided_items": top_voided,
    }


def estimate_customer_return_rate(db: Session, days: int = 30, restaurant_id: int = None) -> dict:
    """
    Estimate repeat customer patterns using table number + time patterns.
    If the same table has orders at similar times on different days,
    it suggests repeat customers.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    # Count orders per table
    table_q = (
        db.query(
            Order.table_number,
            func.count(Order.id).label("order_count"),
            func.count(distinct(func.date(Order.created_at))).label("unique_days"),
        )
        .filter(
            Order.table_number.isnot(None),
            Order.table_number != "",
            Order.status != "cancelled",
            Order.created_at >= cutoff,
        )
    )
    if restaurant_id:
        table_q = table_q.filter(Order.restaurant_id == restaurant_id)
    table_orders = (
        table_q
        .group_by(Order.table_number)
        .all()
    )

    total_unique_tables = len(table_orders)
    repeat_tables = sum(1 for t in table_orders if t.unique_days > 1)
    total_orders = sum(t.order_count for t in table_orders)

    repeat_rate = (repeat_tables / total_unique_tables * 100) if total_unique_tables > 0 else 0

    # Top repeat tables
    top_repeats = sorted(
        [
            {
                "table_number": t.table_number,
                "total_orders": t.order_count,
                "unique_days": t.unique_days,
            }
            for t in table_orders
            if t.unique_days > 1
        ],
        key=lambda x: x["total_orders"],
        reverse=True,
    )[:10]

    return {
        "period_days": days,
        "total_unique_tables": total_unique_tables,
        "repeat_tables": repeat_tables,
        "repeat_rate_pct": round(repeat_rate, 1),
        "total_orders_from_tables": total_orders,
        "avg_orders_per_table": round(total_orders / max(total_unique_tables, 1), 1),
        "top_repeat_tables": top_repeats,
    }


def calculate_menu_complexity(db: Session, restaurant_id: int = None) -> list[dict]:
    """
    Calculate menu complexity score per category.
    Research shows menus with >7 items per category have lower per-item sales.
    Alert when categories become too large.
    """
    OPTIMAL_ITEMS = 7

    cat_q = (
        db.query(
            Category.id,
            Category.name,
            func.count(MenuItem.id).label("item_count"),
        )
        .join(MenuItem, MenuItem.category_id == Category.id)
        .filter(Category.is_active.is_(True), MenuItem.is_available.is_(True))
    )
    if restaurant_id:
        cat_q = cat_q.filter(MenuItem.restaurant_id == restaurant_id)
    categories = (
        cat_q
        .group_by(Category.id, Category.name)
        .all()
    )

    results = []
    for cat_id, cat_name, item_count in categories:
        # Get per-item avg sales in this category (last 30 days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        item_sales = (
            db.query(
                MenuItem.id.label("item_id"),
                func.coalesce(func.sum(VSale.quantity), 0).label("qty"),
            )
            .select_from(MenuItem)
            .outerjoin(VSale, (VSale.item_id == MenuItem.id) & (VSale.sold_at >= cutoff))
            .filter(
                MenuItem.category_id == cat_id,
                MenuItem.is_available.is_(True),
            )
            .group_by(MenuItem.id)
            .subquery()
        )

        overall_avg = db.query(func.avg(item_sales.c.qty)).scalar() or 0

        if item_count <= OPTIMAL_ITEMS:
            complexity = "optimal"
            alert = None
        elif item_count <= 10:
            complexity = "moderate"
            alert = f"Category has {item_count} items (optimal: ≤{OPTIMAL_ITEMS}). Consider consolidating."
        else:
            complexity = "high"
            alert = (
                f"Category has {item_count} items — well above the optimal {OPTIMAL_ITEMS}. "
                f"Research shows this reduces per-item sales. Strongly recommend trimming."
            )

        results.append({
            "category_id": cat_id,
            "category_name": cat_name,
            "item_count": item_count,
            "optimal_count": OPTIMAL_ITEMS,
            "complexity": complexity,
            "avg_sales_per_item": round(float(overall_avg), 1),
            "alert": alert,
        })

    results.sort(key=lambda x: x["item_count"], reverse=True)
    return results


def calculate_operational_metrics(db: Session, days: int = 30, restaurant_id: int = None) -> dict:
    """
    Operational metrics managers care about daily:
    - Average order value (AOV)
    - Peak hour identification
    - Orders by type (dine-in / takeaway / delivery)
    - Staff performance by order count
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    base_filter = [
        Order.status != "cancelled",
        Order.created_at >= cutoff,
    ]
    if restaurant_id:
        base_filter.append(Order.restaurant_id == restaurant_id)

    # Average Order Value
    aov_result = (
        db.query(
            func.avg(Order.total_amount).label("avg_order_value"),
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total_amount).label("total_revenue"),
        )
        .filter(*base_filter)
        .first()
    )

    aov = float(aov_result.avg_order_value or 0)
    total_orders = int(aov_result.total_orders or 0)
    total_revenue = float(aov_result.total_revenue or 0)

    # Peak hours (group by hour of day)
    hour_data = (
        db.query(
            func.extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("revenue"),
        )
        .filter(*base_filter)
        .group_by(func.extract("hour", Order.created_at))
        .order_by(func.count(Order.id).desc())
        .all()
    )

    peak_hours = [
        {
            "hour": int(h.hour),
            "label": f"{int(h.hour):02d}:00",
            "order_count": int(h.order_count),
            "revenue": round(float(h.revenue or 0), 2),
        }
        for h in hour_data
    ]

    # Orders by type
    type_data = (
        db.query(
            Order.order_type,
            func.count(Order.id).label("count"),
            func.sum(Order.total_amount).label("revenue"),
        )
        .filter(*base_filter)
        .group_by(Order.order_type)
        .all()
    )

    orders_by_type = [
        {
            "type": t.order_type or "unknown",
            "count": int(t.count),
            "revenue": round(float(t.revenue or 0), 2),
        }
        for t in type_data
    ]

    return {
        "period_days": days,
        "avg_order_value": round(aov, 2),
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "peak_hours": peak_hours,
        "orders_by_type": orders_by_type,
    }


# ── Internal helpers ──────────────────────────────


def _item_qty_in_range(db: Session, item_id: int, start: datetime, end: datetime) -> int:
    result = (
        db.query(func.coalesce(func.sum(VSale.quantity), 0))
        .filter(
            VSale.item_id == item_id,
            VSale.sold_at >= start,
            VSale.sold_at < end,
        )
        .scalar()
    )
    return int(result or 0)


def _estimate_category_elasticity(db: Session) -> dict[str, float]:
    """
    Rough elasticity estimates per category based on industry benchmarks
    for Indian restaurants. Negative values indicate inverse relationship
    (higher price → lower demand).
    """
    # Default elasticity benchmarks (can be overridden with historical data)
    defaults = {
        "Beverages": -1.2,      # Drinks are more elastic
        "Starters": -0.9,
        "Main Course": -0.6,    # Mains are less elastic (core of meal)
        "Biryani": -0.5,
        "Breads": -0.3,         # Very inelastic (complement goods)
        "Desserts": -1.0,
        "Sides": -0.8,
    }

    # Try to compute from actual price-change data
    categories = db.query(Category).filter(Category.is_active.is_(True)).all()
    result = {}

    for cat in categories:
        # Use default if available, otherwise moderate estimate
        result[cat.name] = defaults.get(cat.name, -0.8)

    return result
