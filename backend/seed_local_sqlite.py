"""
seed_local_sqlite.py — Basic Offline Seed Script
================================================
Runs safely on any PC without network dependencies (SQLite).
Seeds 1 restaurant, a few categories, menu items, and orders.
"""

import sys, os, random, hashlib, uuid
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal, Base
from models import Restaurant, Category, MenuItem, Order, OrderItem

def h(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def seed_offline_data():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Check if already seeded
        if db.query(Restaurant).count() > 0:
            print("Database is already seeded with restaurants.")
            return

        print("Seeding offline SQLite database...")

        # 1. Restaurant
        r1 = Restaurant(
            name="Spice Craft",
            slug="spice-craft",
            email="admin@spicecraft.in",
            password_hash=h("spicecraft123"),
            phone="+91-9876543210",
            address="12, MG Road, Bengaluru",
            cuisine_type="Indian Multi-Cuisine",
        )
        db.add(r1)
        db.commit()
        db.refresh(r1)

        # 2. Categories
        cat_mains = Category(restaurant_id=r1.id, name="Main Course", display_order=1)
        cat_bread = Category(restaurant_id=r1.id, name="Roti & Naan", display_order=2)
        cat_drinks = Category(restaurant_id=r1.id, name="Beverages", display_order=3)
        db.add_all([cat_mains, cat_bread, cat_drinks])
        db.commit()
        db.refresh(cat_mains)
        db.refresh(cat_bread)
        db.refresh(cat_drinks)

        # 3. Menu Items
        items = [
            MenuItem(restaurant_id=r1.id, category_id=cat_mains.id, name="Paneer Butter Masala", selling_price=360, food_cost=120, is_veg=True),
            MenuItem(restaurant_id=r1.id, category_id=cat_mains.id, name="Butter Chicken", selling_price=420, food_cost=150, is_veg=False),
            MenuItem(restaurant_id=r1.id, category_id=cat_mains.id, name="Dal Makhani", selling_price=280, food_cost=85, is_veg=True),
            MenuItem(restaurant_id=r1.id, category_id=cat_bread.id, name="Butter Naan", selling_price=60, food_cost=18, is_veg=True),
            MenuItem(restaurant_id=r1.id, category_id=cat_bread.id, name="Garlic Naan", selling_price=70, food_cost=22, is_veg=True),
            MenuItem(restaurant_id=r1.id, category_id=cat_drinks.id, name="Mango Lassi", selling_price=150, food_cost=50, is_veg=True),
            MenuItem(restaurant_id=r1.id, category_id=cat_drinks.id, name="Masala Chai", selling_price=60, food_cost=15, is_veg=True),
        ]
        db.add_all(items)
        db.commit()
        
        for item in items:
            db.refresh(item)

        # 4. Dummy Orders for ML/Dashboards
        print("Generating dummy orders...")
        now = datetime.now(timezone.utc)
        
        for i in range(1, 151):
            dt = now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
            o = Order(
                restaurant_id=r1.id,
                order_id=f"ORD-SYNC-{i}-{uuid.uuid4().hex[:4]}",
                order_number=f"#{1000 + i}",
                total_amount=0.0,
                status="confirmed",
                order_type=random.choice(["dine_in", "takeaway"]),
                source="manual",
                created_at=dt,
                updated_at=dt
            )
            db.add(o)
            db.commit()
            db.refresh(o)
            
            # Add 2 to 4 items per order
            num_items = random.randint(2, 4)
            order_total = 0.0
            chosen = random.choices(items, k=num_items)
            
            for mi in chosen:
                qty = random.randint(1, 2)
                line_total = qty * mi.selling_price
                order_total += line_total
                
                oi = OrderItem(
                    order_pk=o.id,
                    item_id=mi.id,
                    quantity=qty,
                    unit_price=mi.selling_price,
                    line_total=line_total
                )
                db.add(oi)
                
            o.total_amount = order_total
            db.commit()

        print("Offline database successfully seeded!")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_offline_data()
