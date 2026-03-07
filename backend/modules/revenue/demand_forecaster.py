"""
demand_forecaster.py — Item Demand Forecasting Model
======================================================
Gradient Boosting model predicting next-7-day demand per menu item
using lag features, rolling stats, and calendar features.
"""

import logging
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import MenuItem, VSale, Category

logger = logging.getLogger("petpooja.revenue.ml.demand")

_demand_model = None
_demand_metrics = None
_item_lookup = None


def train_demand_model(db: Session, restaurant_id: int = None) -> dict:
    """Train demand forecasting model on daily item sales time-series."""
    global _demand_model, _demand_metrics, _item_lookup

    logger.info("Training demand forecasting model...")

    now = datetime.now(timezone.utc)
    lookback_start = now - timedelta(days=120)

    daily_sales = (
        db.query(VSale.item_id, func.date(VSale.sold_at).label("sale_date"),
                 func.sum(VSale.quantity).label("qty"))
        .filter(VSale.sold_at >= lookback_start)
    )
    if restaurant_id:
        daily_sales = daily_sales.filter(VSale.restaurant_id == restaurant_id)
    daily_sales = daily_sales.group_by(VSale.item_id, func.date(VSale.sold_at)).all()

    if len(daily_sales) < 50:
        return {"status": "skipped", "reason": "insufficient_data", "rows_found": len(daily_sales)}

    item_q = db.query(MenuItem).filter(MenuItem.is_available.is_(True))
    if restaurant_id:
        item_q = item_q.filter(MenuItem.restaurant_id == restaurant_id)
    items = item_q.all()

    prices = [float(i.selling_price or 0) for i in items]
    q1, q2, q3 = (np.percentile(prices, [25, 50, 75]) if prices else (100, 200, 300))

    item_meta = {}
    for item in items:
        p = float(item.selling_price or 0)
        tier = 1 if p <= q1 else (2 if p <= q2 else (3 if p <= q3 else 4))
        item_meta[item.id] = {
            "name": item.name, "price": p, "price_tier": tier,
            "is_veg": 1 if item.is_veg else 0, "category_id": item.category_id,
        }
    _item_lookup = item_meta

    records = []
    for row in daily_sales:
        records.append({"item_id": row.item_id,
                        "date": pd.Timestamp(row.sale_date) if not isinstance(row.sale_date, datetime) else row.sale_date,
                        "qty": int(row.qty or 0)})

    if not records:
        return {"status": "skipped", "reason": "no_records"}

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    date_range = pd.date_range(start=lookback_start.date(), end=now.date(), freq="D")
    all_items = df["item_id"].unique()

    feature_rows, target_vals = [], []

    for item_id in all_items:
        if item_id not in item_meta:
            continue
        item_df = df[df["item_id"] == item_id].set_index("date")["qty"]
        item_ts = item_df.reindex(date_range, fill_value=0)
        meta = item_meta[item_id]
        if len(item_ts) < 31:
            continue

        for i in range(30, len(item_ts)):
            d = item_ts.index[i]
            w7 = item_ts.iloc[max(0, i-7):i]
            w30 = item_ts.iloc[max(0, i-30):i]
            feature_rows.append({
                "lag_1": item_ts.iloc[i-1], "lag_3": item_ts.iloc[i-3],
                "lag_7": item_ts.iloc[i-7], "lag_14": item_ts.iloc[i-14],
                "lag_30": item_ts.iloc[i-30],
                "rolling_avg_7": w7.mean(), "rolling_avg_30": w30.mean(),
                "rolling_std_7": w7.std() if len(w7) > 1 else 0,
                "dow": d.weekday(), "month": d.month,
                "is_weekend": 1 if d.weekday() >= 5 else 0,
                "price_tier": meta["price_tier"], "is_veg": meta["is_veg"],
            })
            target_vals.append(item_ts.iloc[i])

    if len(feature_rows) < 50:
        return {"status": "skipped", "reason": "insufficient_features", "feature_rows": len(feature_rows)}

    X = pd.DataFrame(feature_rows)
    y = np.array(target_vals, dtype=float)

    model = GradientBoostingRegressor(n_estimators=100, max_depth=5, learning_rate=0.1,
                                       min_samples_split=10, random_state=42)
    cv_folds = min(5, max(2, len(feature_rows) // 10))
    cv_scores = cross_val_score(model, X, y, cv=cv_folds, scoring="r2")
    cv_r2 = float(np.mean(cv_scores))
    model.fit(X, y)
    y_pred = model.predict(X)
    mae = float(np.mean(np.abs(y - y_pred)))
    importances = dict(zip(X.columns, [round(float(v), 4) for v in model.feature_importances_]))

    _demand_model = model
    _demand_metrics = {"cv_r2": round(cv_r2, 4), "mae": round(mae, 2),
                       "training_samples": len(feature_rows), "unique_items": len(all_items),
                       "feature_importances": importances}

    logger.info("Demand model trained: R²=%.3f, MAE=%.2f, samples=%d, items=%d",
                cv_r2, mae, len(feature_rows), len(all_items))
    return {"status": "completed", **_demand_metrics}


def forecast_demand(db: Session, days_ahead: int = 7, restaurant_id: int = None) -> list[dict]:
    """Forecast next N days demand for each active menu item."""
    if _demand_model is None or _item_lookup is None:
        return _fallback_forecast(db, days_ahead, restaurant_id)

    now = datetime.now(timezone.utc)
    lookback = now - timedelta(days=35)

    daily_sales = (
        db.query(VSale.item_id, func.date(VSale.sold_at).label("sale_date"),
                 func.sum(VSale.quantity).label("qty"))
        .filter(VSale.sold_at >= lookback)
    )
    if restaurant_id:
        daily_sales = daily_sales.filter(VSale.restaurant_id == restaurant_id)
    daily_sales = daily_sales.group_by(VSale.item_id, func.date(VSale.sold_at)).all()

    records = {}
    for row in daily_sales:
        records.setdefault(row.item_id, {})[str(row.sale_date)] = int(row.qty or 0)

    date_range = pd.date_range(start=lookback.date(), end=now.date(), freq="D")
    results = []

    for item_id, meta in _item_lookup.items():
        ts_data = records.get(item_id, {})
        ts = pd.Series([ts_data.get(str(d.date()), 0) for d in date_range], index=date_range)
        if len(ts) < 31:
            continue

        daily_preds = []
        extended_ts = ts.copy()

        for d in range(days_ahead):
            future_date = now + timedelta(days=d + 1)
            features = {
                "lag_1": extended_ts.iloc[-1],
                "lag_3": extended_ts.iloc[-3] if len(extended_ts) > 3 else 0,
                "lag_7": extended_ts.iloc[-7] if len(extended_ts) > 7 else 0,
                "lag_14": extended_ts.iloc[-14] if len(extended_ts) > 14 else 0,
                "lag_30": extended_ts.iloc[-30] if len(extended_ts) > 30 else 0,
                "rolling_avg_7": extended_ts.iloc[-7:].mean(),
                "rolling_avg_30": extended_ts.iloc[-30:].mean(),
                "rolling_std_7": extended_ts.iloc[-7:].std() if len(extended_ts) >= 7 else 0,
                "dow": future_date.weekday(), "month": future_date.month,
                "is_weekend": 1 if future_date.weekday() >= 5 else 0,
                "price_tier": meta["price_tier"], "is_veg": meta["is_veg"],
            }
            pred = max(0, float(_demand_model.predict(pd.DataFrame([features]))[0]))
            daily_preds.append(pred)
            extended_ts = pd.concat([extended_ts, pd.Series([pred], index=[pd.Timestamp(future_date.date())])])

        avg_daily = np.mean(daily_preds) if daily_preds else 0
        last_7_avg = ts.iloc[-7:].mean()
        trend_pct = ((avg_daily - last_7_avg) / last_7_avg * 100) if last_7_avg > 0 else (100.0 if avg_daily > 0 else 0.0)
        trend = "rising" if trend_pct > 10 else ("falling" if trend_pct < -10 else "stable")

        results.append({
            "item_id": item_id, "item_name": meta["name"],
            "predicted_daily_qty": round(avg_daily, 1),
            "predicted_total_qty": round(sum(daily_preds), 0),
            "last_7d_avg": round(float(last_7_avg), 1),
            "trend": trend, "trend_pct": round(trend_pct, 1),
            "daily_forecasts": [round(d, 1) for d in daily_preds],
            "forecast_days": days_ahead,
        })

    results.sort(key=lambda x: x["predicted_total_qty"], reverse=True)
    return results


def get_demand_insights(db: Session, restaurant_id: int = None) -> dict:
    """High-level demand insights: rising/falling items, stockout risk."""
    forecasts = forecast_demand(db, days_ahead=7, restaurant_id=restaurant_id)
    rising = [f for f in forecasts if f["trend"] == "rising"]
    falling = [f for f in forecasts if f["trend"] == "falling"]

    stockout_risk = []
    for f in rising[:10]:
        item = db.query(MenuItem).filter(MenuItem.id == f["item_id"]).first()
        if item and item.current_stock is not None:
            days_of_stock = item.current_stock / max(f["predicted_daily_qty"], 0.1)
            if days_of_stock < 3:
                stockout_risk.append({
                    "item_id": f["item_id"], "item_name": f["item_name"],
                    "current_stock": item.current_stock,
                    "predicted_daily_demand": f["predicted_daily_qty"],
                    "days_until_stockout": round(days_of_stock, 1),
                    "urgency": "critical" if days_of_stock < 1 else "warning",
                })

    return {"total_items_forecasted": len(forecasts), "rising_items": rising[:10],
            "falling_items": falling[:10], "stockout_risks": stockout_risk,
            "model_metrics": _demand_metrics}


def _fallback_forecast(db: Session, days_ahead: int, restaurant_id: int = None) -> list[dict]:
    """Simple trailing-average fallback when ML model is not trained."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)

    item_sales = (
        db.query(VSale.item_id, MenuItem.name, func.sum(VSale.quantity).label("total_qty"))
        .join(MenuItem, VSale.item_id == MenuItem.id)
        .filter(VSale.sold_at >= cutoff)
    )
    if restaurant_id:
        item_sales = item_sales.filter(VSale.restaurant_id == restaurant_id)
    item_sales = item_sales.group_by(VSale.item_id, MenuItem.name).all()

    results = []
    for row in item_sales:
        daily_avg = float(row.total_qty or 0) / 30
        results.append({
            "item_id": row.item_id, "item_name": row.name,
            "predicted_daily_qty": round(daily_avg, 1),
            "predicted_total_qty": round(daily_avg * days_ahead, 0),
            "last_7d_avg": round(daily_avg, 1), "trend": "stable", "trend_pct": 0.0,
            "daily_forecasts": [round(daily_avg, 1)] * days_ahead,
            "forecast_days": days_ahead,
        })
    results.sort(key=lambda x: x["predicted_total_qty"], reverse=True)
    return results
