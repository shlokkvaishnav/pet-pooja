"""
analyzer.py — Revenue Analysis Orchestrator
=============================================
Main entry point that calls all sub-modules and assembles
the complete revenue intelligence report.
"""

from sqlalchemy.orm import Session

from .contribution_margin import calculate_margins
from .popularity import calculate_popularity
from .menu_matrix import classify_menu_matrix
from .hidden_stars import detect_hidden_stars
from .combo_engine import generate_combos
from .price_optimizer import generate_price_recommendations
from .trend_analyzer import calculate_trends, calculate_wow_mom
from .advanced_analytics import calculate_operational_metrics


def run_full_analysis(db: Session) -> dict:
    """
    Run the complete revenue intelligence pipeline.

    Returns a dict with:
    - margins: per-item CM and margin %
    - popularity: per-item velocity and popularity scores
    - matrix: BCG quadrant classification
    - hidden_stars: high-CM, low-visibility items
    - combos: association-rule combo suggestions
    - price_recommendations: rule-based price nudges
    - trends: time-series trend data
    - summary: overall menu health metrics (with breakdown)
    """
    # Step 1: Contribution margins
    margins = calculate_margins(db)

    # Step 2: Popularity / velocity
    popularity = calculate_popularity(db)

    # Step 3: BCG matrix classification (needs both margins + popularity)
    matrix = classify_menu_matrix(margins, popularity)

    # Step 4: Hidden star detection
    hidden_stars = detect_hidden_stars(margins, popularity)

    # Step 5: Combo recommendations (association rules)
    combos = generate_combos(db)

    # Step 6: Price optimization
    price_recs = generate_price_recommendations(margins, popularity)

    # Step 7: Time-series trends
    trends = calculate_trends(db)

    # Summary metrics
    total_items = len(margins)
    avg_margin = (
        sum(m["margin_pct"] for m in margins) / total_items
        if total_items > 0
        else 0
    )
    stars_count = sum(1 for m in matrix if m["quadrant"] == "star")
    plowhorses_count = sum(1 for m in matrix if m["quadrant"] == "plowhorse")
    puzzles_count = sum(1 for m in matrix if m["quadrant"] == "puzzle")
    dogs_count = sum(1 for m in matrix if m["quadrant"] == "dog")

    # Health score with transparent breakdown
    health_score_breakdown = _calculate_health_score(
        avg_margin, stars_count, dogs_count, total_items, hidden_stars
    )

    return {
        "margins": margins,
        "popularity": popularity,
        "matrix": matrix,
        "hidden_stars": hidden_stars,
        "combos": combos,
        "price_recommendations": price_recs,
        "trends": trends,
        "summary": {
            "total_items": total_items,
            "avg_margin_pct": round(avg_margin, 1),
            "health_score": health_score_breakdown["score"],
            "health_score_breakdown": health_score_breakdown,
            "stars": stars_count,
            "plowhorses": plowhorses_count,
            "puzzles": puzzles_count,
            "dogs": dogs_count,
            "hidden_stars_count": len(hidden_stars),
            "combos_suggested": len(combos),
            "price_actions": sum(
                1 for p in price_recs if p["direction"] != "hold"
            ),
        },
    }


def _calculate_health_score(
    avg_margin: float,
    stars_count: int,
    dogs_count: int,
    total_items: int,
    hidden_stars: list,
) -> dict:
    """
    Calculate health score with a transparent, explainable breakdown.

    Components:
    1. Margin Score (0-40): Based on avg margin vs 60% target
    2. Star Ratio Score (0-25): % of items that are Stars
    3. Dog Penalty (0 to -20): % of items that are Dogs
    4. Hidden Star Bonus (0-15): Untapped potential = positive signal

    Returns dict with score and human-readable explanation of each factor.
    """
    components = []

    # 1. Margin component: 40 points max
    margin_score = min(40, max(0, (avg_margin / 60) * 40))
    components.append({
        "name": "Average Margin",
        "score": round(margin_score, 1),
        "max": 40,
        "detail": f"Avg CM is {avg_margin:.1f}% (target: 60%). {'Above' if avg_margin >= 60 else 'Below'} target.",
    })

    # 2. Star ratio: 25 points max
    star_ratio = (stars_count / total_items) if total_items > 0 else 0
    star_score = min(25, star_ratio * 100)
    components.append({
        "name": "Star Items",
        "score": round(star_score, 1),
        "max": 25,
        "detail": f"{stars_count} of {total_items} items are Stars ({star_ratio*100:.0f}%).",
    })

    # 3. Dog penalty: up to -20
    dog_ratio = (dogs_count / total_items) if total_items > 0 else 0
    dog_penalty = min(20, dog_ratio * 100)
    components.append({
        "name": "Dog Penalty",
        "score": round(-dog_penalty, 1),
        "max": -20,
        "detail": f"{dogs_count} Dogs ({dog_ratio*100:.0f}% of menu). Each Dog reduces the score.",
    })

    # 4. Hidden star bonus: 15 points max
    hs_count = len(hidden_stars)
    hs_score = min(15, hs_count * 3)
    components.append({
        "name": "Hidden Star Potential",
        "score": round(hs_score, 1),
        "max": 15,
        "detail": f"{hs_count} hidden stars found — untapped revenue opportunities.",
    })

    raw = margin_score + star_score - dog_penalty + hs_score
    final = min(100, max(0, raw))

    return {
        "score": round(final, 1),
        "components": components,
        "explanation": (
            f"Health Score is {final:.0f}/100. "
            f"Margin contributes {margin_score:.0f} pts, "
            f"Stars add {star_score:.0f} pts, "
            f"Dogs subtract {dog_penalty:.0f} pts, "
            f"and {hs_count} Hidden Stars add {hs_score:.0f} pts of potential."
        ),
    }
