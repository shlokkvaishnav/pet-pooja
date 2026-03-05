"""
routes_revenue.py — Revenue Intelligence API Endpoints
========================================================
/api/revenue/* — Dashboard, menu matrix, hidden stars, risks,
combos, price recommendations, category breakdown
"""

import logging
import threading
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import MenuItem, SaleTransaction, Category
from modules.revenue.analyzer import run_full_analysis
from modules.revenue.contribution_margin import calculate_margins
from modules.revenue.popularity import calculate_popularity
from modules.revenue.menu_matrix import classify_menu_matrix, get_quadrant_summary
from modules.revenue.hidden_stars import detect_hidden_stars
from modules.revenue.combo_engine import generate_combos
from modules.revenue.price_optimizer import generate_price_recommendations

router = APIRouter()
logger = logging.getLogger("petpooja.api.revenue")

# ── Thread-safe cache for expensive computations ──
_cache_lock = threading.Lock()
_cache: dict = {}
_CACHE_TTL = 300  # 5 minutes


def _get_cached(key: str):
    """Return cached value if still valid, else None."""
    entry = _cache.get(key)
    if entry and time.time() - entry["ts"] < _CACHE_TTL:
        return entry["data"]
    return None


def _set_cached(key: str, data):
    """Store data in cache with timestamp."""
    with _cache_lock:
        _cache[key] = {"data": data, "ts": time.time()}


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    """
    GET /api/revenue/dashboard
    Returns: total_revenue, avg_cm_percent, items_at_risk_count, uplift_potential
    """
    try:
        cached = _get_cached("dashboard")
        if cached:
            return cached

        analysis = run_full_analysis(db)
        summary = analysis.get("summary", {})

        total_revenue = (
            db.query(func.sum(SaleTransaction.total_price))
            .scalar() or 0.0
        )

        items_at_risk = sum(
            1 for m in analysis.get("matrix", [])
            if m.get("quadrant") == "dog" or (
                m.get("margin_pct", 100) < 40 and m.get("popularity_score", 0) > 50
            )
        )

        hidden_stars = analysis.get("hidden_stars", [])
        uplift = sum(h.get("estimated_monthly_uplift", 0) for h in hidden_stars)

        result = {
            "total_revenue": round(total_revenue, 2),
            "avg_cm_percent": summary.get("avg_margin_pct", 0),
            "items_at_risk_count": items_at_risk,
            "uplift_potential": round(uplift, 2),
            "health_score": summary.get("health_score", 0),
            "total_items": summary.get("total_items", 0),
            "stars_count": summary.get("stars", 0),
            "dogs_count": summary.get("dogs", 0),
            "hidden_stars_count": summary.get("hidden_stars_count", 0),
        }

        _set_cached("dashboard", result)
        return result
    except Exception as e:
        logger.exception("Error computing dashboard")
        raise HTTPException(status_code=500, detail=f"Dashboard computation failed: {e}")


@router.get("/menu-matrix")
def get_menu_matrix(db: Session = Depends(get_db)):
    """
    GET /api/revenue/menu-matrix
    Returns: all items with quadrant, cm_percent, popularity_score
    Used by frontend scatter chart.
    """
    try:
        cached = _get_cached("menu_matrix")
        if cached:
            return cached

        margins = calculate_margins(db)
        popularity = calculate_popularity(db)
        matrix = classify_menu_matrix(margins, popularity)
        summary = get_quadrant_summary(matrix)
        result = {"items": matrix, "summary": summary}

        _set_cached("menu_matrix", result)
        return result
    except Exception as e:
        logger.exception("Error computing menu matrix")
        raise HTTPException(status_code=500, detail=f"Menu matrix failed: {e}")


@router.get("/hidden-stars")
def get_hidden_stars(db: Session = Depends(get_db)):
    """
    GET /api/revenue/hidden-stars
    Returns: hidden star items with estimated_monthly_uplift, recommendation
    """
    try:
        margins = calculate_margins(db)
        popularity = calculate_popularity(db)
        return {"items": detect_hidden_stars(margins, popularity)}
    except Exception as e:
        logger.exception("Error detecting hidden stars")
        raise HTTPException(status_code=500, detail=f"Hidden stars detection failed: {e}")


