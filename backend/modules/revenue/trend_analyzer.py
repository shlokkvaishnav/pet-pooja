"""
trend_analyzer.py — Time-Series Trend Analytics
=================================================
Adds the missing time dimension to revenue intelligence:
- 30/60/90 day metric comparisons per item
- Week-over-week and month-over-month revenue changes
- Trend arrows on BCG quadrant classifications
- Seasonal pattern detection
- Price elasticity estimation
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from models import MenuItem, SaleTransaction, Category

logger = logging.getLogger("petpooja.revenue.trends")


# ── Batch query helpers (avoid N+1) ──────────────


def _batch_item_revenue(db: Session, start: datetime, end: datetime) -> dict[int, float]:
    """Get total revenue per item_id in a date range — single query."""
    rows = (
        db.query(
            SaleTransaction.item_id,
            func.coalesce(func.sum(SaleTransaction.total_price), 0).label("rev"),
        )
        .filter(SaleTransaction.sold_at >= start, SaleTransaction.sold_at < end)
        .group_by(SaleTransaction.item_id)
        .all()
    )
    return {r.item_id: float(r.rev) for r in rows}


def _batch_item_qty(db: Session, start: datetime, end: datetime) -> dict[int, int]:
    """Get total qty per item_id in a date range — single query."""
    rows = (
        db.query(
            SaleTransaction.item_id,
            func.coalesce(func.sum(SaleTransaction.quantity), 0).label("qty"),
        )
        .filter(SaleTransaction.sold_at >= start, SaleTransaction.sold_at < end)
        .group_by(SaleTransaction.item_id)
        .all()
    )
    return {r.item_id: int(r.qty) for r in rows}


def _batch_items_revenue(db: Session, item_ids: list[int], start: datetime, end: datetime) -> dict[int, float]:
    """Get total revenue per item_id for a list of IDs — single query."""
    if not item_ids:
        return {}
    rows = (
        db.query(
            SaleTransaction.item_id,
            func.coalesce(func.sum(SaleTransaction.total_price), 0).label("rev"),
        )
        .filter(
            SaleTransaction.item_id.in_(item_ids),
            SaleTransaction.sold_at >= start,
            SaleTransaction.sold_at < end,
        )
        .group_by(SaleTransaction.item_id)
        .all()
    )
    return {r.item_id: float(r.rev) for r in rows}


def calculate_trends(db: Session) -> dict:
    """
    Calculate time-based trends for all menu items.

    Returns:
        {
            "item_trends": [...],         # per-item 30/60/90 day comparison
            "category_trends": [...],     # per-category revenue trends
            "seasonal_patterns": [...],   # items with detected seasonal spikes
            "quadrant_drift": [...],      # items whose BCG quadrant is shifting
        }
    """
    now = datetime.now(timezone.utc)

    item_trends = _calculate_item_trends(db, now)
    category_trends = _calculate_category_trends(db, now)
    seasonal = _detect_seasonal_patterns(db, now)
    drift = _detect_quadrant_drift(db, now)

    return {
        "item_trends": item_trends,
        "category_trends": category_trends,
        "seasonal_patterns": seasonal,
        "quadrant_drift": drift,
    }


def calculate_wow_mom(db: Session) -> list[dict]:
    """
    Calculate week-over-week and month-over-month revenue changes per item.
    Uses 4 batch queries instead of 4 × N individual queries.
    """
    now = datetime.now(timezone.utc)
    results = []

    items = (
        db.query(MenuItem)
        .options(joinedload(MenuItem.category))
        .filter(MenuItem.is_available.is_(True))
        .all()
    )

    # 4 batch queries
    rev_this_week = _batch_item_revenue(db, now - timedelta(days=7), now)
    rev_last_week = _batch_item_revenue(db, now - timedelta(days=14), now - timedelta(days=7))
    rev_this_month = _batch_item_revenue(db, now - timedelta(days=30), now)
    rev_last_month = _batch_item_revenue(db, now - timedelta(days=60), now - timedelta(days=30))

    for item in items:
        tw = rev_this_week.get(item.id, 0)
        lw = rev_last_week.get(item.id, 0)
        tm = rev_this_month.get(item.id, 0)
        lm = rev_last_month.get(item.id, 0)

        wow_change = _pct_change(lw, tw)
        mom_change = _pct_change(lm, tm)

        results.append({
            "item_id": item.id,
            "name": item.name,
            "category": item.category.name if item.category else "Uncategorized",
            "this_week_revenue": round(tw, 2),
            "last_week_revenue": round(lw, 2),
            "wow_change_pct": wow_change,
            "wow_arrow": _trend_arrow(wow_change),
            "this_month_revenue": round(tm, 2),
            "last_month_revenue": round(lm, 2),
            "mom_change_pct": mom_change,
            "mom_arrow": _trend_arrow(mom_change),
        })

    results.sort(key=lambda x: abs(x["wow_change_pct"]), reverse=True)
    return results


def estimate_price_elasticity(db: Session) -> list[dict]:
    """
    Estimate price elasticity by comparing periods where an item's
    effective price changed (different unit_price values in SaleTransaction).

    Returns items where a price change was detected along with
    estimated elasticity coefficient.
    """
    now = datetime.now(timezone.utc)
    results = []

    items = (
        db.query(MenuItem)
        .options(joinedload(MenuItem.category))
        .filter(MenuItem.is_available.is_(True))
        .all()
    )

    for item in items:
        # Get distinct price periods
        price_periods = (
            db.query(
                SaleTransaction.unit_price,
                func.min(SaleTransaction.sold_at).label("first_sold"),
                func.max(SaleTransaction.sold_at).label("last_sold"),
                func.sum(SaleTransaction.quantity).label("total_qty"),
                func.count(SaleTransaction.id).label("txn_count"),
            )
            .filter(
                SaleTransaction.item_id == item.id,
                SaleTransaction.sold_at >= now - timedelta(days=180),
            )
            .group_by(SaleTransaction.unit_price)
            .order_by(func.min(SaleTransaction.sold_at))
            .all()
        )

        if len(price_periods) < 2:
            continue

        # Compare last two price levels
        old_period = price_periods[-2]
        new_period = price_periods[-1]

        old_price = old_period.unit_price
        new_price = new_period.unit_price

        if old_price == new_price or old_price == 0:
            continue

        # Calculate days in each period for daily rate
        old_days = max((old_period.last_sold - old_period.first_sold).days, 1)
        new_days = max((new_period.last_sold - new_period.first_sold).days, 1)

        old_daily_qty = old_period.total_qty / old_days
        new_daily_qty = new_period.total_qty / new_days

        if old_daily_qty == 0:
            continue

        price_change_pct = ((new_price - old_price) / old_price) * 100
        qty_change_pct = ((new_daily_qty - old_daily_qty) / old_daily_qty) * 100

        # Elasticity = % change in quantity / % change in price
        elasticity = qty_change_pct / price_change_pct if price_change_pct != 0 else 0

        sensitivity = "inelastic"
        if abs(elasticity) > 1.5:
            sensitivity = "highly elastic"
        elif abs(elasticity) > 1.0:
            sensitivity = "elastic"
        elif abs(elasticity) > 0.5:
            sensitivity = "moderately elastic"

        results.append({
            "item_id": item.id,
            "name": item.name,
            "category": item.category.name if item.category else "Uncategorized",
            "old_price": old_price,
            "new_price": new_price,
            "price_change_pct": round(price_change_pct, 1),
            "old_daily_qty": round(old_daily_qty, 2),
            "new_daily_qty": round(new_daily_qty, 2),
            "qty_change_pct": round(qty_change_pct, 1),
            "elasticity": round(elasticity, 3),
            "sensitivity": sensitivity,
        })

    results.sort(key=lambda x: abs(x["elasticity"]), reverse=True)
    return results


# ── Internal helpers ──────────────────────────────


def _calculate_item_trends(db: Session, now: datetime) -> list[dict]:
    """30/60/90 day comparison per item — uses batch queries (6 total, not 6×N)."""
    items = (
        db.query(MenuItem)
        .options(joinedload(MenuItem.category))
        .filter(MenuItem.is_available.is_(True))
        .all()
    )

    # 6 batch queries instead of 6 × len(items)
    rev_30 = _batch_item_revenue(db, now - timedelta(days=30), now)
    rev_60 = _batch_item_revenue(db, now - timedelta(days=60), now - timedelta(days=30))
    rev_90 = _batch_item_revenue(db, now - timedelta(days=90), now - timedelta(days=60))
    qty_30 = _batch_item_qty(db, now - timedelta(days=30), now)
    qty_60 = _batch_item_qty(db, now - timedelta(days=60), now - timedelta(days=30))
    qty_90 = _batch_item_qty(db, now - timedelta(days=90), now - timedelta(days=60))

    results = []
    for item in items:
        r30 = rev_30.get(item.id, 0)
        r60 = rev_60.get(item.id, 0)
        r90 = rev_90.get(item.id, 0)
        q30 = qty_30.get(item.id, 0)
        q60 = qty_60.get(item.id, 0)
        q90 = qty_90.get(item.id, 0)

        rev_trend_30v60 = _pct_change(r60, r30)
        pop_trend_30v60 = _pct_change(q60, q30)

        if rev_trend_30v60 > 10:
            direction = "improving"
        elif rev_trend_30v60 < -10:
            direction = "declining"
        else:
            direction = "stable"

        results.append({
            "item_id": item.id,
            "name": item.name,
            "name_hi": item.name_hi,
            "category": item.category.name if item.category else "Uncategorized",
            "revenue_last_30d": round(r30, 2),
            "revenue_prev_30d": round(r60, 2),
            "revenue_oldest_30d": round(r90, 2),
            "revenue_trend_pct": rev_trend_30v60,
            "revenue_trend_arrow": _trend_arrow(rev_trend_30v60),
            "qty_last_30d": q30,
            "qty_prev_30d": q60,
            "qty_oldest_30d": q90,
            "popularity_trend_pct": pop_trend_30v60,
            "popularity_trend_arrow": _trend_arrow(pop_trend_30v60),
            "direction": direction,
        })

    results.sort(key=lambda x: x["revenue_trend_pct"], reverse=True)
    return results


def _calculate_category_trends(db: Session, now: datetime) -> list[dict]:
    """Per-category revenue trend over 30-day windows — 2 batch queries."""
    # Batch: all item revenue in each 30-day window
    rev_30_all = _batch_item_revenue(db, now - timedelta(days=30), now)
    rev_60_all = _batch_item_revenue(db, now - timedelta(days=60), now - timedelta(days=30))

    categories = db.query(Category).filter(Category.is_active.is_(True)).all()
    results = []

    for cat in categories:
        item_ids = {i.id for i in cat.items if i.is_available}
        if not item_ids:
            continue

        rev_30 = sum(rev_30_all.get(iid, 0) for iid in item_ids)
        rev_60 = sum(rev_60_all.get(iid, 0) for iid in item_ids)

        trend = _pct_change(rev_60, rev_30)

        results.append({
            "category_id": cat.id,
            "category_name": cat.name,
            "revenue_last_30d": round(rev_30, 2),
            "revenue_prev_30d": round(rev_60, 2),
            "trend_pct": trend,
            "trend_arrow": _trend_arrow(trend),
        })

    results.sort(key=lambda x: x["trend_pct"], reverse=True)
    return results


def _detect_seasonal_patterns(db: Session, now: datetime) -> list[dict]:
    """
    Detect items with monthly sales variance > 50% of their mean,
    indicating seasonal demand patterns.
    Uses 6 batch queries instead of 6 × N.
    """
    items = (
        db.query(MenuItem)
        .options(joinedload(MenuItem.category))
        .filter(MenuItem.is_available.is_(True))
        .all()
    )

    # 6 batch queries for 6 months
    monthly_batches = []
    for i in range(6):
        start = now - timedelta(days=30 * (i + 1))
        end = now - timedelta(days=30 * i)
        monthly_batches.append(_batch_item_qty(db, start, end))

    results = []
    for item in items:
        monthly_sales = [batch.get(item.id, 0) for batch in monthly_batches]

        if not any(monthly_sales):
            continue

        mean_sales = sum(monthly_sales) / len(monthly_sales)
        if mean_sales == 0:
            continue

        variance = sum((s - mean_sales) ** 2 for s in monthly_sales) / len(monthly_sales)
        std_dev = variance ** 0.5
        cv = std_dev / mean_sales

        if cv > 0.5:
            peak_month_idx = monthly_sales.index(max(monthly_sales))
            peak_month = (now - timedelta(days=30 * peak_month_idx)).strftime("%B")

            results.append({
                "item_id": item.id,
                "name": item.name,
                "category": item.category.name if item.category else "Uncategorized",
                "monthly_sales": list(reversed(monthly_sales)),
                "mean_monthly_sales": round(mean_sales, 1),
                "coefficient_of_variation": round(cv, 2),
                "peak_month": peak_month,
                "seasonal_flag": True,
            })

    results.sort(key=lambda x: x["coefficient_of_variation"], reverse=True)
    return results


def _detect_quadrant_drift(db: Session, now: datetime) -> list[dict]:
    """
    Detect items whose BCG quadrant position is shifting.
    Uses batch queries (4 total) instead of 4 × N.
    """
    from .contribution_margin import calculate_margins
    from .popularity import calculate_popularity
    from .menu_matrix import classify_menu_matrix

    margins = calculate_margins(db)
    popularity = calculate_popularity(db)
    current_matrix = classify_menu_matrix(margins, popularity)
    current_map = {m["item_id"]: m for m in current_matrix}

    items = db.query(MenuItem).filter(MenuItem.is_available.is_(True)).all()

    # 4 batch queries
    qty_recent = _batch_item_qty(db, now - timedelta(days=30), now)
    qty_prev = _batch_item_qty(db, now - timedelta(days=60), now - timedelta(days=30))
    rev_recent = _batch_item_revenue(db, now - timedelta(days=30), now)
    rev_prev = _batch_item_revenue(db, now - timedelta(days=60), now - timedelta(days=30))

    results = []
    for item in items:
        current = current_map.get(item.id)
        if not current:
            continue

        pop_trend = _pct_change(qty_prev.get(item.id, 0), qty_recent.get(item.id, 0))
        rev_trend = _pct_change(rev_prev.get(item.id, 0), rev_recent.get(item.id, 0))

        quadrant = current["quadrant"]
        drift = None
        drift_warning = None

        if quadrant == "star":
            if pop_trend < -15:
                drift = "star → puzzle"
                drift_warning = "Star losing popularity — risk of becoming a Puzzle"
            elif rev_trend < -15 and pop_trend >= 0:
                drift = "star → plowhorse"
                drift_warning = "Star's margin declining — drifting toward Plowhorse"
        elif quadrant == "plowhorse":
            if pop_trend < -20:
                drift = "plowhorse → dog"
                drift_warning = "Plowhorse losing popularity — becoming a Dog"
            elif rev_trend > 15:
                drift = "plowhorse → star"
                drift_warning = "Plowhorse margins improving — potential Star"
        elif quadrant == "puzzle":
            if pop_trend > 20:
                drift = "puzzle → star"
                drift_warning = "Puzzle gaining popularity — emerging Star"
            elif rev_trend < -15:
                drift = "puzzle → dog"
                drift_warning = "Puzzle's margin declining — risk of becoming Dog"
        elif quadrant == "dog":
            if pop_trend > 25 or rev_trend > 25:
                drift = "dog → recovering"
                drift_warning = "Dog showing improvement — worth monitoring"

        if drift:
            results.append({
                "item_id": item.id,
                "name": current["name"],
                "category": current["category"],
                "current_quadrant": quadrant,
                "drift_direction": drift,
                "drift_warning": drift_warning,
                "popularity_trend_pct": pop_trend,
                "revenue_trend_pct": rev_trend,
                "trend_arrow": _trend_arrow(pop_trend),
            })

    results.sort(key=lambda x: abs(x["popularity_trend_pct"]), reverse=True)
    return results


# ── Query helpers ─────────────────────────────────


def _item_revenue_in_range(db: Session, item_id: int, start: datetime, end: datetime) -> float:
    result = (
        db.query(func.coalesce(func.sum(SaleTransaction.total_price), 0))
        .filter(
            SaleTransaction.item_id == item_id,
            SaleTransaction.sold_at >= start,
            SaleTransaction.sold_at < end,
        )
        .scalar()
    )
    return float(result or 0)


def _item_qty_in_range(db: Session, item_id: int, start: datetime, end: datetime) -> int:
    result = (
        db.query(func.coalesce(func.sum(SaleTransaction.quantity), 0))
        .filter(
            SaleTransaction.item_id == item_id,
            SaleTransaction.sold_at >= start,
            SaleTransaction.sold_at < end,
        )
        .scalar()
    )
    return int(result or 0)


def _items_revenue_in_range(db: Session, item_ids: list[int], start: datetime, end: datetime) -> float:
    if not item_ids:
        return 0.0
    result = (
        db.query(func.coalesce(func.sum(SaleTransaction.total_price), 0))
        .filter(
            SaleTransaction.item_id.in_(item_ids),
            SaleTransaction.sold_at >= start,
            SaleTransaction.sold_at < end,
        )
        .scalar()
    )
    return float(result or 0)


def _pct_change(old_val: float, new_val: float) -> float:
    if old_val == 0:
        return 100.0 if new_val > 0 else 0.0
    return round(((new_val - old_val) / old_val) * 100, 1)


def _trend_arrow(pct_change: float) -> str:
    if pct_change > 10:
        return "↑↑"
    elif pct_change > 3:
        return "↑"
    elif pct_change < -10:
        return "↓↓"
    elif pct_change < -3:
        return "↓"
    return "→"
