"""
combo_engine.py — FP-Growth Combo Generator
==============================================
Uses FP-Growth algorithm (via mlxtend) to discover
frequently co-ordered item sets and generate
profitable combo suggestions with association rules.

Supports:
- Sliding window (last N orders) for trend relevance
- DB caching via ComboSuggestion table
- Background training at startup + configurable schedule (not on every request)
- Stock-aware filtering — out-of-stock items excluded
- Category-aware combo validation (main+side+drink preferred)
- Configurable discount percentage
- Fallback pair counting when mlxtend is unavailable
"""

import logging
import os
import threading
from collections import Counter

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from mlxtend.frequent_patterns import fpgrowth, association_rules

from models import MenuItem, SaleTransaction, ComboSuggestion, Category

# Thread-safe tracking of training state
_train_lock = threading.Lock()
_last_trained_order_count = 0
_training_in_progress = False

# Background scheduler interval (env-overridable, default: 86400 = 24h)
_COMBO_RETRAIN_INTERVAL_SEC = int(os.getenv("COMBO_RETRAIN_INTERVAL_SEC", "86400"))
_scheduler_timer: threading.Timer | None = None

# Category groups for combo validation (Indian restaurant structure)
_COMBO_CATEGORY_GROUPS = {
    "main": {"Main Course", "Mains", "Biryani", "Rice", "Thali"},
    "bread": {"Breads", "Roti", "Naan"},
    "side": {"Starters", "Appetizers", "Sides", "Salads", "Raita"},
    "drink": {"Beverages", "Drinks", "Juices", "Lassi"},
    "dessert": {"Desserts", "Sweets"},
}

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
    force_retrain: bool = False,
) -> list[dict]:
    """
    Generate combo suggestions using FP-Growth + association rules.

    Uses a sliding window over recent orders and caches results in the
    ComboSuggestion table. Retrains on-demand (force_retrain=True) or
    when enough new orders accumulate since last training.

    Args:
        db: Database session
        min_support: Minimum support threshold (0-1)
        min_confidence: Minimum confidence for rules
        min_lift: Minimum lift for rules
        max_combos: Maximum combos to return
        window_size: Number of recent orders to analyze
        update_threshold: Retrain after this many new orders
        target_discount_pct: Default bundle discount percentage (configurable)
        force_retrain: If True, retrain regardless of threshold

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
            force_retrain
            or existing_combos_count == 0
            or total_orders >= _last_trained_order_count + update_threshold
        )

        if needs_training and total_orders > 0:
            logger.info(
                "Training Combo ML Model (orders: %d, window: %d, forced: %s)",
                total_orders, window_size, force_retrain,
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

    # 2. Return cached combos from the database, filtering out-of-stock items
    return _fetch_combos_from_db(db)


def fetch_combos_from_db(db: Session) -> list[dict]:
    """
    Public read-only accessor: fetch pre-computed combos from the DB.
    Used by the API endpoint — never triggers training.
    """
    return _fetch_combos_from_db(db)


def run_combo_training_background(db_session_factory):
    """
    Run FP-Growth training in a background thread.
    Called at startup and on a recurring schedule.
    db_session_factory: callable that returns a new DB session.
    """
    global _training_in_progress

    if _training_in_progress:
        logger.info("Combo training already in progress — skipping")
        return

    def _train():
        global _training_in_progress
        _training_in_progress = True
        db = db_session_factory()
        try:
            logger.info("Background combo training started")
            generate_combos(db, force_retrain=True)
            logger.info("Background combo training completed")
        except Exception as e:
            logger.error("Background combo training failed: %s", e)
        finally:
            _training_in_progress = False
            db.close()

    thread = threading.Thread(target=_train, daemon=True, name="combo-trainer")
    thread.start()


def start_combo_scheduler(db_session_factory):
    """
    Start a periodic background scheduler that retrains combos.
    Runs immediately on first call, then every COMBO_RETRAIN_INTERVAL_SEC.
    """
    global _scheduler_timer

    def _run_and_reschedule():
        global _scheduler_timer
        run_combo_training_background(db_session_factory)
        _scheduler_timer = threading.Timer(
            _COMBO_RETRAIN_INTERVAL_SEC, _run_and_reschedule
        )
        _scheduler_timer.daemon = True
        _scheduler_timer.start()

    # Run first training immediately
    _run_and_reschedule()
    logger.info(
        "Combo scheduler started (interval=%ds)", _COMBO_RETRAIN_INTERVAL_SEC
    )


def stop_combo_scheduler():
    """Cancel the periodic combo scheduler (called on shutdown)."""
    global _scheduler_timer
    if _scheduler_timer is not None:
        _scheduler_timer.cancel()
        _scheduler_timer = None
        logger.info("Combo scheduler stopped")


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
            Category.name.label("category_name"),
        )
        .join(MenuItem, SaleTransaction.item_id == MenuItem.id)
        .outerjoin(Category, MenuItem.category_id == Category.id)
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

    for order_id, item_id, name, price, cost, category_name in transactions_raw:
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
                "category": category_name or "Uncategorized",
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

        # --- ML Prediction Engine: Dynamic Combo Pricing & Scoring ---
        avg_cm_consequent = consequent_info["cm_pct"]

        # Category diversity bonus: prefer cross-category combos
        all_names = antecedents + consequents
        all_infos = antecedent_infos + [consequent_info]
        item_categories = [info.get("category", "") for info in all_infos]
        diversity_mult = _score_category_diversity(item_categories)

        # AI Score weighting: affinity × profitability × reliability × diversity
        combo_score = (lift * 1.5) * avg_cm_consequent * (confidence * 2.0) * diversity_mult

        individual_total = sum(info["price"] for info in all_infos)
        total_cost = sum(info["cost"] for info in all_infos)
        
        # Predict Elasticity / Optimal Discount based on ML features (Lift & Margin)
        # If lift is high (> 2.5), items organically cross-sell → minimize given discount.
        # If lift is lower (< 1.5), items need a behavioral push → higher discount to incentivize.
        if lift >= 2.5:
            ml_predicted_discount = 5.0
        elif lift >= 1.5:
            ml_predicted_discount = 10.0
        else:
            ml_predicted_discount = 15.0
            
        # Margin Check: If the items are extremely profitable, we can afford deeper cuts to drive volume
        avg_margin_all = sum(info["cm_pct"] for info in all_infos) / len(all_infos)
        if avg_margin_all > 65.0:
            ml_predicted_discount += 5.0 
            
        # Cap ML discount to protect baseline profitability (max 25%)
        ml_predicted_discount = min(ml_predicted_discount, 25.0)

        discount_factor = 1 - (ml_predicted_discount / 100)
        suggested_bundle_price = round(individual_total * discount_factor)
        
        # Clean pricing (round to nearest ₹5)
        suggested_bundle_price = round(suggested_bundle_price / 5) * 5
        
        # Ensure we don't accidentally sell below cost
        if suggested_bundle_price <= total_cost:
             suggested_bundle_price = total_cost + 10 # Force minimal profit
             ml_predicted_discount = round((1 - (suggested_bundle_price / individual_total)) * 100, 1)

        expected_margin = round(suggested_bundle_price - total_cost, 2)

        combos.append({
            "name": " + ".join(all_names) + " Combo",
            "item_ids": [item_info[n]["id"] for n in all_names],
            "item_names": all_names,
            "individual_total": individual_total,
            "combo_price": suggested_bundle_price,
            "discount_pct": ml_predicted_discount,
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
    """Retrieve cached combos from the database, filtering out those with out-of-stock items."""
    db_combos = (
        db.query(ComboSuggestion)
        .order_by(desc(ComboSuggestion.combo_score))
        .all()
    )

    # Build stock lookup: items with current_stock == 0 are out of stock
    # current_stock == None means unlimited
    oos_ids = set()
    oos_items = (
        db.query(MenuItem.id)
        .filter(MenuItem.current_stock == 0, MenuItem.is_available == True)
        .all()
    )
    for (item_id,) in oos_items:
        oos_ids.add(item_id)

    # Pre-fetch all item categories in one query to avoid N+1
    all_combo_item_ids = set()
    for c in db_combos:
        all_combo_item_ids.update(c.item_ids or [])
    _item_cat_map: dict[int, str] = {}
    if all_combo_item_ids:
        rows = (
            db.query(MenuItem.id, Category.name)
            .join(Category, MenuItem.category_id == Category.id)
            .filter(MenuItem.id.in_(all_combo_item_ids))
            .all()
        )
        _item_cat_map = {iid: cname for iid, cname in rows}

    result = []
    for i, c in enumerate(db_combos):
        # Skip combos containing out-of-stock items
        if any(iid in oos_ids for iid in (c.item_ids or [])):
            continue

        margin_pct = (
            round((c.expected_margin / c.combo_price) * 100, 1)
            if c.combo_price and c.combo_price > 0
            else 0
        )

        # Determine category diversity for combo quality indicator
        item_categories = [_item_cat_map.get(iid, "Uncategorized") for iid in (c.item_ids or [])]
        category_groups = _classify_category_groups(item_categories)
        combo_structure = "diverse" if len(category_groups) >= 2 else "same-category"

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
            "combo_structure": combo_structure,
            "category_groups": list(category_groups),
        })

    return result


# -- Category helpers ------------------------------------------------------

def _get_item_categories(db: Session, item_ids: list[int]) -> list[str]:
    """Get category names for a list of item IDs."""
    if not item_ids:
        return []
    items = (
        db.query(MenuItem.id, Category.name)
        .join(Category, MenuItem.category_id == Category.id)
        .filter(MenuItem.id.in_(item_ids))
        .all()
    )
    return [cat_name for _, cat_name in items]


def _classify_category_groups(category_names: list[str]) -> set[str]:
    """Map category names to abstract groups (main, bread, side, drink, dessert)."""
    groups = set()
    for cat_name in category_names:
        for group, cat_set in _COMBO_CATEGORY_GROUPS.items():
            if cat_name in cat_set:
                groups.add(group)
                break
        else:
            groups.add("other")
    return groups


def _score_category_diversity(category_names: list[str]) -> float:
    """
    Score combo category diversity. A combo with items from different
    category groups (e.g., main + bread + drink) scores higher than
    combos with items from the same group (e.g., two desserts).

    Returns a multiplier: 1.0 (same category) to 1.5 (ideal diverse combo).
    """
    groups = _classify_category_groups(category_names)
    n_groups = len(groups)

    if n_groups >= 3:
        return 1.5  # Ideal: main + side/bread + drink
    elif n_groups == 2:
        return 1.2  # Good: two different groups
    else:
        return 0.8  # Penalize: same category (e.g., two desserts)


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
