# Sizzle — Text-to-Speech Implementation Guide (Refined for Petpooja)
> RTX 4050 (6GB VRAM) · GPU-accelerated · Offline-first · Single-engine 6-language TTS + LLM Summarization
> **Status**: IMPLEMENTED — see MANUAL_SETUP_TTS.md for things to install manually.

---

## Architecture Overview

```
User speaks / types
     |
[Existing 8-stage VoicePipeline] -> dict with items, intent, user_messages, etc.
     |
llm_response.py  (backend/modules/voice/llm_response.py)
  -> Decision: complex? -> Qwen2.5:7B (CPU via Ollama) -> natural summary text
  -> Simple case?       -> Template string (5 languages)
     |
tts_normalizer.py  (backend/modules/voice/tts_normalizer.py)
  -> strips currency, expands digits, converts scripts, adds breathing punctuation
     |
tts_engine_indic.py  (backend/modules/voice/tts_engine_indic.py)
  -> Indic Parler TTS single engine for ALL 6 languages
  -> voice description selected by detected_language
  -> synthesize() -> WAV array
     |
pydub -> MP3 encode -> base64
     |
tts.py  (backend/modules/voice/tts.py)
  -> Orchestrator tying llm_response + normalizer + engine
  -> Returns { audio_b64, spoken_text, language }
     |
routes_voice.py appends { tts_audio_b64, tts_text, tts_language } to response JSON
     |
Frontend (VoiceOrder.jsx) decodes -> Audio API -> autoplay + waveform indicator
```

---

## Project Structure — New and Modified Files

### New Files (backend/modules/voice/)
| File | Purpose |
|---|---|
| llm_response.py | LLM decision logic, Ollama async call, template fallbacks (5 languages) |
| tts_normalizer.py | Currency/quantity/symbol expansion, script conversion, menu item protection |
| tts_engine_indic.py | Indic Parler TTS singleton — warmup, synthesize, in-memory MP3 postprocess |
| tts.py | Orchestrator tying all three modules, graceful failure wrapper |

### Modified Files
| File | Changes |
|---|---|
| voice_config.py | Added 17 TTS + LLM config keys to VoiceConfig class |
| routes_voice.py | TTS block appended to /process-audio and /process; new /speak endpoint |
| main.py | TTS warmup + Ollama health check in lifespan(); updated /api/health |
| requirements.txt | Added 6 TTS/LLM dependencies |
| frontend/src/api/client.js | Added speakText() API call |
| frontend/src/pages/VoiceOrder.jsx | Audio playback, speaking indicator, interrupt on record |
| frontend/src/components/VoiceRecorder.jsx | Added onStartRecording prop for audio interrupt |

---

## Key Design Decisions

### Single TTS Engine
Indic Parler TTS handles all 6 languages (en, hi, gu, mr, kn + Hinglish) with one model.
No dual-engine complexity. ~1.2GB VRAM, leaving 4.5GB free on RTX 4050.

### LLM Decision Logic
LLM (Qwen2.5:7B, CPU via Ollama) is called ONLY when templates produce unnatural output:
- 5+ items (too many to list by name)
- QUERY intent (customer asking about a dish)
- Upsell suggestions present
- 3+ disambiguation options
- Partial orders (some matched, some failed)

All other cases use templates — zero LLM latency.

### Graceful Degradation
- TTS fails -> response still has all order data, frontend shows text only
- LLM times out -> template fallback, no user-visible error
- Engine not loaded -> tts_audio_b64 is null, everything else works
- Ollama down -> templates handle everything

---

## Implementation Order (for reference)

1. voice_config.py additions - DONE
2. tts_normalizer.py - DONE
3. llm_response.py - DONE
4. tts_engine_indic.py - DONE
5. tts.py orchestrator - DONE
6. routes_voice.py modifications - DONE
7. main.py startup hooks - DONE
8. requirements.txt updates - DONE
9. Frontend client.js + VoiceOrder.jsx + VoiceRecorder.jsx - DONE
10. Manual setup guide - DONE (see MANUAL_SETUP_TTS.md)

---

## Performance Expectations on RTX 4050

| Operation | Time |
|---|---|
| Template path (ORDER 1-4 items, most common) | ~1.5-2.5s total |
| LLM path (5+ items, upsell, query) | ~2.0-3.2s total |
| TTS inference alone (GPU) | ~110-170ms |
| LLM inference alone (CPU) | ~500-700ms |
| tts_normalizer | ~3-5ms |
| pydub MP3 encode | ~15-20ms |
