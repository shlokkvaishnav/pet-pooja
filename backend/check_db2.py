import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
from models import RestaurantTable

db = SessionLocal()
tables = db.query(RestaurantTable).all()
print(f"Total tables: {len(tables)}")
seen = set()
dups = []
for t in tables:
    print(t.id, t.table_number)
    if t.table_number in seen:
        dups.append(t.id)
    seen.add(t.table_number)

if dups:
    print("Deleting duplicates:", dups)
    for d in dups:
        db.query(RestaurantTable).filter(RestaurantTable.id == d).delete()
    db.commit()
    print("Deleted duplicates!")
