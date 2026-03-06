# Sizzle TTS — Manual Setup Guide
> Things you need to install, download, or configure manually before the TTS system works.

---

## 1. Install Ollama (LLM Backend)

Ollama runs Qwen2.5:7B on CPU for natural language summarization.

### Linux / WSL
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Windows
Download from [https://ollama.com/download](https://ollama.com/download) and run the installer.

### After installation — Pull the model
```bash
ollama pull qwen2.5:7b-instruct-q4_K_M
```

### Start Ollama service
```bash
# Linux
sudo systemctl enable ollama && sudo systemctl start ollama

# Windows — Ollama runs as a system service after installation
# Verify it's running:
curl http://localhost:11434/api/tags
```

> **Disk space**: ~4.5GB for the Q4_K_M quantized model  
> **RAM**: ~6GB when loaded  
> **GPU**: None — runs entirely on CPU

---

## 2. Install Python Dependencies

> **IMPORTANT**: Due to dependency conflicts between `parler-tts` (wants `transformers==4.46.1`) and Python 3.14 (needs `tokenizers>=0.22` which requires `transformers>=5.0`), you **cannot** just run `pip install -r requirements.txt`. Follow the steps below in order.

### Step-by-step install (from project root):

```bash
cd backend

# 1. Install parler-tts from GitHub (it will install with its deps)
pip install "git+https://github.com/huggingface/parler-tts.git"

# 2. Install descript-audiotools (required by parler-tts → dac)
pip install descript-audiotools

# 3. Install einops (required by descript-audio-codec)
pip install einops

# 4. Upgrade protobuf back to v4+ (descript-audiotools downgrades it, parler-tts needs >=4)
pip install "protobuf>=4.0.0"

# 5. Upgrade transformers to 5.x (needed for tokenizers 0.22+ on Python 3.14)
pip install --no-deps "transformers>=5.0.0"

# 6. Patch parler-tts for transformers 5.x compatibility (SlidingWindowCache was removed)
python -c "
import pathlib, re
f = pathlib.Path(__import__('parler_tts').__file__).parent / 'modeling_parler_tts.py'
t = f.read_text(encoding='utf-8')
old = '''from transformers.cache_utils import (
    Cache,
    DynamicCache,
    EncoderDecoderCache,
    SlidingWindowCache,
    StaticCache,
)'''
new = '''from transformers.cache_utils import (
    Cache,
    DynamicCache,
    EncoderDecoderCache,
    StaticCache,
)
try:
    from transformers.cache_utils import SlidingWindowCache
except ImportError:
    SlidingWindowCache = StaticCache  # compat shim for transformers>=5'''
f.write_text(t.replace(old, new), encoding='utf-8')
print('Patched parler_tts for transformers 5.x compatibility')
"

# 7. Install remaining dependencies
pip install soundfile>=0.12.1 indic-transliteration>=2.3.0 httpx>=0.27.0 sentencepiece

# 8. Verify everything imports
python -c "from parler_tts import ParlerTTSForConditionalGeneration; print('parler_tts OK'); import soundfile; print('soundfile OK'); import httpx; print('httpx OK'); from indic_transliteration import sanscript; print('indic_transliteration OK')"
```

### Key packages:

| Package | Size | Purpose |
|---|---|---|
| `parler-tts` (from GitHub) | ~50MB code | TTS engine framework (by HuggingFace) |
| `descript-audiotools` + `descript-audio-codec` | ~120MB | Audio processing (required by parler-tts) |
| `transformers>=5.0.0` | ~10MB | HuggingFace model loading (patched for compat) |
| `soundfile` | ~5MB | WAV I/O |
| `indic-transliteration` | ~10MB | Script conversion (Roman↔Devanagari/Gujarati/Kannada) |
| `httpx` | ~1MB | Async HTTP client for Ollama |

> **Note**: The TTS *code* comes from `huggingface/parler-tts` (GitHub). The *model weights* (`ai4bharat/indic-parler-tts`) are downloaded from HuggingFace Hub at first run.

### Why the manual steps?

`parler-tts` v0.2.2 pins `transformers<=4.46.1,>=4.46.1` (exact version), but `transformers==4.46.1` requires `tokenizers<0.21`, which has no pre-built wheel for Python 3.14. The solution is to use `transformers>=5.0` with `tokenizers>=0.22` and patch one removed import (`SlidingWindowCache`) in parler-tts.

> pip will show dependency conflict warnings — these are expected and safe to ignore after applying the patch.

---

## 3. Pre-Download TTS Model Weights

The Indic Parler TTS model is ~1.1GB. Pre-download it before starting the server to avoid a 30-second cold start on the first request.

> **Note**: You must first accept the license on [https://huggingface.co/ai4bharat/indic-parler-tts](https://huggingface.co/ai4bharat/indic-parler-tts) and login with `huggingface-cli login` before downloading.

```bash
pip install huggingface_hub
huggingface-cli login

python -c "
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer
print('Downloading Indic Parler TTS model weights...')
model = ParlerTTSForConditionalGeneration.from_pretrained('ai4bharat/indic-parler-tts')
AutoTokenizer.from_pretrained('ai4bharat/indic-parler-tts')
AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)
print('Download complete!')
"
```

> **Storage**: ~1.1GB in `~/.cache/huggingface/hub/`  
> **VRAM**: ~1.2GB when loaded to GPU

---

## 4. Verify CUDA / GPU Setup

The TTS engine runs on GPU for fast inference (~110–170ms per sentence).

```bash
python -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB')
"
```

If CUDA is not available, TTS will fall back to CPU (much slower ~1–3 seconds per synthesis). Ensure you have:
- NVIDIA GPU with ≥4GB VRAM
- CUDA toolkit installed
- PyTorch with CUDA support: `pip install torch --index-url https://download.pytorch.org/whl/cu121`

---

## 5. Verify ffmpeg

`pydub` (used for WAV→MP3 conversion) requires `ffmpeg`. This should already be installed for the existing STT (Whisper) pipeline.

```bash
ffmpeg -version
```

If not installed:
- **Windows**: `winget install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)
- **Linux**: `sudo apt install ffmpeg`

---

## 6. Environment Variables (Optional Overrides)

All TTS/LLM config has sensible defaults. Override via environment variables only if needed:

```env
# Disable TTS entirely (responses will be text-only)
TTS_ENABLED=false

# Disable LLM (all responses use templates — no Ollama needed)
LLM_ENABLED=false

# Change TTS device (if no GPU)
TTS_DEVICE=cpu

# Change Ollama URL (if running on different machine)
LLM_BASE_URL=http://192.168.1.100:11434

# Increase LLM timeout (for slower machines)
LLM_TIMEOUT_SEC=5.0

# Change voice descriptions (for different TTS voice character)
TTS_VOICE_EN="A deep male voice with clear pronunciation. Slow pace."
```

---

## 7. First Run Checklist

Before starting the server with TTS enabled:

- [ ] Ollama installed and running (`curl http://localhost:11434/api/tags` returns 200)
- [ ] Qwen2.5:7B model pulled (`ollama list` shows `qwen2.5:7b-instruct-q4_K_M`)
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Indic Parler TTS weights downloaded (run the pre-download script above)
- [ ] CUDA available (`python -c "import torch; print(torch.cuda.is_available())"` → True)
- [ ] ffmpeg installed (`ffmpeg -version`)

### Start the server:
```bash
cd backend
python main.py
```

You should see these log lines during startup:
```
Loading Indic Parler TTS (ai4bharat/indic-parler-tts) on cuda...
Running TTS warmup inference...
Indic Parler TTS ready on cuda (warmup: ~9s, sample_rate: 44100Hz)
Ollama reachable — available models: ['qwen2.5:7b-instruct-q4_K_M']
```

### Test TTS via API:
```bash
curl -X POST http://localhost:8000/api/voice/speak \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"text": "Hello, welcome to our restaurant!", "language": "en"}'
```

---

## 8. Troubleshooting

| Problem | Solution |
|---|---|
| `Import "parler_tts" could not be resolved` | Run `pip install git+https://github.com/huggingface/parler-tts.git` |
| `cannot import name 'SlidingWindowCache'` | Run the patch script from Step 2, step 6 |
| `tokenizers>=0.20,<0.21 is required` | You have wrong transformers version. Run `pip install --no-deps "transformers>=5.0.0"` then patch |
| `No module named 'dac'` or `No module named 'audiotools'` | Run `pip install descript-audio-codec descript-audiotools einops` |
| `CUDA out of memory` | Reduce other GPU usage, or set `TTS_DEVICE=cpu` |
| TTS warmup fails but server starts | TTS is disabled gracefully; responses will be text-only |
| Ollama not reachable | LLM falls back to templates automatically; install Ollama or set `LLM_ENABLED=false` |
| Audio plays but sounds robotic | Tune `TTS_VOICE_*` env vars — try different descriptions |
| `pydub` errors on MP3 export | Install ffmpeg: `winget install ffmpeg` (Windows) or `sudo apt install ffmpeg` (Linux) |
| Slow TTS on CPU (>2s) | Install CUDA-enabled PyTorch: `pip install torch --index-url https://download.pytorch.org/whl/cu121` |

---

## Summary of New Files Created

| File | Type |
|---|---|
| `backend/modules/voice/llm_response.py` | New — LLM decision + templates |
| `backend/modules/voice/tts_normalizer.py` | New — text normalization |
| `backend/modules/voice/tts_engine_indic.py` | New — TTS engine singleton |
| `backend/modules/voice/tts.py` | New — orchestrator |

## Summary of Modified Files

| File | Changes |
|---|---|
| `backend/modules/voice/voice_config.py` | Added TTS + LLM config keys |
| `backend/api/routes_voice.py` | TTS integration in `/process-audio`, `/process`; new `/speak` endpoint |
| `backend/main.py` | TTS warmup + Ollama check at startup; updated `/api/health` |
| `backend/requirements.txt` | Added TTS dependencies |
| `frontend/src/api/client.js` | Added `speakText()` API call |
| `frontend/src/pages/VoiceOrder.jsx` | Audio playback, speaking indicator, interrupt |
| `frontend/src/components/VoiceRecorder.jsx` | Added `onStartRecording` prop |
