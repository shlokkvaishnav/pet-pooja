"""
order_builder.py — Order JSON + KOT Generator + DB Persistence
================================================================
Builds structured orders from parsed items, generates
Kitchen Order Tickets (KOT), and saves to database.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import Order, OrderItem, KOT

logger = logging.getLogger("petpooja.voice.order_builder")


def build_order(
    items: list[dict],
    session_id: str = None,
    order_type: str = "dine_in",
    table_number: str = None,
) -> dict:
    """
    Build a structured order JSON from parsed items.

    Args:
        items: Matched items with quantity and modifiers
        session_id: Session/order ID (auto-generated if None)
        order_type: dine_in | takeaway | delivery
        table_number: Table number for dine-in

    Returns:
        Complete order dict
    """
    if not items:
        return {
            "order_id": session_id or f"ORD-{uuid.uuid4().hex[:8].upper()}",
            "items": [],
            "item_count": 0,
            "total_quantity": 0,
            "subtotal": 0,
            "tax": 0,
            "total": 0,
            "order_type": order_type,
            "table_number": table_number,
            "status": "building",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    order_id = session_id or f"ORD-{uuid.uuid4().hex[:8].upper()}"

    order_items = []
    total = 0.0

    for item in items:
        qty = item.get("quantity", 1)
        price = item.get("selling_price", 0)
        line_total = price * qty
        total += line_total

        order_items.append({
            "item_id": item["item_id"],
            "name": item["name"],
            "name_hi": item.get("name_hi", ""),
            "quantity": qty,
            "unit_price": price,
            "line_total": round(line_total, 2),
            "modifiers": item.get("modifiers", {}),
            "is_veg": item.get("is_veg", True),
        })

    return {
        "order_id": order_id,
        "items": order_items,
        "item_count": len(order_items),
        "total_quantity": sum(i["quantity"] for i in order_items),
        "subtotal": round(total, 2),
        "tax": round(total * 0.05, 2),  # 5% GST
        "total": round(total * 1.05, 2),
        "order_type": order_type,
        "table_number": table_number,
        "status": "building",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_kot(order: dict) -> dict:
    """
    Generate a Kitchen Order Ticket from a built order.

    KOT ID format: KOT-YYYYMMDD-XXXX (random 4-char suffix)

    Returns:
        KOT dict with kitchen-friendly formatting + print_ready text
    """
    if not order or not order.get("items"):
        return {}

    now = datetime.now(timezone.utc)
    kot_id = f"KOT-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    kot_items = []
    for item in order["items"]:
        kot_line = {
            "name": item["name"],
            "qty": item["quantity"],
            "modifiers": [],
            "notes": "",
        }

        mods = item.get("modifiers", {})

        # Add spice level if not default
        if mods.get("spice_level") and mods["spice_level"] != "medium":
            kot_line["modifiers"].append(f"Spice: {mods['spice_level']}")

        # Add size if not default
        if mods.get("size") and mods["size"] != "regular":
            kot_line["modifiers"].append(f"Size: {mods['size']}")

        # Add add-ons
        for addon in mods.get("add_ons", []):
            kot_line["modifiers"].append(addon.replace("_", " ").title())

        # Special instructions
        if mods.get("special_instructions"):
            kot_line["notes"] = mods["special_instructions"]

        kot_items.append(kot_line)

    # Build print-ready text (plain text for kitchen printer)
    print_lines = [
        "=" * 32,
        f"  KOT: {kot_id}",
        f"  Order: {order['order_id']}",
        f"  Table: {order.get('table_number', '-')}",
        f"  Type: {order.get('order_type', 'dine_in')}",
        f"  Time: {now.strftime('%d-%b %H:%M')}",
        "-" * 32,
    ]

    for item in kot_items:
        line = f"  {item['qty']}x {item['name']}"
        print_lines.append(line)
        for mod in item["modifiers"]:
            print_lines.append(f"     → {mod}")
        if item["notes"]:
            print_lines.append(f"     ⚠ {item['notes']}")

    print_lines.append("-" * 32)
    print_lines.append(f"  Total Items: {sum(i['qty'] for i in kot_items)}")
    print_lines.append("=" * 32)

    print_ready = "\n".join(print_lines)

    return {
        "kot_id": kot_id,
        "order_id": order["order_id"],
        "table": order.get("table_number", "-"),
        "order_type": order.get("order_type", "dine_in"),
        "items": kot_items,
        "items_summary": [
            {"name": i["name"], "qty": i["qty"], "modifiers": i["modifiers"]}
            for i in kot_items
        ],
        "total_items": sum(i["qty"] for i in kot_items),
        "timestamp": now.strftime("%d-%b %H:%M"),
        "print_ready": print_ready,
        "priority": "normal",
    }


def save_order_to_db(order: dict, kot: dict, db: Session) -> dict:
    """
    Save a confirmed order to the database.
    Writes Order + OrderItem rows + KOT row in a transaction.

    Args:
        order: Built order dict from build_order()
        kot: KOT dict from generate_kot()
        db: Database session

    Returns:
        Dict with saved order_id and kot_id

    Raises:
        Exception: rolls back transaction on any error
    """
    try:
        # Write Order row
        db_order = Order(
            order_id=order["order_id"],
            order_number=order["order_id"],
            total_amount=order["total"],
            status="confirmed",
            order_type=order.get("order_type", "dine_in"),
            table_number=order.get("table_number"),
            source="voice",
        )
        db.add(db_order)
        db.flush()

        # Write OrderItem rows
        for item in order["items"]:
            db_item = OrderItem(
                order_id=order["order_id"],
                item_id=item["item_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                modifiers_applied=item.get("modifiers", {}),
                line_total=item["line_total"],
            )
            db.add(db_item)

        # Write KOT row
        if kot and kot.get("kot_id"):
            db_kot = KOT(
                kot_id=kot["kot_id"],
                order_id=order["order_id"],
                items_summary=kot.get("items_summary", []),
                print_ready=kot.get("print_ready", ""),
            )
            db.add(db_kot)

        db.commit()
        logger.info("Order %s saved to DB", order["order_id"])

        return {
            "success": True,
            "order_id": order["order_id"],
            "kot_id": kot.get("kot_id", ""),
            "status": "confirmed",
            "total": order["total"],
        }

    except Exception:
        db.rollback()
        logger.exception("Failed to save order %s", order.get("order_id", "unknown"))
        raise
