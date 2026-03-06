import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
from modules.revenue.combo_engine import generate_combos

def check():
    db = SessionLocal()
    combos = generate_combos(db, force_retrain=True)
    print("Combos Generated:", len(combos) if combos else 0)
    for c in (combos or [])[:5]:
        print(c.get('name'), "Discount:", c.get('discount_pct'), "Confidence:", c.get('confidence'))

if __name__ == "__main__":
    check()
