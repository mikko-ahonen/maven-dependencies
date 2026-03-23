from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

from .cache import FileCache

@dataclass
class RepoInfo:
    provider: str
    owner: str
    repo: str
    host: str

def parse_repo_url(repo_url: str) -> RepoInfo:
    parsed = urllib.parse.urlparse(repo_url)
    host = parsed.netloc.lower()
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"Unsupported repository URL: {repo_url}")
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if "github.com" in host:
        return RepoInfo(provider="github", owner=owner, repo=repo, host=host)
    if "gitlab.com" in host:
        return RepoInfo(provider="gitlab", owner=owner, repo=repo, host=host)
    raise ValueError(f"Unsupported git host: {host}")

def _http_get(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read().decode("utf-8")

def fetch_repo_tree(repo_url: str, ref: str, cache: FileCache) -> list[str]:
    cache_key = f"{repo_url}@{ref}"
    cached = cache.get_text("git_tree", cache_key)
    if cached:
        return json.loads(cached)
    info = parse_repo_url(repo_url)
    if info.provider == "github":
        api = f"https://api.github.com/repos/{info.owner}/{info.repo}/git/trees/{urllib.parse.quote(ref, safe='')}?recursive=1"
        data = json.loads(_http_get(api))
        paths = [item["path"] for item in data.get("tree", []) if item.get("type") == "blob"]
    elif info.provider == "gitlab":
        project = urllib.parse.quote(f"{info.owner}/{info.repo}", safe="")
        api = f"https://gitlab.com/api/v4/projects/{project}/repository/tree?recursive=true&ref={urllib.parse.quote(ref, safe='')}&per_page=1000"
        data = json.loads(_http_get(api))
        paths = [item["path"] for item in data if item.get("type") == "blob"]
    else:
        raise ValueError(info.provider)
    cache.set_text("git_tree", cache_key, json.dumps(paths))
    return paths

def fetch_repo_file(repo_url: str, ref: str, path: str, cache: FileCache) -> str:
    cache_key = f"{repo_url}@{ref}:{path}"
    cached = cache.get_text("git_file", cache_key)
    if cached is not None:
        return cached
    info = parse_repo_url(repo_url)
    if info.provider == "github":
        raw = f"https://raw.githubusercontent.com/{info.owner}/{info.repo}/{urllib.parse.quote(ref, safe='')}/{path}"
        text = _http_get(raw)
    elif info.provider == "gitlab":
        project = urllib.parse.quote(f"{info.owner}/{info.repo}", safe="")
        encoded_path = urllib.parse.quote(path, safe="")
        api = f"https://gitlab.com/api/v4/projects/{project}/repository/files/{encoded_path}/raw?ref={urllib.parse.quote(ref, safe='')}"
        text = _http_get(api)
    else:
        raise ValueError(info.provider)
    cache.set_text("git_file", cache_key, text)
    return text

def find_pom_files(repo_url: str, ref: str, cache: FileCache) -> list[str]:
    return [p for p in fetch_repo_tree(repo_url, ref, cache) if p.endswith("pom.xml")]