@router.get("/risks")
def get_risk_items(db: Session = Depends(get_db)):
    """
    GET /api/revenue/risks
    Returns: risk items with risk_score, volume, cm_percent
    Risk = high sales volume + low contribution margin
    """
    try:
        margins = calculate_margins(db)
        popularity = calculate_popularity(db)
        matrix = classify_menu_matrix(margins, popularity)

        risk_items = []
        for item in matrix:
            cm = item.get("margin_pct", 100)
            pop = item.get("popularity_score", 0)

            if cm < 40 and pop > 50:
                risk_score = round((100 - cm) * (pop / 100), 1)
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
    except Exception as e:
        logger.exception("Error computing risk items")
        raise HTTPException(status_code=500, detail=f"Risk analysis failed: {e}")


@router.get("/combos")
def get_combo_suggestions(db: Session = Depends(get_db)):
    """
    GET /api/revenue/combos
    Returns: top 20 combos from FP-Growth combo engine.
    Results are cached since computation is expensive.
    """
    try:
        cached = _get_cached("combos")
        if cached:
            return {"combos": cached}

        combos = generate_combos(db)
        _set_cached("combos", combos)
        return {"combos": combos}
    except Exception as e:
        logger.exception("Error generating combos")
        raise HTTPException(status_code=500, detail=f"Combo generation failed: {e}")


@router.get("/price-recommendations")
def get_price_recommendations(db: Session = Depends(get_db)):
    """
    GET /api/revenue/price-recommendations
    Returns: items with current_price, recommended_price, reason
    """
    try:
        margins = calculate_margins(db)
        popularity = calculate_popularity(db)
        return {"recommendations": generate_price_recommendations(margins, popularity)}
    except Exception as e:
        logger.exception("Error generating price recommendations")
        raise HTTPException(status_code=500, detail=f"Price recommendation failed: {e}")


@router.get("/category-breakdown")
def get_category_breakdown(db: Session = Depends(get_db)):
    """
    GET /api/revenue/category-breakdown
    Returns: per-category stats (item_count, avg_cm_pct, total_revenue)
    """
    try:
        # Single query: aggregate revenue and units per category
        cat_stats = (
            db.query(
                Category.id,
                Category.name,
                Category.name_hi,
                func.count(func.distinct(MenuItem.id)).label("item_count"),
                func.coalesce(func.sum(SaleTransaction.total_price), 0).label("total_revenue"),
                func.coalesce(func.sum(SaleTransaction.quantity), 0).label("total_units"),
                func.avg(MenuItem.selling_price - MenuItem.food_cost).label("avg_cm"),
                func.avg(MenuItem.selling_price).label("avg_price"),
            )
            .join(MenuItem, MenuItem.category_id == Category.id)
            .outerjoin(SaleTransaction, SaleTransaction.item_id == MenuItem.id)
            .filter(Category.is_active == True, MenuItem.is_available == True)
            .group_by(Category.id, Category.name, Category.name_hi)
            .all()
        )

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
    except Exception as e:
        logger.exception("Error computing category breakdown")
        raise HTTPException(status_code=500, detail=f"Category breakdown failed: {e}")


# ── Keep backward-compatible endpoints ──

@router.get("/analyze")
def full_analysis(db: Session = Depends(get_db)):
    """Run the complete revenue intelligence pipeline."""
    return run_full_analysis(db)


@router.get("/margins")
def get_margins(db: Session = Depends(get_db)):
    """Get contribution margins for all items."""
    return {"items": calculate_margins(db)}


@router.get("/popularity")
def get_popularity(db: Session = Depends(get_db)):
    """Get popularity/velocity scores for all items."""
    return {"items": calculate_popularity(db)}


@router.get("/matrix")
def get_matrix_legacy(db: Session = Depends(get_db)):
    """Legacy endpoint — redirects to /menu-matrix."""
    return get_menu_matrix(db)


@router.get("/pricing")
def get_pricing_legacy(db: Session = Depends(get_db)):
    """Legacy endpoint — redirects to /price-recommendations."""
    margins = calculate_margins(db)
    popularity = calculate_popularity(db)
    return {"recommendations": generate_price_recommendations(margins, popularity)}
