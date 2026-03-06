"""
routes_revenue.py — Revenue Intelligence API Endpoints
========================================================
/api/revenue/* — Dashboard, menu matrix, hidden stars, risks,
combos, price recommendations, category breakdown, trends,
advanced analytics
"""

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import MenuItem, VSale, Category, RestaurantSettings
from config import get_default_settings, REVENUE_CACHE_TTL_SEC, REVENUE_CACHE_MAX_SIZE
from modules.revenue.analyzer import run_full_analysis
from modules.revenue.analyzer import _calculate_health_score
from modules.revenue.contribution_margin import calculate_margins
from modules.revenue.popularity import calculate_popularity
from modules.revenue.menu_matrix import classify_menu_matrix, get_quadrant_summary
from modules.revenue.hidden_stars import detect_hidden_stars
from modules.revenue.combo_engine import generate_combos, fetch_combos_from_db, run_combo_training_background
from modules.revenue.price_optimizer import generate_price_recommendations
from modules.revenue.trend_analyzer import (
    calculate_trends,
    calculate_wow_mom,
    estimate_price_elasticity,
)
from modules.revenue.advanced_analytics import (
    analyze_category_cannibalization,
    estimate_price_sensitivity,
    analyze_waste_and_voids,
    estimate_customer_return_rate,
    calculate_menu_complexity,
    calculate_operational_metrics,
)

router = APIRouter()
logger = logging.getLogger("petpooja.api.revenue")

# ── Default thresholds from config (fallback if no settings) ──
def _default_thresholds():
    return get_default_settings()["display_thresholds"]


def _get_thresholds(db: Session, restaurant_id: int | None) -> dict:
    """Load display_thresholds from the restaurant settings, falling back to defaults."""
    base = _default_thresholds()
    if restaurant_id:
        row = db.query(RestaurantSettings).filter(
            RestaurantSettings.restaurant_id == restaurant_id
        ).first()
        if row and row.display_thresholds:
            return {**base, **row.display_thresholds}
    return base

# ── Thread-safe cache for expensive computations ──
_cache_lock = threading.Lock()
_cache: dict = {}
_CACHE_TTL = REVENUE_CACHE_TTL_SEC
_CACHE_MAX_SIZE = REVENUE_CACHE_MAX_SIZE


def _get_cached(key: str):
    """Return cached value if still valid, else None."""
    with _cache_lock:
        entry = _cache.get(key)
    if entry and time.time() - entry["ts"] < _CACHE_TTL:
        return entry["data"]
    return None


def _set_cached(key: str, data):
    """Store data in cache with timestamp. Evicts oldest entries if cache is full."""
    with _cache_lock:
        if len(_cache) >= _CACHE_MAX_SIZE:
            oldest_key = min(_cache, key=lambda k: _cache[k]["ts"])
            del _cache[oldest_key]
        _cache[key] = {"data": data, "ts": time.time()}


def _get_or_compute(key: str, compute_fn: Callable[[], Any]):
    """
    Return cached value when available; otherwise compute and cache.
    If compute fails but a stale value exists, return stale data.
    """
    cached = _get_cached(key)
    if cached is not None:
        return cached

    try:
        value = compute_fn()
        _set_cached(key, value)
        return value
    except Exception:
        with _cache_lock:
            stale = _cache.get(key)
        if stale:
            logger.warning("Serving stale cached value for key=%s", key)
            return stale["data"]
        raise


def _get_margins_popularity(db: Session, restaurant_id: int = None) -> tuple[list[dict], list[dict]]:
    """Return margins and popularity, reusing cached values if available."""
    suffix = f"_{restaurant_id}" if restaurant_id else ""
    margins = _get_cached(f"_margins{suffix}")
    popularity = _get_cached(f"_popularity{suffix}")
    if margins is None:
        margins = calculate_margins(db, restaurant_id=restaurant_id)
        _set_cached(f"_margins{suffix}", margins)
    if popularity is None:
        popularity = calculate_popularity(db, restaurant_id=restaurant_id)
        _set_cached(f"_popularity{suffix}", popularity)
    return margins, popularity


