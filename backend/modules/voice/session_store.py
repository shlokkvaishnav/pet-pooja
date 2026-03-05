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
    - ORDER: adds items to cart
    - CANCEL: clears the cart
    - MODIFY: keeps cart, new items replace matching ones
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
            # Merge: if same item_id exists, update quantity
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

        elif intent == "CANCEL":
            session["order_items"] = []

        elif intent == "CONFIRM":
            session["confirmed"] = True

        elif intent == "MODIFY":
            # Replace matching items with new versions
            for item in new_items:
                existing_ids = {i["item_id"]: idx for idx, i in enumerate(session["order_items"])}
                if item["item_id"] in existing_ids:
                    idx = existing_ids[item["item_id"]]
                    session["order_items"][idx] = dict(item)


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
