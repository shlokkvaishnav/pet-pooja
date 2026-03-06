"""
combo_engine.py — Multi-Signal Combo Generator
=====================================================
Uses multiple association metrics (Phi correlation, Lift, PMI) with
time-decay weighting on a purchase basket matrix to discover items
genuinely ordered together, then scores combos with GradientBoosting
trained on real pair features and prices using margin-aware heuristics.

Approach:
- Basketize the last N orders from v_sales with time-decay weighting
- Build item × order boolean matrix
- Compute pairwise Phi, Lift, PMI, and Support metrics
- Multi-signal filtering for candidate pairs, extend to triples
- Train GradientBoosting on real pair features for combo quality scoring
- Margin-aware pricing with profitability floor
- Persist results to DB; always fast for the frontend
"""

import itertools
import logging
import math
import os
import threading
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from models import MenuItem, VSale, ComboSuggestion, Category, RestaurantSettings, Restaurant
from config import get_default_combo_category_groups

# Thread-safe tracking of training state
_train_lock = threading.Lock()
_last_trained_order_count = 0
_training_in_progress = False

# Background scheduler interval (env-overridable, default: 86400 = 24h)
_COMBO_RETRAIN_INTERVAL_SEC = int(os.getenv("COMBO_RETRAIN_INTERVAL_SEC", "86400"))
_scheduler_timer: threading.Timer | None = None

# Min Pearson/Phi correlation to treat a pair as a candidate combo
_COMBO_MIN_CORRELATION = float(os.getenv("COMBO_MIN_CORRELATION", "0.07"))
_COMBO_MAX_COMBOS = int(os.getenv("COMBO_MAX_COMBOS", "20"))
_COMBO_WINDOW_SIZE = int(os.getenv("COMBO_WINDOW_SIZE", "200"))
_COMBO_UPDATE_THRESHOLD = int(os.getenv("COMBO_UPDATE_THRESHOLD", "50"))
_COMBO_DEFAULT_DISCOUNT_PCT = float(os.getenv("COMBO_DEFAULT_DISCOUNT_PCT", "10.0"))
# AOV uplift % cap so we never show nonsensical values (e.g. 200%+)
_COMBO_AOV_UPLIFT_PCT_CAP = float(os.getenv("COMBO_AOV_UPLIFT_PCT_CAP", "100.0"))
# Max lift to avoid extreme values from rare pairs
_COMBO_MAX_LIFT = float(os.getenv("COMBO_MAX_LIFT", "20.0"))

logger = logging.getLogger("petpooja.revenue.combo")


def _resolve_restaurant_id(db: Session, restaurant_id: int | None) -> int | None:
    """Return restaurant_id if given; otherwise first restaurant's id or None."""
    if restaurant_id is not None:
        return restaurant_id
    first = db.query(Restaurant.id).order_by(Restaurant.id.asc()).first()
    return first[0] if first else None


def _get_combo_category_groups(db: Session, restaurant_id: int | None) -> dict[str, set[str]]:
    """
    Load combo category groups from restaurant settings (DB).
    Keys: abstract group (main, bread, side, drink, dessert). Values: set of category names.
    Falls back to config default when not set in DB.
    """
    default = get_default_combo_category_groups()
    rid = _resolve_restaurant_id(db, restaurant_id)
    if rid is None:
        return {k: set(v) for k, v in default.items()}
    row = db.query(RestaurantSettings).filter(
        RestaurantSettings.restaurant_id == rid
    ).first()
    if not row or not row.combo_category_groups:
        return {k: set(v) for k, v in default.items()}
    raw = row.combo_category_groups
    if not isinstance(raw, dict):
        return {k: set(v) for k, v in default.items()}
    return {
        str(k): set(v) if isinstance(v, (list, tuple)) else {str(v)}
        for k, v in raw.items()
    }


