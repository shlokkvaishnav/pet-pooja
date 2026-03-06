"""
Patch parler-tts for transformers 5.x compatibility.

parler-tts v0.2.2 imports `SlidingWindowCache` from `transformers.cache_utils`,
which was removed in transformers 5.0. This script patches the import to use a
try/except fallback.

Run this after installing (or upgrading) parler-tts:
    python patch_parler_tts.py
"""

import pathlib
import sys


def patch():
    try:
        import parler_tts
    except Exception:
        print("ERROR: parler_tts is not installed. Install it first:")
        print("  pip install git+https://github.com/huggingface/parler-tts.git")
        sys.exit(1)

    pkg_dir = pathlib.Path(parler_tts.__file__).parent
    target = pkg_dir / "modeling_parler_tts.py"

    if not target.exists():
        print(f"ERROR: {target} not found")
        sys.exit(1)

    text = target.read_text(encoding="utf-8")

    OLD_IMPORT = (
        "from transformers.cache_utils import (\n"
        "    Cache,\n"
        "    DynamicCache,\n"
        "    EncoderDecoderCache,\n"
        "    SlidingWindowCache,\n"
        "    StaticCache,\n"
        ")"
    )

    NEW_IMPORT = (
        "from transformers.cache_utils import (\n"
        "    Cache,\n"
        "    DynamicCache,\n"
        "    EncoderDecoderCache,\n"
        "    StaticCache,\n"
        ")\n"
        "try:\n"
        "    from transformers.cache_utils import SlidingWindowCache\n"
        "except ImportError:\n"
        "    SlidingWindowCache = StaticCache  # compat shim for transformers>=5"
    )

    if OLD_IMPORT in text:
        text = text.replace(OLD_IMPORT, NEW_IMPORT)
        target.write_text(text, encoding="utf-8")
        print(f"PATCHED: {target}")
        print("  SlidingWindowCache import now uses try/except fallback.")
    elif "SlidingWindowCache = StaticCache" in text:
        print(f"ALREADY PATCHED: {target}")
    else:
        print(f"WARNING: Could not find expected import block in {target}")
        print("  The parler-tts code may have changed. Manual patching may be needed.")
        sys.exit(1)


if __name__ == "__main__":
    patch()
