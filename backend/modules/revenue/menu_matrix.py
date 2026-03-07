"""
menu_matrix.py — BCG Quadrant Classification
==============================================
Classifies menu items into the 4 BCG quadrants:
  ⭐ Stars       — High popularity, High margin
  🐴 Plowhorses  — High popularity, Low margin
  🧩 Puzzles     — Low popularity, High margin
  🐕 Dogs        — Low popularity, Low margin
"""


import os

_DEFAULT_MARGIN_THRESHOLD = float(os.getenv("MENU_MATRIX_MARGIN_THRESHOLD", "60.0"))
_DEFAULT_POPULARITY_THRESHOLD = float(os.getenv("MENU_MATRIX_POPULARITY_THRESHOLD", "0.4"))


def classify_menu_matrix(
    margins: list[dict],
    popularity: list[dict],
    margin_threshold: float = _DEFAULT_MARGIN_THRESHOLD,
    popularity_threshold: float = _DEFAULT_POPULARITY_THRESHOLD,
) -> list[dict]:
    """
    Classify items into BCG quadrants.

    Args:
        margins: Output of calculate_margins()
        popularity: Output of calculate_popularity()
        margin_threshold: Margin % cutoff for high/low
        popularity_threshold: Popularity score cutoff (0–1)

    Returns:
        List of items with quadrant classification
    """
    # Build lookup maps
    pop_map = {p["item_id"]: p for p in popularity}

    results = []
    for m in margins:
        item_id = m["item_id"]
        pop = pop_map.get(item_id, {})

        margin_pct = m.get("margin_pct", 0)
        pop_score = pop.get("popularity_score", 0)

        # Classify
        high_margin = margin_pct >= margin_threshold
        high_pop = pop_score >= popularity_threshold

        if high_margin and high_pop:
            quadrant = "star"
            emoji = "⭐"
            action = "Protect and promote. Keep quality consistent."
        elif not high_margin and high_pop:
            quadrant = "plowhorse"
            emoji = "🐴"
            action = "Increase price gradually or reduce portion cost."
        elif high_margin and not high_pop:
            quadrant = "puzzle"
            emoji = "🧩"
            action = "Boost visibility — feature in specials, train staff to upsell."
        else:
            quadrant = "dog"
            emoji = "🐕"
            action = "Consider removing or reworking the recipe."

        # ML: quadrant confidence = how far inside the quadrant (distance from thresholds)
        margin_gap = abs(margin_pct - margin_threshold)
        pop_gap = abs(pop_score - popularity_threshold)
        quadrant_confidence = min(0.99, 0.5 + (margin_gap / 30) * 0.25 + (pop_gap / 0.3) * 0.25)
        ml_insight = (
            f"ML: {quadrant.upper()} with {quadrant_confidence:.0%} confidence — "
            f"margin {margin_pct:.0f}%, popularity {pop_score:.0%}."
        )

        results.append({
            "item_id": item_id,
            "name": m["name"],
            "name_hi": m.get("name_hi", ""),
            "category": m["category"],
            "selling_price": m["selling_price"],
            "food_cost": m["food_cost"],
            "margin_pct": margin_pct,
            "popularity_score": pop_score,
            "daily_velocity": pop.get("daily_velocity", 0),
            "quadrant": quadrant,
            "emoji": emoji,
            "action": action,
            "is_veg": m.get("is_veg", True),
            "ml_quadrant_confidence": round(quadrant_confidence, 2),
            "ml_insight": ml_insight,
            "ml_profitability_score": m.get("ml_profitability_score"),
            "ml_profit_tier": m.get("ml_profit_tier"),
            "ml_confidence": m.get("ml_confidence") or pop.get("ml_confidence"),
            "ml_velocity_trend_pct": pop.get("ml_velocity_trend_pct"),
            "ml_velocity_label": pop.get("ml_velocity_label"),
        })

    return results


def get_quadrant_summary(matrix: list[dict]) -> dict:
    """Get count and items per quadrant."""
    summary = {
        "star": {"count": 0, "items": []},
        "plowhorse": {"count": 0, "items": []},
        "puzzle": {"count": 0, "items": []},
        "dog": {"count": 0, "items": []},
    }
    for item in matrix:
        q = item["quadrant"]
        summary[q]["count"] += 1
        summary[q]["items"].append(item["name"])

    return summary