def generate_combos(
    db: Session,
    restaurant_id: int | None = None,
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
            category_groups = _get_combo_category_groups(db, restaurant_id)
            _run_ml_pipeline(
                db,
                min_support=min_support,
                min_confidence=0.0,
                min_lift=0.0,
                max_combos=max_combos,
                window_size=window_size,
                target_discount_pct=target_discount_pct,
                category_groups=category_groups,
            )
            _last_trained_order_count = total_orders

    # 2. Return cached combos from the database, filtering out-of-stock items
    return _fetch_combos_from_db(db, restaurant_id=restaurant_id)


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


# -- Statistical Helpers ---------------------------------------------------

def _compute_pmi(p_ab: float, p_a: float, p_b: float) -> float:
    """Pointwise Mutual Information: log2(P(A,B) / (P(A)*P(B))).
    Measures how much more (or less) two items co-occur vs independence."""
    if p_ab <= 0 or p_a <= 0 or p_b <= 0:
        return 0.0
    return math.log2(p_ab / (p_a * p_b))


def _wilson_lower_bound(successes: int, total: int, z: float = 1.96) -> float:
    """Wilson score lower bound — conservative estimate of true proportion.
    Handles small samples better than raw proportion (successes/total)."""
    if total == 0:
        return 0.0
    p = successes / total
    denominator = 1 + z ** 2 / total
    centre = p + z ** 2 / (2 * total)
    spread = z * math.sqrt((p * (1 - p) + z ** 2 / (4 * total)) / total)
    return max((centre - spread) / denominator, 0.0)


# -- ML Pipeline ----------------------------------------------------------

def _run_ml_pipeline(
    db: Session,
    min_support: float,
    min_confidence: float,
    min_lift: float,
    max_combos: int,
    window_size: int,
    target_discount_pct: float,
    category_groups: dict[str, set[str]] | None = None,
):
    """Run multi-signal combo discovery on the last `window_size` orders.

    Pipeline:
    1. Fetch recent orders with timestamps for time-decay weighting
    2. Compute item marginal probabilities (time-weighted)
    3. Build Phi correlation matrix + pairwise Lift, PMI, Support, Confidence
    4. Multi-signal filtering (lift > 1 OR phi > threshold, min 2 co-occurrences)
    5. Train GradientBoosting on real pair features for combo quality scoring
    6. Extend pairs to triples using geometric mean of sub-pair quality
    7. Margin-aware pricing with profitability floor
    """

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

    # Step B: Get all transactions (include sold_at for time-decay, total_price for AOV)
    transactions_raw = (
        db.query(
            VSale.order_id,
            MenuItem.id,
            MenuItem.name,
            MenuItem.selling_price,
            MenuItem.food_cost,
            Category.name.label("category_name"),
            MenuItem.restaurant_id,
            VSale.sold_at,
            VSale.total_price,
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
        return

    if category_groups is None:
        category_groups = {k: set(v) for k, v in get_default_combo_category_groups().items()}

    # Step C: Build baskets, item info, order timestamps, and order totals
    baskets: dict[str, set] = {}
    item_info: dict[str, dict] = {}
    order_timestamps: dict = {}
    order_totals: dict[str, float] = {}  # order_id -> sum of line-item revenue

    for row in transactions_raw:
        order_id = row[0]
        item_id, name, price, cost = row[1], row[2], row[3], row[4]
        category_name, rest_id, sold_at = row[5], row[6], row[7]
        line_total = row[8] or 0.0

        baskets.setdefault(order_id, set()).add(name)
        order_totals[order_id] = order_totals.get(order_id, 0.0) + float(line_total)
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
        # Track latest timestamp per order
        if sold_at and (order_id not in order_timestamps or sold_at > order_timestamps[order_id]):
            order_timestamps[order_id] = sold_at

    # Compute global AOV from order totals in the window
    global_aov = (
        sum(order_totals.values()) / len(order_totals)
        if order_totals else 0.0
    )

    logger.info(
        "Built baskets from %d orders, %d unique items",
        len(baskets), len(item_info),
    )

    # Step D: Compute time-decay weights (exponential, half-life = 30 days)
    _HALF_LIFE_DAYS = 30
    if order_timestamps:
        max_ts = max(order_timestamps.values())
        decay_weights = {}
        for oid in baskets:
            ts = order_timestamps.get(oid)
            if ts and max_ts:
                age_days = max((max_ts - ts).total_seconds() / 86400, 0)
                decay_weights[oid] = 2.0 ** (-age_days / _HALF_LIFE_DAYS)
            else:
                decay_weights[oid] = 1.0
    else:
        decay_weights = {oid: 1.0 for oid in baskets}
    total_weight = sum(decay_weights.values()) or 1.0  # avoid division by zero

    # Step E: Compute item marginal probabilities (time-decay weighted)
    item_weighted_freq: dict[str, float] = {}
    for oid, items in baskets.items():
        w = decay_weights[oid]
        for item in items:
            item_weighted_freq[item] = item_weighted_freq.get(item, 0.0) + w
    item_prob = {
        item: freq / total_weight for item, freq in item_weighted_freq.items()
    }

    # Step F: Boolean basket matrix + Phi correlation
    all_items = sorted(item_info.keys())
    rows = []
    for order_id, items in baskets.items():
        row = {item: (item in items) for item in all_items}
        rows.append(row)

    basket_df = pd.DataFrame(rows, columns=all_items).astype(bool)

    try:
        corr_matrix = basket_df.corr(method="pearson")
        # Replace NaN/Inf so downstream loops don't produce invalid metrics
        corr_matrix = corr_matrix.fillna(0.0).replace([np.inf, -np.inf], 0.0)
    except Exception as e:
        logger.error("Correlation matrix failed: %s -- falling back", e)
        _save_fallback_combos(db, baskets, item_info, max_combos, target_discount_pct, global_aov=global_aov)
        return

    items_list = list(basket_df.columns)
    n_items = len(items_list)
    logger.info("Correlation matrix built: %d × %d items", n_items, n_items)

    # Step G: Compute full pairwise association metrics
    min_corr = min_support
    pair_metrics: dict[frozenset, dict] = {}

    for i in range(n_items):
        for j in range(i + 1, n_items):
            a, b = items_list[i], items_list[j]
            phi = corr_matrix.at[a, b]
            if pd.isna(phi):
                continue

            # Time-weighted co-occurrence
            co_weight = sum(
                decay_weights[oid]
                for oid, items in baskets.items()
                if a in items and b in items
            )
            support = co_weight / total_weight if total_weight > 0 else 0.0
            raw_co_count = sum(1 for items in baskets.values() if a in items and b in items)

            if raw_co_count < 2:
                continue  # Need at least 2 co-occurrences for statistical relevance

            p_a = item_prob.get(a, 0)
            p_b = item_prob.get(b, 0)
            expected = p_a * p_b

            # Lift: observed co-occurrence vs expected under independence (cap to avoid extreme values)
            lift_raw = support / expected if expected > 0 else 0.0
            lift = min(float(lift_raw), _COMBO_MAX_LIFT) if lift_raw == lift_raw else 0.0  # NaN check

            # PMI: information-theoretic association strength
            pmi = _compute_pmi(support, p_a, p_b)
            if pmi != pmi or abs(pmi) == np.inf:
                pmi = 0.0

            # Confidence: conditional probability in both directions (cap at 1.0)
            conf_ab = co_weight / item_weighted_freq.get(a, 1.0) if item_weighted_freq.get(a, 0) else 0.0
            conf_ba = co_weight / item_weighted_freq.get(b, 1.0) if item_weighted_freq.get(b, 0) else 0.0
            conf_ab = min(max(float(conf_ab), 0.0), 1.0) if conf_ab == conf_ab else 0.0
            conf_ba = min(max(float(conf_ba), 0.0), 1.0) if conf_ba == conf_ba else 0.0

            # Wilson lower bound on support (conservative for small samples)
            support_wilson = _wilson_lower_bound(raw_co_count, len(baskets))
            support_wilson = max(0.0, min(1.0, support_wilson)) if support_wilson == support_wilson else 0.0

            # Multi-signal filter: require positive association from at least one metric
            if lift < 1.0 and phi < min_corr:
                continue

            pair_metrics[frozenset({a, b})] = {
                "phi": float(phi),
                "support": min(1.0, max(0.0, support)),
                "raw_count": raw_co_count,
                "lift": lift,
                "pmi": pmi,
                "conf_ab": conf_ab,
                "conf_ba": conf_ba,
                "support_wilson": support_wilson,
            }

    logger.info(
        "Computed association metrics for %d pairs (min_corr=%.3f)",
        len(pair_metrics), min_corr,
    )

    if not pair_metrics:
        logger.warning("No qualifying pairs found -- falling back")
        _save_fallback_combos(db, baskets, item_info, max_combos, target_discount_pct, global_aov=global_aov)
        return

    # Step H: Train GradientBoosting on real pair features
    # Features: item-level characteristics + association metrics
    # Target: combo quality signal from real data (support_wilson * sqrt(lift))
    train_features = []
    train_targets = []
    pair_keys_for_training = []

    for pair_key, metrics in pair_metrics.items():
        names = sorted(pair_key)
        infos = [item_info.get(n) for n in names]
        if not all(infos):
            continue

        prices = sorted([info["price"] for info in infos])
        margins = [info["cm_pct"] for info in infos]
        cats = [info["category"] for info in infos]
        diversity = _score_category_diversity(cats, category_groups)
        popularities = sorted([item_prob.get(n, 0) for n in names])

        feat = [
            prices[0],                                               # lower price
            prices[1],                                               # higher price
            prices[0] / prices[1] if prices[1] > 0 else 0,          # price ratio
            np.mean(margins),                                        # avg margin %
            np.std(margins) if len(margins) > 1 else 0,             # margin spread
            popularities[0],                                         # lower popularity
            popularities[1],                                         # higher popularity
            diversity,                                               # category diversity
            metrics["phi"],                                          # phi correlation
            metrics["lift"],                                         # lift
        ]

        # Quality target: conservative support * association strength (bounded for GBR stability)
        quality = metrics["support_wilson"] * math.sqrt(max(metrics["lift"], 0.01))
        quality = min(max(float(quality), 1e-6), 1e3) if quality == quality else 1e-6
        train_features.append(feat)
        train_targets.append(quality)
        pair_keys_for_training.append(pair_key)

    ml_quality_scores: dict[frozenset, float] = {}

    if len(train_features) >= 10:
        X_train = np.array(train_features, dtype=np.float64)
        y_train = np.array(train_targets, dtype=np.float64)
        # Clip targets to avoid extreme values that destabilize GBR
        y_train = np.clip(y_train, 1e-6, 100.0)
        # Replace any remaining NaN/Inf in features
        X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_train)
        X_scaled = np.nan_to_num(X_scaled, nan=0.0, posinf=0.0, neginf=0.0)

        gbr = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            min_samples_leaf=2,
            random_state=42,
        )
        gbr.fit(X_scaled, y_train)
        logger.info(
            "Trained GBR combo scorer on %d real pair feature vectors", len(X_train)
        )

        predictions = gbr.predict(X_scaled)
        for idx, pair_key in enumerate(pair_keys_for_training):
            pred = predictions[idx]
            if pred != pred or pred < 0 or np.isinf(pred):
                pred = 0.01
            ml_quality_scores[pair_key] = float(max(pred, 0.01))
    else:
        # Not enough pairs for ML — use direct quality formula
        logger.info(
            "Too few pairs (%d) for GBR training — using direct scoring",
            len(train_features),
        )
        for idx, pair_key in enumerate(pair_keys_for_training):
            ml_quality_scores[pair_key] = float(max(train_targets[idx], 0.01))

    # Step I: Build candidate combos (pairs + triples)
    candidate_sets: list[tuple[frozenset, float]] = []
    seen_keys: set[frozenset] = set()

    # Pairs ranked by ML quality score
    ranked_pairs = sorted(
        pair_metrics.items(),
        key=lambda kv: ml_quality_scores.get(kv[0], 0),
        reverse=True,
    )
    for pair_key, metrics in ranked_pairs:
        if pair_key not in seen_keys:
            seen_keys.add(pair_key)
            score = ml_quality_scores.get(pair_key, metrics["support"] * metrics["lift"])
            candidate_sets.append((pair_key, score))

    # Extend to triples from top pairs
    top_pairs = ranked_pairs[:60]
    top_pair_items = sorted({item for pair_key, _ in top_pairs for item in pair_key})
    for pair_key, _ in top_pairs:
        a, b = sorted(pair_key)
        for c in top_pair_items:
            if c == a or c == b:
                continue
            met_ac = pair_metrics.get(frozenset({a, c}))
            met_bc = pair_metrics.get(frozenset({b, c}))
            if not met_ac or not met_bc:
                continue
            # All three sub-pairs must show positive association
            if met_ac["lift"] < 1.0 or met_bc["lift"] < 1.0:
                continue
            triple_key = frozenset({a, b, c})
            if triple_key not in seen_keys:
                seen_keys.add(triple_key)
                # Triple quality = geometric mean of sub-pair qualities
                q_ab = ml_quality_scores.get(pair_key, 0.01)
                q_ac = ml_quality_scores.get(frozenset({a, c}), 0.01)
                q_bc = ml_quality_scores.get(frozenset({b, c}), 0.01)
                triple_score = (q_ab * q_ac * q_bc) ** (1.0 / 3)
                candidate_sets.append((triple_key, triple_score))

    logger.info("Total candidate sets (pairs + triples): %d", len(candidate_sets))

    # Step J: Score, price, and build final combos
    base_margin = float(np.mean([i["cm_pct"] for i in item_info.values()])) if item_info else 15.0
    if base_margin <= 0 or base_margin != base_margin:
        base_margin = 15.0

    combos = []
    for combo_key, ml_score in candidate_sets:
        all_names = sorted(combo_key)
        all_infos = [item_info.get(n) for n in all_names]
        if not all(all_infos):
            continue

        item_categories = [info.get("category", "") for info in all_infos]
        diversity_mult = _score_category_diversity(item_categories, category_groups)

        individual_total = sum(info["price"] for info in all_infos)
        total_cost = sum(info["cost"] for info in all_infos)
        n_infos = len(all_infos)
        avg_margin_pct = (sum(info["cm_pct"] for info in all_infos) / n_infos) if n_infos else 0.0

        # Retrieve real metrics for confidence and lift reporting (clamped for display)
        if len(combo_key) == 2:
            metrics = pair_metrics.get(combo_key, {})
            lift_val = metrics.get("lift", 1.0)
            confidence_val = max(metrics.get("conf_ab", 0), metrics.get("conf_ba", 0))
        else:
            # Triple: average sub-pair metrics
            sub_pairs = [frozenset(p) for p in itertools.combinations(all_names, 2)]
            sub_metrics = [pair_metrics.get(sp, {}) for sp in sub_pairs]
            lift_val = float(np.mean([m.get("lift", 1.0) for m in sub_metrics]))
            confidence_val = float(np.mean([
                max(m.get("conf_ab", 0), m.get("conf_ba", 0)) for m in sub_metrics
            ]))
        # Clamp to valid ranges (avoid NaN/Inf or >100% confidence / extreme lift in UI)
        lift_val = min(_COMBO_MAX_LIFT, max(0.0, lift_val)) if lift_val == lift_val else 1.0
        confidence_val = min(1.0, max(0.0, confidence_val)) if confidence_val == confidence_val else 0.0

        # Margin-aware pricing
        margin_headroom = max(avg_margin_pct - 15, 0) / 100  # room above 15% floor
        lift_factor = min(lift_val / 3, 1.0)  # normalize lift to 0-1 range
        # Strong association -> less discount needed; high margin -> more discount possible
        discount_pct = target_discount_pct * (1 - lift_factor * 0.3) + margin_headroom * 10
        discount_pct = round(min(max(discount_pct, 5.0), 25.0), 1)

        discount_factor = 1 - (discount_pct / 100)
        suggested_bundle_price = round(individual_total * discount_factor / 5) * 5

        # Ensure profitability: price must exceed cost + minimum margin
        min_viable_price = round((total_cost * 1.1) / 5) * 5
        if suggested_bundle_price <= total_cost:
            suggested_bundle_price = min_viable_price
            discount_pct = round((1 - suggested_bundle_price / individual_total) * 100, 1)

        expected_margin = round(suggested_bundle_price - total_cost, 2)

        # Final combo score: ML quality * diversity * margin factor
        margin_factor = max(avg_margin_pct / base_margin, 0.5) if base_margin > 0 else 1.0
        combo_score = ml_score * diversity_mult * margin_factor

        # Observed support from actual baskets
        n_orders = len(baskets)
        co_count = sum(1 for items in baskets.values() if all(n in items for n in all_names))
        observed_support = co_count / n_orders if n_orders else 0.0

        # AOV uplift: how much the combo bundle price exceeds average order value (capped for display)
        if global_aov > 0 and suggested_bundle_price > global_aov:
            aov_uplift = round(suggested_bundle_price - global_aov, 2)
            aov_uplift_pct = round(
                min((aov_uplift / global_aov) * 100, _COMBO_AOV_UPLIFT_PCT_CAP), 1
            )
        else:
            aov_uplift = 0.0
            aov_uplift_pct = 0.0

        combos.append({
            "name": " + ".join(all_names) + " Combo",
            "item_ids": [item_info[n]["id"] for n in all_names],
            "item_names": all_names,
            "restaurant_id": all_infos[0]["restaurant_id"],
            "individual_total": individual_total,
            "combo_price": suggested_bundle_price,
            "discount_pct": discount_pct,
            "expected_margin": expected_margin,
            "support": round(observed_support, 4),
            "confidence": round(float(confidence_val), 4),
            "lift": round(float(lift_val), 4),
            "combo_score": round(float(combo_score), 4),
            "aov_uplift": aov_uplift,
            "aov_uplift_pct": aov_uplift_pct,
        })

    combos.sort(key=lambda c: c["combo_score"], reverse=True)
    combos = combos[:max_combos]

    _save_combos_to_db(db, combos)
    logger.info("Saved %d multi-signal combo suggestions to DB", len(combos))


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
                aov_uplift=combo.get("aov_uplift"),
                aov_uplift_pct=combo.get("aov_uplift_pct"),
            ))

        # Only now wipe+replace atomically
        db.query(ComboSuggestion).delete()
        db.add_all(new_combos)
        db.commit()
        logger.info("_save_combos_to_db: committed %d rows", len(new_combos))
    except Exception as e:
        db.rollback()
        logger.error("Error saving combos to DB: %s", e)


