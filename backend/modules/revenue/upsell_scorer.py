"""
upsell_scorer.py — Upsell Opportunity Scoring Model
=====================================================
Given items already in a cart, ranks menu items by their upsell
probability and margin impact using co-occurrence patterns and
contribution margin data.
"""

import logging
from collections import Counter

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import MenuItem, VSale, Category

logger = logging.getLogger("petpooja.revenue.ml.upsell")

_upsell_matrix = None  # item_id → {co_item_id: probability}
_upsell_metrics = None
_item_margins = None   # item_id → {price, cost, margin, margin_pct, name, category}


def train_upsell_model(db: Session, restaurant_id: int = None) -> dict:
    """
    Build a co-occurrence matrix from basket data for upsell scoring.
    For each item pair (A, B): P(B | A) = count(orders with A and B) / count(orders with A)

    Returns dict with model metrics.
    """
    global _upsell_matrix, _upsell_metrics, _item_margins

    logger.info("Training upsell scoring model...")

    # Fetch all baskets (order → set of item_ids)
    basket_q = (
        db.query(VSale.order_id, VSale.item_id)
    )
    if restaurant_id:
        basket_q = basket_q.filter(VSale.restaurant_id == restaurant_id)
    basket_data = basket_q.all()

    baskets: dict[str, set[int]] = {}
    for order_id, item_id in basket_data:
        baskets.setdefault(order_id, set()).add(item_id)

    if len(baskets) < 20:
        return {"status": "skipped", "reason": "insufficient_baskets", "baskets_found": len(baskets)}

    # Item frequency and pair co-occurrence
    item_freq = Counter()
    pair_freq = Counter()
    for items in baskets.values():
        for item in items:
            item_freq[item] += 1
        sorted_items = sorted(items)
        for i in range(len(sorted_items)):
            for j in range(i + 1, len(sorted_items)):
                pair_freq[(sorted_items[i], sorted_items[j])] += 1

    # Build conditional probability matrix
    co_matrix: dict[int, dict[int, float]] = {}
    n_baskets = len(baskets)

    for (a, b), count in pair_freq.items():
        prob_b_given_a = count / item_freq[a] if item_freq[a] > 0 else 0
        prob_a_given_b = count / item_freq[b] if item_freq[b] > 0 else 0

        co_matrix.setdefault(a, {})[b] = round(prob_b_given_a, 4)
        co_matrix.setdefault(b, {})[a] = round(prob_a_given_b, 4)

    # Build item margin lookup
    items = db.query(MenuItem).filter(MenuItem.is_available.is_(True))
    if restaurant_id:
        items = items.filter(MenuItem.restaurant_id == restaurant_id)

    margins = {}
    for item in items.all():
        price = float(item.selling_price or 0)
        cost = float(item.food_cost or 0)
        margin = price - cost
        margin_pct = (margin / price * 100) if price > 0 else 0

        cat = db.query(Category.name).filter(Category.id == item.category_id).scalar() or "Uncategorized"

        margins[item.id] = {
            "name": item.name, "price": price, "cost": cost,
            "margin": round(margin, 2), "margin_pct": round(margin_pct, 1),
            "category": cat, "is_veg": item.is_veg,
        }

    _upsell_matrix = co_matrix
    _item_margins = margins
    _upsell_metrics = {
        "total_baskets": n_baskets,
        "unique_items": len(item_freq),
        "co_occurrence_pairs": len(pair_freq),
        "avg_basket_size": round(np.mean([len(b) for b in baskets.values()]), 1),
    }

    logger.info("Upsell model trained: %d baskets, %d items, %d pairs",
                n_baskets, len(item_freq), len(pair_freq))
    return {"status": "completed", **_upsell_metrics}


def score_upsell_candidates(
    db: Session,
    current_items: list[int],
    top_k: int = 5,
    restaurant_id: int = None,
) -> list[dict]:
    """
    Given items in a cart, rank all other items by upsell score.

    upsell_score = P(candidate | current_basket) × contribution_margin × demand_weight

    Returns top_k candidates with score, reason, and expected margin lift.
    """
    if _upsell_matrix is None or _item_margins is None:
        return _fallback_upsell(db, current_items, top_k, restaurant_id)

    if not current_items:
        return []

    # Aggregate co-occurrence probabilities across all current items
    candidate_scores: dict[int, float] = {}
    candidate_reasons: dict[int, str] = {}

    for item_id in current_items:
        co_probs = _upsell_matrix.get(item_id, {})
        item_name = _item_margins.get(item_id, {}).get("name", f"Item {item_id}")

        for cand_id, prob in co_probs.items():
            if cand_id in current_items:
                continue  # skip items already in cart

            cand_info = _item_margins.get(cand_id)
            if not cand_info:
                continue

            # Upsell score = co-occurrence prob × margin
            margin_weight = max(cand_info["margin"], 1)
            score = prob * margin_weight

            if cand_id not in candidate_scores or score > candidate_scores[cand_id]:
                candidate_scores[cand_id] = score
                candidate_reasons[cand_id] = (
                    f"Often ordered with {item_name} "
                    f"({prob*100:.0f}% co-occurrence, "
                    f"₹{cand_info['margin']:.0f} margin)"
                )

    # Sort by score and return top_k
    ranked = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    results = []
    for cand_id, score in ranked:
        info = _item_margins.get(cand_id, {})
        results.append({
            "item_id": cand_id,
            "name": info.get("name", ""),
            "price": info.get("price", 0),
            "category": info.get("category", ""),
            "is_veg": info.get("is_veg", True),
            "upsell_score": round(score, 2),
            "expected_margin_lift": round(info.get("margin", 0), 2),
            "reason": candidate_reasons.get(cand_id, ""),
        })

    return results


def _fallback_upsell(db: Session, current_items: list[int], top_k: int, restaurant_id: int = None) -> list[dict]:
    """Fallback: recommend highest-margin items not in cart."""
    q = db.query(MenuItem).filter(
        MenuItem.is_available.is_(True),
        MenuItem.id.notin_(current_items) if current_items else True,
    )
    if restaurant_id:
        q = q.filter(MenuItem.restaurant_id == restaurant_id)

    items = q.all()
    scored = []
    for item in items:
        price = float(item.selling_price or 0)
        cost = float(item.food_cost or 0)
        margin = price - cost
        if margin > 0:
            scored.append((item, margin))

    scored.sort(key=lambda x: x[1], reverse=True)

    results = []
    for item, margin in scored[:top_k]:
        results.append({
            "item_id": item.id, "name": item.name,
            "price": float(item.selling_price or 0),
            "category": "", "is_veg": item.is_veg,
            "upsell_score": round(margin, 2),
            "expected_margin_lift": round(margin, 2),
            "reason": f"High margin item (₹{margin:.0f})",
        })
    return results


def get_upsell_metrics() -> dict | None:
    """Return cached model metrics or None."""
    return _upsell_metrics
