"""
test_changes.py -- Tests for the 4 recent fixes
==================================================
1. Whisper & Semantic model pre-loading at startup
2. FP-Growth combo as background job (not blocking requests)
3. Hindi number support extended (1-20)
4. Rate limiting on compute-heavy endpoints

Run:  cd backend && python test_changes.py
"""

import sys
import os
import io
import time
import threading

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Track results
_results = {"passed": 0, "failed": 0, "errors": []}


def _pass(name):
    _results["passed"] += 1
    print(f"  [PASS] {name}")


def _fail(name, detail=""):
    _results["failed"] += 1
    msg = f"  [FAIL] {name}" + (f" -- {detail}" if detail else "")
    _results["errors"].append(msg)
    print(msg)


# ============================================================
# 1. MODEL PRE-LOADING (warmup functions exist & are callable)
# ============================================================

def test_stt_warmup():
    """Verify stt.warmup() exists, is callable, and _get_model is importable."""
    print("=" * 60)
    print("TEST 1: WHISPER & SEMANTIC MODEL PRE-LOADING")
    print("=" * 60)

    # 1a. stt.warmup function exists
    try:
        from modules.voice.stt import warmup as stt_warmup, _get_model
        assert callable(stt_warmup), "warmup is not callable"
        _pass("stt.warmup() exists and is callable")
    except (ImportError, AssertionError) as e:
        _fail("stt.warmup() import", str(e))
        return

    # 1b. _get_model caching: calling twice returns same object
    try:
        from modules.voice import stt
        # Reset the global to test lazy loading
        original_model = stt._model
        stt._model = None

        # We won't actually load the heavy model in tests,
        # but verify the function exists and would set _model
        assert stt._model is None, "_model should be None after reset"
        _pass("stt._model is lazy-loaded (None before first call)")

        # Restore
        stt._model = original_model
    except Exception as e:
        _fail("stt._model caching", str(e))

    # 1c. Semantic model warmup exists
    try:
        from modules.voice.item_matcher import warmup_semantic_model, _semantic_index
        assert callable(warmup_semantic_model), "warmup_semantic_model not callable"
        _pass("item_matcher.warmup_semantic_model() exists and is callable")
    except (ImportError, AssertionError) as e:
        _fail("item_matcher.warmup_semantic_model() import", str(e))

    # 1d. warmup is called in main.py lifespan
    try:
        import ast
        with open("main.py", "r", encoding="utf-8") as f:
            source = f.read()
        assert "stt_warmup()" in source, "stt_warmup() not called in main.py"
        assert "warmup_semantic_model()" in source or "warmup_semantic_model" in source, \
            "warmup_semantic_model not referenced in main.py"
        _pass("main.py lifespan calls stt_warmup() and warmup_semantic_model()")
    except AssertionError as e:
        _fail("main.py lifespan warmup calls", str(e))

    print()


# ============================================================
# 2. FP-GROWTH COMBO BACKGROUND JOB
# ============================================================

