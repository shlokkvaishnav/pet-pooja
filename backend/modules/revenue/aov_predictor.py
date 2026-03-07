"""
aov_predictor.py — AOV (Average Order Value) Prediction Model
==============================================================
Gradient Boosting model that predicts per-order AOV based on
time features, order composition, and historical trailing averages.

Training data: Aggregates from v_sales joined with orders.
"""

import logging
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session
from sqlalchemy import func, case, distinct

from models import Order, OrderItem, MenuItem, VSale, Category

logger = logging.getLogger("petpooja.revenue.ml.aov")

# ── In-memory model cache ────────────────────────
_aov_model = None
_aov_scaler = None
_aov_metrics = None


def train_aov_model(db: Session, restaurant_id: int = None) -> dict:
    """
    Train an AOV prediction model on historical order data.

    Features per order:
      - hour_of_day, day_of_week, month, is_weekend
      - num_items, num_unique_items
      - category_mix: pct_main, pct_bread, pct_drink, pct_side, pct_dessert
      - trailing_aov_7d, trailing_aov_30d

    Target: order total_amount

    Returns dict with model metrics (R², MAE, feature importances).
    """
    global _aov_model, _aov_scaler, _aov_metrics

    logger.info("Training AOV prediction model...")

    # ── Step 1: Fetch order-level data ───────────────────────────────
    base_filter = [Order.status != "cancelled"]
    if restaurant_id:
        base_filter.append(Order.restaurant_id == restaurant_id)

    orders = (
        db.query(
            Order.id,
            Order.total_amount,
            Order.created_at,
            Order.order_type,
        )
        .filter(*base_filter)
        .order_by(Order.created_at)
        .all()
    )

    if len(orders) < 30:
        logger.warning("Insufficient orders (%d) for AOV model — need ≥30", len(orders))
        return {"status": "skipped", "reason": "insufficient_data", "orders_found": len(orders)}

    # ── Step 2: Fetch per-order item details ─────────────────────────
    order_ids = [o.id for o in orders]

    item_details = (
        db.query(
            OrderItem.order_pk,
            OrderItem.quantity,
            MenuItem.category_id,
            Category.name.label("category_name"),
        )
        .join(MenuItem, OrderItem.item_id == MenuItem.id)
        .outerjoin(Category, MenuItem.category_id == Category.id)
        .filter(OrderItem.order_pk.in_(order_ids))
        .all()
    )

    # Group items by order
    order_items_map: dict[int, list] = {}
    for oi in item_details:
        order_items_map.setdefault(oi.order_pk, []).append(oi)

    # ── Step 3: Build features ───────────────────────────────────────
    CATEGORY_GROUPS = {
        "main": {"Main Course", "Mains", "Biryani", "Rice", "Thali"},
        "bread": {"Breads", "Roti", "Naan"},
        "side": {"Starters", "Appetizers", "Sides", "Salads", "Raita"},
        "drink": {"Beverages", "Drinks", "Juices", "Lassi"},
        "dessert": {"Desserts", "Sweets"},
    }

    def _classify(cat_name: str) -> str:
        if not cat_name:
            return "other"
        for group, names in CATEGORY_GROUPS.items():
            if cat_name in names:
                return group
        return "other"

    rows = []
    amounts = []
    trailing_amounts = []  # for computing rolling AOV

    for order in orders:
        if order.total_amount is None or order.total_amount <= 0:
            trailing_amounts.append(0)
            continue

        created = order.created_at
        if created is None:
            trailing_amounts.append(float(order.total_amount))
            continue

        # Time features
        hour = created.hour
        dow = created.weekday()
        month = created.month
        is_weekend = 1 if dow >= 5 else 0

        # Item composition features
        items = order_items_map.get(order.id, [])
        num_items = sum(i.quantity for i in items) if items else 0
        num_unique = len(items)

        # Category mix
        cat_counts = {"main": 0, "bread": 0, "side": 0, "drink": 0, "dessert": 0, "other": 0}
        total_item_qty = 0
        for item in items:
            grp = _classify(item.category_name)
            qty = item.quantity or 1
            cat_counts[grp] = cat_counts.get(grp, 0) + qty
            total_item_qty += qty

        if total_item_qty > 0:
            pct_main = cat_counts["main"] / total_item_qty
            pct_bread = cat_counts["bread"] / total_item_qty
            pct_drink = cat_counts["drink"] / total_item_qty
            pct_side = cat_counts["side"] / total_item_qty
            pct_dessert = cat_counts["dessert"] / total_item_qty
        else:
            pct_main = pct_bread = pct_drink = pct_side = pct_dessert = 0.0

        # Trailing AOV (7-day and 30-day rolling average)
        trailing_amounts.append(float(order.total_amount))
        n = len(trailing_amounts)
        trail_7 = np.mean(trailing_amounts[max(0, n - 7):n]) if n > 1 else float(order.total_amount)
        trail_30 = np.mean(trailing_amounts[max(0, n - 30):n]) if n > 1 else float(order.total_amount)

        rows.append({
            "hour": hour,
            "dow": dow,
            "month": month,
            "is_weekend": is_weekend,
            "num_items": num_items,
            "num_unique": num_unique,
            "pct_main": pct_main,
            "pct_bread": pct_bread,
            "pct_drink": pct_drink,
            "pct_side": pct_side,
            "pct_dessert": pct_dessert,
            "trailing_aov_7d": trail_7,
            "trailing_aov_30d": trail_30,
        })
        amounts.append(float(order.total_amount))

    if len(rows) < 20:
        logger.warning("Too few valid rows (%d) after filtering", len(rows))
        return {"status": "skipped", "reason": "insufficient_valid_data", "valid_rows": len(rows)}

    # ── Step 4: Train model ──────────────────────────────────────────
    feature_names = list(rows[0].keys())
    X = pd.DataFrame(rows, columns=feature_names)
    y = np.array(amounts)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        min_samples_split=5,
        random_state=42,
    )

    # Cross-validation
    cv_scores = cross_val_score(model, X_scaled, y, cv=min(5, len(rows) // 5 or 2), scoring="r2")
    cv_r2 = float(np.mean(cv_scores))

    # Final fit on all data
    model.fit(X_scaled, y)

    # MAE on training set (indicative)
    y_pred = model.predict(X_scaled)
    mae = float(np.mean(np.abs(y - y_pred)))

    importances = dict(zip(feature_names, [round(float(v), 4) for v in model.feature_importances_]))

    _aov_model = model
    _aov_scaler = scaler
    _aov_metrics = {
        "cv_r2": round(cv_r2, 4),
        "mae": round(mae, 2),
        "training_samples": len(rows),
        "feature_importances": importances,
    }

    logger.info(
        "AOV model trained: R²=%.3f, MAE=₹%.2f, samples=%d",
        cv_r2, mae, len(rows),
    )

    return {"status": "completed", **_aov_metrics}


def predict_aov(
    hour: int = 12,
    dow: int = 3,
    month: int = 3,
    is_weekend: int = 0,
    num_items: int = 3,
    num_unique: int = 2,
    pct_main: float = 0.5,
    pct_bread: float = 0.2,
    pct_drink: float = 0.1,
    pct_side: float = 0.1,
    pct_dessert: float = 0.1,
    trailing_aov_7d: float = 0.0,
    trailing_aov_30d: float = 0.0,
) -> float | None:
    """Predict AOV for a hypothetical order composition."""
    if _aov_model is None or _aov_scaler is None:
        return None

    features = np.array([[
        hour, dow, month, is_weekend,
        num_items, num_unique,
        pct_main, pct_bread, pct_drink, pct_side, pct_dessert,
        trailing_aov_7d, trailing_aov_30d,
    ]])
    features_scaled = _aov_scaler.transform(features)
    return float(_aov_model.predict(features_scaled)[0])


def get_aov_insights(db: Session, restaurant_id: int = None) -> dict:
    """
    Return AOV insights:
    - current_aov: actual average from last 30 days
    - predicted_aov_by_hour: predicted AOV for each hour slot
    - improvement_opportunities: actionable suggestions
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)

    base_filter = [Order.status != "cancelled", Order.created_at >= cutoff]
    if restaurant_id:
        base_filter.append(Order.restaurant_id == restaurant_id)

    # Current AOV
    result = (
        db.query(
            func.avg(Order.total_amount).label("avg"),
            func.count(Order.id).label("cnt"),
            func.min(Order.total_amount).label("min_val"),
            func.max(Order.total_amount).label("max_val"),
        )
        .filter(*base_filter)
        .first()
    )
    current_aov = float(result.avg or 0)
    total_orders = int(result.cnt or 0)
    min_order = float(result.min_val or 0)
    max_order = float(result.max_val or 0)

    # AOV by hour
    hourly = (
        db.query(
            func.extract("hour", Order.created_at).label("hour"),
            func.avg(Order.total_amount).label("avg"),
            func.count(Order.id).label("cnt"),
        )
        .filter(*base_filter)
        .group_by(func.extract("hour", Order.created_at))
        .order_by(func.extract("hour", Order.created_at))
        .all()
    )

    aov_by_hour = [
        {
            "hour": int(h.hour),
            "label": f"{int(h.hour):02d}:00",
            "actual_aov": round(float(h.avg or 0), 2),
            "order_count": int(h.cnt),
            "predicted_aov": round(predict_aov(hour=int(h.hour), trailing_aov_7d=current_aov, trailing_aov_30d=current_aov) or 0, 2),
        }
        for h in hourly
    ]

    # AOV by order type
    type_aov = (
        db.query(
            Order.order_type,
            func.avg(Order.total_amount).label("avg"),
            func.count(Order.id).label("cnt"),
        )
        .filter(*base_filter)
        .group_by(Order.order_type)
        .all()
    )

    aov_by_type = [
        {
            "type": t.order_type or "unknown",
            "aov": round(float(t.avg or 0), 2),
            "order_count": int(t.cnt),
        }
        for t in type_aov
    ]

    # Improvement opportunities
    opportunities = []
    if aov_by_hour:
        lowest_hour = min(aov_by_hour, key=lambda x: x["actual_aov"])
        highest_hour = max(aov_by_hour, key=lambda x: x["actual_aov"])
        if highest_hour["actual_aov"] > 0:
            gap_pct = ((highest_hour["actual_aov"] - lowest_hour["actual_aov"]) / highest_hour["actual_aov"]) * 100
            if gap_pct > 20:
                opportunities.append({
                    "type": "time_gap",
                    "title": f"AOV gap between {lowest_hour['label']} and {highest_hour['label']}",
                    "description": (
                        f"AOV at {lowest_hour['label']} is ₹{lowest_hour['actual_aov']:.0f} vs "
                        f"₹{highest_hour['actual_aov']:.0f} at {highest_hour['label']}. "
                        f"Consider upsell prompts or combo offers during low-AOV hours."
                    ),
                    "potential_lift_pct": round(gap_pct, 1),
                })

    if aov_by_type and len(aov_by_type) > 1:
        typed = sorted(aov_by_type, key=lambda x: x["aov"])
        if typed[-1]["aov"] > 0:
            type_gap = ((typed[-1]["aov"] - typed[0]["aov"]) / typed[-1]["aov"]) * 100
            if type_gap > 15:
                opportunities.append({
                    "type": "order_type_gap",
                    "title": f"{typed[0]['type']} orders have lower AOV",
                    "description": (
                        f"{typed[0]['type']} AOV is ₹{typed[0]['aov']:.0f} vs "
                        f"₹{typed[-1]['aov']:.0f} for {typed[-1]['type']}. "
                        f"Add-on suggestions for {typed[0]['type']} orders could boost revenue."
                    ),
                    "potential_lift_pct": round(type_gap, 1),
                })

    return {
        "current_aov": round(current_aov, 2),
        "total_orders_30d": total_orders,
        "min_order_value": round(min_order, 2),
        "max_order_value": round(max_order, 2),
        "aov_by_hour": aov_by_hour,
        "aov_by_order_type": aov_by_type,
        "improvement_opportunities": opportunities,
        "model_metrics": _aov_metrics,
    }
