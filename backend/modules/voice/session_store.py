"""
session_store.py — Persistent Session State for Multi-Turn Conversations
==========================================================================
Tracks order context across requests using session_id.
Enables "add two more of those", "remove the last item", etc.

Persistence backends (auto-detected at import):
  1. Redis   — fast, multi-worker safe, native TTL  (set REDIS_URL)
  2. Database — survives restarts via voice_sessions table  (uses DATABASE_URL)
  3. In-memory — development fallback (warns on startup)

The public API is identical regardless of backend.
"""

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from threading import Lock

from .voice_config import cfg

logger = logging.getLogger("petpooja.voice.session_store")

# From centralized config (env-overridable)
_MAX_SESSIONS = cfg.SESSION_MAX_COUNT
_SESSION_TIMEOUT = cfg.SESSION_TIMEOUT_SEC


def _new_session(session_id: str) -> dict:
    """Create a blank session dict."""
    return {
        "session_id": session_id,
        "last_active": time.time(),
        "order_items": [],
        "last_items": [],
        "turn_count": 0,
        "confirmed": False,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Cart-mutation helpers (shared by all backends — operate on plain dicts)
# ═══════════════════════════════════════════════════════════════════════════

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
    """Remove specific items from cart. If no items specified, clear everything."""
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
    """Apply targeted modifier updates from extract_modifiers_with_target()."""
    for update in modifier_updates:
        item_id = update["item_id"]
        for i, cart_item in enumerate(session["order_items"]):
            if cart_item["item_id"] == item_id:
                existing_mods = cart_item.get("modifiers", {})
                new_mods = update["modifiers"]
                if new_mods.get("spice_level"):
                    existing_mods["spice_level"] = new_mods["spice_level"]
                if new_mods.get("size"):
                    existing_mods["size"] = new_mods["size"]
                for addon in new_mods.get("add_ons", []):
                    if addon not in existing_mods.get("add_ons", []):
                        existing_mods.setdefault("add_ons", []).append(addon)
                session["order_items"][i]["modifiers"] = existing_mods
                break


def _apply_intents(session: dict, intent: str, new_items: list):
    """Route a single intent to the correct mutation."""
    if intent == "ORDER":
        _apply_order(session, new_items)
    elif intent == "CANCEL":
        _apply_cancel(session, new_items)
    elif intent == "CONFIRM":
        session["confirmed"] = True
    elif intent == "MODIFY":
        _apply_modify(session, new_items)


# ═══════════════════════════════════════════════════════════════════════════
# Backend interface
# ═══════════════════════════════════════════════════════════════════════════

class _SessionBackend(ABC):
    @abstractmethod
    def get(self, session_id: str) -> dict: ...
    @abstractmethod
    def save(self, session: dict) -> None: ...
    @abstractmethod
    def delete(self, session_id: str) -> None: ...
    @abstractmethod
    def get_items(self, session_id: str) -> list: ...


# ═══════════════════════════════════════════════════════════════════════════
# 1. Redis backend
# ═══════════════════════════════════════════════════════════════════════════

class _RedisBackend(_SessionBackend):
    def __init__(self, redis_url: str):
        import redis
        self._r = redis.from_url(redis_url, decode_responses=True)
        self._r.ping()  # fail fast if unreachable
        self._prefix = "voice_session:"
        logger.info("Session store: Redis (%s)", redis_url.split("@")[-1])

    def _key(self, session_id: str) -> str:
        return f"{self._prefix}{session_id}"

    def get(self, session_id: str) -> dict:
        raw = self._r.get(self._key(session_id))
        if raw:
            session = json.loads(raw)
            session["last_active"] = time.time()
            self.save(session)
            return session
        session = _new_session(session_id)
        self.save(session)
        return session

    def save(self, session: dict) -> None:
        session["last_active"] = time.time()
        self._r.setex(
            self._key(session["session_id"]),
            _SESSION_TIMEOUT,
            json.dumps(session),
        )

    def delete(self, session_id: str) -> None:
        self._r.delete(self._key(session_id))

    def get_items(self, session_id: str) -> list:
        raw = self._r.get(self._key(session_id))
        if raw:
            return json.loads(raw).get("order_items", [])
        return []


# ═══════════════════════════════════════════════════════════════════════════
# 2. Database backend (uses existing SQLAlchemy engine)
# ═══════════════════════════════════════════════════════════════════════════

class _DatabaseBackend(_SessionBackend):
    def __init__(self):
        from database import engine, SessionLocal, Base
        from models import VoiceSession  # noqa: F811
        # Create voice_sessions table if it doesn't exist yet
        VoiceSession.__table__.create(bind=engine, checkfirst=True)
        self._SessionLocal = SessionLocal
        logger.info("Session store: Database (voice_sessions table)")

    def _db(self):
        return self._SessionLocal()

    def get(self, session_id: str) -> dict:
        from models import VoiceSession
        db = self._db()
        try:
            self._evict_expired(db)
            row = db.query(VoiceSession).filter(
                VoiceSession.session_id == session_id
            ).first()
            if row:
                row.last_active = time.time()
                db.commit()
                return row.to_dict()
            # Create new
            session = _new_session(session_id)
            row = VoiceSession.from_dict(session)
            db.add(row)
            # Evict oldest if at capacity
            count = db.query(VoiceSession).count()
            if count >= _MAX_SESSIONS:
                oldest = (
                    db.query(VoiceSession)
                    .order_by(VoiceSession.last_active.asc())
                    .limit(count - _MAX_SESSIONS + 1)
                    .all()
                )
                for o in oldest:
                    db.delete(o)
            db.commit()
            return session
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def save(self, session: dict) -> None:
        from models import VoiceSession
        db = self._db()
        try:
            row = db.query(VoiceSession).filter(
                VoiceSession.session_id == session["session_id"]
            ).first()
            if row:
                row.last_active = time.time()
                row.order_items = session.get("order_items", [])
                row.last_items = session.get("last_items", [])
                row.turn_count = session.get("turn_count", 0)
                row.confirmed = session.get("confirmed", False)
            else:
                session["last_active"] = time.time()
                row = VoiceSession.from_dict(session)
                db.add(row)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete(self, session_id: str) -> None:
        from models import VoiceSession
        db = self._db()
        try:
            db.query(VoiceSession).filter(
                VoiceSession.session_id == session_id
            ).delete()
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_items(self, session_id: str) -> list:
        from models import VoiceSession
        db = self._db()
        try:
            row = db.query(VoiceSession).filter(
                VoiceSession.session_id == session_id
            ).first()
            if row:
                return row.order_items or []
            return []
        finally:
            db.close()

    def _evict_expired(self, db):
        from models import VoiceSession
        cutoff = time.time() - _SESSION_TIMEOUT
        db.query(VoiceSession).filter(
            VoiceSession.last_active < cutoff
        ).delete()


# ═══════════════════════════════════════════════════════════════════════════
# 3. In-memory backend (original fallback)
# ═══════════════════════════════════════════════════════════════════════════

class _MemoryBackend(_SessionBackend):
    def __init__(self):
        self._lock = Lock()
        self._sessions: OrderedDict = OrderedDict()
        logger.warning(
            "Session store: IN-MEMORY — sessions lost on restart. "
            "Set REDIS_URL or DATABASE_URL for persistence."
        )

    def _evict_expired(self):
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s["last_active"] > _SESSION_TIMEOUT
        ]
        for sid in expired:
            del self._sessions[sid]

    def get(self, session_id: str) -> dict:
        with self._lock:
            self._evict_expired()
            if session_id in self._sessions:
                self._sessions[session_id]["last_active"] = time.time()
                self._sessions.move_to_end(session_id)
                return self._sessions[session_id]
            while len(self._sessions) >= _MAX_SESSIONS:
                self._sessions.popitem(last=False)
            session = _new_session(session_id)
            self._sessions[session_id] = session
            return session

    def save(self, session: dict) -> None:
        with self._lock:
            session["last_active"] = time.time()
            self._sessions[session["session_id"]] = session

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def get_items(self, session_id: str) -> list:
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                return list(session["order_items"])
            return []


