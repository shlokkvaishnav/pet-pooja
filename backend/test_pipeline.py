"""
test_pipeline.py -- Standalone Voice Pipeline Test
===================================================
Tests the complete NLP pipeline with mock menu items.
No DB or Whisper model required.
Run: cd backend && python test_pipeline.py
"""

import sys
import os
import io

# Add backend to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class MockItem:
    """Mock MenuItem ORM object for testing without DB."""
    def __init__(self, id, name, name_hi, aliases, selling_price, modifiers,
                 is_available=True, current_stock=None):
        self.id = id
        self.name = name
        self.name_hi = name_hi
        self.aliases = aliases
        self.selling_price = selling_price
        self.modifiers = modifiers
        self.is_available = is_available
        self.current_stock = current_stock  # None = unlimited


# Mock menu items (simulates what DB would return)
menu_items = [
    MockItem(1, "Paneer Tikka",  "panir tikka", "pnr tikka|panir tikka", 350, '{"spice":["mild","medium","hot"]}'),
    MockItem(2, "Butter Naan",   "butter nan",  "bttr naan|butter nan",  60,  '{}'),
    MockItem(3, "Dal Makhani",   "dal makhni",  "dal makhni|daal makhani", 280, '{"spice":["mild","medium","hot"]}'),
    MockItem(4, "Mango Lassi",   "mango lassi", "mango lassi|lassi mango", 120, '{}'),
    MockItem(5, "Veg Biryani",   "veg biryani", "veg biryani|biryani",   320, '{"spice":["mild","medium","hot"]}',
            is_available=False),  # out of stock for testing
]


def test_normalizer():
    """Test normalizer -- only linguistic cleaning, no food aliases."""
    from modules.voice.normalizer import normalize

    print("=" * 60)
    print("TESTING NORMALIZER")
    print("=" * 60)

    tests = [
        ("Bhai umm do paneer tikka dena please", "2 paneer tikka dena"),
        ("Ek biryani aur teen cold drink chahiye", "1 biryani aur 3 cold drink chahiye"),
        ("boss paanch butter naan", "5 butter naan"),
        ("bhaiya do paneer tikka aur ek butter naan dena", "2 paneer tikka aur 1 butter naan dena"),
    ]
    passed = 0
    for input_text, expected in tests:
        result = normalize(input_text)
        ok = expected in result or result == expected
        passed += int(ok)
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] '{input_text}' -> '{result}'")
    print(f"  Normalizer: {passed}/{len(tests)} passed\n")
    return passed == len(tests)


def test_intent_mapper():
    """Test intent mapper."""
    from modules.voice.intent_mapper import classify_intent

    print("=" * 60)
    print("TESTING INTENT MAPPER")
    print("=" * 60)

    tests = [
        ("2 paneer tikka dena", "ORDER"),
        ("haan theek hai confirm karo", "CONFIRM"),
        ("extra spicy banana", "MODIFY"),
        ("cancel karo last wala", "CANCEL"),
    ]
    passed = 0
    for input_text, expected_intent in tests:
        intent, pattern = classify_intent(input_text)
        ok = intent == expected_intent
        passed += int(ok)
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] '{input_text}' -> {intent} (matched: '{pattern}')")
    print(f"  Intent Mapper: {passed}/{len(tests)} passed\n")
    return passed == len(tests)


def test_item_matcher():
    """Test dynamic item matching against mock DB items."""
    from modules.voice.item_matcher import build_search_corpus, extract_all_items

    print("=" * 60)
    print("TESTING ITEM MATCHER (Dynamic from Mock DB)")
    print("=" * 60)

    corpus = build_search_corpus(menu_items)
    print(f"  Corpus built dynamically: {len(corpus)} entries from {len(menu_items)} menu items")

    tests = [
        ("pnr tikka aur bttr naan", 2),       # fuzzy alias match
        ("panir tikka lao", 1),                # typo alias
        ("dal makhni chahiye", 1),             # alias
        ("mango lassi aur veg biryani", 2),    # two items
        ("2 paneer tikka aur 1 butter naan", 2),  # exact names
    ]
    passed = 0
    for text, expected_count in tests:
        matches = extract_all_items(text, corpus)
        ok = len(matches) >= expected_count
        passed += int(ok)
        items_str = ", ".join(f"{m['matched_as']} (conf:{m['confidence']})" for m in matches)
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] '{text}' -> {len(matches)} items [{items_str}]")
    print(f"  Item Matcher: {passed}/{len(tests)} passed\n")
    return passed == len(tests)


