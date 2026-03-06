import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
from sqlalchemy import text

def fix_dates():
    db = SessionLocal()
    
    db.execute(text(
        "UPDATE orders SET updated_at = created_at, settled_at = created_at WHERE DATE(updated_at) != DATE(created_at)"
    ))
    db.commit()
    
    db.execute(text(
        "UPDATE orders SET settled_at = created_at WHERE settled_at IS NULL"
    ))
    db.commit()

    print("Fixed order dates.")
    db.close()

if __name__ == "__main__":
    fix_dates()
