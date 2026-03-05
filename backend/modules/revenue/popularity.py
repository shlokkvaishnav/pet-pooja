"""
popularity.py — Sales Velocity & Popularity Scoring
=====================================================
Calculates how frequently each item is ordered,
daily velocity, and a normalized popularity score.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import MenuItem, SaleTransaction


def calculate_popularity(db: Session, days: int = 30) -> list[dict]:
    """
    Calculate popularity metrics for all menu items
    based on recent sales data.

    Returns list of dicts:
    [
        {
            "item_id": 1,
            "name": "Paneer Tikka",
            "total_qty_sold": 145,
            "order_count": 120,
            "daily_velocity": 4.83,
            "popularity_score": 0.82,  # normalized 0–1
            "popularity_tier": "high",
        }
    ]
    """
    # Aggregate sales per item
    sales_data = (
        db.query(
            SaleTransaction.item_id,
            func.sum(SaleTransaction.quantity).label("total_qty"),
            func.count(SaleTransaction.id).label("order_count"),
        )
        .group_by(SaleTransaction.item_id)
        .all()
    )

    sales_map = {
        row.item_id: {
            "total_qty": row.total_qty or 0,
            "order_count": row.order_count or 0,
        }
        for row in sales_data
    }

    # Get all items
    items = db.query(MenuItem).filter(MenuItem.is_available == True).all()

    results = []

    # Robust normalization: use mean × 2 instead of max to handle
    # co-occurrence outliers (e.g., Butter Naan appearing in 70% of orders).
    # In menu engineering, "high popularity" means "above average", not
    # "close to the single most popular item".
    all_qtys = [s["total_qty"] for s in sales_map.values() if s["total_qty"] > 0]
    if all_qtys:
        mean_qty = sum(all_qtys) / len(all_qtys)
        norm_qty = max(mean_qty * 2, 1)  # 2× mean as ceiling
    else:
        norm_qty = 1

    for item in items:
        sales = sales_map.get(item.id, {"total_qty": 0, "order_count": 0})
        daily_velocity = sales["total_qty"] / max(days, 1)
        pop_score = min(sales["total_qty"] / norm_qty, 1.0)  # cap at 1.0

        # Tier classification
        if pop_score >= 0.6:
            tier = "high"
        elif pop_score >= 0.3:
            tier = "medium"
        else:
            tier = "low"

        results.append({
            "item_id": item.id,
            "name": item.name,
            "name_hi": item.name_hi,
            "category": item.category.name if item.category else "Uncategorized",
            "total_qty_sold": sales["total_qty"],
            "order_count": sales["order_count"],
            "daily_velocity": round(daily_velocity, 2),
            "popularity_score": round(pop_score, 3),
            "popularity_tier": tier,
        })

    results.sort(key=lambda x: x["popularity_score"], reverse=True)
    return results
