"""
combo_engine.py — FP-Growth Combo Generator
==============================================
Uses FP-Growth algorithm (via mlxtend) to discover
frequently co-ordered item sets and generate
profitable combo suggestions with association rules.

Supports:
- Sliding window (last N orders) for trend relevance
- DB caching via ComboSuggestion table
- Automatic retraining when enough new orders arrive
- Fallback pair counting when mlxtend is unavailable
"""

import logging
import threading
from collections import Counter

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from mlxtend.frequent_patterns import fpgrowth, association_rules

from models import MenuItem, SaleTransaction, ComboSuggestion

# Thread-safe tracking of training state
_train_lock = threading.Lock()
_last_trained_order_count = 0

logger = logging.getLogger("petpooja.revenue.combo")


def generate_combos(
    db: Session,
    min_support: float = 0.04,
    min_confidence: float = 0.30,
    min_lift: float = 1.2,
    max_combos: int = 20,
    window_size: int = 500,
    update_threshold: int = 50,
    target_discount_pct: float = 10.0,
) -> list[dict]:
    """
    Generate combo suggestions using FP-Growth + association rules.

    Uses a sliding window over recent orders and caches results in the
    ComboSuggestion table. Only retrains when enough new orders arrive.

    Args:
        db: Database session
        min_support: Minimum support threshold (0-1)
        min_confidence: Minimum confidence for rules
        min_lift: Minimum lift for rules
        max_combos: Maximum combos to return
        window_size: Number of recent orders to analyze
        update_threshold: Retrain after this many new orders
        target_discount_pct: Bundle discount percentage

    Returns:
        List of combo dicts with item names, confidence, lift, cm_gain, bundle price
    """
    global _last_trained_order_count

    # 1. Determine if we need to (re)train the ML model
    total_orders = (
        db.query(func.count(func.distinct(SaleTransaction.order_id))).scalar() or 0
    )
    existing_combos_count = db.query(ComboSuggestion).count()

    with _train_lock:
        needs_training = (
            existing_combos_count == 0
            or total_orders >= _last_trained_order_count + update_threshold
        )

        if needs_training and total_orders > 0:
            logger.info(
                "Training Combo ML Model (orders: %d, window: %d)",
                total_orders, window_size,
            )
            _run_ml_pipeline(
                db,
                min_support=min_support,
                min_confidence=min_confidence,
                min_lift=min_lift,
                max_combos=max_combos,
                window_size=window_size,
                target_discount_pct=target_discount_pct,
            )
            _last_trained_order_count = total_orders

    # 2. Return cached combos from the database
    return _fetch_combos_from_db(db)


# -- ML Pipeline ----------------------------------------------------------

def _run_ml_pipeline(
    db: Session,
    min_support: float,
    min_confidence: float,
    min_lift: float,
    max_combos: int,
    window_size: int,
    target_discount_pct: float,
):
    """Run FP-Growth on a sliding window of recent orders, persist results."""

    # Step A: Get the most recent N distinct order IDs
    recent_order_ids_subquery = (
        db.query(
            SaleTransaction.order_id,
            func.max(SaleTransaction.sold_at).label("latest_sold_at"),
        )
        .group_by(SaleTransaction.order_id)
        .order_by(desc("latest_sold_at"))
        .limit(window_size)
        .subquery()
    )

    # Step B: Get all transactions for these recent orders
    transactions_raw = (
        db.query(
            SaleTransaction.order_id,
            MenuItem.id,
            MenuItem.name,
            MenuItem.selling_price,
            MenuItem.food_cost,
        )
        .join(MenuItem, SaleTransaction.item_id == MenuItem.id)
        .join(
            recent_order_ids_subquery,
            SaleTransaction.order_id == recent_order_ids_subquery.c.order_id,
        )
        .all()
    )

    if not transactions_raw:
        logger.warning("No transactions found -- cannot generate combos")
        return

    # Step C: Group by order_id and collect item info
    baskets: dict[str, set] = {}
    item_info: dict[str, dict] = {}

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

    logger.info(
        "Built baskets from %d orders, %d unique items",
        len(baskets), len(item_info),
    )

    # Step D: Boolean basket matrix
    all_items = sorted(item_info.keys())
    rows = []
    for order_id, items in baskets.items():
        row = {item: (item in items) for item in all_items}
        rows.append(row)

    basket_df = pd.DataFrame(rows, columns=all_items).astype(bool)

    # Step E: Run FP-Growth
    try:
        frequent = fpgrowth(basket_df, min_support=min_support, use_colnames=True)

        if frequent.empty:
            logger.warning("No frequent itemsets found -- try lowering min_support")
            _save_fallback_combos(db, baskets, item_info, max_combos, target_discount_pct)
            return

        logger.info("Found %d frequent itemsets", len(frequent))

        # Step F: Association rules
        rules = association_rules(frequent, metric="lift", min_threshold=min_lift)

        if rules.empty:
            logger.warning("No association rules found -- using fallback")
            _save_fallback_combos(db, baskets, item_info, max_combos, target_discount_pct)
            return

        logger.info("Generated %d association rules", len(rules))

    except Exception as e:
        logger.error("FP-Growth pipeline error: %s -- falling back to pair counting", e)
        _save_fallback_combos(db, baskets, item_info, max_combos, target_discount_pct)
        return

    # Step G: Filter rules
    rules = rules[rules["confidence"] >= min_confidence]
    rules = rules[rules["consequents"].apply(lambda x: len(x) == 1)]

    if rules.empty:
        logger.warning("No rules passed filters -- using fallback")
        _save_fallback_combos(db, baskets, item_info, max_combos, target_discount_pct)
        return

    # Step H: Score each rule and build combos
    combos = []
    for _, rule in rules.iterrows():
        antecedents = list(rule["antecedents"])
        consequents = list(rule["consequents"])
        confidence = rule["confidence"]
        lift = rule["lift"]
        support = rule["support"]

        consequent_name = consequents[0]
        consequent_info = item_info.get(consequent_name)
        if not consequent_info:
            continue

        antecedent_infos = [item_info.get(a) for a in antecedents]
        if not all(antecedent_infos):
            continue

        # combo_score = lift x avg_cm_of_consequent x confidence
        avg_cm_consequent = consequent_info["cm_pct"]
        combo_score = lift * avg_cm_consequent * confidence

        all_names = antecedents + consequents
        all_infos = antecedent_infos + [consequent_info]
        individual_total = sum(info["price"] for info in all_infos)
        total_cost = sum(info["cost"] for info in all_infos)
        discount_factor = 1 - (target_discount_pct / 100)
        suggested_bundle_price = round(individual_total * discount_factor, 2)
        expected_margin = round(suggested_bundle_price - total_cost, 2)

        combos.append({
            "name": " + ".join(all_names) + " Combo",
            "item_ids": [item_info[n]["id"] for n in all_names],
            "item_names": all_names,
            "individual_total": individual_total,
            "combo_price": suggested_bundle_price,
            "discount_pct": target_discount_pct,
            "expected_margin": expected_margin,
            "support": round(support, 4),
            "confidence": round(confidence, 4),
            "lift": round(lift, 4),
            "combo_score": round(combo_score, 2),
        })

    # Sort by combo_score descending, take top N
    combos.sort(key=lambda c: c["combo_score"], reverse=True)
    combos = combos[:max_combos]

    # Persist to DB
    _save_combos_to_db(db, combos)

    logger.info(f"Saved {len(combos)} combo suggestions to DB")