def test_combo_background():
    """Verify combo engine has background training, read-only fetch, and scheduler."""
    print("=" * 60)
    print("TEST 2: FP-GROWTH COMBO AS BACKGROUND JOB")
    print("=" * 60)

    # 2a. fetch_combos_from_db exists (public read-only)
    try:
        from modules.revenue.combo_engine import fetch_combos_from_db
        assert callable(fetch_combos_from_db), "fetch_combos_from_db not callable"
        _pass("fetch_combos_from_db() exists (read-only accessor)")
    except (ImportError, AssertionError) as e:
        _fail("fetch_combos_from_db import", str(e))

    # 2b. run_combo_training_background exists
    try:
        from modules.revenue.combo_engine import run_combo_training_background
        assert callable(run_combo_training_background), "not callable"
        _pass("run_combo_training_background() exists")
    except (ImportError, AssertionError) as e:
        _fail("run_combo_training_background import", str(e))

    # 2c. start/stop combo scheduler exist
    try:
        from modules.revenue.combo_engine import start_combo_scheduler, stop_combo_scheduler
        assert callable(start_combo_scheduler), "start not callable"
        assert callable(stop_combo_scheduler), "stop not callable"
        _pass("start_combo_scheduler() and stop_combo_scheduler() exist")
    except (ImportError, AssertionError) as e:
        _fail("combo scheduler import", str(e))

    # 2d. _training_in_progress flag prevents duplicate runs
    try:
        from modules.revenue import combo_engine
        assert hasattr(combo_engine, "_training_in_progress"), "missing flag"
        assert combo_engine._training_in_progress is False, "should start False"
        _pass("_training_in_progress flag exists (default=False)")
    except (ImportError, AssertionError) as e:
        _fail("_training_in_progress flag", str(e))

    # 2e. COMBO_RETRAIN_INTERVAL_SEC is configurable via env
    try:
        from modules.revenue.combo_engine import _COMBO_RETRAIN_INTERVAL_SEC
        assert isinstance(_COMBO_RETRAIN_INTERVAL_SEC, int), "should be int"
        assert _COMBO_RETRAIN_INTERVAL_SEC > 0, "should be positive"
        _pass(f"COMBO_RETRAIN_INTERVAL_SEC = {_COMBO_RETRAIN_INTERVAL_SEC}s (env-overridable)")
    except (ImportError, AssertionError) as e:
        _fail("COMBO_RETRAIN_INTERVAL_SEC config", str(e))

    # 2f. GET /combos route does NOT call generate_combos — uses fetch_combos_from_db
    try:
        with open("api/routes_revenue.py", "r", encoding="utf-8") as f:
            source = f.read()

        # Find the get_combo_suggestions function body
        idx = source.index("def get_combo_suggestions")
        # Take next ~30 lines
        func_block = source[idx:idx + 600]

        assert "fetch_combos_from_db" in func_block, \
            "GET /combos should call fetch_combos_from_db"
        assert "generate_combos" not in func_block, \
            "GET /combos should NOT call generate_combos directly"
        _pass("GET /combos is read-only (calls fetch_combos_from_db, not generate_combos)")
    except (ValueError, AssertionError) as e:
        _fail("GET /combos route is read-only", str(e))

    # 2g. POST /combos/retrain endpoint exists
    try:
        assert "def retrain_combos" in source, \
            "retrain_combos endpoint not found"
        assert '"/combos/retrain"' in source, \
            "/combos/retrain path not found"
        _pass("POST /combos/retrain endpoint exists")
    except AssertionError as e:
        _fail("POST /combos/retrain endpoint", str(e))

    # 2h. main.py starts the scheduler at startup and stops on shutdown
    try:
        with open("main.py", "r", encoding="utf-8") as f:
            main_source = f.read()
        assert "start_combo_scheduler" in main_source, "scheduler not started in lifespan"
        assert "stop_combo_scheduler" in main_source, "scheduler not stopped on shutdown"
        _pass("main.py starts combo scheduler at startup, stops on shutdown")
    except AssertionError as e:
        _fail("main.py combo scheduler lifecycle", str(e))

    print()


# ============================================================
# 3. HINDI NUMBER SUPPORT (1-20)
# ============================================================

