"""
test_voice_config.py — Tests for Centralized Voice Config & Latest Changes
============================================================================
Covers:
  1. voice_config.py — defaults, env-var overrides, type casting
  2. session_store.py — MemoryBackend CRUD, cart mutations, eviction, timeout
  3. order_builder.py — tax calculation via config
  4. quantity_extractor.py — window sizes & limits via config
  5. upsell_engine.py — config-driven limits and thresholds
  6. VoiceSession model — to_dict / from_dict round-trip

Run: cd backend && python test_voice_config.py
"""

import sys
import os
import time

# Add backend dir to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ═══════════════════════════════════════════════════════════════════════════
# 1. VoiceConfig — defaults & env-var overrides
# ═══════════════════════════════════════════════════════════════════════════

def test_config_defaults():
    """All config values should have sensible defaults without any env vars."""
    from modules.voice.voice_config import VoiceConfig

    c = VoiceConfig()

    checks = [
        ("WHISPER_MODEL",            "large-v3-turbo"),
        ("STT_MIN_CONFIDENCE",       0.45),
        ("STT_BEAM_SIZE",            5),
        ("VAD_THRESHOLD",            0.40),
        ("VAD_MIN_SPEECH_SEC",       0.3),
        ("VAD_SAMPLE_RATE",          16000),
        ("ITEM_MATCH_FUZZY_WEIGHT",  0.4),
        ("ITEM_MATCH_SEMANTIC_WEIGHT", 0.6),
        ("ITEM_MATCH_FUZZY_THRESHOLD", 70),
        ("ITEM_MATCH_FAISS_TOP_K",   20),
        ("QTY_WINDOW_BEFORE",        3),
        ("QTY_WINDOW_AFTER",         4),
        ("QTY_DEFAULT",              1),
        ("QTY_MAX_VALID",            50),
        ("ORDER_TAX_RATE",           0.05),
        ("SESSION_MAX_COUNT",        500),
        ("SESSION_TIMEOUT_SEC",      1800),
        ("UPSELL_MAX_SUGGESTIONS",   2),
        ("UPSELL_HIDDEN_STAR_WEIGHT", 0.5),
        ("UPSELL_HIDDEN_STARS_POOL", 5),
        ("UPSELL_MIN_MARGIN_PCT",    55.0),
        ("UPSELL_RELATED_ORDERS_LIMIT", 500),
        ("UPSELL_CO_ITEMS_LIMIT",    20),
        ("UPSELL_FALLBACK_MARGIN",   60.0),
    ]

    passed = 0
    for attr, expected in checks:
        actual = getattr(c, attr)
        ok = actual == expected
        status = "PASS" if ok else "FAIL"
        if not ok:
            print(f"  {status}: {attr} expected={expected} got={actual}")
        passed += int(ok)

    print(f"  Config defaults: {passed}/{len(checks)} passed")
    return passed == len(checks)


def test_config_env_override():
    """Env vars should override defaults with correct type casting."""
    import importlib
    import modules.voice.voice_config as vc_mod

    # Set env vars BEFORE reloading the module so class attrs re-evaluate
    os.environ["WHISPER_MODEL"] = "tiny"
    os.environ["STT_MIN_CONFIDENCE"] = "0.99"
    os.environ["STT_BEAM_SIZE"] = "10"
    os.environ["STT_VAD_FILTER"] = "true"
    os.environ["VAD_THRESHOLD"] = "0.80"
    os.environ["QTY_MAX_VALID"] = "100"
    os.environ["ORDER_TAX_RATE"] = "0.18"
    os.environ["UPSELL_MAX_SUGGESTIONS"] = "5"

    importlib.reload(vc_mod)
    c = vc_mod.VoiceConfig()

    checks = [
        ("WHISPER_MODEL",          "tiny",  str),
        ("STT_MIN_CONFIDENCE",     0.99,    float),
        ("STT_BEAM_SIZE",          10,      int),
        ("STT_VAD_FILTER",         True,    bool),
        ("VAD_THRESHOLD",          0.80,    float),
        ("QTY_MAX_VALID",          100,     int),
        ("ORDER_TAX_RATE",         0.18,    float),
        ("UPSELL_MAX_SUGGESTIONS", 5,       int),
    ]

    passed = 0
    for attr, expected, expected_type in checks:
        actual = getattr(c, attr)
        type_ok = isinstance(actual, expected_type)
        val_ok = actual == expected
        ok = type_ok and val_ok
        status = "PASS" if ok else "FAIL"
        if not ok:
            print(f"  {status}: {attr} expected={expected}({expected_type.__name__}) got={actual}({type(actual).__name__})")
        passed += int(ok)

    # Clean up env vars and reload with defaults restored
    for key in ["WHISPER_MODEL", "STT_MIN_CONFIDENCE", "STT_BEAM_SIZE",
                "STT_VAD_FILTER", "VAD_THRESHOLD", "QTY_MAX_VALID",
                "ORDER_TAX_RATE", "UPSELL_MAX_SUGGESTIONS"]:
        os.environ.pop(key, None)
    importlib.reload(vc_mod)

    print(f"  Config env overrides: {passed}/{len(checks)} passed")
    return passed == len(checks)


