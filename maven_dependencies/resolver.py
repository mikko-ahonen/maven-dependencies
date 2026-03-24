from __future__ import annotations

from pathlib import PurePosixPath

from .cache import FileCache
from .effective import make_effective_pom, materialize_dep
from .git_fetch import fetch_repo_file, find_pom_files
from .maven_fetch import fetch_artifact_pom
from .models import Coordinate, DeclaredDependency, EffectivePom, GraphEdge, GraphNode, GraphResult
from .pom_parser import parse_pom

DEFAULT_REPOSITORIES = ["https://repo1.maven.org/maven2"]

def _module_node_id(path: str) -> str:
    return f"module:{path}"

def _artifact_node_id(coord: Coordinate, kind: str = "artifact") -> str:
    return f"{kind}:{coord.gav}"

def _find_parent_in_repo(current_path: str, relative_parent_path: str | None, poms: dict[str, str]) -> str | None:
    if not relative_parent_path:
        relative_parent_path = "../pom.xml"
    parent_path = str((PurePosixPath(current_path).parent / relative_parent_path).as_posix())
    parent_path = str(PurePosixPath(parent_path))
    return parent_path if parent_path in poms else None

def _resolve_boms(effective: EffectivePom, repositories: list[str], cache: FileCache, result: GraphResult) -> EffectivePom:
    # merge imported BOM dependencyManagement into effective pom dependency_management
    merged = list(effective.dependency_management)
    seen = {(d.group_id, d.artifact_id, d.version, d.scope, d.type) for d in merged}
    for dep in list(effective.dependency_management):
        if dep.scope == "import" and (dep.type or "jar") == "pom" and dep.version:
            coord = Coordinate(dep.group_id, dep.artifact_id, dep.version)
            xml = fetch_artifact_pom(coord, repositories, cache)
            if not xml:
                result.add_issue("warning", "BOM_FETCH_FAILED", f"Could not fetch BOM {coord.gav}")
                continue
            bom_raw = parse_pom(xml, f"maven:{coord.gav}")
            bom_eff = make_effective_pom(bom_raw, None, profile_mode="none", active_profiles=None)
            for m in bom_eff.dependency_management:
                key = (m.group_id, m.artifact_id, m.version, m.scope, m.type)
                if key not in seen:
                    merged.append(m)
                    seen.add(key)
            result.add_node(GraphNode(id=_artifact_node_id(coord, "bom"), node_type="bom", display=coord.gav))
            result.add_edge(GraphEdge(from_node=_artifact_node_id(effective.coordinate, "project"), to_node=_artifact_node_id(coord, "bom"), kind="imports_bom"))
    effective.dependency_management = merged
    return effective

