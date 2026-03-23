from __future__ import annotations

import hashlib
from pathlib import Path

class FileCache:
    def __init__(self, cache_dir: str | None = None) -> None:
        self.cache_dir = Path(cache_dir or ".mgi-cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, namespace: str, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        d = self.cache_dir / namespace
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{digest}.xml"

    def get_text(self, namespace: str, key: str) -> str | None:
        p = self._path_for(namespace, key)
        return p.read_text(encoding="utf-8") if p.exists() else None

    def set_text(self, namespace: str, key: str, value: str) -> None:
        self._path_for(namespace, key).write_text(value, encoding="utf-8")
