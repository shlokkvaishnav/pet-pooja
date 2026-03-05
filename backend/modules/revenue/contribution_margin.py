"""
contribution_margin.py — CM Calculation & Classification
=========================================================
Computes contribution margin (Selling Price − Food Cost),
margin percentage, and profitability tiers for every item.
"""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from models import MenuItem, SaleTransaction


def calculate_margins(db: Session) -> list[dict]:
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
    # Get items with revenue data — eagerly load category to avoid N+1
    items = (
        db.query(
            MenuItem,
            func.coalesce(func.sum(SaleTransaction.total_price), 0).label("total_revenue"),
        )
        .outerjoin(SaleTransaction, MenuItem.id == SaleTransaction.item_id)
        .options(joinedload(MenuItem.category))
        .filter(MenuItem.is_available == True)
        .group_by(MenuItem.id)
        .all()
    )

    results = []
    for item, total_revenue in items:
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

    # Sort by margin_pct descending
    results.sort(key=lambda x: x["margin_pct"], reverse=True)
    return results
