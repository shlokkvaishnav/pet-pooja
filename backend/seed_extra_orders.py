import sys
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Restaurant, MenuItem, Order, OrderItem

def generate_random_date(start_days_ago, end_days_ago):
    now = datetime.now(timezone.utc)
    delta = start_days_ago - end_days_ago
    random_days = random.uniform(0, delta)
    random_dt = now - timedelta(days=end_days_ago + random_days)
    return random_dt

def seed_orders():
    db = SessionLocal()
    restaurants = db.query(Restaurant).all()
    
    if not restaurants:
        print("No restaurants found.")
        return

    total_added = 0
    for r in restaurants:
        menu_items = db.query(MenuItem).filter(MenuItem.restaurant_id == r.id, MenuItem.is_available == True).all()
        if not menu_items:
            print(f"Skipping {r.name} - no menu items.")
            continue
            
        print(f"Generating orders for {r.name}...")
        
        # 200 orders in last 30 days, 150 orders older than 30 days (e.g., 30 to 180 days ago)
        date_specs = [
            (30, 0, 200),     # start_days_ago, end_days_ago, count
            (180, 31, 150)    # start_days_ago, end_days_ago, count
        ]
        
        restaurant_orders_added = 0
        
        # Try to get highest existing order to continue sequence ideally, or just random
        # Just use uuid for everything to be safe
        order_idx = db.query(Order).count() + 1
        
        for start_days_ago, end_days_ago, count in date_specs:
            for _ in range(count):
                order_dt = generate_random_date(start_days_ago, end_days_ago)
                
                # Create Order
                order_id_str = f"ORD-{order_dt.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
                order_number = f"#{order_idx}"
                order_idx += 1
                
                order_type = random.choice(["dine_in", "takeaway", "delivery"])
                source = random.choice(["manual", "voice"])
                
                new_order = Order(
                    order_id=order_id_str,
                    order_number=order_number,
                    restaurant_id=r.id,
                    total_amount=0.0, # Will update after items
                    status="confirmed",
                    order_type=order_type,
                    source=source,
                    created_at=order_dt,
                    updated_at=order_dt,
                    settled_at=order_dt,
                )
                
                db.add(new_order)
                db.flush() # To get new_order.id
                
                # Add items
                num_items = random.randint(1, 4)
                items_to_add = random.choices(menu_items, k=num_items)
                
                total_amount = 0.0
                for item in items_to_add:
                    quantity = random.randint(1, 3)
                    unit_price = item.selling_price
                    line_total = unit_price * quantity
                    total_amount += line_total
                    
                    oi = OrderItem(
                        order_pk=new_order.id,
                        item_id=item.id,
                        quantity=quantity,
                        unit_price=unit_price,
                        line_total=line_total,
                    )
                    db.add(oi)
                    
                new_order.total_amount = total_amount
                restaurant_orders_added += 1
                total_added += 1
        
        db.commit()
        print(f"Added {restaurant_orders_added} orders for {r.name}.")
        
    db.close()
    print(f"Done. Successfully added {total_added} total orders.")

if __name__ == "__main__":
    seed_orders()
