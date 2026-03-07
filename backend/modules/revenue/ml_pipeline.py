"""
ml_pipeline.py — Unified ML Pipeline Orchestrator
====================================================
Coordinates training of all ML models, manages model lifecycle,
and persists run metadata to the ml_pipeline_runs table.
"""

import logging
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import MLPipelineRun

logger = logging.getLogger("petpooja.revenue.ml.pipeline")


def run_full_pipeline(db: Session, restaurant_id: int = None) -> dict:
    """
    Train all ML models sequentially and persist run metadata.

    Order: AOV → Bundle Pricing → Demand → Upsell
    Each model is independent and can fail without blocking others.

    Returns consolidated summary of all model training results.
    """
    from .aov_predictor import train_aov_model
    from .bundle_pricer import train_pricing_model
    from .demand_forecaster import train_demand_model
    from .upsell_scorer import train_upsell_model

    start_time = time.time()
    logger.info("Starting full ML pipeline training...")

    # Create a pipeline run record
    run = MLPipelineRun(
        restaurant_id=restaurant_id,
        run_type="full",
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    results = {}
    all_succeeded = True

    # 1. AOV Model
    try:
        logger.info("[1/4] Training AOV model...")
        results["aov"] = train_aov_model(db, restaurant_id=restaurant_id)
    except Exception as e:
        logger.error("AOV model training failed: %s", e)
        results["aov"] = {"status": "failed", "error": str(e)}
        all_succeeded = False

    # 2. Bundle Pricing Model
    try:
        logger.info("[2/4] Training bundle pricing model...")
        results["pricing"] = train_pricing_model(db, restaurant_id=restaurant_id)
    except Exception as e:
        logger.error("Pricing model training failed: %s", e)
        results["pricing"] = {"status": "failed", "error": str(e)}
        all_succeeded = False

    # 3. Demand Forecasting Model
    try:
        logger.info("[3/4] Training demand forecasting model...")
        results["demand"] = train_demand_model(db, restaurant_id=restaurant_id)
    except Exception as e:
        logger.error("Demand model training failed: %s", e)
        results["demand"] = {"status": "failed", "error": str(e)}
        all_succeeded = False

    # 4. Upsell Scoring Model
    try:
        logger.info("[4/4] Training upsell scoring model...")
        results["upsell"] = train_upsell_model(db, restaurant_id=restaurant_id)
    except Exception as e:
        logger.error("Upsell model training failed: %s", e)
        results["upsell"] = {"status": "failed", "error": str(e)}
        all_succeeded = False

    duration = time.time() - start_time

    # Count total orders used
    from sqlalchemy import func
    from models import VSale
    total_orders = db.query(func.count(func.distinct(VSale.order_id))).scalar() or 0

    # Update pipeline run record
    run.status = "completed" if all_succeeded else "partial"
    run.model_metrics = results
    run.predictions_summary = {
        model: res.get("status", "unknown") for model, res in results.items()
    }
    run.orders_used = total_orders
    run.training_duration_sec = round(duration, 2)
    db.commit()

    logger.info("ML pipeline %s in %.1fs (orders=%d)",
                run.status, duration, total_orders)

    return {
        "run_id": run.id,
        "status": run.status,
        "training_duration_sec": round(duration, 2),
        "orders_used": total_orders,
        "models": results,
    }


def get_pipeline_status(db: Session, restaurant_id: int = None) -> dict:
    """
    Return the status of the latest ML pipeline run.
    Includes model metrics, staleness info, and recommendation.
    """
    q = db.query(MLPipelineRun).order_by(MLPipelineRun.created_at.desc())
    if restaurant_id:
        q = q.filter(MLPipelineRun.restaurant_id == restaurant_id)
    last_run = q.first()

    if not last_run:
        return {
            "status": "never_run",
            "recommendation": "Run the ML pipeline to generate predictions.",
            "last_run": None,
        }

    now = datetime.now(timezone.utc)
    created = last_run.created_at
    if created and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)

    age_hours = (now - created).total_seconds() / 3600 if created else 999

    if age_hours > 24:
        staleness = "stale"
        recommendation = "Pipeline is >24h old. Consider retraining for fresh predictions."
    elif age_hours > 6:
        staleness = "aging"
        recommendation = "Pipeline is aging. Retrain before peak hours for best accuracy."
    else:
        staleness = "fresh"
        recommendation = "Models are up to date."

    return {
        "status": last_run.status,
        "staleness": staleness,
        "recommendation": recommendation,
        "last_run": {
            "id": last_run.id,
            "run_type": last_run.run_type,
            "status": last_run.status,
            "created_at": created.isoformat() if created else None,
            "age_hours": round(age_hours, 1),
            "orders_used": last_run.orders_used,
            "training_duration_sec": last_run.training_duration_sec,
            "model_metrics": last_run.model_metrics,
            "predictions_summary": last_run.predictions_summary,
        },
    }


def get_all_predictions(db: Session, restaurant_id: int = None) -> dict:
    """
    Aggregate predictions from all trained ML models into a single response.
    """
    from .aov_predictor import get_aov_insights
    from .demand_forecaster import get_demand_insights
    from .upsell_scorer import get_upsell_metrics
    from .bundle_pricer import get_pricing_metrics

    status = get_pipeline_status(db, restaurant_id)

    aov_data = {}
    try:
        aov_data = get_aov_insights(db, restaurant_id=restaurant_id)
    except Exception as e:
        aov_data = {"error": str(e)}

    demand_data = {}
    try:
        demand_data = get_demand_insights(db, restaurant_id=restaurant_id)
    except Exception as e:
        demand_data = {"error": str(e)}

    return {
        "pipeline_status": status,
        "aov": aov_data,
        "demand": demand_data,
        "pricing_model": get_pricing_metrics() or {"status": "not_trained"},
        "upsell_model": get_upsell_metrics() or {"status": "not_trained"},
    }
