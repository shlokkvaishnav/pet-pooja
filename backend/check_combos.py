from database import SessionLocal
from models import ComboSuggestion

db = SessionLocal()
rows = db.query(ComboSuggestion.id, ComboSuggestion.restaurant_id, ComboSuggestion.name).limit(10).all()
print(f"Total combos in DB: {db.query(ComboSuggestion).count()}")
for r in rows:
    print(f"  id={r[0]}  restaurant_id={r[1]}  name={r[2][:40]}")
db.close()