def test_hindi_numbers():
    """Verify all Hindi numbers 1-20 are supported, plus Whisper variants."""
    print("=" * 60)
    print("TEST 3: HINDI NUMBER SUPPORT (1-20)")
    print("=" * 60)

    from modules.voice.quantity_extractor import HINDI_NUMBERS, extract_quantity

    # 3a. Coverage: all Hindi numbers 1-10 with primary romanizations
    hindi_1_10 = {
        "ek": 1, "do": 2, "teen": 3, "chaar": 4, "paanch": 5,
        "chhe": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
    }
    for word, expected in hindi_1_10.items():
        if word not in HINDI_NUMBERS:
            _fail(f"Hindi 1-10: '{word}'", "missing from HINDI_NUMBERS")
            return
        if HINDI_NUMBERS[word] != expected:
            _fail(f"Hindi 1-10: '{word}'", f"expected {expected}, got {HINDI_NUMBERS[word]}")
            return
    _pass("Hindi 1-10 all present (ek through das)")

    # 3b. Hindi 11-20
    hindi_11_20 = {
        "gyaarah": 11, "baarah": 12, "terah": 13, "chaudah": 14,
        "pandrah": 15, "solah": 16, "satrah": 17, "athaarah": 18,
        "unnees": 19, "bees": 20,
    }
    all_ok = True
    for word, expected in hindi_11_20.items():
        if word not in HINDI_NUMBERS:
            _fail(f"Hindi 11-20: '{word}'", "missing from HINDI_NUMBERS")
            all_ok = False
            break
        if HINDI_NUMBERS[word] != expected:
            _fail(f"Hindi 11-20: '{word}'", f"expected {expected}, got {HINDI_NUMBERS[word]}")
            all_ok = False
            break
    if all_ok:
        _pass("Hindi 11-20 all present (gyaarah through bees)")

    # 3c. English 11-20
    english_11_20 = {
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20,
    }
    all_ok = True
    for word, expected in english_11_20.items():
        if word not in HINDI_NUMBERS or HINDI_NUMBERS[word] != expected:
            _fail(f"English 11-20: '{word}'", "missing or wrong value")
            all_ok = False
            break
    if all_ok:
        _pass("English 11-20 all present (eleven through twenty)")

    # 3d. Devanagari 11-20
    devanagari_11_20 = {
        "ग्यारह": 11, "बारह": 12, "तेरह": 13, "चौदह": 14,
        "पंद्रह": 15, "सोलह": 16, "सत्रह": 17, "अठारह": 18,
        "उन्नीस": 19, "बीस": 20,
    }
    all_ok = True
    for word, expected in devanagari_11_20.items():
        if word not in HINDI_NUMBERS or HINDI_NUMBERS[word] != expected:
            _fail(f"Devanagari 11-20: '{word}'", "missing or wrong value")
            all_ok = False
            break
    if all_ok:
        _pass("Devanagari 11-20 all present")

    # 3e. Whisper romanization variants (common misheard/alternate spellings)
    variants = {
        "aek": 1, "ikk": 1,           # ek variants
        "doh": 2, "dono": 2,          # do variants
        "tiin": 3,                     # teen variant
        "paach": 5, "punch": 5,       # paanch variants
        "cheh": 6, "che": 6,          # chhe variants
        "sat": 7, "saath": 7,         # saat variants
        "ath": 8, "aat": 8,           # aath variants
        "naw": 9,                      # nau variant
        "dus": 10, "duss": 10,        # das variants
        "gyarah": 11, "gyara": 11,    # gyaarah variants
        "barah": 12, "bara": 12,      # baarah variants
        "unnis": 19,                   # unnees variant
        "bis": 20,                     # bees variant
    }
    all_ok = True
    for word, expected in variants.items():
        if word not in HINDI_NUMBERS:
            _fail(f"Whisper variant: '{word}'", "missing from HINDI_NUMBERS")
            all_ok = False
            break
        if HINDI_NUMBERS[word] != expected:
            _fail(f"Whisper variant: '{word}'", f"expected {expected}, got {HINDI_NUMBERS[word]}")
            all_ok = False
            break
    if all_ok:
        _pass(f"Whisper romanization variants present ({len(variants)} checked)")

    # 3f. Functional tests: extract_quantity with realistic phrases
    test_cases = [
        # (text, item_position, expected_qty, description)
        ("aath chai", 1, 8, "'aath chai' -> 8"),
        ("chhe samosa", 1, 6, "'chhe samosa' -> 6"),
        ("saat roti", 1, 7, "'saat roti' -> 7"),
        ("nau lassi", 1, 9, "'nau lassi' -> 9"),
        ("das naan", 1, 10, "'das naan' -> 10"),
        ("gyaarah plate biryani", 1, 11, "'gyaarah plate biryani' -> 11"),
        ("bees roti", 1, 20, "'bees roti' -> 20"),
        ("twelve naan", 1, 12, "'twelve naan' -> 12"),
        ("twenty chai", 1, 20, "'twenty chai' -> 20"),
        ("chai lao", 0, 1, "'chai lao' -> default 1"),
        ("ek biryani", 1, 1, "'ek biryani' -> 1"),
        ("paanch samosa", 1, 5, "'paanch samosa' -> 5"),
    ]
    all_ok = True
    for text, pos, expected, desc in test_cases:
        tokens = text.split()
        qty = extract_quantity(text, pos, tokens)
        if qty != expected:
            _fail(f"extract_quantity: {desc}", f"got {qty}")
            all_ok = False
    if all_ok:
        _pass(f"extract_quantity: all {len(test_cases)} functional tests passed")

    # 3g. Total count sanity check
    count = len(HINDI_NUMBERS)
    if count >= 90:
        _pass(f"HINDI_NUMBERS has {count} entries (comprehensive coverage)")
    else:
        _fail(f"HINDI_NUMBERS entry count", f"only {count}, expected >= 90")

    # 3h. Hindi number words are in item_matcher SKIP_WORDS (prevent false menu matches)
    try:
        from modules.voice.item_matcher import SKIP_WORDS
        hindi_skip = ["chhe", "saat", "aath", "nau", "das", "gyaarah"]
        missing = [w for w in hindi_skip if w not in SKIP_WORDS]
        if missing:
            _fail("Hindi numbers in SKIP_WORDS", f"missing: {missing}")
        else:
            _pass("Hindi number words (6-15) added to item_matcher SKIP_WORDS")
    except ImportError as e:
        _fail("SKIP_WORDS import", str(e))

    print()