def _fetch_combos_from_db(db: Session, restaurant_id: int | None = None) -> list[dict]:
    """Retrieve cached combos from the database, filtering out those with out-of-stock items."""
    combo_cat_groups = _get_combo_category_groups(db, restaurant_id)
    q = db.query(ComboSuggestion).order_by(desc(ComboSuggestion.combo_score))
    if restaurant_id:
        q = q.filter(ComboSuggestion.restaurant_id == restaurant_id)
    db_combos = q.all()

    # Build stock lookup: items with current_stock == 0 are out of stock
    # current_stock == None means unlimited
    oos_ids = set()
    oos_items = (
        db.query(MenuItem.id)
        .filter(MenuItem.current_stock == 0, MenuItem.is_available)
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
        groups_set = _classify_category_groups(item_categories, combo_cat_groups)
        combo_structure = "diverse" if len(groups_set) >= 2 else "same-category"

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
            "id": c.id,
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
            "aov_uplift": round(c.aov_uplift, 2) if c.aov_uplift else 0.0,
            "aov_uplift_pct": round(min(c.aov_uplift_pct or 0, _COMBO_AOV_UPLIFT_PCT_CAP), 1),
            "combo_structure": combo_structure,
            "category_groups": list(groups_set),
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


def _classify_category_groups(
    category_names: list[str],
    category_groups: dict[str, set[str]] | None = None,
) -> set[str]:
    """Map category names to abstract groups (main, bread, side, drink, dessert)."""
    if category_groups is None:
        category_groups = {k: set(v) for k, v in get_default_combo_category_groups().items()}
    groups = set()
    for cat_name in category_names:
        for group, cat_set in category_groups.items():
            if cat_name in cat_set:
                groups.add(group)
                break
        else:
            groups.add("other")
    return groups


def _score_category_diversity(
    category_names: list[str],
    category_groups: dict[str, set[str]] | None = None,
) -> float:
    """
    Score combo category diversity. A combo with items from different
    category groups (e.g., main + bread + drink) scores higher than
    combos with items from the same group (e.g., two desserts).

    Returns a multiplier: 1.0 (same category) to 1.5 (ideal diverse combo).
    """
    groups = _classify_category_groups(category_names, category_groups)
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
    global_aov: float = 0.0,
):
    """Fallback pair counting when correlation/ML yields no usable rules."""
    n_orders = len(baskets)
    pair_counts: Counter = Counter()

    for items in baskets.values():
        item_list = sorted(items)
        for i in range(len(item_list)):
            for j in range(i + 1, len(item_list)):
                pair_counts[(item_list[i], item_list[j])] += 1

    combos = []
    for (a, b), count in pair_counts.most_common(max_combos):
        support = count / n_orders if n_orders else 0
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

        # AOV uplift when we have a valid global_aov (from pipeline)
        if global_aov > 0 and bundle > global_aov:
            aov_uplift = round(bundle - global_aov, 2)
            aov_uplift_pct = round(
                min((aov_uplift / global_aov) * 100, _COMBO_AOV_UPLIFT_PCT_CAP), 1
            )
        else:
            aov_uplift = 0.0
            aov_uplift_pct = 0.0

        combos.append({
            "name": f"{a} + {b} Combo",
            "item_ids": [info_a["id"], info_b["id"]],
            "item_names": [a, b],
            "individual_total": total,
            "combo_price": bundle,
            "discount_pct": discount_pct,
            "expected_margin": expected_margin,
            "support": round(min(1.0, support), 4),
            "confidence": round(min(1.0, support), 4),
            "lift": 1.0,
            "combo_score": round(support * 100, 2),
            "aov_uplift": aov_uplift,
            "aov_uplift_pct": aov_uplift_pct,
        })

    _save_combos_to_db(db, combos)
