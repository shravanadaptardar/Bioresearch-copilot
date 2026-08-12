"""
cache.py
A tiny disk-based cache so repeated identical queries don't burn
Groq API tokens during development/testing.

Cache files are stored as JSON in .cache/ next to this file.
Cache entries expire after CACHE_TTL_HOURS (default 24h).
"""
import json
import os
import hashlib
import time

CACHE_DIR       = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
CACHE_TTL_HOURS = 24

os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_key(query: str) -> str:
    """Normalize query (lowercase, strip whitespace) and hash it."""
    normalized = " ".join(query.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


def _cache_path(query: str) -> str:
    return os.path.join(CACHE_DIR, f"{_cache_key(query)}.json")


def get_cached(query: str) -> dict | None:
    """Return cached result dict if present and not expired, else None."""
    path = _cache_path(query)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            entry = json.load(f)
        age_hours = (time.time() - entry.get("_cached_at", 0)) / 3600
        if age_hours > CACHE_TTL_HOURS:
            os.remove(path)
            return None
        return entry.get("result")
    except Exception as e:
        print(f"[Cache] Read error: {e}")
        return None


def set_cached(query: str, result: dict) -> None:
    """Store result dict in cache with current timestamp."""
    path = _cache_path(query)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"_cached_at": time.time(), "result": result}, f)
    except Exception as e:
        print(f"[Cache] Write error: {e}")


def clear_cache() -> int:
    """Delete all cache files. Returns count deleted."""
    count = 0
    for fname in os.listdir(CACHE_DIR):
        if fname.endswith(".json"):
            os.remove(os.path.join(CACHE_DIR, fname))
            count += 1
    return count
