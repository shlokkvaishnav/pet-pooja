"""
popularity.py — Sales Velocity & Popularity Scoring
=====================================================
Calculates how frequently each item is ordered,
daily velocity, and a normalized popularity score.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from models import MenuItem, VSale


def calculate_popularity(db: Session, days: int = 30, restaurant_id: int = None) -> list[dict]:
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
    # Aggregate sales per item — filtered to recent window
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    sq = db.query(
        VSale.item_id,
        func.sum(VSale.quantity).label("total_qty"),
        func.count(VSale.id).label("order_count"),
    ).filter(VSale.sold_at >= cutoff)
    if restaurant_id:
        sq = sq.filter(VSale.restaurant_id == restaurant_id)
    sales_data = sq.group_by(VSale.item_id).all()

    sales_map = {
        row.item_id: {
            "total_qty": row.total_qty or 0,
            "order_count": row.order_count or 0,
        }
        for row in sales_data
    }

    # ML: velocity trend — last 7d vs previous 7d (for "trending" signal)
    last_7d_start = now - timedelta(days=7)
    prev_7d_start = now - timedelta(days=14)
    sq_recent = db.query(
        VSale.item_id,
        func.sum(VSale.quantity).label("qty"),
    ).filter(VSale.sold_at >= last_7d_start)
    if restaurant_id:
        sq_recent = sq_recent.filter(VSale.restaurant_id == restaurant_id)
    recent_7d = {r.item_id: r.qty or 0 for r in sq_recent.group_by(VSale.item_id).all()}
    sq_prev = db.query(
        VSale.item_id,
        func.sum(VSale.quantity).label("qty"),
    ).filter(VSale.sold_at >= prev_7d_start, VSale.sold_at < last_7d_start)
    if restaurant_id:
        sq_prev = sq_prev.filter(VSale.restaurant_id == restaurant_id)
    prev_7d_map = {r.item_id: r.qty or 0 for r in sq_prev.group_by(VSale.item_id).all()}

    # Get all items — eagerly load category to avoid N+1
    iq = db.query(MenuItem).options(joinedload(MenuItem.category)).filter(MenuItem.is_available == True)
    if restaurant_id:
        iq = iq.filter(MenuItem.restaurant_id == restaurant_id)
    items = iq.all()

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

        # ML: velocity trend (last 7d vs previous 7d)
        qty_last_7 = recent_7d.get(item.id, 0)
        qty_prev_7 = prev_7d_map.get(item.id, 0) or 0.01
        velocity_trend_pct = round((qty_last_7 - qty_prev_7) / qty_prev_7 * 100, 1) if qty_prev_7 else 0
        # ML confidence: higher when more orders support the score (statistical confidence)
        ml_confidence = min(0.99, 0.4 + 0.5 * min(sales["order_count"] / max(days, 1) * 3, 1.0))
        ml_velocity_label = "trending_up" if velocity_trend_pct > 10 else "trending_down" if velocity_trend_pct < -10 else "stable"

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
            "ml_velocity_trend_pct": velocity_trend_pct,
            "ml_velocity_label": ml_velocity_label,
            "ml_confidence": round(ml_confidence, 2),
        })

    results.sort(key=lambda x: x["popularity_score"], reverse=True)
    return results
