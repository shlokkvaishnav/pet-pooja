"""Debug script to analyze false positive matches."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from modules.voice.normalizer import normalize
from modules.voice.item_matcher import extract_all_items, build_search_corpus, match_item
from modules.voice.intent_mapper import classify_intents, _split_clauses
from database import SessionLocal
from models import MenuItem

db = SessionLocal()
items = db.query(MenuItem).filter(MenuItem.is_available == True).all()
corpus = build_search_corpus(items)
menu_map = {item.id: item for item in items}

normalized = (
    "niche paan ki dhukaan oppar randi ka makaan randi lehne ko tayyar "
    "dene ko tayyya dhi ka now give me 1 butter naan and 1 mutton biryani "
    "and 1 cold drink and 3 raita if you have and also suggest me something"
)

print("=== NORMALIZED TEXT ===")
print(normalized)
print()

# Test clause splitting first
print("=== CLAUSE SPLITTING ===")
clauses = _split_clauses(normalized)
for i, c in enumerate(clauses):
    print(f"  Clause {i}: {c!r}")
print()

# Test intent classification
print("=== INTENT CLASSIFICATION ===")
intents = classify_intents(normalized)
for r in intents:
    print(f"  [{r['intent']}] clause {r['clause_index']}: {r['clause']!r}")
print()

# Test individual problematic words
print("=== INDIVIDUAL WORD MATCHES ===")
test_phrases = ['paan', 'randi', 'rabri', 'butter', 'makaan', 'dhi', 'niche', 'oppar', 'cold drink']
for p in test_phrases:
    r = match_item(p, corpus)
    if r:
        db_item = menu_map.get(r['item_id'])
        name = db_item.name if db_item else '?'
        print(f"  match_item({p!r}) -> {name} (conf:{r['confidence']:.3f}, matched_as:{r['matched_as']})")
    else:
        print(f"  match_item({p!r}) -> None (SKIP or no match)")

# Full extraction on each ORDER clause separately (simulating pipeline)
print()
print("=== PER-CLAUSE EXTRACTION (simulating pipeline) ===")
for r in intents:
    if r['intent'] == 'ORDER':
        clause_results = extract_all_items(r['clause'], corpus)
        for cr in clause_results:
            db_item = menu_map.get(cr['item_id'])
            name = db_item.name if db_item else '?'
            print(f"  [{r['intent']}] {name} (conf:{cr['confidence']:.3f}, matched_as:{cr['matched_as']})")

# Full extraction on entire text (old behavior)
print()
print("=== FULL EXTRACTION (entire text) ===")
results = extract_all_items(normalized, corpus)
for r in results:
    db_item = menu_map.get(r['item_id'])
    name = db_item.name if db_item else '?'
    print(f"  {name} (conf:{r['confidence']:.3f}, matched_as:{r['matched_as']}, pos:{r.get('position')})")

# Expected vs actual
print()
print("=== EXPECTED vs ACTUAL ===")
expected = {"Butter Naan", "Mutton Biryani", "Cold Drink", "Raita"}
matched_names = {menu_map.get(r['item_id']).name for r in results if menu_map.get(r['item_id'])}
false_positives = matched_names - expected
missed = expected - matched_names
print("Expected:", sorted(expected))
print("Matched: ", sorted(matched_names))
print("False positives:", sorted(false_positives) if false_positives else "NONE")
print("Missed:", sorted(missed) if missed else "NONE")
if not false_positives and not missed:
    print(">>> ALL CORRECT! <<<")

db.close()
