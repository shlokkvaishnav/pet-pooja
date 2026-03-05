"""
upsell_engine.py — Real-Time Upsell Suggestions
==================================================
Two strategies:
1. Combo-based: if antecedent items ⊆ cart AND consequent NOT in cart → suggest
2. Hidden star promotion: top hidden stars not in cart → "Chef's Special"
Returns max 2 suggestions to avoid overwhelming the customer.
"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import MenuItem, SaleTransaction

logger = logging.getLogger("petpooja.voice.upsell")


def get_upsell_suggestions(
    current_order_items: list[dict],
    menu_data: list[dict],
    combo_rules: list[dict] = None,
    hidden_stars: list[dict] = None,
    max_suggestions: int = 2,
) -> list[dict]:
    """
    Generate upsell suggestions for the current order.

    Args:
        current_order_items: Items currently in the cart [{name, item_id, ...}]
        menu_data: All menu items from DB
        combo_rules: Association rules from combo_engine
        hidden_stars: Hidden star items from analysis
        max_suggestions: Max suggestions to return (default 2)

    Returns:
        List of upsell suggestion dicts, max 2
    """
    if not current_order_items:
        return []

    cart_names = {item.get("name", "").lower() for item in current_order_items}
    cart_ids = {item.get("item_id") for item in current_order_items}
    suggestions = []

    # ── Strategy 1: Combo-based upsell ──
    if combo_rules:
        for rule in combo_rules:
            antecedents = {a.lower() for a in rule.get("antecedents", [])}
            consequents = rule.get("consequents", [])

            if not consequents:
                continue

            consequent_name = consequents[0]

            # Check: antecedent items ⊆ current cart AND consequent NOT in cart
            if antecedents.issubset(cart_names) and consequent_name.lower() not in cart_names:
                # Find the menu item info for the consequent
                item_info = _find_menu_item(menu_data, consequent_name)
                if not item_info:
                    continue

                score = rule.get("combo_score", 0) * rule.get("confidence", 0)

                suggestions.append({
                    "item_id": item_info.get("id"),
                    "name": consequent_name,
                    "name_hi": item_info.get("name_hi", ""),
                    "selling_price": item_info.get("selling_price", 0),
                    "strategy": "combo",
                    "reason": f"Customers who order {', '.join(rule['antecedents'])} also love {consequent_name}!",
                    "confidence": rule.get("confidence", 0),
                    "upsell_score": round(score, 2),
                    "is_veg": item_info.get("is_veg", True),
                })

    # ── Strategy 2: Hidden star promotion ──
    if hidden_stars:
        for star in hidden_stars[:5]:  # Check top 5 hidden stars
            star_name = star.get("name", "")
            star_id = star.get("item_id") or star.get("id")

            # Skip items already in cart
            if star_name.lower() in cart_names or star_id in cart_ids:
                continue

            item_info = _find_menu_item(menu_data, star_name)
            if not item_info:
                continue

            cm_pct = star.get("cm_pct", star.get("margin_pct", 0))
            score = cm_pct * 0.5  # Lower base score than combo-based

            suggestions.append({
                "item_id": star_id,
                "name": star_name,
                "name_hi": item_info.get("name_hi", ""),
                "selling_price": item_info.get("selling_price", 0),
                "strategy": "hidden_star",
                "reason": f"🌟 Chef's Special: Try our {star_name}! Only ₹{item_info.get('selling_price', 0)}",
                "confidence": 0.0,
                "upsell_score": round(score, 2),
                "is_veg": item_info.get("is_veg", True),
            })

    # Sort by score and return max suggestions
    suggestions.sort(key=lambda x: x["upsell_score"], reverse=True)
    return suggestions[:max_suggestions]


def suggest_upsells(
    db: Session,
    ordered_item_ids: list[int],
    max_suggestions: int = 2,
    min_margin_pct: float = 55.0,
) -> list[dict]:
    """
    Suggest upsell items based on co-occurrence data from DB.
    Fallback method when combo_rules/hidden_stars aren't available.

    Args:
        db: Database session
        ordered_item_ids: IDs of items already in the order
        max_suggestions: Max number of upsell suggestions
        min_margin_pct: Minimum margin % for upsell candidates

    Returns:
        List of upsell suggestion dicts
    """
    if not ordered_item_ids:
        return []

    # Find orders that contain the current items
    related_order_ids = (
        db.query(SaleTransaction.order_id)
        .filter(SaleTransaction.item_id.in_(ordered_item_ids))
        .distinct()
        .limit(500)
        .all()
    )
    related_orders = [r[0] for r in related_order_ids]

    if not related_orders:
        return _fallback_suggestions(db, ordered_item_ids, max_suggestions)

    # Find items frequently in those same orders
    co_items = (
        db.query(
            SaleTransaction.item_id,
            func.count(SaleTransaction.id).label("co_count"),
        )
        .filter(
            SaleTransaction.order_id.in_(related_orders),
            ~SaleTransaction.item_id.in_(ordered_item_ids),
        )
        .group_by(SaleTransaction.item_id)
        .order_by(func.count(SaleTransaction.id).desc())
        .limit(20)
        .all()
    )

    if not co_items:
        return _fallback_suggestions(db, ordered_item_ids, max_suggestions)

    # Get item details and filter by margin
    suggestions = []
    for item_id, co_count in co_items:
        item = db.get(MenuItem, item_id)
        if not item or not item.is_available:
            continue

        margin_pct = item.margin_pct
        if margin_pct < min_margin_pct:
            continue

        score = co_count * (margin_pct / 100)

        suggestions.append({
            "item_id": item.id,
            "name": item.name,
            "name_hi": item.name_hi or "",
            "selling_price": item.selling_price,
            "strategy": "co_occurrence",
            "reason": _generate_suggestion_text(item),
            "confidence": 0.0,
            "upsell_score": round(score, 2),
            "is_veg": item.is_veg,
        })

        if len(suggestions) >= max_suggestions:
            break

    suggestions.sort(key=lambda x: x["upsell_score"], reverse=True)
    return suggestions


def _fallback_suggestions(
    db: Session, exclude_ids: list[int], limit: int
) -> list[dict]:
    """Fallback: suggest top-margin items not in the order."""
    items = (
        db.query(MenuItem)
        .filter(
            MenuItem.is_available == True,
            ~MenuItem.id.in_(exclude_ids),
        )
        .all()
    )

    scored = []
    for item in items:
        if item.margin_pct >= 60:
            scored.append({
                "item_id": item.id,
                "name": item.name,
                "name_hi": item.name_hi or "",
                "selling_price": item.selling_price,
                "strategy": "high_margin",
                "reason": _generate_suggestion_text(item),
                "confidence": 0.0,
                "upsell_score": round(item.margin_pct, 2),
                "is_veg": item.is_veg,
            })

    scored.sort(key=lambda x: x["upsell_score"], reverse=True)
    return scored[:limit]


def _generate_suggestion_text(item: MenuItem) -> str:
    """Generate a natural upsell suggestion."""
    if item.is_bestseller:
        return f"Our bestseller {item.name} goes great with your order! ₹{item.selling_price}"
    elif "chef-special" in (item.tags or []):
        return f"🌟 Try our chef's special {item.name}? Just ₹{item.selling_price}"
    else:
        return f"Would you like to add {item.name}? Only ₹{item.selling_price}"


def _find_menu_item(menu_data: list[dict], name: str) -> dict | None:
    """Find a menu item by name in the menu data list."""
    name_lower = name.lower()
    for item in menu_data:
        if isinstance(item, dict):
            if item.get("name", "").lower() == name_lower:
                return item
        else:
            # SQLAlchemy model object
            if hasattr(item, "name") and item.name.lower() == name_lower:
                return {
                    "id": item.id,
                    "name": item.name,
                    "name_hi": getattr(item, "name_hi", ""),
                    "selling_price": item.selling_price,
                    "is_veg": item.is_veg,
                }
    return None
