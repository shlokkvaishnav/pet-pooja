"""
combo_engine.py — FP-Growth Combo Generator
==============================================
Uses FP-Growth algorithm (via mlxtend) to discover
frequently co-ordered item sets and generate
profitable combo suggestions with association rules.
"""

import logging
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from models import MenuItem, SaleTransaction

logger = logging.getLogger("petpooja.revenue.combo")


def generate_combos(
    db: Session,
    min_support: float = 0.04,
    min_confidence: float = 0.30,
    min_lift: float = 1.2,
    max_combos: int = 20,
) -> list[dict]:
    """
    Generate combo suggestions using FP-Growth + association rules.

    Steps:
    1. Build boolean basket matrix (order × item)
    2. Run FP-Growth for frequent itemsets
    3. Generate association rules
    4. Filter + score rules
    5. Return top combos ranked by combo_score

    Args:
        db: Database session
        min_support: Minimum support threshold (0–1)
        min_confidence: Minimum confidence for rules
        min_lift: Minimum lift for rules
        max_combos: Maximum combos to return

    Returns:
        List of combo dicts with item names, confidence, lift, cm_gain, bundle price
    """
    # ── Step 1: Build basket matrix ──
    transactions_raw = (
        db.query(
            SaleTransaction.order_id,
            MenuItem.id,
            MenuItem.name,
            MenuItem.selling_price,
            MenuItem.food_cost,
        )
        .join(MenuItem, SaleTransaction.item_id == MenuItem.id)
        .all()
    )

    if not transactions_raw:
        logger.warning("No transactions found — cannot generate combos")
        return []

    # Group by order_id and collect item info
    baskets: dict[str, set] = {}
    item_info: dict[int, dict] = {}

    for order_id, item_id, name, price, cost in transactions_raw:
        baskets.setdefault(order_id, set()).add(name)
        if name not in item_info:
            cm = price - cost
            cm_pct = (cm / price * 100) if price > 0 else 0
            item_info[name] = {
                "id": item_id,
                "name": name,
                "price": price,
                "cost": cost,
                "cm": round(cm, 2),
                "cm_pct": round(cm_pct, 1),
            }

    logger.info(f"Built baskets from {len(baskets)} orders, {len(item_info)} unique items")

    # ── Step 2: Boolean basket matrix ──
    # Each order = 1 row, each item = 1 column
    # Values MUST be boolean (True/False) — fpgrowth silently gives wrong results with int
    all_items = sorted(item_info.keys())
    rows = []
    for order_id, items in baskets.items():
        row = {item: (item in items) for item in all_items}
        rows.append(row)

    basket_df = pd.DataFrame(rows, columns=all_items).astype(bool)

    # ── Step 3: Run FP-Growth ──
    try:
        from mlxtend.frequent_patterns import fpgrowth, association_rules

        frequent = fpgrowth(basket_df, min_support=min_support, use_colnames=True)

        if frequent.empty:
            logger.warning("No frequent itemsets found — try lowering min_support")
            return []

        logger.info(f"Found {len(frequent)} frequent itemsets")

        # ── Step 4: Association rules ──
        rules = association_rules(frequent, metric="lift", min_threshold=min_lift)

        if rules.empty:
            logger.warning("No association rules found")
            return []

        logger.info(f"Generated {len(rules)} association rules")

    except ImportError:
        logger.error("mlxtend not installed — falling back to pair counting")
        return _fallback_pair_combos(baskets, item_info, max_combos)

    # ── Step 5: Filter rules ──
    # confidence >= threshold
    rules = rules[rules["confidence"] >= min_confidence]

    # Single-item consequent only (no multi-item combos)
    rules = rules[rules["consequents"].apply(lambda x: len(x) == 1)]

    if rules.empty:
        logger.warning("No rules passed filters")
        return []

    # ── Step 6: Score each rule ──
    combos = []
    for _, rule in rules.iterrows():
        antecedents = list(rule["antecedents"])
        consequents = list(rule["consequents"])
        confidence = rule["confidence"]
        lift = rule["lift"]
        support = rule["support"]

        # Get CM info for consequent
        consequent_name = consequents[0]
        consequent_info = item_info.get(consequent_name)
        if not consequent_info:
            continue

        # Get all antecedent info
        antecedent_infos = [item_info.get(a) for a in antecedents]
        if not all(antecedent_infos):
            continue

        # combo_score = lift × avg_cm_of_consequent × confidence
        avg_cm_consequent = consequent_info["cm_pct"]
        combo_score = lift * avg_cm_consequent * confidence

        # Calculate bundle pricing
        all_names = antecedents + consequents
        all_infos = antecedent_infos + [consequent_info]
        individual_total = sum(info["price"] for info in all_infos)
        total_cost = sum(info["cost"] for info in all_infos)
        suggested_bundle_price = round(individual_total * 0.90, 2)  # 10% discount
        cm_gain = round(suggested_bundle_price - total_cost, 2)

        combos.append({
            "antecedents": antecedents,
            "consequents": consequents,
            "item_names": all_names,
            "items": [
                {"name": info["name"], "price": info["price"], "cm_pct": info["cm_pct"]}
                for info in all_infos
            ],
            "confidence": round(confidence, 4),
            "lift": round(lift, 4),
            "support": round(support, 4),
            "combo_score": round(combo_score, 2),
            "individual_total": individual_total,
            "suggested_bundle_price": suggested_bundle_price,
            "cm_gain": cm_gain,
            "discount_pct": 10.0,
        })

    # Sort by combo_score descending, take top N
    combos.sort(key=lambda c: c["combo_score"], reverse=True)
    combos = combos[:max_combos]

    # Add combo IDs and names
    for i, combo in enumerate(combos):
        combo["combo_id"] = f"COMBO-{i + 1:03d}"
        combo["name"] = " + ".join(combo["item_names"]) + " Combo"

    logger.info(f"Returning {len(combos)} combo suggestions")
    return combos


def _fallback_pair_combos(
    baskets: dict, item_info: dict, max_combos: int
) -> list[dict]:
    """Fallback pair counting when mlxtend is unavailable."""
    from collections import Counter

    n_orders = len(baskets)
    pair_counts: Counter = Counter()

    for items in baskets.values():
        item_list = sorted(items)
        for i in range(len(item_list)):
            for j in range(i + 1, len(item_list)):
                pair_counts[(item_list[i], item_list[j])] += 1

    combos = []
    for (a, b), count in pair_counts.most_common(max_combos):
        support = count / n_orders
        if support < 0.03:
            continue
        info_a = item_info.get(a)
        info_b = item_info.get(b)
        if not info_a or not info_b:
            continue
        total = info_a["price"] + info_b["price"]
        bundle = round(total * 0.9, 2)
        combos.append({
            "antecedents": [a],
            "consequents": [b],
            "item_names": [a, b],
            "items": [
                {"name": a, "price": info_a["price"], "cm_pct": info_a["cm_pct"]},
                {"name": b, "price": info_b["price"], "cm_pct": info_b["cm_pct"]},
            ],
            "confidence": round(support, 4),
            "lift": 1.0,
            "support": round(support, 4),
            "combo_score": round(support * 100, 2),
            "individual_total": total,
            "suggested_bundle_price": bundle,
            "cm_gain": round(bundle - info_a["cost"] - info_b["cost"], 2),
            "discount_pct": 10.0,
            "combo_id": f"COMBO-{len(combos) + 1:03d}",
            "name": f"{a} + {b} Combo",
        })

    return combos