def test_config_bool_variants():
    """Boolean env vars accept '1', 'true', 'yes' (case-insensitive)."""
    from modules.voice.voice_config import _env_bool

    truthy = ["1", "true", "True", "TRUE", "yes", "Yes", "YES"]
    falsy = ["0", "false", "no", "nope", ""]

    passed = 0
    total = len(truthy) + len(falsy)

    for val in truthy:
        os.environ["_TEST_BOOL"] = val
        result = _env_bool("_TEST_BOOL", False)
        ok = result is True
        if not ok:
            print(f"  FAIL: _env_bool('{val}') expected True, got {result}")
        passed += int(ok)

    for val in falsy:
        os.environ["_TEST_BOOL"] = val
        result = _env_bool("_TEST_BOOL", True)
        ok = result is False
        if not ok:
            print(f"  FAIL: _env_bool('{val}') expected False, got {result}")
        passed += int(ok)

    os.environ.pop("_TEST_BOOL", None)
    print(f"  Bool parsing: {passed}/{total} passed")
    return passed == total


# ═══════════════════════════════════════════════════════════════════════════
# 2. Session Store — MemoryBackend (no Redis/DB needed)
# ═══════════════════════════════════════════════════════════════════════════

def test_session_memory_backend():
    """Test MemoryBackend CRUD and cart mutations end-to-end."""
    from modules.voice.session_store import (
        _MemoryBackend,
        _apply_order, _apply_cancel, _apply_modify,
        _apply_modify_targeted,
    )

    backend = _MemoryBackend()
    tests_passed = 0
    total = 0

    # -- get() creates new session
    total += 1
    session = backend.get("test-001")
    ok = (
        session["session_id"] == "test-001"
        and session["order_items"] == []
        and session["turn_count"] == 0
        and session["confirmed"] is False
    )
    print(f"  {'PASS' if ok else 'FAIL'}: New session creation")
    tests_passed += int(ok)

    # -- apply ORDER mutation
    total += 1
    items = [
        {"item_id": 1, "name": "Paneer Tikka", "quantity": 2, "unit_price": 350, "line_total": 700},
        {"item_id": 2, "name": "Butter Naan", "quantity": 3, "unit_price": 60, "line_total": 180},
    ]
    _apply_order(session, items)
    ok = len(session["order_items"]) == 2 and session["order_items"][0]["quantity"] == 2
    print(f"  {'PASS' if ok else 'FAIL'}: ORDER adds items to cart")
    tests_passed += int(ok)

    # -- ORDER same item increments quantity
    total += 1
    _apply_order(session, [{"item_id": 1, "name": "Paneer Tikka", "quantity": 1, "unit_price": 350, "line_total": 350}])
    ok = session["order_items"][0]["quantity"] == 3  # 2+1
    print(f"  {'PASS' if ok else 'FAIL'}: ORDER same item increments qty (2+1=3)")
    tests_passed += int(ok)

    # -- CANCEL specific item
    total += 1
    _apply_cancel(session, [{"item_id": 2}])
    ok = len(session["order_items"]) == 1 and session["order_items"][0]["item_id"] == 1
    print(f"  {'PASS' if ok else 'FAIL'}: CANCEL removes specific item")
    tests_passed += int(ok)

    # -- CANCEL all (empty list)
    total += 1
    _apply_cancel(session, [])
    ok = session["order_items"] == []
    print(f"  {'PASS' if ok else 'FAIL'}: CANCEL with empty list clears cart")
    tests_passed += int(ok)

    # -- MODIFY replaces item in cart
    total += 1
    _apply_order(session, [{"item_id": 3, "name": "Dal Makhani", "quantity": 1, "unit_price": 280, "line_total": 280}])
    _apply_modify(session, [{"item_id": 3, "name": "Dal Makhani", "quantity": 2, "unit_price": 280, "line_total": 560}])
    ok = session["order_items"][0]["quantity"] == 2
    print(f"  {'PASS' if ok else 'FAIL'}: MODIFY replaces item details")
    tests_passed += int(ok)

    # -- MODIFY targeted (modifier updates)
    total += 1
    session["order_items"][0]["modifiers"] = {"spice_level": "mild"}
    _apply_modify_targeted(session, [{"item_id": 3, "modifiers": {"spice_level": "hot", "add_ons": ["cheese"]}}])
    ok = (
        session["order_items"][0]["modifiers"]["spice_level"] == "hot"
        and "cheese" in session["order_items"][0]["modifiers"]["add_ons"]
    )
    print(f"  {'PASS' if ok else 'FAIL'}: MODIFY targeted updates modifiers")
    tests_passed += int(ok)

    # -- save() and get() persistence
    total += 1
    session["turn_count"] = 5
    backend.save(session)
    fetched = backend.get("test-001")
    ok = fetched["turn_count"] == 5
    print(f"  {'PASS' if ok else 'FAIL'}: save+get persists state")
    tests_passed += int(ok)

    # -- delete()
    total += 1
    backend.delete("test-001")
    fresh = backend.get("test-001")
    ok = fresh["turn_count"] == 0 and fresh["order_items"] == []
    print(f"  {'PASS' if ok else 'FAIL'}: delete removes session")
    tests_passed += int(ok)

    # -- get_items()
    total += 1
    _apply_order(fresh, [{"item_id": 4, "name": "Mango Lassi", "quantity": 1, "unit_price": 120, "line_total": 120}])
    backend.save(fresh)
    items = backend.get_items("test-001")
    ok = len(items) == 1 and items[0]["name"] == "Mango Lassi"
    print(f"  {'PASS' if ok else 'FAIL'}: get_items returns cart items")
    tests_passed += int(ok)

    print(f"  Session MemoryBackend: {tests_passed}/{total} passed")
    return tests_passed == total


