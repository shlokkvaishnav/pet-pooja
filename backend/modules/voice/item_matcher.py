"""
item_matcher.py — Hybrid Fuzzy + Semantic Menu Item Matching
=============================================================
Builds search corpus FROM THE DATABASE — nothing hardcoded.

Matching strategy:
  1. RapidFuzz token_sort_ratio  — fast, handles word-order variations
  2. Sentence-Transformer + FAISS — semantic meaning vectors that rescue
     phonetic mishearings ("chikken" → "chicken", "murgh" → "chicken")

  final_score = 0.4 × fuzzy + 0.6 × semantic

Model: paraphrase-multilingual-MiniLM-L12-v2 (~420MB)
  - Multilingual: handles English, Hindi, Hinglish, Devanagari natively
  - Fully offline after first download

FAISS: vector similarity search, CPU-only, no server needed
"""

import re
import logging
import numpy as np
from rapidfuzz import process, fuzz
from typing import Optional

logger = logging.getLogger("petpooja.voice.item_matcher")

# Digits-only token pattern — used to strip leading/trailing numbers from phrases
_NUM_RE = re.compile(r"^\d+(\.\d+)?$")

# Common words that shouldn't match on their own
SKIP_WORDS = {"aur", "and", "or", "ya", "bhi", "with", "dena", "lao",
              "chahiye", "please", "extra", "no", "one", "two", "the",
              "ka", "ki", "ke", "se", "me", "hai", "ho", "karo",
              "bhaiya", "bhaiyya", "bhaia", "bhai", "de", "do",
              "yaar", "boss", "ji", "haan", "ok", "okay",
              # Common English filler/sentence words that confuse semantic matching
              "sir", "actually", "wanted", "order", "something", "add",
              "deliver", "place", "my", "in", "can", "you", "to", "i",
              "it", "is", "a", "an", "for", "get", "give", "want", "need",
              "bring", "make", "put", "take", "also", "just", "some",
              "more", "less", "big", "small", "large", "plate", "glass",
              # Hinglish fillers
              "miya", "mia", "bhai", "milay", "kiya", "uske", "saath", "bhi",
              "chahiye", "mat", "maat", "nahi", "ek", "do", "teen",
              "chaar", "paanch", "kuch", "sab", "wala", "wali", "wale",
              "e", "hi", "yeh", "woh", "kya",
              "jara", "zara", "deena", "na", "toh", "bas",
              # Devanagari equivalents (fallback if transliteration missed)
              "और", "या", "भी", "देना", "दे", "लाओ", "चाहिए",
              "भैया", "भइया", "भाई", "जी", "हाँ", "हां"}

# Blend weights — must sum to 1.0
_FUZZY_WEIGHT = 0.4
_SEMANTIC_WEIGHT = 0.6

# Model name — small, multilingual, ~420MB, fully offline
_SEMANTIC_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


# ---------------------------------------------------------------------------
# Semantic Index
# ---------------------------------------------------------------------------

