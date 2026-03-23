from __future__ import annotations

import re
from collections import OrderedDict

from .models import Coordinate, DeclaredDependency, EffectivePom, RawPom, RawProfile

_PROP = re.compile(r"\$\{([^}]+)\}")

def _dep_key(dep: DeclaredDependency) -> tuple[str, str]:
    return dep.group_id, dep.artifact_id

def merge_deps(base: list[DeclaredDependency], extra: list[DeclaredDependency]) -> list[DeclaredDependency]:
    merged: OrderedDict[tuple[str, str], DeclaredDependency] = OrderedDict()
    for dep in base + extra:
        merged[_dep_key(dep)] = dep
    return list(merged.values())

def interpolate(value: str | None, props: dict[str, str], max_rounds: int = 10) -> str | None:
    if value is None:
        return None
    out = value
    for _ in range(max_rounds):
        new = _PROP.sub(lambda m: props.get(m.group(1), m.group(0)), out)
        if new == out:
            break
        out = new
    return out

def apply_profiles(pom: RawPom, profile_mode: str, active_profiles: list[str] | None) -> RawPom:
    selected: list[RawProfile] = []
    active_profiles = active_profiles or []
    for prof in pom.profiles:
        if profile_mode == "all":
            selected.append(prof)
        elif profile_mode == "explicit" and prof.profile_id in active_profiles:
            selected.append(prof)
    out = RawPom(**{**pom.__dict__})
    out.properties = dict(pom.properties)
    out.dependencies = list(pom.dependencies)
    out.dependency_management = list(pom.dependency_management)
    out.plugins = list(pom.plugins)
    out.plugin_management = list(pom.plugin_management)
    out.extensions = list(pom.extensions)
    for prof in selected:
        out.properties.update(prof.properties)
        out.dependencies = merge_deps(out.dependencies, prof.dependencies)
        out.dependency_management = merge_deps(out.dependency_management, prof.dependency_management)
        out.plugins = merge_deps(out.plugins, prof.plugins)
        out.plugin_management = merge_deps(out.plugin_management, prof.plugin_management)
        out.extensions = merge_deps(out.extensions, prof.extensions)
    return out

def build_properties(pom: RawPom, parent: EffectivePom | None) -> dict[str, str]:
    props = {}
    if parent:
        props.update(parent.properties)
        props["parent.groupId"] = parent.coordinate.group_id
        props["parent.artifactId"] = parent.coordinate.artifact_id
        props["parent.version"] = parent.coordinate.version

    gid = pom.group_id or (parent.coordinate.group_id if parent else None)
    ver = pom.version or (parent.coordinate.version if parent else None)
    aid = pom.artifact_id

    props.update({
        "project.groupId": gid or "",
        "project.artifactId": aid or "",
        "project.version": ver or "",
        "pom.groupId": gid or "",
        "pom.artifactId": aid or "",
        "pom.version": ver or "",
    })
    props.update(pom.properties)
    # second pass interpolates property values against the full map
    for _ in range(5):
        changed = False
        for k, v in list(props.items()):
            iv = interpolate(v, props)
            if iv != v:
                props[k] = iv or ""
                changed = True
        if not changed:
            break
    return props

def materialize_dep(dep: DeclaredDependency, props: dict[str, str], managed: dict[tuple[str,str], DeclaredDependency] | None = None) -> DeclaredDependency:
    m = managed.get((dep.group_id, dep.artifact_id)) if managed else None
    version = interpolate(dep.version, props) or (interpolate(m.version, props) if m else None)
    scope = interpolate(dep.scope, props) or (interpolate(m.scope, props) if m and m.scope else None) or "compile"
    dtype = interpolate(dep.type, props) or (interpolate(m.type, props) if m and m.type else None) or "jar"
    classifier = interpolate(dep.classifier, props) or (interpolate(m.classifier, props) if m and m.classifier else None)
    return DeclaredDependency(
        group_id=interpolate(dep.group_id, props) or dep.group_id,
        artifact_id=interpolate(dep.artifact_id, props) or dep.artifact_id,
        version=version,
        scope=scope,
        optional=dep.optional,
        type=dtype,
        classifier=classifier,
        exclusions=dep.exclusions,
        origin=dep.origin,
    )

def make_effective_pom(pom: RawPom, parent: EffectivePom | None, profile_mode: str, active_profiles: list[str] | None) -> EffectivePom:
    pom = apply_profiles(pom, profile_mode, active_profiles)
    props = build_properties(pom, parent)
    gid = interpolate(pom.group_id, props) or (parent.coordinate.group_id if parent else None)
    ver = interpolate(pom.version, props) or (parent.coordinate.version if parent else None)
    aid = interpolate(pom.artifact_id, props)
    if not gid or not aid or not ver:
        raise ValueError(f"Incomplete coordinates in {pom.source}: {gid=} {aid=} {ver=}")
    parent_chain = list(parent.parent_chain) if parent else []
    if parent:
        parent_chain = [parent.coordinate] + parent_chain

    dm = list(parent.dependency_management) if parent else []
    dm = merge_deps(dm, pom.dependency_management)
    pm = list(parent.plugin_management) if parent else []
    pm = merge_deps(pm, pom.plugin_management)
    dep_mgmt_map = {(_dep.group_id, _dep.artifact_id): materialize_dep(_dep, props) for _dep in dm}
    plugin_mgmt_map = {(_dep.group_id, _dep.artifact_id): materialize_dep(_dep, props) for _dep in pm}

    deps = [materialize_dep(d, props, dep_mgmt_map) for d in pom.dependencies]
    plugins = [materialize_dep(d, props, plugin_mgmt_map) for d in pom.plugins]
    exts = [materialize_dep(d, props, dep_mgmt_map) for d in pom.extensions]

    return EffectivePom(
        source=pom.source,
        coordinate=Coordinate(gid, aid, ver),
        packaging=interpolate(pom.packaging, props) or pom.packaging,
        parent_chain=parent_chain,
        properties=props,
        dependencies=deps,
        dependency_management=[materialize_dep(d, props) for d in dm],
        plugins=plugins,
        plugin_management=[materialize_dep(d, props) for d in pm],
        extensions=exts,
    )