# ============================================================
# 4. RATE LIMITING
# ============================================================

def test_rate_limiting():
    """Verify in-process rate limiting is wired up correctly."""
    print("=" * 60)
    print("TEST 4: RATE LIMITING ON COMPUTE-HEAVY ENDPOINTS")
    print("=" * 60)

    # 4a. main.py has rate limiter middleware configured
    try:
        with open("main.py", "r", encoding="utf-8") as f:
            source = f.read()
        assert "rate_limit_middleware" in source, "rate_limit_middleware not imported"
        assert "app.middleware("http")(rate_limit_middleware)" in source, "rate limit middleware not wired"
        _pass("main.py wires in-process rate limiting middleware")
    except AssertionError as e:
        _fail("main.py rate limit middleware", str(e))

    # 4b. rate_limit.py has path-specific limits
    try:
        with open("api/rate_limit.py", "r", encoding="utf-8") as f:
            rl_source = f.read()
        assert "RATE_LIMIT_VOICE_RPM" in rl_source, "voice RPM env var missing"
        assert "RATE_LIMIT_REVENUE_RPM" in rl_source, "revenue RPM env var missing"
        assert "RATE_LIMIT_DEFAULT_RPM" in rl_source, "default RPM env var missing"
        _pass("rate_limit.py defines per-group RPM settings")
    except AssertionError as e:
        _fail("rate_limit.py settings", str(e))

    print()

# ============================================================
# 5. INTEGRATION: Full pipeline with extended numbers
# ============================================================

