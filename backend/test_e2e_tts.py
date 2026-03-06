"""
End-to-end test: Audio → STT → NLP Pipeline → LLM Text → TTS → MP3 output.
Simulates exactly what happens when a user speaks into the mic.
"""
import sys, io, asyncio, base64, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from database import SessionLocal
from models import MenuItem
from modules.voice.pipeline import VoicePipeline
from modules.voice.tts_engine_indic import indic_engine
from modules.voice.tts import tts_orchestrator

AUDIO_FILE = r"C:\Users\Pranshul Soni\Documents\Projects\pet-pooja\audio\Recording (6).m4a"


async def main():
    print("=" * 60)
    print("END-TO-END TEST: Audio → STT → NLP → TTS → MP3")
    print("=" * 60)

    # 1. Warmup TTS engine
    print("\n[1/4] Warming up TTS engine...")
    start = time.time()
    indic_engine.warmup()
    print(f"  TTS ready: {indic_engine.is_ready} ({time.time()-start:.1f}s)")

    # 2. Load pipeline from DB
    print("\n[2/4] Loading voice pipeline from DB...")
    db = SessionLocal()
    items = db.query(MenuItem).filter(MenuItem.is_available == True).all()
    pipeline = VoicePipeline(menu_items=items)
    print(f"  Menu items: {len(items)}")

    # 3. Process audio through pipeline
    print("\n[3/4] Processing audio through pipeline...")
    start = time.time()
    result = pipeline.process_audio(AUDIO_FILE)
    pipeline_time = time.time() - start

    print(f"  Transcript: {result['transcript']}")
    print(f"  Language: {result['detected_language']}")
    print(f"  Intent: {result['intent']}")
    print(f"  Items found: {len(result['items'])}")
    for item in result['items']:
        print(f"    -> {item['item_name']} x{item['quantity']} Rs.{item['unit_price']}")
    if result.get('order'):
        print(f"  Subtotal: Rs.{result['order'].get('subtotal', 0)}")
    print(f"  Pipeline time: {pipeline_time:.2f}s")

    # 4. Generate TTS response
    print("\n[4/4] Generating TTS audio response...")
    start = time.time()
    tts_result = await tts_orchestrator.get_audio_response(
        result, result.get("detected_language", "en")
    )
    tts_time = time.time() - start

    print(f"  Spoken text: {tts_result['spoken_text']}")
    print(f"  Language: {tts_result['language']}")

    if tts_result["audio_b64"]:
        audio_bytes = base64.b64decode(tts_result["audio_b64"])
        print(f"  Audio size: {len(audio_bytes)} bytes ({len(audio_bytes)/1024:.1f} KB)")
        print(f"  TTS time: {tts_time:.2f}s")

        # Save the MP3
        output_path = "test_e2e_response.mp3"
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        print(f"  Saved: {output_path}")

        print("\n" + "=" * 60)
        print("SUCCESS! Full pipeline works end-to-end.")
        print(f"  Total time: {pipeline_time + tts_time:.2f}s")
        print(f"  Play the response: start {output_path}")
        print("=" * 60)
    else:
        print("  ERROR: No audio generated!")
        print(f"  TTS time: {tts_time:.2f}s")

    db.close()


asyncio.run(main())
