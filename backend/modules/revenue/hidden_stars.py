"""
hidden_stars.py — Hidden Star Detection
=========================================
Finds high-CM items with low visibility / sales.
These are "puzzle" items that could become stars
with the right promotion.
"""


import os

_DEFAULT_CM_PERCENTILE = float(os.getenv("HIDDEN_STARS_CM_PERCENTILE", "0.7"))
_DEFAULT_POP_PERCENTILE = float(os.getenv("HIDDEN_STARS_POP_PERCENTILE", "0.3"))


def detect_hidden_stars(
    margins: list[dict],
    popularity: list[dict],
    cm_percentile: float = _DEFAULT_CM_PERCENTILE,
    pop_percentile: float = _DEFAULT_POP_PERCENTILE,
) -> list[dict]:
    """
    Detect hidden stars: items with high contribution margin
    but low sales volume.

    These are the biggest revenue opportunities — items that
    are already profitable but underperforming on visibility.

    Args:
        margins: Output of calculate_margins()
        popularity: Output of calculate_popularity()
        cm_percentile: Top X% by margin to consider "high CM"
        pop_percentile: Bottom X% by popularity to consider "low visibility"

    Returns:
        List of hidden star items with opportunity scores
    """
    if not margins or not popularity:
        return []

    pop_map = {p["item_id"]: p for p in popularity}

    # Calculate thresholds
    sorted_margins = sorted(margins, key=lambda x: x["margin_pct"])
    sorted_pop = sorted(popularity, key=lambda x: x["popularity_score"])

    cm_threshold_idx = int(len(sorted_margins) * cm_percentile)
    pop_threshold_idx = int(len(sorted_pop) * pop_percentile)

    cm_threshold = sorted_margins[cm_threshold_idx]["margin_pct"] if cm_threshold_idx < len(sorted_margins) else 65
    pop_threshold = sorted_pop[pop_threshold_idx]["popularity_score"] if pop_threshold_idx < len(sorted_pop) else 0.3

    hidden_stars = []
    for m in margins:
        item_id = m["item_id"]
        pop = pop_map.get(item_id, {})
        pop_score = pop.get("popularity_score", 0)

        if m["margin_pct"] >= cm_threshold and pop_score <= pop_threshold:
            # Opportunity score: how much margin is being "wasted"
            # Higher margin + lower popularity = bigger opportunity
            opportunity = round(
                m["margin_pct"] / 100 * (1 - pop_score) * 100, 1
            )

            # ML: confidence from sample size (more orders = higher confidence)
            order_count = pop.get("order_count", 0)
            ml_confidence = min(0.99, 0.4 + 0.3 * min(order_count / 20, 1.0))
            ml_velocity_trend = pop.get("ml_velocity_trend_pct")
            ml_tier = "high_opportunity" if opportunity >= 50 else "medium" if opportunity >= 25 else "low"

            hidden_stars.append({
                "item_id": item_id,
                "name": m["name"],
                "name_hi": m.get("name_hi", ""),
                "category": m["category"],
                "selling_price": m["selling_price"],
                "margin_pct": m["margin_pct"],
                "contribution_margin": m["contribution_margin"],
                "popularity_score": pop_score,
                "daily_velocity": pop.get("daily_velocity", 0),
                "opportunity_score": opportunity,
                "suggestions": _generate_suggestions(m, pop),
                "ml_confidence": round(ml_confidence, 2),
                "ml_velocity_trend_pct": ml_velocity_trend,
                "ml_tier": ml_tier,
            })

    # Sort by opportunity score descending
    hidden_stars.sort(key=lambda x: x["opportunity_score"], reverse=True)
    return hidden_stars


def _generate_suggestions(margin_data: dict, pop_data: dict) -> list[str]:
    """Generate actionable suggestions for a hidden star item."""
    suggestions = []

    suggestions.append(
        f"Feature '{margin_data['name']}' as a daily special"
    )
    suggestions.append(
        "Train staff to recommend this item when taking orders"
    )

    if margin_data.get("margin_pct", 0) > 70:
        suggestions.append(
            "Offer a small discount (5-8%) to drive trial — margin allows it"
        )

    if pop_data.get("daily_velocity", 0) < 1:
        suggestions.append(
            "Add attractive photos to menu — item may be overlooked"
        )
        suggestions.append(
            "Bundle with popular items to increase exposure"
        )

    return suggestions