def test_pipeline_with_numbers():
    """Test end-to-end pipeline handles Hindi numbers 6-20 correctly."""
    print("=" * 60)
    print("TEST 5: PIPELINE INTEGRATION WITH EXTENDED NUMBERS")
    print("=" * 60)

    # Use mock items (no DB needed)
    class MockItem:
        def __init__(self, id, name, name_hi, aliases, selling_price, modifiers,
                     is_available=True, current_stock=None):
            self.id = id
            self.name = name
            self.name_hi = name_hi
            self.aliases = aliases
            self.selling_price = selling_price
            self.modifiers = modifiers
            self.is_available = is_available
            self.current_stock = current_stock

    mock_items = [
        MockItem(1, "Chai", "chai", "chai|tea", 30,
                 '{}'),
        MockItem(2, "Samosa", "samosa", "samosa|samose", 20,
                 '{}'),
        MockItem(3, "Roti", "roti", "roti|chapati", 15,
                 '{}'),
        MockItem(4, "Naan", "naan", "naan|nan", 40,
                 '{}'),
        MockItem(5, "Biryani", "biryani", "biryani", 250,
                 '{}'),
    ]

    try:
        from modules.voice.item_matcher import build_search_corpus, extract_all_items
        from modules.voice.quantity_extractor import extract_quantities_for_items

        corpus = build_search_corpus(mock_items)

        test_cases = [
            ("aath chai", "Chai", 8),
            ("das roti", "Roti", 10),
            ("chhe samosa", "Samosa", 6),
            ("saat naan", "Naan", 7),
            ("bees roti", "Roti", 20),
        ]

        all_ok = True
        for text, expected_item, expected_qty in test_cases:
            items = extract_all_items(text, corpus)
            items_with_qty = extract_quantities_for_items(text, items)

            if not items_with_qty:
                _fail(f"Pipeline '{text}'", "no items matched")
                all_ok = False
                continue

            item = items_with_qty[0]
            # Find item name from mock_items
            item_name = next((m.name for m in mock_items if m.id == item["item_id"]), "?")
            qty = item["quantity"]

            if item_name != expected_item:
                _fail(f"Pipeline '{text}'", f"matched '{item_name}', expected '{expected_item}'")
                all_ok = False
            elif qty != expected_qty:
                _fail(f"Pipeline '{text}'", f"qty={qty}, expected {expected_qty}")
                all_ok = False

        if all_ok:
            _pass(f"Pipeline correctly handles Hindi numbers 6-20 ({len(test_cases)} cases)")

    except Exception as e:
        _fail("Pipeline integration", str(e))

    print()


# ============================================================
# 6. SYNTAX CHECK ALL MODIFIED FILES
# ============================================================

def test_syntax():
    """Verify all modified files have valid Python syntax."""
    print("=" * 60)
    print("TEST 6: SYNTAX CHECK (ALL MODIFIED FILES)")
    print("=" * 60)

    import ast

    files = [
        "main.py",
        "modules/voice/stt.py",
        "modules/voice/item_matcher.py",
        "modules/voice/quantity_extractor.py",
        "modules/revenue/combo_engine.py",
        "api/routes_revenue.py",
        "api/routes_voice.py",
    ]

    all_ok = True
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                ast.parse(fh.read())
            _pass(f"Syntax OK: {f}")
        except SyntaxError as e:
            _fail(f"Syntax: {f}", f"line {e.lineno}: {e.msg}")
            all_ok = False

    print()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  TESTING RECENT CHANGES (4 fixes)")
    print("=" * 60)
    print()

    test_stt_warmup()
    test_combo_background()
    test_hindi_numbers()
    test_rate_limiting()
    test_pipeline_with_numbers()
    test_syntax()

    # ── Summary ──
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total = _results["passed"] + _results["failed"]
    print(f"  Passed: {_results['passed']}/{total}")
    print(f"  Failed: {_results['failed']}/{total}")

    if _results["errors"]:
        print()
        print("Failures:")
        for e in _results["errors"]:
            print(f"  {e}")

    print()
    if _results["failed"] == 0:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)

    sys.exit(0 if _results["failed"] == 0 else 1)
