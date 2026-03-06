"""
routes_ops.py — Operations & Back-Office Endpoints
===================================================
/api/ops/* — Orders, tables, inventory, reports, settings
"""

import csv
import logging
from datetime import datetime, timedelta, timezone, date
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database import get_db
from models import Order, RestaurantTable, Ingredient, StockLog, SaleTransaction, MenuItem, Category

router = APIRouter()
logger = logging.getLogger("petpooja.api.ops")


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {value}. Use YYYY-MM-DD.")


class TableUpdateInput(BaseModel):
    status: str = Field(..., pattern=r"^(empty|occupied|reserved|cleaning)$")
    current_order_id: str | None = None


class StockAdjustInput(BaseModel):
    ingredient_id: int
    change_qty: float
    reason: str = Field(..., pattern=r"^(purchase|usage|waste|adjustment)$")
    note: str | None = None
    staff_id: int | None = None


class IngredientUpdateInput(BaseModel):
    reorder_level: float | None = None
    cost_per_unit: float | None = None


@router.get("/orders")
def get_orders(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    days: int = Query(30, ge=1, le=365),
    status: str | None = Query(None, pattern=r"^(building|confirmed|cancelled)$"),
    order_type: str | None = Query(None, pattern=r"^(dine_in|takeaway|delivery)$"),
    source: str | None = Query(None, pattern=r"^(voice|manual)$"),
    search: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Orders list + summary metrics.
    """
    try:
        sd = _parse_date(start_date)
        ed = _parse_date(end_date)
        if sd and ed and sd > ed:
            raise HTTPException(status_code=400, detail="start_date cannot be after end_date.")

        if sd or ed:
            start_dt = datetime.combine(sd or date.min, datetime.min.time(), tzinfo=timezone.utc)
            end_dt = datetime.combine(ed or date.max, datetime.max.time(), tzinfo=timezone.utc)
        else:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            start_dt = cutoff
            end_dt = datetime.now(timezone.utc)

        filters = [Order.created_at >= start_dt, Order.created_at <= end_dt]
        if status:
            filters.append(Order.status == status)
        if order_type:
            filters.append(Order.order_type == order_type)
        if source:
            filters.append(Order.source == source)
        if search:
            like = f"%{search.strip()}%"
            filters.append(
                (Order.order_id.ilike(like)) | (Order.order_number.ilike(like))
            )

        total_orders = db.query(func.count(Order.id)).filter(*filters).scalar() or 0
        total_revenue = (
            db.query(func.coalesce(func.sum(Order.total_amount), 0.0))
            .filter(*filters, Order.status == "confirmed")
            .scalar()
        ) or 0.0

        avg_order_value = (total_revenue / total_orders) if total_orders else 0.0

        status_counts = (
            db.query(Order.status, func.count(Order.id))
            .filter(*filters)
            .group_by(Order.status)
            .all()
        )
        status_map = {s: c for s, c in status_counts}

        orders = (
            db.query(
                Order.order_id,
                Order.order_number,
                Order.total_amount,
                Order.status,
                Order.order_type,
                Order.table_number,
                Order.source,
                Order.created_at,
            )
            .filter(*filters)
            .order_by(desc(Order.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "summary": {
                "total_orders": int(total_orders),
                "total_revenue": round(float(total_revenue), 2),
                "avg_order_value": round(float(avg_order_value), 2),
                "open_orders": int(status_map.get("building", 0)),
                "confirmed_orders": int(status_map.get("confirmed", 0)),
                "cancelled_orders": int(status_map.get("cancelled", 0)),
            },
            "orders": [
                {
                    "order_id": o.order_id,
                    "order_number": o.order_number,
                    "total_amount": o.total_amount,
                    "status": o.status,
                    "order_type": o.order_type,
                    "table_number": o.table_number,
                    "source": o.source,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                }
                for o in orders
            ],
            "count": len(orders),
            "offset": offset,
            "limit": limit,
            "total": int(total_orders),
        }
    except Exception as e:
        logger.exception("Error fetching orders")
        raise HTTPException(status_code=500, detail=f"Orders fetch failed: {e}")


@router.get("/tables")
def get_tables(
    status: str | None = Query(None, pattern=r"^(empty|occupied|reserved|cleaning)$"),
    section: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Table status and reservation view.
    """
    try:
        filters = []
        if status:
            filters.append(RestaurantTable.status == status)
        if section:
            filters.append(RestaurantTable.section == section)
        if search:
            like = f"%{search.strip()}%"
            filters.append(RestaurantTable.table_number.ilike(like))

        tables = db.query(RestaurantTable).filter(*filters).order_by(RestaurantTable.table_number.asc()).all()
        status_counts = (
            db.query(RestaurantTable.status, func.count(RestaurantTable.id))
            .group_by(RestaurantTable.status)
            .all()
        )
        status_map = {s: c for s, c in status_counts}

        return {
            "summary": {
                "total_tables": len(tables),
                "occupied": int(status_map.get("occupied", 0)),
                "reserved": int(status_map.get("reserved", 0)),
                "empty": int(status_map.get("empty", 0)),
                "cleaning": int(status_map.get("cleaning", 0)),
            },
            "tables": [
                {
                    "table_id": t.id,
                    "table_number": t.table_number,
                    "capacity": t.capacity,
                    "section": t.section,
                    "status": t.status,
                    "current_order_id": t.current_order_id,
                }
                for t in tables
            ],
        }
    except Exception as e:
        logger.exception("Error fetching tables")
        raise HTTPException(status_code=500, detail=f"Tables fetch failed: {e}")


@router.patch("/tables/{table_id}")
def update_table(
    table_id: int,
    body: TableUpdateInput,
    db: Session = Depends(get_db),
):
    """
    Update table status and current order assignment.
    """
    try:
        table = db.query(RestaurantTable).filter(RestaurantTable.id == table_id).first()
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")

        table.status = body.status
        table.current_order_id = body.current_order_id
        db.commit()
        db.refresh(table)

        return {
            "table_id": table.id,
            "table_number": table.table_number,
            "status": table.status,
            "current_order_id": table.current_order_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error updating table")
        raise HTTPException(status_code=500, detail=f"Table update failed: {e}")


@router.get("/inventory")
def get_inventory(
    days: int = Query(30, ge=7, le=365),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: str | None = None,
    low_stock_only: bool = False,
    db: Session = Depends(get_db),
):
    """
    Inventory overview with low-stock and usage/waste.
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        filters = []
        if search:
            like = f"%{search.strip()}%"
            filters.append(Ingredient.name.ilike(like))
        if low_stock_only:
            filters.append(Ingredient.current_stock <= Ingredient.reorder_level)

        ingredients_query = db.query(Ingredient).filter(*filters)
        total_ingredients = ingredients_query.count()

        total_stock_value = (
            db.query(func.coalesce(func.sum(Ingredient.current_stock * Ingredient.cost_per_unit), 0.0))
            .filter(*filters)
            .scalar()
        ) or 0.0

        low_stock = (
            db.query(Ingredient)
            .filter(*filters, Ingredient.current_stock <= Ingredient.reorder_level)
            .order_by(Ingredient.name.asc())
            .all()
        )

        ingredients = (
            ingredients_query
            .order_by(Ingredient.name.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        usage_waste = (
            db.query(
                StockLog.reason,
                func.coalesce(func.sum(func.abs(StockLog.change_qty)), 0.0).label("qty"),
            )
            .filter(StockLog.created_at >= cutoff)
            .group_by(StockLog.reason)
            .all()
        )
        usage_map = {r: float(qty) for r, qty in usage_waste}

        return {
            "summary": {
                "total_ingredients": int(total_ingredients),
                "low_stock_count": len(low_stock),
                "total_stock_value": round(float(total_stock_value), 2),
                "usage_qty": round(usage_map.get("usage", 0.0), 2),
                "waste_qty": round(usage_map.get("waste", 0.0), 2),
            },
            "low_stock": [
                {
                    "ingredient_id": i.id,
                    "name": i.name,
                    "unit": i.unit,
                    "current_stock": i.current_stock,
                    "reorder_level": i.reorder_level,
                    "cost_per_unit": i.cost_per_unit,
                }
                for i in low_stock
            ],
            "ingredients": [
                {
                    "ingredient_id": i.id,
                    "name": i.name,
                    "unit": i.unit,
                    "current_stock": i.current_stock,
                    "reorder_level": i.reorder_level,
                    "cost_per_unit": i.cost_per_unit,
                }
                for i in ingredients
            ],
            "count": len(ingredients),
            "offset": offset,
            "limit": limit,
        }
    except Exception as e:
        logger.exception("Error fetching inventory")
        raise HTTPException(status_code=500, detail=f"Inventory fetch failed: {e}")


@router.post("/inventory/adjust")
def adjust_inventory(
    body: StockAdjustInput,
    db: Session = Depends(get_db),
):
    """
    Adjust ingredient stock and log the change.
    """
    try:
        ingredient = db.query(Ingredient).filter(Ingredient.id == body.ingredient_id).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="Ingredient not found")

        new_stock = (ingredient.current_stock or 0) + body.change_qty
        if new_stock < 0:
            raise HTTPException(status_code=400, detail="Stock cannot go below zero")

        ingredient.current_stock = new_stock
        log = StockLog(
            ingredient_id=ingredient.id,
            change_qty=body.change_qty,
            reason=body.reason,
            note=body.note,
            staff_id=body.staff_id,
        )
        db.add(log)
        db.commit()
        db.refresh(ingredient)

        return {
            "ingredient_id": ingredient.id,
            "name": ingredient.name,
            "current_stock": ingredient.current_stock,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error adjusting inventory")
        raise HTTPException(status_code=500, detail=f"Inventory adjustment failed: {e}")


@router.patch("/inventory/{ingredient_id}")
def update_ingredient(
    ingredient_id: int,
    body: IngredientUpdateInput,
    db: Session = Depends(get_db),
):
    """
    Update ingredient metadata (reorder level, cost).
    """
    try:
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="Ingredient not found")

        if body.reorder_level is not None:
            ingredient.reorder_level = body.reorder_level
        if body.cost_per_unit is not None:
            ingredient.cost_per_unit = body.cost_per_unit

        db.commit()
        db.refresh(ingredient)

        return {
            "ingredient_id": ingredient.id,
            "reorder_level": ingredient.reorder_level,
            "cost_per_unit": ingredient.cost_per_unit,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error updating ingredient")
        raise HTTPException(status_code=500, detail=f"Ingredient update failed: {e}")


@router.get("/reports")
def get_reports(
    days: int = Query(14, ge=7, le=90),
    top_n: int = Query(8, ge=3, le=20),
    db: Session = Depends(get_db),
):
    """
    Lightweight operational reports for charts.
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        daily = (
            db.query(
                func.date(SaleTransaction.sold_at).label("day"),
                func.coalesce(func.sum(SaleTransaction.total_price), 0.0).label("revenue"),
                func.coalesce(func.sum(SaleTransaction.quantity), 0).label("items"),
                func.count(func.distinct(SaleTransaction.order_id)).label("orders"),
            )
            .filter(SaleTransaction.sold_at >= cutoff)
            .group_by(func.date(SaleTransaction.sold_at))
            .order_by(func.date(SaleTransaction.sold_at).asc())
            .all()
        )

        top_items = (
            db.query(
                MenuItem.id,
                MenuItem.name,
                func.coalesce(func.sum(SaleTransaction.total_price), 0.0).label("revenue"),
                func.coalesce(func.sum(SaleTransaction.quantity), 0).label("qty"),
            )
            .join(SaleTransaction, SaleTransaction.item_id == MenuItem.id)
            .filter(SaleTransaction.sold_at >= cutoff)
            .group_by(MenuItem.id, MenuItem.name)
            .order_by(desc("revenue"))
            .limit(top_n)
            .all()
        )

        top_categories = (
            db.query(
                Category.id,
                Category.name,
                func.coalesce(func.sum(SaleTransaction.total_price), 0.0).label("revenue"),
            )
            .join(MenuItem, MenuItem.category_id == Category.id)
            .join(SaleTransaction, SaleTransaction.item_id == MenuItem.id)
            .filter(SaleTransaction.sold_at >= cutoff)
            .group_by(Category.id, Category.name)
            .order_by(desc("revenue"))
            .limit(top_n)
            .all()
        )

        return {
            "daily": [
                {
                    "date": str(row.day),
                    "revenue": float(row.revenue),
                    "orders": int(row.orders),
                    "items": int(row.items),
                }
                for row in daily
            ],
            "top_items": [
                {
                    "item_id": row.id,
                    "name": row.name,
                    "revenue": float(row.revenue),
                    "qty": int(row.qty),
                }
                for row in top_items
            ],
            "top_categories": [
                {
                    "category_id": row.id,
                    "name": row.name,
                    "revenue": float(row.revenue),
                }
                for row in top_categories
            ],
        }
    except Exception as e:
        logger.exception("Error fetching reports")
        raise HTTPException(status_code=500, detail=f"Reports fetch failed: {e}")


@router.get("/reports/export")
def export_reports(
    kind: str = Query("daily", pattern=r"^(daily|top_items|top_categories)$"),
    days: int = Query(14, ge=7, le=90),
    top_n: int = Query(20, ge=3, le=50),
    db: Session = Depends(get_db),
):
    """
    CSV export for reports data.
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        output = StringIO()
        writer = csv.writer(output)

        if kind == "daily":
            rows = (
                db.query(
                    func.date(SaleTransaction.sold_at).label("day"),
                    func.coalesce(func.sum(SaleTransaction.total_price), 0.0).label("revenue"),
                    func.coalesce(func.sum(SaleTransaction.quantity), 0).label("items"),
                    func.count(func.distinct(SaleTransaction.order_id)).label("orders"),
                )
                .filter(SaleTransaction.sold_at >= cutoff)
                .group_by(func.date(SaleTransaction.sold_at))
                .order_by(func.date(SaleTransaction.sold_at).asc())
                .all()
            )
            writer.writerow(["date", "revenue", "orders", "items"])
            for row in rows:
                writer.writerow([str(row.day), float(row.revenue), int(row.orders), int(row.items)])

        elif kind == "top_items":
            rows = (
                db.query(
                    MenuItem.id,
                    MenuItem.name,
                    func.coalesce(func.sum(SaleTransaction.total_price), 0.0).label("revenue"),
                    func.coalesce(func.sum(SaleTransaction.quantity), 0).label("qty"),
                )
                .join(SaleTransaction, SaleTransaction.item_id == MenuItem.id)
                .filter(SaleTransaction.sold_at >= cutoff)
                .group_by(MenuItem.id, MenuItem.name)
                .order_by(desc("revenue"))
                .limit(top_n)
                .all()
            )
            writer.writerow(["item_id", "name", "revenue", "qty"])
            for row in rows:
                writer.writerow([row.id, row.name, float(row.revenue), int(row.qty)])

        else:
            rows = (
                db.query(
                    Category.id,
                    Category.name,
                    func.coalesce(func.sum(SaleTransaction.total_price), 0.0).label("revenue"),
                )
                .join(MenuItem, MenuItem.category_id == Category.id)
                .join(SaleTransaction, SaleTransaction.item_id == MenuItem.id)
                .filter(SaleTransaction.sold_at >= cutoff)
                .group_by(Category.id, Category.name)
                .order_by(desc("revenue"))
                .limit(top_n)
                .all()
            )
            writer.writerow(["category_id", "name", "revenue"])
            for row in rows:
                writer.writerow([row.id, row.name, float(row.revenue)])

        filename = f"reports_{kind}_{days}d.csv"
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.exception("Error exporting reports")
        raise HTTPException(status_code=500, detail=f"Reports export failed: {e}")


@router.get("/settings")
def get_settings():
    """
    Surface runtime settings for UI display.
    """
    try:
        import os
        from api.auth import AUTH_ENABLED
        from api.rate_limit import _VOICE_RPM, _REVENUE_RPM, _DEFAULT_RPM
        from database import DATABASE_URL

        return {
            "auth_enabled": AUTH_ENABLED,
            "rate_limits": {
                "voice_rpm": _VOICE_RPM,
                "revenue_rpm": _REVENUE_RPM,
                "default_rpm": _DEFAULT_RPM,
            },
            "cors_origins": os.getenv("CORS_ORIGINS", ""),
            "database": {
                "url": DATABASE_URL,
                "engine": "postgres" if DATABASE_URL and "postgres" in DATABASE_URL else "sqlite",
            },
        }
    except Exception as e:
        logger.exception("Error fetching settings")
        raise HTTPException(status_code=500, detail=f"Settings fetch failed: {e}")
