"""Test real audio file through the full pipeline."""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import MenuItem
from modules.voice.pipeline import VoicePipeline

audio_path = r"c:\Users\Pranshul Soni\Documents\Projects\pet-pooja\audio\Recording.m4a"

db = SessionLocal()
items = db.query(MenuItem).filter(MenuItem.is_available == True).all()
pipeline = VoicePipeline(db_session=db, menu_items=items)

print(f"Testing audio: {audio_path}")
print(f"Menu items loaded: {len(items)}")
print("Processing audio through full pipeline...\n")

result = pipeline.process_audio(audio_path)

print(f"Transcript: {result['transcript']}")
print(f"Language: {result['detected_language']}")
print(f"Normalized: {result['normalized']}")
print(f"Intent: {result['intent']}")
print(f"Items found: {len(result['items'])}")
for item in result['items']:
    mods = item.get('modifiers', {})
    spice = mods.get('spice_level', '-')
    print(f"  -> {item['item_name']} x{item['quantity']} Rs.{item['line_total']} (conf:{item['confidence']}, spice:{spice})")
if result.get('order'):
    print(f"Subtotal: Rs.{result['order']['subtotal']}")
print(f"Needs clarification: {result['needs_clarification']}")

db.close()