class _SemanticIndex:
    """
    Lazy-loading FAISS index of corpus embeddings.
    Built once per VoicePipeline startup, queried per match.
    """

    def __init__(self):
        self._model = None
        self._index = None          # faiss.IndexFlatIP (inner-product on L2-normed = cosine)
        self._keys: list = []       # corpus alias strings, parallel to FAISS vectors
        self._ids: list = []        # item_ids, parallel to _keys
        self._ready = False

    def _load_model(self):
        """Lazy-load the sentence-transformer model on first use."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading semantic model '%s'...", _SEMANTIC_MODEL_NAME)
                self._model = SentenceTransformer(_SEMANTIC_MODEL_NAME)
                logger.info("Semantic model loaded — fully offline from now on")
            except Exception as e:
                logger.warning("Could not load semantic model: %s — falling back to fuzzy-only", e)
                self._model = None

    def build(self, corpus: dict):
        """
        Encode all corpus keys and build a FAISS inner-product index.
        corpus: { alias_string: item_id }
        """
        self._load_model()
        if self._model is None:
            return

        try:
            import faiss
            self._keys = list(corpus.keys())
            self._ids = [corpus[k] for k in self._keys]

            logger.info("Building semantic index for %d corpus entries...", len(self._keys))
            embeddings = self._model.encode(
                self._keys,
                batch_size=64,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,   # L2-normalise → inner product = cosine sim
            )
            embeddings = embeddings.astype(np.float32)

            dim = embeddings.shape[1]
            self._index = faiss.IndexFlatIP(dim)
            self._index.add(embeddings)
            self._ready = True
            logger.info("Semantic index ready (%d vectors, dim=%d)", len(self._keys), dim)

        except Exception as e:
            logger.warning("Could not build semantic index: %s — falling back to fuzzy-only", e)
            self._ready = False

    def score(self, query: str, item_id: int) -> float:
        """
        Return the best cosine similarity (0–1) among all corpus aliases
        that belong to `item_id`.
        Returns 0.0 if index is not ready.
        """
        if not self._ready or self._model is None:
            return 0.0
        try:
            vec = self._model.encode(
                [query],
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).astype(np.float32)

            # Search top-20 to find the best match that belongs to our item_id
            k = min(20, len(self._keys))
            scores, indices = self._index.search(vec, k)

            best = 0.0
            for idx, raw_score in zip(indices[0], scores[0]):
                if idx < 0:
                    continue
                if self._ids[idx] == item_id:
                    best = max(best, float(raw_score))
            return best

        except Exception as e:
            logger.debug("Semantic score error: %s", e)
            return 0.0

    def top_k(self, query: str, k: int = 5) -> list:
        """
        Return list of (item_id, semantic_score) for top-k nearest neighbors.
        Used to generate disambiguation alternatives semantically.
        """
        if not self._ready or self._model is None:
            return []
        try:
            vec = self._model.encode(
                [query],
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).astype(np.float32)

            k_search = min(k * 4, len(self._keys))  # oversample to deduplicate
            scores, indices = self._index.search(vec, k_search)

            seen_ids: set = set()
            results = []
            for idx, raw_score in zip(indices[0], scores[0]):
                if idx < 0:
                    continue
                iid = self._ids[idx]
                if iid not in seen_ids:
                    seen_ids.add(iid)
                    results.append((iid, float(raw_score)))
                if len(results) >= k:
                    break
            return results

        except Exception as e:
            logger.debug("Semantic top_k error: %s", e)
            return []


# Module-level singleton — shared across all calls
_semantic_index = _SemanticIndex()


# ---------------------------------------------------------------------------
# Corpus builder
# ---------------------------------------------------------------------------

def build_search_corpus(menu_items: list) -> dict:
    """
    DYNAMICALLY builds search corpus from DB menu items.
    Returns: { "alias string" -> item_id }
    Also rebuilds the semantic FAISS index in one go.
    """
    corpus = {}
    for item in menu_items:
        entries = []
        if item.name:
            entries.append(item.name.lower().strip())
        if item.name_hi:
            entries.append(item.name_hi.strip())
        if hasattr(item, "aliases") and item.aliases:
            for alias in item.aliases.split("|"):
                alias = alias.strip().lower()
                if alias:
                    entries.append(alias)
        for entry in entries:
            if entry:
                corpus[entry] = item.id

    # Build semantic index from the full corpus
    _semantic_index.build(corpus)
    return corpus


# ---------------------------------------------------------------------------
# Core matching
# ---------------------------------------------------------------------------

# Confidence threshold below which we flag for disambiguation
DISAMBIGUATION_THRESHOLD = 0.85


def match_item(text: str, corpus: dict, threshold: int = 70) -> Optional[dict]:
    """
    Hybrid match: RapidFuzz (fuzzy) + Sentence-Transformer (semantic).

    Architecture:
      - Fuzzy must pass 'threshold' (default 70) to enter hybrid scoring.
      - Semantic boosts confident fuzzy matches: final = 0.4×fuzzy + 0.6×semantic
      - Phonetic mishearings (chikan→chicken) are corrected in normalizer.py
        BEFORE reaching this function.
      - Multi-word phrases with any SKIP_WORD token are rejected upfront.

    Falls back to fuzzy-only score if semantic index is not ready.
    """
    if not text or not corpus:
        return None

    text_clean = text.strip().lower()
    if text_clean in SKIP_WORDS or len(text_clean) < 2:
        return None

    # Strip leading/trailing digit tokens (quantities added by normalizer)
    # e.g. "1 mutton" → "mutton", "2 roti" → "roti"
    parts = text_clean.split()
    while parts and _NUM_RE.match(parts[0]):
        parts = parts[1:]
    while parts and _NUM_RE.match(parts[-1]):
        parts = parts[:-1]
    if not parts:
        return None
    text_clean = " ".join(parts)

    if text_clean in SKIP_WORDS or len(text_clean) < 2:
        return None

    # Reject multi-word phrases that contain a filler/skip word.
    # Example: "biryani aur" → reject because "aur" is a filler.
    # "cold drink" → pass (no skip words).
    tokens = text_clean.split()
    if len(tokens) > 1 and any(t in SKIP_WORDS for t in tokens):
        return None

    # --- Step 1: RapidFuzz MUST pass first ---
    # token_sort_ratio requires ALL words to be present (any order).
    # Prevents "paneer tikka" matching "paneer butter masala" at 85%.
    # Semantic is only applied when fuzzy already passes the threshold.
    fuzzy_result = process.extractOne(
        text_clean,
        corpus.keys(),
        scorer=fuzz.token_sort_ratio,
        score_cutoff=threshold,
    )

    if fuzzy_result is None:
        # Fuzzy rejected — try word-in-corpus fallback for single words.
        # E.g. "chicken" doesn't fuzzy-match "chicken tikka" well with
        # token_sort_ratio, but if "chicken" appears as a whole word in
        # a corpus key, that's a strong signal.
        if len(tokens) == 1 and tokens[0] not in SKIP_WORDS and len(tokens[0]) >= 4:
            word = tokens[0]
            # Find all corpus entries containing our word
            candidates = [
                (key, item_id)
                for key, item_id in corpus.items()
                if word in key.split()
            ]
            if candidates:
                # Pick best by semantic score if available, else first match
                if _semantic_index._ready and len(candidates) > 1:
                    best_key, best_id, best_sem = None, None, -1
                    for key, item_id in candidates:
                        sem = _semantic_index.score(word, item_id)
                        if sem > best_sem:
                            best_key, best_id, best_sem = key, item_id, sem
                    # Flag for disambiguation — multiple items contain this word
                    return _build_result(
                        best_id, best_key, 0.75, corpus, text_clean
                    )
                else:
                    key, item_id = candidates[0]
                    conf = 0.80 if len(candidates) == 1 else 0.70
                    return _build_result(item_id, key, conf, corpus, text_clean)
        return None

    matched_fuzzy_key, fuzzy_raw, _ = fuzzy_result
    fuzzy_norm = fuzzy_raw / 100.0
    item_id = corpus[matched_fuzzy_key]

    # --- Step 2: Semantic score for the SAME item fuzzy matched ---
    if _semantic_index._ready:
        sem_score = _semantic_index.score(text_clean, item_id)
        final_score = _FUZZY_WEIGHT * fuzzy_norm + _SEMANTIC_WEIGHT * sem_score
    else:
        # Semantic not available — use fuzzy only
        final_score = fuzzy_norm

    return _build_result(item_id, matched_fuzzy_key, final_score, corpus, text_clean)


def _build_result(
    item_id: int,
    matched_key: str,
    final_score: float,
    corpus: dict,
    original_query: str,
) -> dict:
    """Build the standard result dict, adding disambiguation info if needed."""
    match_result = {
        "item_id": item_id,
        "matched_as": matched_key,
        "confidence": round(final_score, 3),
    }

    if final_score < DISAMBIGUATION_THRESHOLD:
        match_result["needs_disambiguation"] = True
        match_result["alternatives"] = get_alternatives(original_query, corpus, top_n=3)
    else:
        match_result["needs_disambiguation"] = False
        match_result["alternatives"] = []

    return match_result


def get_alternatives(text: str, corpus: dict, top_n: int = 3) -> list:
    """Return top-N hybrid-scored candidates for disambiguation."""
    text_clean = text.strip().lower()

    # Fuzzy candidates
    fuzzy_results = process.extract(
        text_clean,
        corpus.keys(),
        scorer=fuzz.token_sort_ratio,
        limit=top_n * 3,   # oversample, will hybrid-score and re-rank
        score_cutoff=50,
    )

    # Semantic top-k
    sem_top = _semantic_index.top_k(text_clean, k=top_n * 3)
    sem_lookup: dict = {iid: s for iid, s in sem_top}

    # Build unique-by-item_id result set
    seen_ids: set = set()
    scored = []

    for fuzzy_key, fuzzy_raw, _ in fuzzy_results:
        iid = corpus[fuzzy_key]
        if iid in seen_ids:
            continue
        seen_ids.add(iid)
        fuzzy_norm = fuzzy_raw / 100.0
        sem = sem_lookup.get(iid, 0.0)
        if _semantic_index._ready:
            final = _FUZZY_WEIGHT * fuzzy_norm + _SEMANTIC_WEIGHT * sem
        else:
            final = fuzzy_norm
        scored.append((final, iid, fuzzy_key))

    # Also include pure-semantic candidates not in fuzzy results
    for iid, sem in sem_top:
        if iid in seen_ids:
            continue
        seen_ids.add(iid)
        alias = next((k for k, v in corpus.items() if v == iid), "")
        final = _SEMANTIC_WEIGHT * sem
        scored.append((final, iid, alias))

    scored.sort(reverse=True)
    return [
        {"item_id": iid, "matched_as": key, "confidence": round(s, 3)}
        for s, iid, key in scored[:top_n]
    ]


# ---------------------------------------------------------------------------
# Sliding-window multi-item extraction
# ---------------------------------------------------------------------------

def extract_all_items(text: str, corpus: dict) -> list:
    """
    Sliding window over transcript tokens.
    Tries 3-word, 2-word, then 1-word phrases.
    Uses overlap prevention + minimum confidence per window size.
    Hybrid scoring automatically handles accented/misspelled words.

    Returns: list of matched items.
    Also sets __last_fuzzy_suggestions on the function for pipeline
    access when zero items matched (provides recovery suggestions).
    """
    extract_all_items._last_fuzzy_suggestions = []

    if not text or not corpus:
        return []

    tokens = text.split()
    found = {}           # item_id -> best match dict
    used_positions = set()

    # Minimum confidence per window size
    # Larger windows = more intentional, lower threshold OK
    # Single words = high false positive risk, need high threshold
    # With hybrid scoring 2/3-word windows can use 0.75+; 1-word needs 0.75+
    # (safely lowered from 0.90 because word-in-corpus fallback is precise)
    MIN_CONF = {3: 0.85, 2: 0.78, 1: 0.75}

    for window_size in [3, 2, 1]:
        min_confidence = MIN_CONF[window_size]

        for i in range(len(tokens) - window_size + 1):
            window_positions = set(range(i, i + window_size))
            if window_positions & used_positions:
                continue

            phrase = " ".join(tokens[i:i + window_size])
            if phrase.strip().isdigit():
                continue

            match = match_item(phrase, corpus)
            if match and match["confidence"] >= min_confidence:
                item_id = match["item_id"]
                if item_id not in found or match["confidence"] > found[item_id]["confidence"]:
                    found[item_id] = {**match, "position": i}
                    used_positions.update(window_positions)

    result = sorted(found.values(), key=lambda x: x["position"])

    # When nothing matched, compute fuzzy suggestions for recovery
    if not result and tokens:
        # Try the longest non-skip phrase as the suggestion query
        meaningful = [t for t in tokens if t.lower() not in SKIP_WORDS and len(t) >= 2]
        query = " ".join(meaningful) if meaningful else text
        extract_all_items._last_fuzzy_suggestions = get_alternatives(query, corpus, top_n=3)

    return result