def test_full_pipeline():
    """Test complete pipeline with all 5 demo cases."""
    from modules.voice.pipeline import VoicePipeline

    print("=" * 60)
    print("TESTING FULL PIPELINE (Dynamic)")
    print("=" * 60)

    # Build pipeline with mock DB data (simulates real DB load)
    pipeline = VoicePipeline(
        db_session=None,
        menu_items=menu_items,
        combo_rules=[],
        hidden_stars=[],
    )

    tests = [
        {
            "name": "Test 1 -- English",
            "input": "2 paneer tikka and 1 butter naan please",
            "check": lambda r: len(r["items"]) >= 2,
        },
        {
            "name": "Test 2 -- Hindi",
            "input": "ek biryani dena aur do lassi bhi",
            "check": lambda r: len(r["items"]) >= 1,
        },
        {
            "name": "Test 3 -- Hinglish with modifier",
            "input": "bhai do paneer tikka extra spicy chahiye aur ek lassi",
            "check": lambda r: len(r["items"]) >= 1,
        },
        {
            "name": "Test 4 -- Typos (fuzzy match)",
            "input": "pnr tikka 2 aur bttr naan ek",
            "check": lambda r: len(r["items"]) >= 1,
        },
        {
            "name": "Test 5 -- No items (needs clarification)",
            "input": "kuch dena yaar",
            "check": lambda r: r["needs_clarification"] is True,
        },
    ]

    passed = 0
    for test in tests:
        result = pipeline.process_text(test["input"])
        ok = test["check"](result)
        passed += int(ok)
        status = "PASS" if ok else "FAIL"

        print(f"\n  [{status}] {test['name']}")
        print(f"    Input:      '{test['input']}'")
        print(f"    Normalized: '{result['normalized']}'")
        print(f"    Intent:      {result['intent']}")
        print(f"    Items:       {len(result['items'])} found")

        for item in result["items"]:
            mods = item.get("modifiers", {})
            spice = mods.get("spice_level", "-")
            print(f"      -> {item['item_name']} x{item['quantity']} "
                  f"Rs.{item['line_total']} (conf:{item['confidence']}, spice:{spice})")

        print(f"    Clarification: {result['needs_clarification']}")

        if result.get("order"):
            print(f"    Subtotal: Rs.{result['order'].get('subtotal', 0)}")

    print(f"\n  Pipeline: {passed}/{len(tests)} passed\n")
    return passed == len(tests)