# ═══════════════════════════════════════════════════════════════════════════
# Backend auto-detection  (Redis → DB → Memory)
# ═══════════════════════════════════════════════════════════════════════════

def _init_backend() -> _SessionBackend:
    # 1. Try Redis
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            return _RedisBackend(redis_url)
        except Exception as e:
            logger.warning("Redis unavailable (%s) — trying database backend", e)

    # 2. Try Database
    if os.getenv("DATABASE_URL"):
        try:
            return _DatabaseBackend()
        except Exception as e:
            logger.warning("Database session backend failed (%s) — falling back to memory", e)

    # 3. In-memory fallback
    return _MemoryBackend()


_backend: _SessionBackend = _init_backend()


# ═══════════════════════════════════════════════════════════════════════════
# Public API — identical signatures to the original in-memory version
# ═══════════════════════════════════════════════════════════════════════════

def get_session(session_id: str) -> dict:
    """Get or create a session. Returns the session state dict."""
    return _backend.get(session_id)


def update_session(session_id: str, new_items: list, intent: str):
    """
    Update session state after a pipeline run.
    - ORDER: adds items to cart
    - CANCEL: removes specific items (or clears all if no items specified)
    - MODIFY: updates modifiers on matching items
    - CONFIRM: marks session as confirmed
    """
    session = _backend.get(session_id)
    session["last_active"] = time.time()
    session["turn_count"] += 1
    session["last_items"] = new_items
    _apply_intents(session, intent, new_items)
    _backend.save(session)


def update_session_compound(session_id: str, intent_actions: list):
    """
    Apply multiple intent actions from a compound utterance.
    Each action is applied sequentially so "cancel naan, add roti" works.
    """
    session = _backend.get(session_id)
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
    _backend.save(session)


def clear_session(session_id: str):
    """Remove a session entirely."""
    _backend.delete(session_id)


def get_session_items(session_id: str) -> list:
    """Get all accumulated order items for a session."""
    return _backend.get_items(session_id)