@router.get("/dashboard")
def get_dashboard(restaurant_id: int = Query(None), db: Session = Depends(get_db)):
    """
    GET /api/revenue/dashboard?restaurant_id=1
    Returns: total_revenue, avg_cm_percent, items_at_risk_count, uplift_potential,
             health_score with breakdown, operational metrics
    """
    try:
        cache_key = f"dashboard_{restaurant_id}" if restaurant_id else "dashboard"
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

        # Only compute what the dashboard needs (skip combos & trends for speed)
        margins, popularity = _get_margins_popularity(db, restaurant_id=restaurant_id)
        matrix = classify_menu_matrix(margins, popularity)
        hidden_stars_list = detect_hidden_stars(margins, popularity)
        thresholds = _get_thresholds(db, restaurant_id)

        total_items = len(margins)
        avg_margin = (
            sum(m["margin_pct"] for m in margins) / total_items
            if total_items > 0
            else 0
        )

        cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)
        rev_q = db.query(func.sum(VSale.total_price)).filter(VSale.sold_at >= cutoff_30d)
        if restaurant_id:
            rev_q = rev_q.filter(VSale.restaurant_id == restaurant_id)
        total_revenue = rev_q.scalar() or 0.0

        items_at_risk = sum(
            1 for m in matrix
            if m.get("quadrant") == "dog" or (
                m.get("margin_pct", 100) < thresholds["risk_margin_max"]
                and m.get("popularity_score", 0) > thresholds["risk_popularity_min"]
            )
        )

        uplift = sum(h.get("estimated_monthly_uplift", 0) for h in hidden_stars_list)

        stars_count = sum(1 for m in matrix if m["quadrant"] == "star")
        plowhorses_count = sum(1 for m in matrix if m["quadrant"] == "plowhorse")
        puzzles_count = sum(1 for m in matrix if m["quadrant"] == "puzzle")
        dogs_count = sum(1 for m in matrix if m["quadrant"] == "dog")
        health_score_breakdown = _calculate_health_score(
            avg_margin, stars_count, dogs_count, total_items, hidden_stars_list
        )

        # Operational metrics
        ops = calculate_operational_metrics(db, restaurant_id=restaurant_id)

        result = {
            "total_revenue": round(total_revenue, 2),
            "avg_cm_percent": round(avg_margin, 1),
            "items_at_risk_count": items_at_risk,
            "uplift_potential": round(uplift, 2),
            "health_score": health_score_breakdown["score"],
            "health_score_breakdown": health_score_breakdown,
            "total_items": total_items,
            "stars_count": stars_count,
            "plowhorses_count": plowhorses_count,
            "puzzles_count": puzzles_count,
            "dogs_count": dogs_count,
            "hidden_stars_count": len(hidden_stars_list),
            # Operational metrics
            "avg_order_value": ops.get("avg_order_value", 0),
            "total_orders": ops.get("total_orders", 0),
            "peak_hours": ops.get("peak_hours", [])[:5],
            "orders_by_type": ops.get("orders_by_type", []),
        }

        _set_cached(cache_key, result)
        return result
    except Exception as e:
        logger.exception("Error computing dashboard")
        raise HTTPException(status_code=500, detail=f"Dashboard computation failed: {e}")


@router.get("/menu-matrix")
def get_menu_matrix(restaurant_id: int = Query(None), db: Session = Depends(get_db)):
    """
    GET /api/revenue/menu-matrix?restaurant_id=1
    Returns: all items with quadrant, cm_percent, popularity_score
    Used by frontend scatter chart.
    """
    try:
        cache_key = f"menu_matrix_{restaurant_id}" if restaurant_id else "menu_matrix"
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

        margins, popularity = _get_margins_popularity(db, restaurant_id=restaurant_id)
        matrix = classify_menu_matrix(margins, popularity)
        summary = get_quadrant_summary(matrix)
        result = {"items": matrix, "summary": summary}

        _set_cached(cache_key, result)
        return result
    except Exception as e:
        logger.exception("Error computing menu matrix")
        raise HTTPException(status_code=500, detail=f"Menu matrix failed: {e}")


