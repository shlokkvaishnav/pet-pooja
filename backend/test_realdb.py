import sys,io,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
from models import MenuItem
from modules.voice.pipeline import VoicePipeline
db=SessionLocal()
items=db.query(MenuItem).filter(MenuItem.is_available==True).all()
p=VoicePipeline(menu_items=items)
tests=[
 "bhaiya do paneer tikka aur ek butter naan dena",
 "do paneer tikka aur ek butter naan dena",
 "ek chicken biryani extra spicy aur do lassi",
 "teen roti aur dal makhani chahiye",
 "pnr tikka 2 aur bttr naan ek",
 "ek gulab jamun aur masala chai dena",
]
for t in tests:
 r=p.process_text(t)
 names=[f"{i['item_name']}x{i['quantity']}" for i in r['items']]
 print(f"{t}")
 print(f"  -> {', '.join(names)}")
 print()
db.close()
