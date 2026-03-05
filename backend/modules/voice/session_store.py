"""
session_store.py — In-Memory Session State for Multi-Turn Conversations
========================================================================
Tracks order context across requests using session_id.
Enables "add two more of those", "remove the last item", etc.
"""

import time
from collections import OrderedDict
from threading import Lock

# Max sessions before evicting oldest (prevent memory leak)
_MAX_SESSIONS = 500
# Session timeout in seconds (30 minutes)
_SESSION_TIMEOUT = 1800

_lock = Lock()
_sessions: OrderedDict = OrderedDict()


def _evict_expired():
    """Remove sessions older than timeout."""
    now = time.time()
    expired = [
        sid for sid, s in _sessions.items()
        if now - s["last_active"] > _SESSION_TIMEOUT
    ]
    for sid in expired:
        del _sessions[sid]


def get_session(session_id: str) -> dict:
    """Get or create a session. Returns the session state dict."""
    with _lock:
        _evict_expired()

        if session_id in _sessions:
            _sessions[session_id]["last_active"] = time.time()
            _sessions.move_to_end(session_id)
            return _sessions[session_id]

        # Evict oldest if at capacity
        while len(_sessions) >= _MAX_SESSIONS:
            _sessions.popitem(last=False)

        session = {
            "session_id": session_id,
            "last_active": time.time(),
            "order_items": [],       # Items from previous turns
            "last_items": [],        # Items from the most recent turn
            "turn_count": 0,
            "confirmed": False,
        }
        _sessions[session_id] = session
        return session


def update_session(session_id: str, new_items: list, intent: str):
    """
    Update session state after a pipeline run.
    Handles a single intent action. For compound intents,
    call this once per clause via update_session_compound().
    - ORDER: adds items to cart
    - CANCEL: removes specific items (or clears all if no items specified)
    - MODIFY: updates modifiers on matching items
    - CONFIRM: marks session as confirmed
    """
    with _lock:
        if session_id not in _sessions:
            return

        session = _sessions[session_id]
        session["last_active"] = time.time()
        session["turn_count"] += 1
        session["last_items"] = new_items

        if intent == "ORDER":
            _apply_order(session, new_items)
        elif intent == "CANCEL":
            _apply_cancel(session, new_items)
        elif intent == "CONFIRM":
            session["confirmed"] = True
        elif intent == "MODIFY":
            _apply_modify(session, new_items)


def update_session_compound(session_id: str, intent_actions: list):
    """
    Apply multiple intent actions from a compound utterance.

    intent_actions: list of {"intent": str, "items": list, "modifier_updates": list}
    Each action is applied sequentially so "cancel naan, add roti" works correctly.
    """
    with _lock:
        if session_id not in _sessions:
            get_session(session_id)  # create it
        session = _sessions[session_id]
        session["last_active"] = time.time()
        session["turn_count"] += 1

        all_items = []
        for action in intent_actions:
            intent = action["intent"]
            items = action.get("items", [])
            modifier_updates = action.get("modifier_updates", [])

            if intent == "ORDER":
                _apply_order(session, items)
                all_items.extend(items)
            elif intent == "CANCEL":
                _apply_cancel(session, items)
            elif intent == "CONFIRM":
                session["confirmed"] = True
            elif intent == "MODIFY":
                _apply_modify_targeted(session, modifier_updates)

        session["last_items"] = all_items


def _apply_order(session: dict, new_items: list):
    """Merge new items into cart. If same item exists, increment quantity."""
    existing_ids = {i["item_id"]: idx for idx, i in enumerate(session["order_items"])}
    for item in new_items:
        if item["item_id"] in existing_ids:
            idx = existing_ids[item["item_id"]]
            session["order_items"][idx]["quantity"] += item["quantity"]
            session["order_items"][idx]["line_total"] = (
                session["order_items"][idx]["quantity"]
                * session["order_items"][idx]["unit_price"]
            )
        else:
            session["order_items"].append(dict(item))


def _apply_cancel(session: dict, items_to_cancel: list):
    """
    Remove specific items from cart. If no items specified, clear everything.
    Matches by item_id.
    """
    if not items_to_cancel:
        session["order_items"] = []
        return
    cancel_ids = {i["item_id"] for i in items_to_cancel}
    session["order_items"] = [
        i for i in session["order_items"] if i["item_id"] not in cancel_ids
    ]


def _apply_modify(session: dict, new_items: list):
    """Replace matching items with new versions (legacy single-intent path)."""
    for item in new_items:
        existing_ids = {i["item_id"]: idx for idx, i in enumerate(session["order_items"])}
        if item["item_id"] in existing_ids:
            idx = existing_ids[item["item_id"]]
            session["order_items"][idx] = dict(item)


def _apply_modify_targeted(session: dict, modifier_updates: list):
    """
    Apply targeted modifier updates from extract_modifiers_with_target().
    Each update: {"item_id": int, "modifiers": {...}, "target_type": str}
    """
    for update in modifier_updates:
        item_id = update["item_id"]
        for i, cart_item in enumerate(session["order_items"]):
            if cart_item["item_id"] == item_id:
                existing_mods = cart_item.get("modifiers", {})
                new_mods = update["modifiers"]
                # Merge: new values overwrite existing per key
                if new_mods.get("spice_level"):
                    existing_mods["spice_level"] = new_mods["spice_level"]
                if new_mods.get("size"):
                    existing_mods["size"] = new_mods["size"]
                for addon in new_mods.get("add_ons", []):
                    if addon not in existing_mods.get("add_ons", []):
                        existing_mods.setdefault("add_ons", []).append(addon)
                session["order_items"][i]["modifiers"] = existing_mods
                break


def clear_session(session_id: str):
    """Remove a session entirely."""
    with _lock:
        _sessions.pop(session_id, None)


def get_session_items(session_id: str) -> list:
    """Get all accumulated order items for a session."""
    with _lock:
        session = _sessions.get(session_id)
        if session:
            return list(session["order_items"])
        return []
