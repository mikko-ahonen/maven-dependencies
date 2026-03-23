from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request

from .cache import FileCache
from .models import Coordinate

def pom_url(repo: str, coordinate: Coordinate) -> str:
    group_path = coordinate.group_id.replace(".", "/")
    return f"{repo.rstrip('/')}/{group_path}/{coordinate.artifact_id}/{coordinate.version}/{coordinate.artifact_id}-{coordinate.version}.pom"

def fetch_artifact_pom(coordinate: Coordinate, repositories: list[str], cache: FileCache) -> str | None:
    key = coordinate.gav + "|" + "|".join(repositories)
    cached = cache.get_text("artifact_pom", key)
    if cached is not None:
        return cached
    for repo in repositories:
        url = pom_url(repo, coordinate)
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                text = resp.read().decode("utf-8")
                cache.set_text("artifact_pom", key, text)
                return text
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
        except Exception:
            continue
    return None