# -- DB Persistence --------------------------------------------------------

def _save_combos_to_db(db: Session, combos: list[dict]):
    """Persist combo suggestions to the ComboSuggestion table."""
    try:
        # Build new combo objects first, then delete+insert in one transaction
        new_combos = []
        for combo in combos:
            new_combos.append(ComboSuggestion(
                name=combo["name"],
                item_ids=combo["item_ids"],
                item_names=combo["item_names"],
                individual_total=combo["individual_total"],
                combo_price=combo["combo_price"],
                discount_pct=combo["discount_pct"],
                expected_margin=combo["expected_margin"],
                support=combo["support"],
                confidence=combo["confidence"],
                lift=combo.get("lift"),
                combo_score=combo.get("combo_score"),
            ))

        db.query(ComboSuggestion).delete()
        db.add_all(new_combos)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Error saving combos to DB: %s", e)


def _fetch_combos_from_db(db: Session) -> list[dict]:
    """Retrieve cached combos from the database."""
    db_combos = (
        db.query(ComboSuggestion)
        .order_by(desc(ComboSuggestion.combo_score))
        .all()
    )

    result = []
    for i, c in enumerate(db_combos):
        margin_pct = (
            round((c.expected_margin / c.combo_price) * 100, 1)
            if c.combo_price and c.combo_price > 0
            else 0
        )
        result.append({
            "combo_id": f"COMBO-{i + 1:03d}",
            "name": c.name,
            "item_ids": c.item_ids,
            "item_names": c.item_names,
            "items": [
                {"id": item_id, "name": name}
                for item_id, name in zip(c.item_ids or [], c.item_names or [])
            ],
            "individual_total": c.individual_total,
            "combo_price": c.combo_price,
            "suggested_bundle_price": c.combo_price,
            "discount_pct": c.discount_pct,
            "expected_margin": c.expected_margin,
            "cm_gain": c.expected_margin,
            "margin_pct": margin_pct,
            "support": round(c.support, 4) if c.support else 0.0,
            "confidence": round(c.confidence, 4) if c.confidence else 0.0,
            "lift": round(c.lift, 4) if c.lift else 0.0,
            "combo_score": round(c.combo_score, 2) if c.combo_score else 0.0,
        })

    return result


# -- Fallback (pair counting) ----------------------------------------------

def _save_fallback_combos(
    db: Session,
    baskets: dict,
    item_info: dict,
    max_combos: int,
    discount_pct: float,
):
    """Fallback pair counting when FP-Growth yields no usable rules."""
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
        discount_factor = 1 - (discount_pct / 100)
        bundle = round(total * discount_factor, 2)
        expected_margin = round(bundle - info_a["cost"] - info_b["cost"], 2)

        combos.append({
            "name": f"{a} + {b} Combo",
            "item_ids": [info_a["id"], info_b["id"]],
            "item_names": [a, b],
            "individual_total": total,
            "combo_price": bundle,
            "discount_pct": discount_pct,
            "expected_margin": expected_margin,
            "support": round(support, 4),
            "confidence": round(support, 4),
            "lift": 1.0,
            "combo_score": round(support * 100, 2),
        })

    _save_combos_to_db(db, combos)
