"""
routes_revenue.py — Revenue Intelligence API Endpoints
========================================================
/api/revenue/* — Dashboard, menu matrix, hidden stars, risks,
combos, price recommendations, category breakdown
"""

from fastapi import APIRouter, Depends
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

# ── Cache for expensive combo computation ──
_combo_cache: dict = {"data": None, "timestamp": None}


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    """
    GET /api/revenue/dashboard
    Returns: total_revenue, avg_cm_percent, items_at_risk_count, uplift_potential
    """
    analysis = run_full_analysis(db)
    summary = analysis.get("summary", {})

    # Calculate total revenue from sales
    total_revenue = (
        db.query(func.sum(SaleTransaction.total_price))
        .scalar() or 0.0
    )

    # Count risk items (high sales + low CM)
    items_at_risk = sum(
        1 for m in analysis.get("matrix", [])
        if m.get("quadrant") == "dog" or (
            m.get("margin_pct", 100) < 40 and m.get("popularity_score", 0) > 50
        )
    )

    # Estimate uplift potential from hidden stars
    hidden_stars = analysis.get("hidden_stars", [])
    uplift = sum(h.get("estimated_monthly_uplift", 0) for h in hidden_stars)

    return {
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


@router.get("/menu-matrix")
def get_menu_matrix(db: Session = Depends(get_db)):
    """
    GET /api/revenue/menu-matrix
    Returns: all items with quadrant, cm_percent, popularity_score
    Used by frontend scatter chart.
    """
    margins = calculate_margins(db)
    popularity = calculate_popularity(db)
    matrix = classify_menu_matrix(margins, popularity)
    summary = get_quadrant_summary(matrix)
    return {"items": matrix, "summary": summary}


@router.get("/hidden-stars")
def get_hidden_stars(db: Session = Depends(get_db)):
    """
    GET /api/revenue/hidden-stars
    Returns: hidden star items with estimated_monthly_uplift, recommendation
    """
    margins = calculate_margins(db)
    popularity = calculate_popularity(db)
    return {"items": detect_hidden_stars(margins, popularity)}


@router.get("/risks")
def get_risk_items(db: Session = Depends(get_db)):
    """
    GET /api/revenue/risks
    Returns: risk items with risk_score, volume, cm_percent
    Risk = high sales volume + low contribution margin
    """
    margins = calculate_margins(db)
    popularity = calculate_popularity(db)
    matrix = classify_menu_matrix(margins, popularity)

    # Risk items: low CM% but high sales (dangerous for profitability)
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


@router.get("/combos")
def get_combo_suggestions(db: Session = Depends(get_db)):
    """
    GET /api/revenue/combos
    Returns: top 20 combos from FP-Growth combo engine.
    Results are cached since computation is expensive.
    """
    import time

    now = time.time()
    # Cache for 5 minutes
    if _combo_cache["data"] is not None and _combo_cache["timestamp"]:
        if now - _combo_cache["timestamp"] < 300:
            return {"combos": _combo_cache["data"]}

    combos = generate_combos(db)
    _combo_cache["data"] = combos
    _combo_cache["timestamp"] = now

    return {"combos": combos}


@router.get("/price-recommendations")
def get_price_recommendations(db: Session = Depends(get_db)):
    """
    GET /api/revenue/price-recommendations
    Returns: items with current_price, recommended_price, reason
    """
    margins = calculate_margins(db)
    popularity = calculate_popularity(db)
    return {"recommendations": generate_price_recommendations(margins, popularity)}


@router.get("/category-breakdown")
def get_category_breakdown(db: Session = Depends(get_db)):
    """
    GET /api/revenue/category-breakdown
    Returns: per-category stats (item_count, avg_cm_pct, total_revenue)
    """
    categories = db.query(Category).filter(Category.is_active == True).all()
    breakdown = []

    for cat in categories:
        items = (
            db.query(MenuItem)
            .filter(MenuItem.category_id == cat.id, MenuItem.is_available == True)
            .all()
        )

        if not items:
            continue

        item_ids = [i.id for i in items]
        total_rev = (
            db.query(func.sum(SaleTransaction.total_price))
            .filter(SaleTransaction.item_id.in_(item_ids))
            .scalar() or 0.0
        )
        total_units = (
            db.query(func.sum(SaleTransaction.quantity))
            .filter(SaleTransaction.item_id.in_(item_ids))
            .scalar() or 0
        )
        avg_cm = sum(i.margin_pct for i in items) / len(items) if items else 0

        breakdown.append({
            "category_id": cat.id,
            "category_name": cat.name,
            "category_name_hi": cat.name_hi or "",
            "item_count": len(items),
            "total_revenue": round(total_rev, 2),
            "total_units_sold": total_units,
            "avg_cm_pct": round(avg_cm, 1),
        })

    breakdown.sort(key=lambda x: x["total_revenue"], reverse=True)
    return {"categories": breakdown}


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
