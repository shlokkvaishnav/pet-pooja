"""
config.py — Centralized configuration from environment and defaults
====================================================================
Single source of truth for non-secret app settings. Prefer env vars
in production; defaults are for development only.
"""

import os
from pathlib import Path


def _env_int(name: str, default: int, min_val: int | None = None, max_val: int | None = None) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    if min_val is not None and value < min_val:
        return default
    if max_val is not None and value > max_val:
        return default
    return value


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


# ── Database ─────────────────────────────────────
DB_POOL_SIZE = _env_int("DB_POOL_SIZE", 5, min_val=1, max_val=50)
DB_MAX_OVERFLOW = _env_int("DB_MAX_OVERFLOW", 10, min_val=0, max_val=100)
DB_POOL_RECYCLE = _env_int("DB_POOL_RECYCLE", 300, min_val=60, max_val=3600)
SQLITE_PATH = os.getenv("SQLITE_PATH", str(Path(__file__).parent / "petpooja.db"))

# ── Orders / Ops ──────────────────────────────────
ORDER_ID_PREFIX = os.getenv("ORDER_ID_PREFIX", "ORD-")
ORDERS_DEFAULT_LIMIT = _env_int("ORDERS_DEFAULT_LIMIT", 50, min_val=1, max_val=200)
ORDERS_MAX_LIMIT = _env_int("ORDERS_MAX_LIMIT", 200, min_val=50, max_val=500)
ORDERS_DEFAULT_DAYS = _env_int("ORDERS_DEFAULT_DAYS", 30, min_val=1, max_val=365)
MENU_ITEMS_LIST_LIMIT = _env_int("MENU_ITEMS_LIST_LIMIT", 100, min_val=10, max_val=500)
REPORTS_DEFAULT_DAYS = _env_int("REPORTS_DEFAULT_DAYS", 14, min_val=1, max_val=365)
REPORTS_TOP_N = _env_int("REPORTS_TOP_N", 8, min_val=1, max_val=50)
REPORTS_EXPORT_TOP_N = _env_int("REPORTS_EXPORT_TOP_N", 20, min_val=1, max_val=100)

# ── Revenue cache ────────────────────────────────
REVENUE_CACHE_TTL_SEC = _env_int("REVENUE_CACHE_TTL_SEC", 300, min_val=60, max_val=3600)
REVENUE_CACHE_MAX_SIZE = _env_int("REVENUE_CACHE_MAX_SIZE", 100, min_val=10, max_val=1000)

# ── Public / branding (exposed to frontend via API) ──
APP_NAME = os.getenv("APP_NAME", "sizzle-ai-copilot")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "hello@sizzle.ai")
CONTACT_PHONE = os.getenv("CONTACT_PHONE", "")
CONTACT_LOCATION = os.getenv("CONTACT_LOCATION", "")
DEFAULT_COMBO_DISCOUNT_PCT = _env_float("DEFAULT_COMBO_DISCOUNT_PCT", 10.0)


def get_default_settings() -> dict:
    """
    Default restaurant settings (DB-backed; this is fallback when creating new settings).
    Values can be overridden per restaurant in restaurant_settings table.
    """
    return {
        "menu_management": {
            "default_tax_pct": _env_float("DEFAULT_TAX_PCT", 5.0),
            "service_charge_pct": _env_float("DEFAULT_SERVICE_CHARGE_PCT", 0.0),
            "hide_unavailable_items": True,
            "category_ordering_mode": "manual",
        },
        "notifications": {
            "low_stock_alerts": True,
            "daily_revenue_digest": True,
            "weekly_performance_report": True,
        },
        "integrations": {
            "petpooja_connected": False,
            "posist_connected": False,
            "zomato_connected": False,
            "swiggy_connected": False,
            "payment_gateway": "not_connected",
        },
        "billing_plan": {
            "plan_name": "Starter",
            "plan_status": "active",
            "usage_month_to_date": 0,
            "invoices_available": False,
        },
        "security": {
            "two_factor_enabled": False,
            "active_sessions": 1,
            "api_keys_configured": 0,
        },
        "voice_ai_config": {
            "primary_language": os.getenv("VOICE_PRIMARY_LANGUAGE", "en"),
            "upsell_aggressiveness": os.getenv("VOICE_UPSELL_AGGRESSIVENESS", "medium"),
            "order_confirmation_phrase": os.getenv("VOICE_ORDER_CONFIRMATION_PHRASE", "Please confirm your order."),
            "call_transfer_enabled": False,
        },
        "profile_extras": {
            "operating_hours": os.getenv("DEFAULT_OPERATING_HOURS", "09:00-23:00"),
            "gst_number": "",
        },
        "display_thresholds": {
            "cm_green_min": _env_int("THRESHOLD_CM_GREEN_MIN", 65, min_val=0, max_val=100),
            "cm_yellow_min": _env_int("THRESHOLD_CM_YELLOW_MIN", 50, min_val=0, max_val=100),
            "risk_margin_max": _env_int("THRESHOLD_RISK_MARGIN_MAX", 40, min_val=0, max_val=100),
            "risk_popularity_min": _env_float("THRESHOLD_RISK_POPULARITY_MIN", 0.5),
            "confidence_green_min": _env_int("THRESHOLD_CONFIDENCE_GREEN_MIN", 80, min_val=0, max_val=100),
            "confidence_yellow_min": _env_int("THRESHOLD_CONFIDENCE_YELLOW_MIN", 60, min_val=0, max_val=100),
        },
    }


def get_default_combo_category_groups() -> dict:
    """
    Default category groups for combo validation (Indian restaurant structure).
    Keys: abstract group names (main, bread, side, drink, dessert).
    Values: list of category names that map to that group.
    Stored in DB per restaurant; this is the fallback when not set.
    """
    return {
        "main": ["Main Course", "Mains", "Biryani", "Rice", "Thali"],
        "bread": ["Breads", "Roti", "Naan"],
        "side": ["Starters", "Appetizers", "Sides", "Salads", "Raita"],
        "drink": ["Beverages", "Drinks", "Juices", "Lassi"],
        "dessert": ["Desserts", "Sweets"],
    }
