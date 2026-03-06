import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
from models import Order
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

db = SessionLocal()
now = datetime.now(timezone.utc)
yesterday = now - timedelta(days=1)
two_days_ago = now - timedelta(days=2)

print("Orders today:", db.query(func.count(Order.id)).filter(Order.created_at >= yesterday).scalar())
print("Orders yesterday:", db.query(func.count(Order.id)).filter(Order.created_at >= two_days_ago, Order.created_at < yesterday).scalar())
print("Total orders:", db.query(func.count(Order.id)).scalar())

# Get date distribution
dist = db.query(func.date(Order.created_at), func.count(Order.id)).group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at).desc()).limit(10).all()
print("Recent date distribution:", dist)

db.close()
