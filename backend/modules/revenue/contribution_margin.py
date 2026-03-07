"""
contribution_margin.py — CM Calculation & Classification
=========================================================
Computes contribution margin (Selling Price − Food Cost),
margin percentage, and profitability tiers for every item.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from models import MenuItem, VSale


def calculate_margins(db: Session, restaurant_id: int = None, days: int = 30) -> list[dict]:
    """
    Calculate contribution margin for all active menu items.

    Returns list of dicts:
    [
        {
            "item_id": 1,
            "name": "Paneer Tikka",
            "category": "Starters",
            "selling_price": 280,
            "food_cost": 85,
            "contribution_margin": 195,
            "margin_pct": 69.6,
            "margin_tier": "high",   # high (>65%) | medium (50-65%) | low (<50%)
            "total_revenue": 15400,
        }
    ]
    """
    # Get items + category (no aggregates here)
    q = (
        db.query(MenuItem)
        .options(joinedload(MenuItem.category))
        .filter(MenuItem.is_available == True)
    )
    if restaurant_id:
        q = q.filter(MenuItem.restaurant_id == restaurant_id)
    items = q.all()

    # Revenue per item (aggregate in separate query to avoid GROUP BY issues)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rev_q = (
        db.query(
            VSale.item_id,
            func.coalesce(func.sum(VSale.total_price), 0).label("total_revenue"),
        )
        .filter(VSale.sold_at >= cutoff)
    )
    if restaurant_id:
        rev_q = rev_q.filter(VSale.restaurant_id == restaurant_id)
    revenue_rows = rev_q.group_by(VSale.item_id).all()
    revenue_map = {r.item_id: float(r.total_revenue or 0) for r in revenue_rows}

    results = []
    for item in items:
        total_revenue = revenue_map.get(item.id, 0.0)
        cm = item.selling_price - item.food_cost
        margin_pct = (cm / item.selling_price * 100) if item.selling_price > 0 else 0

        # Classify margin tier
        if margin_pct >= 65:
            tier = "high"
        elif margin_pct >= 50:
            tier = "medium"
        else:
            tier = "low"

        results.append({
            "item_id": item.id,
            "name": item.name,
            "name_hi": item.name_hi,
            "category": item.category.name if item.category else "Uncategorized",
            "selling_price": item.selling_price,
            "food_cost": item.food_cost,
            "contribution_margin": round(cm, 2),
            "margin_pct": round(margin_pct, 1),
            "margin_tier": tier,
            "is_veg": item.is_veg,
            "total_revenue": round(total_revenue, 2),
        })

    # ML: profitability score (0–100) = margin quality + revenue rank
    sorted_revs = sorted(set(r["total_revenue"] for r in results), reverse=True)
    rev_rank = {v: i for i, v in enumerate(sorted_revs)}
    n = max(len(sorted_revs), 1)
    for r in results:
        margin_component = min(100, r["margin_pct"] * 1.2)  # 65% margin → 78 pts
        rank = rev_rank.get(r["total_revenue"], n)
        rev_pct = (n - rank) / n * 100
        revenue_component = rev_pct * 0.4  # weight revenue rank
        r["ml_profitability_score"] = round(margin_component * 0.6 + revenue_component, 1)
        r["ml_profit_tier"] = "high" if r["ml_profitability_score"] >= 70 else "medium" if r["ml_profitability_score"] >= 45 else "low"
        r["ml_confidence"] = round(min(0.99, 0.35 + 0.01 * (r["total_revenue"] or 0) ** 0.5), 2)

    # Sort by margin_pct descending
    results.sort(key=lambda x: x["margin_pct"], reverse=True)
    return results