def test_session_eviction():
    """MemoryBackend evicts oldest sessions when MAX_SESSIONS is exceeded."""
    from modules.voice.session_store import _MemoryBackend, _MAX_SESSIONS

    backend = _MemoryBackend()

    # Create MAX_SESSIONS sessions
    for i in range(_MAX_SESSIONS):
        backend.get(f"evict-{i:04d}")

    # One more should evict the oldest
    backend.get(f"evict-{_MAX_SESSIONS:04d}")

    # The very first session should be gone
    fresh = backend.get("evict-0000")
    ok = fresh["turn_count"] == 0  # fresh session, not the old one
    print(f"  {'PASS' if ok else 'FAIL'}: Eviction after MAX_SESSIONS ({_MAX_SESSIONS})")
    return ok


def test_session_timeout():
    """Sessions older than SESSION_TIMEOUT should be evicted."""
    from modules.voice.session_store import _MemoryBackend, _SESSION_TIMEOUT

    backend = _MemoryBackend()
    session = backend.get("timeout-test")

    # Fake the timestamp to be expired
    session["last_active"] = time.time() - _SESSION_TIMEOUT - 10
    backend.save(session)

    # Accessing any session triggers eviction of expired ones
    backend.get("other-session")

    # The expired session should be gone from internal store
    items = backend.get_items("timeout-test")
    ok = items == []
    print(f"  {'PASS' if ok else 'FAIL'}: Expired session evicted (timeout={_SESSION_TIMEOUT}s)")
    return ok


# ═══════════════════════════════════════════════════════════════════════════
# 3. Order Builder — tax rate from config
# ═══════════════════════════════════════════════════════════════════════════

