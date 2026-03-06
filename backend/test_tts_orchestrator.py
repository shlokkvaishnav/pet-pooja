"""Test the full TTS orchestrator pipeline."""
import sys, io, asyncio, base64
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from modules.voice.tts_engine_indic import indic_engine
from modules.voice.tts import tts_orchestrator

# Warmup engine first
indic_engine.warmup()

pipeline_result = {
    "intent": "ORDER",
    "items": [
        {"item_name": "Butter Naan", "quantity": 1, "unit_price": 60},
        {"item_name": "Mutton Biryani", "quantity": 1, "unit_price": 400},
        {"item_name": "Cold Drink", "quantity": 1, "unit_price": 60},
        {"item_name": "Raita", "quantity": 3, "unit_price": 60},
    ],
    "order": {"subtotal": 700},
    "upsell_suggestions": [],
    "stage_results": [],
    "disambiguation": [],
}


async def test():
    # Test English
    result = await tts_orchestrator.get_audio_response(pipeline_result, "en")
    print(f"spoken_text: {result['spoken_text']}")
    print(f"language: {result['language']}")
    audio_b64 = result["audio_b64"]
    if audio_b64:
        audio_bytes = base64.b64decode(audio_b64)
        print(f"audio bytes: {len(audio_bytes)}")
        with open("test_orchestrator_output.mp3", "wb") as f:
            f.write(audio_bytes)
        print("Saved: test_orchestrator_output.mp3")
    else:
        print("NO AUDIO GENERATED")

    # Test Hindi
    result_hi = await tts_orchestrator.get_audio_response(pipeline_result, "hi")
    print(f"\nspoken_text (hi): {result_hi['spoken_text']}")
    audio_b64_hi = result_hi["audio_b64"]
    if audio_b64_hi:
        audio_bytes_hi = base64.b64decode(audio_b64_hi)
        print(f"audio bytes (hi): {len(audio_bytes_hi)}")
        with open("test_orchestrator_output_hi.mp3", "wb") as f:
            f.write(audio_bytes_hi)
        print("Saved: test_orchestrator_output_hi.mp3")
    else:
        print("NO AUDIO GENERATED (hi)")

    # Test speak_text endpoint
    speak_result = await tts_orchestrator.speak_text("Welcome to Petpooja!", "en")
    if speak_result["audio_b64"]:
        print(f"\nspeak_text: OK ({len(base64.b64decode(speak_result['audio_b64']))} bytes)")
    else:
        print("\nspeak_text: FAILED")


asyncio.run(test())
