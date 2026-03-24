from __future__ import annotations

import argparse
import json

from .resolver import resolve_repository_graph

def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve a maximal static Maven dependency graph from a Git repo")
    parser.add_argument("repo_url")
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--root-module-path", default="pom.xml")
    parser.add_argument("--cache-dir", default=".mgi-cache")
    parser.add_argument("--profile-mode", choices=["all", "explicit", "none"], default="all")
    parser.add_argument("--profile", action="append", dest="profiles", default=[])
    parser.add_argument("--provider", choices=["github", "gitlab"], default=None,
                        help="Git provider (auto-detected from URL if not specified)")
    parser.add_argument("--no-plugins", action="store_true")
    parser.add_argument("--no-extensions", action="store_true")
    parser.add_argument("--no-plugin-transitive", action="store_true")
    parser.add_argument("--no-optional", action="store_true")
    parser.add_argument("--no-test-scope", action="store_true")
    args = parser.parse_args()

    result = resolve_repository_graph(
        repo_url=args.repo_url,
        ref=args.ref,
        root_module_path=args.root_module_path,
        cache_dir=args.cache_dir,
        provider=args.provider,
        profile_mode=args.profile_mode,
        active_profiles=args.profiles,
        include_plugins=not args.no_plugins,
        include_extensions=not args.no_extensions,
        include_plugin_transitive=not args.no_plugin_transitive,
        include_optional=not args.no_optional,
        include_test_scope=not args.no_test_scope,
    )
    payload = {
        "nodes": {k: {"type": v.node_type, "display": v.display, "metadata": v.metadata} for k, v in result.nodes.items()},
        "edges": [e.__dict__ for e in result.edges],
        "issues": [i.__dict__ for i in result.issues],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