def test_error_taxonomy():
    """
    Test the structured error taxonomy with a compound sentence that
    exercises every pipeline stage:
      - Compound intent (ORDER + MODIFY)
      - Successful match (paneer tikka, butter naan)
      - Out-of-stock item (veg biryani — is_available=False)
      - Zero match with fuzzy recovery ("chicken momos" — not on menu)
      - Unsupported modifier ("large" size on butter naan — no size options)
      - Valid modifier (extra spicy on paneer tikka)
      - Quantity extraction (2 paneer tikka, 1 butter naan, 1 veg biryani)
    """
    from modules.voice.pipeline import VoicePipeline

    print("=" * 60)
    print("TESTING ERROR TAXONOMY (Compound Stress Test)")
    print("=" * 60)

    pipeline = VoicePipeline(
        db_session=None,
        menu_items=menu_items,
        combo_rules=[],
        hidden_stars=[],
    )

    # ── The magic sentence ──
    #   Clause splitting: "aur"/"but" split into sub-clauses
    #   "dena" in the order clause ensures ORDER intent classification
    #   "chicken momos" is NOT on the menu → zero_match + fuzzy recovery
    #   "large butter naan" → unsupported modifier (no size options)
    #   "veg biryani" → is_available=False → out_of_stock
    #   "extra spicy paneer tikka" → valid modifier (hot spice)
    #   "cancel dal makhani" → compound CANCEL clause
    test_input = (
        "2 paneer tikka extra spicy aur 1 large butter naan "
        "aur 1 veg biryani aur chicken momos dena, "
        "but cancel dal makhani"
    )

    print(f"\n  Input: '{test_input}'\n")
    result = pipeline.process_text(test_input)

    checks = []

    # 1. Compound intents detected
    is_compound = result.get("is_compound", False)
    intents = [i["intent"] for i in result.get("intents", [])]
    checks.append(("Compound detected", is_compound))
    print(f"  [{'PASS' if is_compound else 'FAIL'}] Compound: {is_compound}, intents: {intents}")

    # 2. stage_results present (list)
    sr = result.get("stage_results", None)
    has_sr = isinstance(sr, list)
    checks.append(("stage_results is list", has_sr))
    print(f"  [{'PASS' if has_sr else 'FAIL'}] stage_results: {len(sr) if has_sr else 'MISSING'} entries")

    # 3. user_messages present (list)
    um = result.get("user_messages", None)
    has_um = isinstance(um, list)
    checks.append(("user_messages is list", has_um))
    print(f"  [{'PASS' if has_um else 'FAIL'}] user_messages: {len(um) if has_um else 'MISSING'} entries")

    # 4. Print every stage result
    if has_sr:
        for i, s in enumerate(sr):
            print(f"    stage_result[{i}]: status={s.get('status')}, "
                  f"type={s.get('error_type')}, msg={s.get('user_message', '')[:80]}")

    # 5. Print every user message
    if has_um:
        for i, msg in enumerate(um):
            print(f"    user_message[{i}]: {msg[:100]}")

    # 6. Out-of-stock item flagged
    oos_items = [i for i in result.get("items", []) if i.get("out_of_stock")]
    has_oos = len(oos_items) > 0
    checks.append(("Out-of-stock flagged", has_oos))
    print(f"  [{'PASS' if has_oos else 'FAIL'}] Out-of-stock items: "
          f"{[i['item_name'] for i in oos_items] if oos_items else 'NONE'}")

    # 7. Any stage result with error_type containing "zero_match" or "out_of_stock" or "modifier"
    error_types = [s.get("error_type", "") for s in (sr or [])]
    has_oos_sr = any("out_of_stock" in t for t in error_types)
    checks.append(("out_of_stock stage result", has_oos_sr))
    print(f"  [{'PASS' if has_oos_sr else 'FAIL'}] out_of_stock in stage_results: {has_oos_sr}")

    has_zero = any("zero_item_matches" in t for t in error_types)
    checks.append(("zero_match stage result", has_zero))
    print(f"  [{'PASS' if has_zero else 'FAIL'}] zero_item_matches in stage_results: {has_zero} "
          f"(for 'chicken momos')")

    # 8. Needs clarification
    nc = result.get("needs_clarification", False)
    checks.append(("needs_clarification", nc))
    print(f"  [{'PASS' if nc else 'FAIL'}] needs_clarification: {nc}")

    # 9. Items matched
    items = result.get("items", [])
    item_names = [i["item_name"] for i in items]
    has_items = len(items) >= 2
    checks.append(("At least 2 items matched", has_items))
    print(f"  [{'PASS' if has_items else 'FAIL'}] Items: {item_names}")

    # 10. Print full order summary
    print(f"\n  Intent: {result.get('intent')}")
    print(f"  Normalized: {result.get('normalized')}")
    for item in items:
        mods = item.get("modifiers", {})
        oos = " [OUT OF STOCK]" if item.get("out_of_stock") else ""
        print(f"    -> {item['item_name']} x{item['quantity']} "
              f"Rs.{item.get('line_total', '?')} spice={mods.get('spice_level', '-')}{oos}")

    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)
    print(f"\n  Error Taxonomy: {passed}/{total} passed\n")
    return passed == total


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("\n[VOICE PIPELINE TEST SUITE]\n")

    results = []
    results.append(("Normalizer", test_normalizer()))
    results.append(("Intent Mapper", test_intent_mapper()))
    results.append(("Item Matcher", test_item_matcher()))
    results.append(("Full Pipeline", test_full_pipeline()))

    results.append(("Error Taxonomy", test_error_taxonomy()))

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_pass = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        all_pass = all_pass and passed
        print(f"  [{status}] {name}")

    print(f"\n{'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
    print("=" * 60)