def test_order_builder_tax():
    """Tax should use cfg.ORDER_TAX_RATE, not a hardcoded value."""
    from modules.voice.order_builder import build_order
    from modules.voice.voice_config import cfg

    items = [
        {"item_id": 1, "name": "Paneer Tikka", "selling_price": 350, "quantity": 2},
        {"item_id": 2, "name": "Butter Naan", "selling_price": 60, "quantity": 3},
    ]
    order = build_order(items, session_id="TAX-TEST")

    subtotal = 350 * 2 + 60 * 3  # 700 + 180 = 880
    expected_tax = round(subtotal * cfg.ORDER_TAX_RATE, 2)
    expected_total = round(subtotal * (1 + cfg.ORDER_TAX_RATE), 2)

    tests_passed = 0
    total = 4

    ok = order["subtotal"] == subtotal
    print(f"  {'PASS' if ok else 'FAIL'}: Subtotal = {subtotal} (got {order['subtotal']})")
    tests_passed += int(ok)

    ok = order["tax"] == expected_tax
    print(f"  {'PASS' if ok else 'FAIL'}: Tax @{cfg.ORDER_TAX_RATE*100}% = {expected_tax} (got {order['tax']})")
    tests_passed += int(ok)

    ok = order["total"] == expected_total
    print(f"  {'PASS' if ok else 'FAIL'}: Total = {expected_total} (got {order['total']})")
    tests_passed += int(ok)

    ok = order["item_count"] == 2 and order["total_quantity"] == 5
    print(f"  {'PASS' if ok else 'FAIL'}: item_count=2, total_quantity=5")
    tests_passed += int(ok)

    print(f"  Order builder tax: {tests_passed}/{total} passed")
    return tests_passed == total


def test_order_builder_empty():
    """Empty items should return a valid skeleton order."""
    from modules.voice.order_builder import build_order

    order = build_order([], session_id="EMPTY-001")
    ok = (
        order["items"] == []
        and order["subtotal"] == 0
        and order["tax"] == 0
        and order["total"] == 0
        and order["status"] == "building"
    )
    print(f"  {'PASS' if ok else 'FAIL'}: Empty order returns valid skeleton")
    return ok


# ═══════════════════════════════════════════════════════════════════════════
# 4. Quantity Extractor — config-driven windows & limits
# ═══════════════════════════════════════════════════════════════════════════

def test_quantity_basic():
    """Quantity extraction uses cfg window sizes and defaults."""
    from modules.voice.quantity_extractor import extract_quantity, extract_quantities_for_items
    from modules.voice.voice_config import cfg

    tests_passed = 0
    total = 0

    # Numeric before item
    total += 1
    tokens = "do paneer tikka dena".split()
    qty = extract_quantity("do paneer tikka dena", 1, tokens)  # 'paneer' at position 1
    ok = qty == 2  # 'do' = 2 in HINDI_NUMBERS
    print(f"  {'PASS' if ok else 'FAIL'}: Hindi 'do' → 2 (got {qty})")
    tests_passed += int(ok)

    # Digit before item
    total += 1
    tokens = "3 butter naan please".split()
    qty = extract_quantity("3 butter naan please", 1, tokens)
    ok = qty == 3
    print(f"  {'PASS' if ok else 'FAIL'}: Digit '3' → 3 (got {qty})")
    tests_passed += int(ok)

    # Default when no quantity found
    total += 1
    tokens = "paneer tikka dena".split()
    qty = extract_quantity("paneer tikka dena", 0, tokens)
    ok = qty == cfg.QTY_DEFAULT
    print(f"  {'PASS' if ok else 'FAIL'}: No quantity → default {cfg.QTY_DEFAULT} (got {qty})")
    tests_passed += int(ok)

    # Out of range (exceeds QTY_MAX_VALID) — falls through to default
    total += 1
    tokens = "999 paneer tikka".split()
    qty = extract_quantity("999 paneer tikka", 1, tokens)
    ok = qty == cfg.QTY_DEFAULT  # 999 > 50
    print(f"  {'PASS' if ok else 'FAIL'}: 999 exceeds max ({cfg.QTY_MAX_VALID}) → default (got {qty})")
    tests_passed += int(ok)

    # extract_quantities_for_items batch
    total += 1
    matched = [
        {"item_id": 1, "name": "Paneer Tikka", "position": 1},
        {"item_id": 2, "name": "Butter Naan", "position": 5},
    ]
    results = extract_quantities_for_items("do paneer tikka aur teen butter naan", matched)
    ok = results[0]["quantity"] == 2 and results[1]["quantity"] == 3
    print(f"  {'PASS' if ok else 'FAIL'}: Batch extraction: 2 paneer, 3 naan")
    tests_passed += int(ok)

    print(f"  Quantity extractor: {tests_passed}/{total} passed")
    return tests_passed == total


# ═══════════════════════════════════════════════════════════════════════════
# 5. Upsell Engine — config-driven limits
# ═══════════════════════════════════════════════════════════════════════════

