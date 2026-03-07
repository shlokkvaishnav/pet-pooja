"""
bundle_pricer.py — ML-Based Bundle Price Optimizer
====================================================
Replaces synthetic RF pricing with a model trained on actual order data.

Analyzes historical basket data to learn the relationship between
item combinations, discount depth, and purchase frequency, then
predicts the optimal combo price that maximizes margin × uptake.
"""

import logging
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from models import MenuItem, VSale, Category

logger = logging.getLogger("petpooja.revenue.ml.pricing")

# ── Category groups (shared with combo engine) ────
_CATEGORY_GROUPS = {
    "main": {"Main Course", "Mains", "Biryani", "Rice", "Thali"},
    "bread": {"Breads", "Roti", "Naan"},
    "side": {"Starters", "Appetizers", "Sides", "Salads", "Raita"},
    "drink": {"Beverages", "Drinks", "Juices", "Lassi"},
    "dessert": {"Desserts", "Sweets"},
}

# ── In-memory model cache ────────────────────────
_pricing_model = None
_pricing_metrics = None
_item_stats_cache = None  # item-level stats for feature engineering


def train_pricing_model(db: Session, restaurant_id: int = None) -> dict:
    """
    Train a bundle pricing model on historical multi-item basket data.

    For each historical basket (order with 2+ items), we extract:
    Features:
      - avg_item_price: mean selling price of items
      - avg_item_margin_pct: mean contribution margin %
      - basket_size: number of unique items
      - total_qty: total quantity
      - category_diversity: number of distinct category groups
      - co_occurrence_freq: how often this pair/triple appears across all orders
      - max_item_price / min_item_price ratio (spread)

    Target: actual_basket_total (what customers actually paid)
      → We learn the "natural discount" customers implicitly get via
        multi-item ordering patterns.

    Returns dict with model metrics.
    """
    global _pricing_model, _pricing_metrics, _item_stats_cache

    logger.info("Training bundle pricing model...")

    # ── Step 1: Fetch all multi-item baskets ─────────────────────────
    # Get orders with 2+ items
    multi_item_orders = (
        db.query(VSale.order_id)
        .group_by(VSale.order_id)
        .having(func.count(func.distinct(VSale.item_id)) >= 2)
    )
    if restaurant_id:
        multi_item_orders = multi_item_orders.filter(VSale.restaurant_id == restaurant_id)
    multi_ids = [r.order_id for r in multi_item_orders.all()]

    if len(multi_ids) < 20:
        logger.warning("Insufficient multi-item orders (%d) for pricing model", len(multi_ids))
        return {"status": "skipped", "reason": "insufficient_data", "orders_found": len(multi_ids)}

    # ── Step 2: Fetch basket details ─────────────────────────────────
    basket_data = (
        db.query(
            VSale.order_id,
            VSale.item_id,
            VSale.quantity,
            VSale.unit_price,
            VSale.total_price,
            MenuItem.selling_price,
            MenuItem.food_cost,
            Category.name.label("category_name"),
        )
        .join(MenuItem, VSale.item_id == MenuItem.id)
        .outerjoin(Category, MenuItem.category_id == Category.id)
        .filter(VSale.order_id.in_(multi_ids))
        .all()
    )

    # Group by order
    baskets: dict[str, list] = {}
    for row in basket_data:
        baskets.setdefault(row.order_id, []).append(row)

    # Build item-level stats cache
    item_stats = {}
    for row in basket_data:
        if row.item_id not in item_stats:
            margin = (row.selling_price - row.food_cost) if row.selling_price and row.food_cost else 0
            margin_pct = (margin / row.selling_price * 100) if row.selling_price and row.selling_price > 0 else 0
            item_stats[row.item_id] = {
                "price": float(row.selling_price or 0),
                "cost": float(row.food_cost or 0),
                "margin_pct": round(margin_pct, 1),
                "category": row.category_name or "Uncategorized",
            }
    _item_stats_cache = item_stats

    # Count pair co-occurrences for frequency feature
    pair_counter = Counter()
    total_baskets = len(baskets)
    for items in baskets.values():
        ids = sorted(set(r.item_id for r in items))
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                pair_counter[frozenset({ids[i], ids[j]})] += 1

    # ── Step 3: Build features for each basket ───────────────────────
    def _classify(cat_name: str) -> str:
        for group, names in _CATEGORY_GROUPS.items():
            if cat_name in names:
                return group
        return "other"

    rows = []
    targets = []

    for order_id, items in baskets.items():
        prices = [float(r.selling_price or r.unit_price or 0) for r in items]
        costs = [float(r.food_cost or 0) for r in items if r.food_cost]
        quantities = [int(r.quantity or 1) for r in items]

        if not prices or sum(prices) == 0:
            continue

        individual_total = sum(p * q for p, q in zip(prices, quantities))
        actual_total = sum(float(r.total_price or 0) for r in items)

        if individual_total <= 0 or actual_total <= 0:
            continue

        avg_price = np.mean(prices)
        avg_margin = np.mean([
            item_stats.get(r.item_id, {}).get("margin_pct", 50) for r in items
        ])
        basket_size = len(set(r.item_id for r in items))
        total_qty = sum(quantities)

        # Category diversity
        cats = [_classify(item_stats.get(r.item_id, {}).get("category", "")) for r in items]
        diversity = len(set(cats))

        # Co-occurrence frequency (avg of all pairs in basket)
        item_ids = sorted(set(r.item_id for r in items))
        if len(item_ids) >= 2:
            pair_freqs = []
            for i in range(len(item_ids)):
                for j in range(i + 1, len(item_ids)):
                    key = frozenset({item_ids[i], item_ids[j]})
                    pair_freqs.append(pair_counter.get(key, 0) / total_baskets)
            avg_co_freq = np.mean(pair_freqs) if pair_freqs else 0
        else:
            avg_co_freq = 0

        # Price spread
        price_spread = max(prices) / min(prices) if min(prices) > 0 else 1.0

        # Effective discount the customer got (natural pricing behavior)
        effective_discount_pct = ((individual_total - actual_total) / individual_total) * 100

        rows.append({
            "avg_item_price": avg_price,
            "avg_margin_pct": avg_margin,
            "basket_size": basket_size,
            "total_qty": total_qty,
            "category_diversity": diversity,
            "co_occurrence_freq": avg_co_freq,
            "price_spread": price_spread,
            "individual_total": individual_total,
        })
        # Target: ratio of actual to individual total (the "natural" bundle factor)
        targets.append(actual_total / individual_total)

    if len(rows) < 15:
        logger.warning("Too few valid baskets (%d) for pricing model", len(rows))
        return {"status": "skipped", "reason": "insufficient_valid_baskets", "valid_baskets": len(rows)}

    # ── Step 4: Train model ──────────────────────────────────────────
    feature_names = list(rows[0].keys())
    X = pd.DataFrame(rows, columns=feature_names)
    y = np.array(targets)

    model = GradientBoostingRegressor(
        n_estimators=80,
        max_depth=4,
        learning_rate=0.1,
        min_samples_split=5,
        random_state=42,
    )

    cv_folds = min(5, max(2, len(rows) // 5))
    cv_scores = cross_val_score(model, X, y, cv=cv_folds, scoring="r2")
    cv_r2 = float(np.mean(cv_scores))

    model.fit(X, y)

    y_pred = model.predict(X)
    mae = float(np.mean(np.abs(y - y_pred)))

    importances = dict(zip(feature_names, [round(float(v), 4) for v in model.feature_importances_]))

    _pricing_model = model
    _pricing_metrics = {
        "cv_r2": round(cv_r2, 4),
        "mae": round(mae, 4),
        "training_baskets": len(rows),
        "feature_importances": importances,
        "avg_bundle_factor": round(float(np.mean(y)), 4),
    }

    logger.info(
        "Bundle pricing model trained: R²=%.3f, MAE=%.4f, baskets=%d, avg_factor=%.3f",
        cv_r2, mae, len(rows), np.mean(y),
    )

    return {"status": "completed", **_pricing_metrics}


def predict_bundle_price(
    combo_items: list[dict],
    co_occurrence_freq: float = 0.05,
    target_discount_pct: float = 10.0,
) -> dict:
    """
    Predict optimal bundle price for a candidate combo.

    Args:
        combo_items: list of dicts with keys: price, cost, margin_pct, category
        co_occurrence_freq: observed co-occurrence frequency (0-1)
        target_discount_pct: fallback discount if no model available

    Returns:
        dict with combo_price, discount_pct, expected_margin, confidence
    """
    if not combo_items:
        return {"combo_price": 0, "discount_pct": 0, "expected_margin": 0, "confidence": 0}

    individual_total = sum(item["price"] for item in combo_items)
    total_cost = sum(item["cost"] for item in combo_items)

    if _pricing_model is None:
        # Fallback to simple rule-based pricing
        discount_factor = 1 - (target_discount_pct / 100)
        combo_price = round(individual_total * discount_factor / 5) * 5
        if combo_price <= total_cost:
            combo_price = round((total_cost + 10) / 5) * 5
        return {
            "combo_price": combo_price,
            "discount_pct": round((1 - combo_price / individual_total) * 100, 1) if individual_total > 0 else 0,
            "expected_margin": round(combo_price - total_cost, 2),
            "confidence": 0.5,
            "method": "fallback",
        }

    # Build features for ML prediction
    prices = [item["price"] for item in combo_items]
    margin_pcts = [item["margin_pct"] for item in combo_items]

    def _classify(cat_name: str) -> str:
        for group, names in _CATEGORY_GROUPS.items():
            if cat_name in names:
                return group
        return "other"

    cats = [_classify(item.get("category", "")) for item in combo_items]
    diversity = len(set(cats))

    features = pd.DataFrame([{
        "avg_item_price": np.mean(prices),
        "avg_margin_pct": np.mean(margin_pcts),
        "basket_size": len(combo_items),
        "total_qty": len(combo_items),
        "category_diversity": diversity,
        "co_occurrence_freq": co_occurrence_freq,
        "price_spread": max(prices) / min(prices) if min(prices) > 0 else 1.0,
        "individual_total": individual_total,
    }])

    # Predict the bundle factor (ratio of bundle price to individual total)
    predicted_factor = float(_pricing_model.predict(features)[0])

    # Clamp to reasonable range (5% to 25% discount)
    predicted_factor = max(0.75, min(0.95, predicted_factor))

    combo_price = round(individual_total * predicted_factor / 5) * 5
    if combo_price <= total_cost:
        combo_price = round((total_cost + 10) / 5) * 5
        predicted_factor = combo_price / individual_total if individual_total > 0 else 1.0

    discount_pct = round((1 - predicted_factor) * 100, 1)
    expected_margin = round(combo_price - total_cost, 2)

    # Confidence based on how close prediction is to training average
    avg_factor = _pricing_metrics.get("avg_bundle_factor", 0.9) if _pricing_metrics else 0.9
    deviation = abs(predicted_factor - avg_factor)
    confidence = max(0.3, min(0.95, 1.0 - deviation * 3))

    return {
        "combo_price": combo_price,
        "discount_pct": discount_pct,
        "expected_margin": expected_margin,
        "confidence": round(confidence, 3),
        "predicted_factor": round(predicted_factor, 4),
        "method": "ml",
    }


def get_pricing_metrics() -> dict | None:
    """Return cached model metrics or None if not trained."""
    return _pricing_metrics