def resolve_repository_graph(
    repo_url: str,
    *,
    ref: str = "HEAD",
    root_module_path: str = "pom.xml",
    cache_dir: str | None = None,
    repositories: list[str] | None = None,
    provider: str | None = None,
    profile_mode: str = "all",
    active_profiles: list[str] | None = None,
    include_plugins: bool = True,
    include_extensions: bool = True,
    include_plugin_transitive: bool = True,
    include_optional: bool = True,
    include_test_scope: bool = True,
) -> GraphResult:
    repositories = repositories or list(DEFAULT_REPOSITORIES)
    cache = FileCache(cache_dir)
    result = GraphResult()

    pom_paths = find_pom_files(repo_url, ref, cache, provider)
    poms = {path: fetch_repo_file(repo_url, ref, path, cache, provider) for path in pom_paths}
    parsed = {path: parse_pom(xml, f"git:{repo_url}@{ref}:{path}") for path, xml in poms.items()}
    effective_cache: dict[str, EffectivePom] = {}

    def resolve_module(path: str) -> EffectivePom:
        if path in effective_cache:
            return effective_cache[path]
        raw = parsed[path]
        parent_eff = None
        if raw.parent:
            parent_path = _find_parent_in_repo(path, raw.relative_parent_path, poms)
            if parent_path and parent_path in parsed:
                parent_eff = resolve_module(parent_path)
            elif raw.parent.version:
                coord = Coordinate(raw.parent.group_id, raw.parent.artifact_id, raw.parent.version)
                xml = fetch_artifact_pom(coord, repositories, cache)
                if xml:
                    parent_eff = make_effective_pom(parse_pom(xml, f"maven:{coord.gav}"), None, "none", None)
                else:
                    result.add_issue("warning", "PARENT_FETCH_FAILED", f"Could not fetch parent {coord.gav}", module=path)
        eff = make_effective_pom(raw, parent_eff, profile_mode, active_profiles)
        eff = _resolve_boms(eff, repositories, cache, result)
        effective_cache[path] = eff
        return eff

    # create module/project nodes
    for path in pom_paths:
        eff = resolve_module(path)
        result.add_node(GraphNode(
            id=_module_node_id(path),
            node_type="module",
            display=eff.coordinate.gav,
            metadata={"path": path},
        ))
        result.add_node(GraphNode(
            id=_artifact_node_id(eff.coordinate, "project"),
            node_type="project",
            display=eff.coordinate.gav,
            metadata={"path": path},
        ))
        result.add_edge(GraphEdge(from_node=_module_node_id(path), to_node=_artifact_node_id(eff.coordinate, "project"), kind="declares_project"))
        if eff.parent_chain:
            parent = eff.parent_chain[0]
            result.add_node(GraphNode(id=_artifact_node_id(parent, "parent"), node_type="parent", display=parent.gav))
            result.add_edge(GraphEdge(from_node=_artifact_node_id(eff.coordinate, "project"), to_node=_artifact_node_id(parent, "parent"), kind="has_parent"))

    visited: set[tuple[str, str]] = set()

    def should_include(dep: DeclaredDependency) -> bool:
        if dep.optional and not include_optional:
            return False
        if dep.scope == "test" and not include_test_scope:
            return False
        return bool(dep.version)

    def traverse_artifact(dep: DeclaredDependency, from_node: str, edge_kind: str, *, transitive_kind: str, node_kind: str = "artifact"):
        if not should_include(dep):
            return
        coord = Coordinate(dep.group_id, dep.artifact_id, dep.version or "")
        node_id = _artifact_node_id(coord, node_kind)
        result.add_node(GraphNode(id=node_id, node_type=node_kind, display=coord.gav))
        result.add_edge(GraphEdge(
            from_node=from_node,
            to_node=node_id,
            kind=edge_kind,
            scope=dep.scope,
            optional=dep.optional,
            metadata={"origin": dep.origin},
        ))
        key = (node_kind, coord.gav)
        if key in visited:
            return
        visited.add(key)
        xml = fetch_artifact_pom(coord, repositories, cache)
        if not xml:
            result.add_issue("warning", "ARTIFACT_POM_NOT_FOUND", f"Could not fetch artifact POM {coord.gav}")
            return
        raw = parse_pom(xml, f"maven:{coord.gav}")
        eff = make_effective_pom(raw, None, "none", None)
        eff = _resolve_boms(eff, repositories, cache, result)
        dep_mgmt = {(d.group_id, d.artifact_id): d for d in eff.dependency_management}
        for child in eff.dependencies:
            child = materialize_dep(child, eff.properties, dep_mgmt)
            if any(ex.ga == f"{child.group_id}:{child.artifact_id}" for ex in dep.exclusions):
                continue
            traverse_artifact(child, node_id, transitive_kind, transitive_kind=transitive_kind, node_kind="artifact")

    for path in pom_paths:
        eff = resolve_module(path)
        project_id = _artifact_node_id(eff.coordinate, "project")
        dep_mgmt = {(d.group_id, d.artifact_id): d for d in eff.dependency_management}
        plugin_mgmt = {(d.group_id, d.artifact_id): d for d in eff.plugin_management}

        for dep in eff.dependencies:
            dep = materialize_dep(dep, eff.properties, dep_mgmt)
            traverse_artifact(dep, project_id, "declares_dependency", transitive_kind="transitive_dependency", node_kind="artifact")

        if include_plugins:
            for plugin in eff.plugins:
                plugin = materialize_dep(plugin, eff.properties, plugin_mgmt)
                traverse_artifact(plugin, project_id, "declares_plugin", transitive_kind="plugin_transitive_dependency", node_kind="plugin")

        if include_extensions:
            for ext in eff.extensions:
                ext = materialize_dep(ext, eff.properties, dep_mgmt)
                traverse_artifact(ext, project_id, "declares_extension", transitive_kind="extension_transitive_dependency", node_kind="extension")

    return result