def test_upsell_combo_strategy():
    """Combo-based upsell uses config max_suggestions."""
    from modules.voice.upsell_engine import get_upsell_suggestions
    from modules.voice.voice_config import cfg

    cart = [{"item_id": 1, "name": "Paneer Tikka"}]
    menu = [
        {"id": 1, "name": "Paneer Tikka", "selling_price": 350, "is_veg": True},
        {"id": 2, "name": "Butter Naan", "selling_price": 60, "is_veg": True},
        {"id": 3, "name": "Dal Makhani", "selling_price": 280, "is_veg": True},
    ]
    rules = [
        {"antecedents": ["Paneer Tikka"], "consequents": ["Butter Naan"],
         "combo_score": 0.8, "confidence": 0.9},
        {"antecedents": ["Paneer Tikka"], "consequents": ["Dal Makhani"],
         "combo_score": 0.6, "confidence": 0.7},
    ]

    suggestions = get_upsell_suggestions(cart, menu, combo_rules=rules)

    tests_passed = 0
    total = 0

    total += 1
    ok = len(suggestions) <= cfg.UPSELL_MAX_SUGGESTIONS
    print(f"  {'PASS' if ok else 'FAIL'}: Max suggestions capped at {cfg.UPSELL_MAX_SUGGESTIONS} (got {len(suggestions)})")
    tests_passed += int(ok)

    total += 1
    ok = len(suggestions) == 2 and suggestions[0]["strategy"] == "combo"
    print(f"  {'PASS' if ok else 'FAIL'}: Both combo suggestions returned")
    tests_passed += int(ok)

    total += 1
    ok = suggestions[0]["upsell_score"] >= suggestions[1]["upsell_score"]
    print(f"  {'PASS' if ok else 'FAIL'}: Sorted by score descending")
    tests_passed += int(ok)

    print(f"  Upsell combo: {tests_passed}/{total} passed")
    return tests_passed == total


def test_upsell_hidden_star_strategy():
    """Hidden star suggestions use config pool size and weight."""
    from modules.voice.upsell_engine import get_upsell_suggestions
    from modules.voice.voice_config import cfg

    cart = [{"item_id": 1, "name": "Paneer Tikka"}]
    menu = [
        {"id": 1, "name": "Paneer Tikka", "selling_price": 350, "is_veg": True},
        {"id": 10, "name": "Star Item A", "selling_price": 200, "is_veg": True},
        {"id": 11, "name": "Star Item B", "selling_price": 250, "is_veg": True},
        {"id": 12, "name": "Star Item C", "selling_price": 300, "is_veg": False},
    ]
    # 8 hidden stars — only UPSELL_HIDDEN_STARS_POOL should be checked
    hidden_stars = [
        {"item_id": i, "name": f"Star Item {chr(65+i-10)}", "cm_pct": 70 - i}
        for i in range(10, 18)
    ]

    suggestions = get_upsell_suggestions(cart, menu, hidden_stars=hidden_stars)

    tests_passed = 0
    total = 0

    total += 1
    ok = len(suggestions) <= cfg.UPSELL_MAX_SUGGESTIONS
    print(f"  {'PASS' if ok else 'FAIL'}: Hidden star suggestions <= {cfg.UPSELL_MAX_SUGGESTIONS}")
    tests_passed += int(ok)

    total += 1
    ok = all(s["strategy"] == "hidden_star" for s in suggestions)
    print(f"  {'PASS' if ok else 'FAIL'}: All suggestions are hidden_star strategy")
    tests_passed += int(ok)

    # Score should be cm_pct * UPSELL_HIDDEN_STAR_WEIGHT
    total += 1
    if suggestions:
        first = suggestions[0]
        # Find matching hidden star
        star = next((h for h in hidden_stars if h["item_id"] == first["item_id"]), None)
        if star:
            expected_score = round(star["cm_pct"] * cfg.UPSELL_HIDDEN_STAR_WEIGHT, 2)
            ok = first["upsell_score"] == expected_score
        else:
            ok = False
    else:
        ok = False
    print(f"  {'PASS' if ok else 'FAIL'}: Score = cm_pct * {cfg.UPSELL_HIDDEN_STAR_WEIGHT}")
    tests_passed += int(ok)

    print(f"  Upsell hidden star: {tests_passed}/{total} passed")
    return tests_passed == total


def test_upsell_empty_cart():
    """Empty cart should return no suggestions."""
    from modules.voice.upsell_engine import get_upsell_suggestions
    result = get_upsell_suggestions([], [], combo_rules=[{"antecedents": ["X"], "consequents": ["Y"]}])
    ok = result == []
    print(f"  {'PASS' if ok else 'FAIL'}: Empty cart → no suggestions")
    return ok