@router.get("/hidden-stars")
def get_hidden_stars(
    restaurant_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """
    GET /api/revenue/hidden-stars
    Returns: hidden star items with estimated_monthly_uplift, recommendation
    """
    try:
        cache_key = f"hidden_stars_{restaurant_id}" if restaurant_id else "hidden_stars"
        return _get_or_compute(
            cache_key,
            lambda: {"items": detect_hidden_stars(*_get_margins_popularity(db, restaurant_id=restaurant_id))},
        )
    except Exception as e:
        logger.exception("Error detecting hidden stars")
        raise HTTPException(status_code=500, detail=f"Hidden stars detection failed: {e}")


@router.get("/risks")
def get_risk_items(
    restaurant_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """
    GET /api/revenue/risks
    Returns: risk items with risk_score, volume, cm_percent
    Risk = high sales volume + low contribution margin
    """
    try:
        cache_key = f"risk_items_{restaurant_id}" if restaurant_id else "risk_items"

        def _compute():
            margins, popularity = _get_margins_popularity(db, restaurant_id=restaurant_id)
            matrix = classify_menu_matrix(margins, popularity)
            thresholds = _get_thresholds(db, restaurant_id)
            margin_max = thresholds["risk_margin_max"]
            pop_min = thresholds["risk_popularity_min"]

            risk_items = []
            for item in matrix:
                cm = item.get("margin_pct", 100)
                pop = item.get("popularity_score", 0)

                if cm < margin_max and pop > pop_min:
                    risk_score = round((100 - cm) * pop, 1)
                    risk_items.append({
                        **item,
                        "risk_score": risk_score,
                        "risk_level": "high" if risk_score > 60 else "medium",
                        "recommendation": (
                            f"High volume but only {cm:.0f}% margin. "
                            f"Consider raising price or reducing food cost."
                        ),
                    })

            risk_items.sort(key=lambda x: x["risk_score"], reverse=True)
            return {"items": risk_items, "count": len(risk_items)}

        return _get_or_compute(cache_key, _compute)
    except Exception as e:
        logger.exception("Error computing risk items")
        raise HTTPException(status_code=500, detail=f"Risk analysis failed: {e}")


@router.get("/combos")
def get_combo_suggestions(
    force_retrain: bool = Query(False),
    discount_pct: float = Query(10.0, ge=1.0, le=30.0),
    restaurant_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """
    GET /api/revenue/combos
    Returns: top 20 combos.
    If DB is empty or force_retrain=True, runs the correlation pipeline
    SYNCHRONOUSLY so the response always contains combos.
    """
    try:
        combos = fetch_combos_from_db(db, restaurant_id=restaurant_id)

        # If empty or force retrain, run pipeline inline (synchronous)
        if force_retrain or len(combos) == 0:
            logger.info("Running combo pipeline inline (force=%s, existing=%d)", force_retrain, len(combos))
            generate_combos(db, restaurant_id=restaurant_id, force_retrain=True)
            combos = fetch_combos_from_db(db, restaurant_id=restaurant_id)

        return {"combos": combos}
    except Exception as e:
        logger.exception("Error fetching combos")
        raise HTTPException(status_code=500, detail=f"Combo fetch failed: {e}")


@router.post("/combos/retrain")
def retrain_combos(
    db: Session = Depends(get_db),
    discount_pct: float = Query(10.0, ge=1.0, le=30.0, description="Target discount percentage"),
):
    """
    POST /api/revenue/combos/retrain
    Trigger an immediate combo retraining in a background thread.
    Returns immediately — results appear in GET /combos once training completes.
    """
    try:
        from database import SessionLocal
        run_combo_training_background(SessionLocal)
        return {"status": "training_started", "message": "Combo retraining started in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Combo retrain failed: {e}")


@router.post("/combos/{combo_id}/promote")
def promote_combo(
    combo_id: int,
    db: Session = Depends(get_db),
):
    """
    POST /api/revenue/combos/{combo_id}/promote
    Converts an AI suggestion into a real MenuItem in the exact database.
    Single transaction: category (if created) + menu item committed together.
    """
    from models import ComboSuggestion, Category
    from sqlalchemy.exc import IntegrityError, SQLAlchemyError

    try:
        combo = db.query(ComboSuggestion).filter(ComboSuggestion.id == combo_id).first()
        if not combo:
            raise HTTPException(status_code=404, detail="Combo suggestion not found")

        combo_cat = db.query(Category).filter(
            Category.restaurant_id == combo.restaurant_id,
            func.lower(Category.name) == "combos"
        ).first()

        if not combo_cat:
            combo_cat = Category(
                restaurant_id=combo.restaurant_id,
                name="Combos",
                is_active=True
            )
            db.add(combo_cat)
            db.flush()

        food_cost = max(0.0, (combo.combo_price or 0) - (combo.expected_margin or 0))

        existing = db.query(MenuItem).filter(
            MenuItem.restaurant_id == combo.restaurant_id,
            MenuItem.name == combo.name
        ).first()

        if existing:
            return {"status": "already_promoted", "menu_item_id": existing.id}

        new_item = MenuItem(
            restaurant_id=combo.restaurant_id,
            name=combo.name,
            category_id=combo_cat.id,
            selling_price=combo.combo_price or 0,
            food_cost=food_cost,
            description=f"AI Optimized Combo: {', '.join(combo.item_names or [])}",
            is_veg=True,
            is_available=True,
            tags=["ai-combo", "promoted"]
        )
        db.add(new_item)
        db.flush()
        db.commit()
        db.refresh(new_item)

        return {"status": "success", "menu_item_id": new_item.id}
    except HTTPException:
        raise
    except (IntegrityError, SQLAlchemyError) as e:
        db.rollback()
        logger.exception("Error promoting combo (DB)")
        raise HTTPException(status_code=500, detail="Failed to promote combo. Check server logs.")
    except Exception as e:
        db.rollback()
        logger.exception("Error promoting combo")
        raise HTTPException(status_code=500, detail="Failed to promote combo. Check server logs.")


@router.get("/price-recommendations")
def get_price_recommendations(
    restaurant_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """
    GET /api/revenue/price-recommendations
    Returns: items with current_price, recommended_price, reason
    """
    try:
        cache_key = f"price_recommendations_{restaurant_id}" if restaurant_id else "price_recommendations"
        return _get_or_compute(
            cache_key,
            lambda: {"recommendations": generate_price_recommendations(*_get_margins_popularity(db, restaurant_id=restaurant_id))},
        )
    except Exception as e:
        logger.exception("Error generating price recommendations")
        raise HTTPException(status_code=500, detail=f"Price recommendation failed: {e}")


@router.get("/category-breakdown")
def get_category_breakdown(
    restaurant_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """
    GET /api/revenue/category-breakdown
    Returns: per-category stats (item_count, avg_cm_pct, total_revenue)
    """
    try:
        cache_key = f"category_breakdown_{restaurant_id}" if restaurant_id else "category_breakdown"

        def _compute():
            # Single query: aggregate revenue and units per category
            cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)
            q = (
                db.query(
                    Category.id,
                    Category.name,
                    Category.name_hi,
                    func.count(func.distinct(MenuItem.id)).label("item_count"),
                    func.coalesce(func.sum(VSale.total_price), 0).label("total_revenue"),
                    func.coalesce(func.sum(VSale.quantity), 0).label("total_units"),
                    func.avg(MenuItem.selling_price - MenuItem.food_cost).label("avg_cm"),
                    func.avg(MenuItem.selling_price).label("avg_price"),
                )
                .join(MenuItem, MenuItem.category_id == Category.id)
                .outerjoin(VSale, (VSale.item_id == MenuItem.id) & (VSale.sold_at >= cutoff_30d))
                .filter(Category.is_active == True, MenuItem.is_available == True)
            )
            if restaurant_id:
                q = q.filter(MenuItem.restaurant_id == restaurant_id)

            cat_stats = q.group_by(Category.id, Category.name, Category.name_hi).all()

            breakdown = []
            for row in cat_stats:
                avg_price = row.avg_price or 1
                avg_cm = row.avg_cm or 0
                avg_cm_pct = (avg_cm / avg_price * 100) if avg_price > 0 else 0

                breakdown.append({
                    "category_id": row.id,
                    "category_name": row.name,
                    "category_name_hi": row.name_hi or "",
                    "item_count": row.item_count,
                    "total_revenue": round(float(row.total_revenue), 2),
                    "total_units_sold": int(row.total_units),
                    "avg_cm_pct": round(float(avg_cm_pct), 1),
                })

            breakdown.sort(key=lambda x: x["total_revenue"], reverse=True)
            return {"categories": breakdown}

        return _get_or_compute(cache_key, _compute)
    except Exception as e:
        logger.exception("Error computing category breakdown")
        raise HTTPException(status_code=500, detail=f"Category breakdown failed: {e}")


# ── Keep backward-compatible endpoints ──

@router.get("/analyze")
def full_analysis(restaurant_id: int = Query(None), db: Session = Depends(get_db)):
    """Run the complete revenue intelligence pipeline."""
    return run_full_analysis(db, restaurant_id=restaurant_id)


@router.get("/margins")
def get_margins(restaurant_id: int = Query(None), db: Session = Depends(get_db)):
    """Get contribution margins for all items."""
    margins, _ = _get_margins_popularity(db, restaurant_id=restaurant_id)
    return {"items": margins}


@router.get("/popularity")
def get_popularity(restaurant_id: int = Query(None), db: Session = Depends(get_db)):
    """Get popularity/velocity scores for all items."""
    _, popularity = _get_margins_popularity(db, restaurant_id=restaurant_id)
    return {"items": popularity}


@router.get("/matrix")
def get_matrix_legacy(restaurant_id: int = Query(None), db: Session = Depends(get_db)):
    """Legacy endpoint — redirects to /menu-matrix."""
    return get_menu_matrix(restaurant_id=restaurant_id, db=db)


@router.get("/pricing")
def get_pricing_legacy(restaurant_id: int = Query(None), db: Session = Depends(get_db)):
    """Legacy endpoint — redirects to /price-recommendations."""
    margins, popularity = _get_margins_popularity(db, restaurant_id=restaurant_id)
    return {"recommendations": generate_price_recommendations(margins, popularity)}


# ── Trend & Time-Series Endpoints ──

@router.get("/trends")
def get_trends(restaurant_id: int = Query(None), db: Session = Depends(get_db)):
    """
    GET /api/revenue/trends
    Returns: item_trends (30/60/90 day), category_trends, seasonal_patterns, quadrant_drift
    """
    try:
        cache_key = f"trends_{restaurant_id}" if restaurant_id else "trends"
        return _get_or_compute(cache_key, lambda: calculate_trends(db, restaurant_id=restaurant_id))
    except Exception as e:
        logger.exception("Error computing trends")
        raise HTTPException(status_code=500, detail=f"Trend analysis failed: {e}")


@router.get("/trends/wow-mom")
def get_wow_mom(restaurant_id: int = Query(None), db: Session = Depends(get_db)):
    """
    GET /api/revenue/trends/wow-mom
    Returns: per-item week-over-week and month-over-month revenue changes
    """
    try:
        cache_key = f"wow_mom_{restaurant_id}" if restaurant_id else "wow_mom"
        return _get_or_compute(cache_key, lambda: {"items": calculate_wow_mom(db, restaurant_id=restaurant_id)})
    except Exception as e:
        logger.exception("Error computing WoW/MoM")
        raise HTTPException(status_code=500, detail=f"WoW/MoM analysis failed: {e}")


@router.get("/trends/price-elasticity")
def get_price_elasticity(restaurant_id: int = Query(None), db: Session = Depends(get_db)):
    """
    GET /api/revenue/trends/price-elasticity
    Returns: items where price changes were detected with elasticity estimates
    """
    try:
        cache_key = f"price_elasticity_{restaurant_id}" if restaurant_id else "price_elasticity"
        return _get_or_compute(cache_key, lambda: {"items": estimate_price_elasticity(db, restaurant_id=restaurant_id)})
    except Exception as e:
        logger.exception("Error estimating price elasticity")
        raise HTTPException(status_code=500, detail=f"Price elasticity failed: {e}")


# ── Advanced Analytics Endpoints ──

@router.get("/analytics/cannibalization")
def get_cannibalization(
    restaurant_id: int = Query(None),
    db: Session = Depends(get_db),
    days: int = Query(90, ge=30, le=365),
):
    """
    GET /api/revenue/analytics/cannibalization
    Returns: items where new additions are cannibalizing existing items
    """
    try:
        cache_key = f"cannibalization_{restaurant_id}_{days}" if restaurant_id else f"cannibalization_{days}"
        return _get_or_compute(cache_key, lambda: {"items": analyze_category_cannibalization(db, lookback_days=days, restaurant_id=restaurant_id)})
    except Exception as e:
        logger.exception("Error analyzing cannibalization")
        raise HTTPException(status_code=500, detail=f"Cannibalization analysis failed: {e}")


@router.get("/analytics/price-sensitivity")
def get_price_sensitivity(restaurant_id: int = Query(None), db: Session = Depends(get_db)):
    """
    GET /api/revenue/analytics/price-sensitivity
    Returns: plowhorse items with price increase scenarios and projected impact
    """
    try:
        cache_key = f"price_sensitivity_{restaurant_id}" if restaurant_id else "price_sensitivity"
        return _get_or_compute(cache_key, lambda: {"items": estimate_price_sensitivity(db, restaurant_id=restaurant_id)})
    except Exception as e:
        logger.exception("Error estimating price sensitivity")
        raise HTTPException(status_code=500, detail=f"Price sensitivity failed: {e}")


@router.get("/analytics/waste")
def get_waste_analysis(
    restaurant_id: int = Query(None),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=7, le=365),
):
    """
    GET /api/revenue/analytics/waste
    Returns: waste costs, void rates, top wasted ingredients, top voided items
    """
    try:
        cache_key = f"waste_{restaurant_id}_{days}" if restaurant_id else f"waste_{days}"
        return _get_or_compute(cache_key, lambda: analyze_waste_and_voids(db, days=days, restaurant_id=restaurant_id))
    except Exception as e:
        logger.exception("Error analyzing waste")
        raise HTTPException(status_code=500, detail=f"Waste analysis failed: {e}")


@router.get("/analytics/customer-returns")
def get_customer_returns(
    restaurant_id: int = Query(None),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=7, le=365),
):
    """
    GET /api/revenue/analytics/customer-returns
    Returns: estimated repeat customer rates based on table patterns
    """
    try:
        cache_key = f"customer_returns_{restaurant_id}_{days}" if restaurant_id else f"customer_returns_{days}"
        return _get_or_compute(cache_key, lambda: estimate_customer_return_rate(db, days=days, restaurant_id=restaurant_id))
    except Exception as e:
        logger.exception("Error estimating customer returns")
        raise HTTPException(status_code=500, detail=f"Customer return analysis failed: {e}")


@router.get("/analytics/menu-complexity")
def get_menu_complexity(restaurant_id: int = Query(None), db: Session = Depends(get_db)):
    """
    GET /api/revenue/analytics/menu-complexity
    Returns: per-category complexity scores and alerts when >7 items
    """
    try:
        cache_key = f"menu_complexity_{restaurant_id}" if restaurant_id else "menu_complexity"
        return _get_or_compute(cache_key, lambda: {"categories": calculate_menu_complexity(db, restaurant_id=restaurant_id)})
    except Exception as e:
        logger.exception("Error computing menu complexity")
        raise HTTPException(status_code=500, detail=f"Menu complexity failed: {e}")


@router.get("/analytics/operational")
def get_operational_metrics_endpoint(
    restaurant_id: int = Query(None),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=7, le=365),
):
    """
    GET /api/revenue/analytics/operational
    Returns: AOV, peak hours, orders by type, total stats
    """
    try:
        cache_key = f"operational_{restaurant_id}_{days}" if restaurant_id else f"operational_{days}"
        return _get_or_compute(cache_key, lambda: calculate_operational_metrics(db, days=days, restaurant_id=restaurant_id))
    except Exception as e:
        logger.exception("Error computing operational metrics")
        raise HTTPException(status_code=500, detail=f"Operational metrics failed: {e}")
