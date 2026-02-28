import logging
from pathlib import Path

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path("knowledge")

_cache: str | None = None
_cache_mtime: dict[str, float] = {}


def _needs_reload() -> bool:
    if _cache is None:
        return True
    if not KNOWLEDGE_DIR.exists():
        return _cache != ""
    for f in KNOWLEDGE_DIR.glob("*.md"):
        mtime = f.stat().st_mtime
        if _cache_mtime.get(str(f)) != mtime:
            return True
    return False


def load_knowledge_base() -> str:
    global _cache, _cache_mtime

    if not _needs_reload():
        return _cache

    if not KNOWLEDGE_DIR.exists():
        _cache = ""
        _cache_mtime = {}
        return _cache

    parts = []
    new_mtimes = {}
    for f in sorted(KNOWLEDGE_DIR.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        parts.append(f"## {f.stem}\n\n{content}")
        new_mtimes[str(f)] = f.stat().st_mtime

    _cache = "\n\n---\n\n".join(parts)
    _cache_mtime = new_mtimes
    return _cache
