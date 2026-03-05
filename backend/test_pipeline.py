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
    def __init__(self, id, name, name_hi, aliases, selling_price, modifiers):
        self.id = id
        self.name = name
        self.name_hi = name_hi
        self.aliases = aliases
        self.selling_price = selling_price
        self.modifiers = modifiers


# Mock menu items (simulates what DB would return)
menu_items = [
    MockItem(1, "Paneer Tikka",  "panir tikka", "pnr tikka|panir tikka", 350, '{"spice":["mild","medium","hot"]}'),
    MockItem(2, "Butter Naan",   "butter nan",  "bttr naan|butter nan",  60,  '{}'),
    MockItem(3, "Dal Makhani",   "dal makhni",  "dal makhni|daal makhani", 280, '{"spice":["mild","medium","hot"]}'),
    MockItem(4, "Mango Lassi",   "mango lassi", "mango lassi|lassi mango", 120, '{}'),
    MockItem(5, "Veg Biryani",   "veg biryani", "veg biryani|biryani",   320, '{"spice":["mild","medium","hot"]}'),
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


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("\n[VOICE PIPELINE TEST SUITE]\n")

    results = []
    results.append(("Normalizer", test_normalizer()))
    results.append(("Intent Mapper", test_intent_mapper()))
    results.append(("Item Matcher", test_item_matcher()))
    results.append(("Full Pipeline", test_full_pipeline()))

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