def test_upsell_no_duplicate():
    """Items already in cart should not appear in suggestions."""
    from modules.voice.upsell_engine import get_upsell_suggestions

    cart = [{"item_id": 2, "name": "Butter Naan"}]
    menu = [{"id": 2, "name": "Butter Naan", "selling_price": 60, "is_veg": True}]
    rules = [{"antecedents": ["Butter Naan"], "consequents": ["Butter Naan"],
              "combo_score": 1.0, "confidence": 1.0}]

    suggestions = get_upsell_suggestions(cart, menu, combo_rules=rules)
    ok = len(suggestions) == 0
    print(f"  {'PASS' if ok else 'FAIL'}: Cart item not re-suggested")
    return ok


# ═══════════════════════════════════════════════════════════════════════════
# 6. VoiceSession model — round-trip
# ═══════════════════════════════════════════════════════════════════════════

def test_voice_session_model():
    """VoiceSession.to_dict() ↔ from_dict() should round-trip."""
    from models import VoiceSession

    data = {
        "session_id": "round-trip-001",
        "last_active": 1700000000.0,
        "order_items": [{"item_id": 1, "name": "Paneer Tikka", "quantity": 2}],
        "last_items": [{"item_id": 1, "name": "Paneer Tikka"}],
        "turn_count": 3,
        "confirmed": True,
    }

    row = VoiceSession.from_dict(data)
    restored = row.to_dict()

    tests_passed = 0
    total = 0

    total += 1
    ok = restored["session_id"] == data["session_id"]
    print(f"  {'PASS' if ok else 'FAIL'}: session_id round-trips")
    tests_passed += int(ok)

    total += 1
    ok = restored["last_active"] == data["last_active"]
    print(f"  {'PASS' if ok else 'FAIL'}: last_active round-trips")
    tests_passed += int(ok)

    total += 1
    ok = restored["order_items"] == data["order_items"]
    print(f"  {'PASS' if ok else 'FAIL'}: order_items round-trips")
    tests_passed += int(ok)

    total += 1
    ok = restored["turn_count"] == data["turn_count"]
    print(f"  {'PASS' if ok else 'FAIL'}: turn_count round-trips")
    tests_passed += int(ok)

    total += 1
    ok = restored["confirmed"] == data["confirmed"]
    print(f"  {'PASS' if ok else 'FAIL'}: confirmed round-trips")
    tests_passed += int(ok)

    print(f"  VoiceSession model: {tests_passed}/{total} passed")
    return tests_passed == total


# ═══════════════════════════════════════════════════════════════════════════
# 7. Config singleton is shared across modules
# ═══════════════════════════════════════════════════════════════════════════

def test_config_singleton():
    """All modules should share the same cfg singleton."""
    from modules.voice.voice_config import cfg as cfg1
    from modules.voice.voice_config import cfg as cfg2

    ok = cfg1 is cfg2
    print(f"  {'PASS' if ok else 'FAIL'}: cfg is a singleton across imports")
    return ok


# ═══════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════

def main():
    test_groups = [
        ("VoiceConfig Defaults",        test_config_defaults),
        ("VoiceConfig Env Overrides",   test_config_env_override),
        ("VoiceConfig Bool Parsing",    test_config_bool_variants),
        ("Config Singleton",            test_config_singleton),
        ("Session MemoryBackend CRUD",  test_session_memory_backend),
        ("Session Eviction",            test_session_eviction),
        ("Session Timeout",             test_session_timeout),
        ("Order Builder Tax",           test_order_builder_tax),
        ("Order Builder Empty",         test_order_builder_empty),
        ("Quantity Extraction",         test_quantity_basic),
        ("Upsell Combo Strategy",       test_upsell_combo_strategy),
        ("Upsell Hidden Star",          test_upsell_hidden_star_strategy),
        ("Upsell Empty Cart",           test_upsell_empty_cart),
        ("Upsell No Duplicate",         test_upsell_no_duplicate),
        ("VoiceSession Model",          test_voice_session_model),
    ]

    print("=" * 60)
    print("VOICE CONFIG & LATEST CHANGES — TEST SUITE")
    print("=" * 60)

    all_passed = 0
    all_failed = 0

    for name, fn in test_groups:
        print(f"\n▶ {name}")
        try:
            result = fn()
            if result:
                all_passed += 1
            else:
                all_failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            all_failed += 1

    total = all_passed + all_failed
    print("\n" + "=" * 60)
    print(f"RESULTS: {all_passed}/{total} test groups passed")
    if all_failed == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ {all_failed} test group(s) FAILED")
    print("=" * 60)

    return 0 if all_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
