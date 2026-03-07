"""
combo_engine.py — Correlation-Based Combo Generator
=====================================================
Uses Pearson/Phi correlation on a boolean purchase basket matrix
to discover items that are genuinely ordered together more than
by random chance, then ranks and prices them with a Random Forest.

Approach:
- Basketize the last N orders from v_sales
- Build item × order boolean matrix
- Compute pairwise Phi (Pearson on bool) correlations
- Threshold strong pairs, extend to triples
- Price combos with Random Forest Regressor
- Persist results to DB; always fast for the frontend
"""

import logging
import os
import threading
from collections import Counter

import itertools

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from models import MenuItem, VSale, ComboSuggestion, Category

# Thread-safe tracking of training state
_train_lock = threading.Lock()
_last_trained_order_count = 0
_training_in_progress = False
_last_ml_summary: dict | None = None  # Set by _run_ml_pipeline; returned with combos for UI

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

# Min Pearson/Phi correlation to treat a pair as a candidate combo
_COMBO_MIN_CORRELATION = float(os.getenv("COMBO_MIN_CORRELATION", "0.07"))
_COMBO_MAX_COMBOS = int(os.getenv("COMBO_MAX_COMBOS", "20"))
_COMBO_WINDOW_SIZE = int(os.getenv("COMBO_WINDOW_SIZE", "200"))
_COMBO_UPDATE_THRESHOLD = int(os.getenv("COMBO_UPDATE_THRESHOLD", "50"))
_COMBO_DEFAULT_DISCOUNT_PCT = float(os.getenv("COMBO_DEFAULT_DISCOUNT_PCT", "10.0"))

logger = logging.getLogger("petpooja.revenue.combo")


def generate_combos(
    db: Session,
    min_support: float = _COMBO_MIN_CORRELATION,
    max_combos: int = _COMBO_MAX_COMBOS,
    window_size: int = _COMBO_WINDOW_SIZE,
    update_threshold: int = _COMBO_UPDATE_THRESHOLD,
    target_discount_pct: float = _COMBO_DEFAULT_DISCOUNT_PCT,
    force_retrain: bool = False,
) -> list[dict]:
    """
    Generate combo suggestions using Pearson correlation on the basket matrix.

    Uses a sliding window over recent orders and caches results in the
    ComboSuggestion table. Retrains on-demand (force_retrain=True) or
    when enough new orders accumulate since last training.

    Args:
        db: Database session
        min_support: Minimum Phi/Pearson correlation threshold (0-1)
        max_combos: Maximum combos to return
        window_size: Number of recent orders to analyze
        update_threshold: Retrain after this many new orders
        target_discount_pct: Default bundle discount percentage
        force_retrain: If True, retrain regardless of threshold

    Returns:
        List of combo dicts with item names, confidence, lift (=corr), bundle price
    """
    global _last_trained_order_count

    # 1. Determine if we need to (re)train the ML model
    total_orders = (
        db.query(func.count(func.distinct(VSale.order_id))).scalar() or 0
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
                min_confidence=0.0,
                min_lift=0.0,
                max_combos=max_combos,
                window_size=window_size,
                target_discount_pct=target_discount_pct,
            )
            _last_trained_order_count = total_orders

    # 2. Return cached combos from the database and last ML run summary for UI
    return _fetch_combos_from_db(db), _last_ml_summary


def get_last_ml_summary() -> dict | None:
    """Return summary of last combo ML pipeline run for UI (orders_used, pricing_model, etc.)."""
    return _last_ml_summary


def fetch_combos_from_db(db: Session, restaurant_id: int = None) -> list[dict]:
    """
    Public read-only accessor: fetch pre-computed combos from the DB.
    Used by the API endpoint — never triggers training.
    """
    return _fetch_combos_from_db(db, restaurant_id=restaurant_id)


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
            import traceback
            logger.error("Background combo training failed: %s\n%s", e, traceback.format_exc())
        finally:
            _training_in_progress = False
            db.close()

    thread = threading.Thread(target=_train, daemon=True, name="combo-trainer")
    thread.start()


def start_combo_scheduler(db_session_factory):
    """
    Start a periodic background scheduler that retrains combos.
    Delays the first run by 30s (server warm-up), then every COMBO_RETRAIN_INTERVAL_SEC.
    Skips training on first run if combos already exist in DB.
    """
    global _scheduler_timer

    def _run_and_reschedule(skip_if_exists: bool = False):
        global _scheduler_timer
        try:
            if skip_if_exists:
                from database import SessionLocal as _SL
                _db = _SL()
                try:
                    count = _db.query(ComboSuggestion).count()
                finally:
                    _db.close()
                if count > 0:
                    logger.info(
                        "Combo scheduler: %d combos already in DB, skipping initial training", count
                    )
                else:
                    run_combo_training_background(db_session_factory)
            else:
                run_combo_training_background(db_session_factory)
        except Exception as e:
            logger.error("Combo scheduler tick error: %s", e)
        finally:
            _scheduler_timer = threading.Timer(
                _COMBO_RETRAIN_INTERVAL_SEC, _run_and_reschedule
            )
            _scheduler_timer.daemon = True
            _scheduler_timer.start()

    # Delay first run 30 seconds so the server is fully initialised
    _scheduler_timer = threading.Timer(
        30, lambda: _run_and_reschedule(skip_if_exists=True)
    )
    _scheduler_timer.daemon = True
    _scheduler_timer.start()
    logger.info(
        "Combo scheduler started (first run in 30s, interval=%ds)", _COMBO_RETRAIN_INTERVAL_SEC
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
    """Run correlation-based combo discovery on the last `window_size` orders."""

    # Step A: Get the most recent N distinct order IDs
    recent_order_ids_subquery = (
        db.query(
            VSale.order_id,
            func.max(VSale.sold_at).label("latest_sold_at"),
        )
        .group_by(VSale.order_id)
        .order_by(desc("latest_sold_at"))
        .limit(window_size)
        .subquery()
    )

    # Step B: Get all transactions for these recent orders
    transactions_raw = (
        db.query(
            VSale.order_id,
            MenuItem.id,
            MenuItem.name,
            MenuItem.selling_price,
            MenuItem.food_cost,
            Category.name.label("category_name"),
            MenuItem.restaurant_id,
        )
        .join(MenuItem, VSale.item_id == MenuItem.id)
        .outerjoin(Category, MenuItem.category_id == Category.id)
        .join(
            recent_order_ids_subquery,
            VSale.order_id == recent_order_ids_subquery.c.order_id,
        )
        .all()
    )

    if not transactions_raw:
        logger.warning("No transactions found -- cannot generate combos")
        global _last_ml_summary
        _last_ml_summary = {"orders_used": 0, "trained": False, "reason": "no_transactions"}
        return

    # Step C: Group by order_id and collect item info
    baskets: dict[str, set] = {}
    item_info: dict[str, dict] = {}

    for order_id, item_id, name, price, cost, category_name, rest_id in transactions_raw:
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
                "restaurant_id": rest_id,
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

    # Step E: Compute pairwise Phi (Pearson on booleans) correlation matrix
    # This directly measures whether items appear together more than by random chance
    try:
        corr_matrix = basket_df.corr(method="pearson")
    except Exception as e:
        logger.error("Correlation matrix failed: %s -- falling back", e)
        _save_fallback_combos(db, baskets, item_info, max_combos, target_discount_pct)
        global _last_ml_summary
        _last_ml_summary = {"orders_used": len(baskets), "window_size": window_size, "pricing_model": "rule-based", "trained": True, "reason": "correlation_fallback"}
        return

    items_list = list(basket_df.columns)
    n_items = len(items_list)
    logger.info("Correlation matrix built: %d × %d items", n_items, n_items)

    # Step F: Extract strongly correlated pairs above threshold
    min_corr = min_support  # reuse the tunable threshold (env: COMBO_MIN_CORRELATION)
    candidate_pairs: list[tuple[str, str, float]] = []  # (itemA, itemB, corr)
    for i in range(n_items):
        for j in range(i + 1, n_items):
            a, b = items_list[i], items_list[j]
            r = corr_matrix.at[a, b]
            if pd.notna(r) and r >= min_corr:
                candidate_pairs.append((a, b, float(r)))

    # Sort pairs by correlation descending
    candidate_pairs.sort(key=lambda x: x[2], reverse=True)
    logger.info("Found %d correlated pairs above threshold %.3f", len(candidate_pairs), min_corr)

    if not candidate_pairs:
        logger.warning("No correlated pairs found -- falling back")
        _save_fallback_combos(db, baskets, item_info, max_combos, target_discount_pct)
        global _last_ml_summary
        _last_ml_summary = {"orders_used": len(baskets), "window_size": window_size, "correlation_pairs": 0, "pricing_model": "rule-based", "trained": True, "reason": "no_pairs_fallback"}
        return

    # Step G: Build candidate item sets (pairs + triples)
    # For triples: extend pairs by adding a third item that is correlated with BOTH members
    corr_lookup: dict[frozenset, float] = {
        frozenset({a, b}): r for a, b, r in candidate_pairs
    }

    candidate_sets: list[tuple[frozenset, float]] = []
    seen_keys: set[frozenset] = set()

    # All strong pairs become candidates
    for a, b, r in candidate_pairs:
        key = frozenset({a, b})
        if key not in seen_keys:
            seen_keys.add(key)
            candidate_sets.append((key, r))

    # Build triples from the top pairs only (limit blast to top-60 pairs)
    top_pairs = candidate_pairs[:60]
    pair_items = sorted({item for a, b, _ in top_pairs for item in (a, b)})
    for a, b, r_ab in top_pairs:
        for c in pair_items:
            if c == a or c == b:
                continue
            r_ac = corr_lookup.get(frozenset({a, c}), 0.0)
            r_bc = corr_lookup.get(frozenset({b, c}), 0.0)
            if r_ac >= min_corr and r_bc >= min_corr:
                key = frozenset({a, b, c})
                if key not in seen_keys:
                    seen_keys.add(key)
                    avg_r = (r_ab + r_ac + r_bc) / 3
                    candidate_sets.append((key, avg_r))

    logger.info("Total candidate sets (pairs + triples): %d", len(candidate_sets))

    # --- ML-Powered Pricing via bundle_pricer (replaces synthetic RF) ---
    try:
        from .bundle_pricer import train_pricing_model, predict_bundle_price
        pricing_result = train_pricing_model(db)
        use_ml_pricing = pricing_result.get("status") == "completed"
        if use_ml_pricing:
            logger.info("Using ML bundle pricer (trained on %d baskets)", pricing_result.get("training_baskets", 0))
        else:
            logger.info("ML pricing skipped (%s) — using rule-based fallback", pricing_result.get("reason", "unknown"))
    except Exception as e:
        logger.warning("ML pricing import/train failed: %s — using rule-based fallback", e)
        use_ml_pricing = False

    # Step H: Convert candidate sets → scored combo dicts
    combos = []
    for combo_key, corr_strength in candidate_sets:
        all_names = sorted(combo_key)
        all_infos = [item_info.get(n) for n in all_names]
        if not all(all_infos):
            continue

        item_categories = [info.get("category", "") for info in all_infos]
        diversity_mult = _score_category_diversity(item_categories)

        individual_total = sum(info["price"] for info in all_infos)
        total_cost = sum(info["cost"] for info in all_infos)
        avg_margin_all = sum(info["cm_pct"] for info in all_infos) / len(all_infos)

        # Use actual observed co-occurrence count from baskets as support proxy
        n_orders = len(baskets)
        co_count = sum(1 for items in baskets.values() if all(n in items for n in all_names))
        support_value = co_count / n_orders if n_orders else 0.0

        # Price the combo using ML or rule-based fallback
        if use_ml_pricing:
            combo_items = [
                {"price": info["price"], "cost": info["cost"],
                 "margin_pct": info["cm_pct"], "category": info["category"]}
                for info in all_infos
            ]
            pricing = predict_bundle_price(
                combo_items=combo_items,
                co_occurrence_freq=support_value,
                target_discount_pct=target_discount_pct,
            )
            suggested_bundle_price = pricing["combo_price"]
            ml_predicted_discount = pricing["discount_pct"]
            ml_confidence_score = pricing["confidence"]
            expected_margin = pricing["expected_margin"]
        else:
            # Rule-based fallback: apply target discount, clamp above cost
            discount_factor = 1 - (target_discount_pct / 100)
            suggested_bundle_price = round(individual_total * discount_factor / 5) * 5
            if suggested_bundle_price <= total_cost:
                suggested_bundle_price = round((total_cost + 10) / 5) * 5
            ml_predicted_discount = round((1 - suggested_bundle_price / individual_total) * 100, 1) if individual_total > 0 else 0
            ml_confidence_score = 0.5 + corr_strength * 0.3
            expected_margin = round(suggested_bundle_price - total_cost, 2)

        combo_score = corr_strength * avg_margin_all * ml_confidence_score * diversity_mult

        combos.append({
            "name": " + ".join(all_names) + " Combo",
            "item_ids": [item_info[n]["id"] for n in all_names],
            "item_names": all_names,
            "restaurant_id": all_infos[0]["restaurant_id"],
            "individual_total": individual_total,
            "combo_price": suggested_bundle_price,
            "discount_pct": ml_predicted_discount,
            "expected_margin": expected_margin,
            "support": round(support_value, 4),
            "confidence": round(ml_confidence_score, 4),
            "lift": round(corr_strength, 4),
            "combo_score": round(combo_score, 4),
        })

    combos.sort(key=lambda c: c["combo_score"], reverse=True)
    combos = combos[:max_combos]

    _save_combos_to_db(db, combos)
    logger.info("Saved %d combo suggestions to DB (pricing=%s)", len(combos), "ml" if use_ml_pricing else "rule-based")

    global _last_ml_summary
    _last_ml_summary = {
        "orders_used": len(baskets),
        "window_size": window_size,
        "combos_saved": len(combos),
        "pricing_model": "ml" if use_ml_pricing else "rule-based",
        "correlation_pairs": len(candidate_pairs),
        "trained": True,
    }


# -- DB Persistence --------------------------------------------------------

def _save_combos_to_db(db: Session, combos: list[dict]):
    """Persist combo suggestions to the ComboSuggestion table.
    Only replaces existing rows when we have new combos to write, so
    a pipeline crash never leaves the table empty.
    """
    if not combos:
        logger.warning("_save_combos_to_db: no combos to save, keeping existing rows")
        return
    try:
        # Build all ORM objects FIRST before touching the DB
        new_combos = []
        for combo in combos:
            new_combos.append(ComboSuggestion(
                restaurant_id=combo.get("restaurant_id"),
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

        # Only now wipe+replace atomically
        db.query(ComboSuggestion).delete()
        db.add_all(new_combos)
        db.commit()
        logger.info("_save_combos_to_db: committed %d rows", len(new_combos))
    except Exception as e:
        db.rollback()
        logger.error("Error saving combos to DB: %s", e)


def _fetch_combos_from_db(db: Session, restaurant_id: int = None) -> list[dict]:
    """Retrieve cached combos from the database, filtering out those with out-of-stock items."""
    q = db.query(ComboSuggestion).order_by(desc(ComboSuggestion.combo_score))
    if restaurant_id:
        q = q.filter(ComboSuggestion.restaurant_id == restaurant_id)
    db_combos = q.all()

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

        # Get exact lifetime occurrence of this specific combo pattern in actual database
        occurrence_count = 0
        if c.item_ids:
            subq = (
                db.query(VSale.order_id)
                .filter(VSale.item_id.in_(c.item_ids))
                .group_by(VSale.order_id)
                .having(func.count(func.distinct(VSale.item_id)) == len(c.item_ids))
                .subquery()
            )
            occurrence_count = db.query(func.count(func.distinct(subq.c.order_id))).scalar() or 0

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
            "occurrence_count": occurrence_count,
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
