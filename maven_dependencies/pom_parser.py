from __future__ import annotations

import xml.etree.ElementTree as ET

from .models import DeclaredDependency, DependencyKey, RawPom, RawProfile

MAVEN_NS = {"m": "http://maven.apache.org/POM/4.0.0"}

def _strip(text: str | None) -> str | None:
    return text.strip() if text and text.strip() else None

def _child_text(node: ET.Element | None, path: str) -> str | None:
    if node is None:
        return None
    el = node.find(path, MAVEN_NS)
    return _strip(el.text if el is not None else None)

def _parse_exclusions(dep_el: ET.Element) -> list[DependencyKey]:
    out = []
    for ex in dep_el.findall("m:exclusions/m:exclusion", MAVEN_NS):
        gid = _child_text(ex, "m:groupId")
        aid = _child_text(ex, "m:artifactId")
        if gid and aid:
            out.append(DependencyKey(gid, aid))
    return out

def _parse_dep(dep_el: ET.Element, origin: str) -> DeclaredDependency | None:
    gid = _child_text(dep_el, "m:groupId")
    aid = _child_text(dep_el, "m:artifactId")
    if not gid or not aid:
        return None
    return DeclaredDependency(
        group_id=gid,
        artifact_id=aid,
        version=_child_text(dep_el, "m:version"),
        scope=_child_text(dep_el, "m:scope"),
        optional=(_child_text(dep_el, "m:optional") or "").lower() == "true",
        type=_child_text(dep_el, "m:type"),
        classifier=_child_text(dep_el, "m:classifier"),
        exclusions=_parse_exclusions(dep_el),
        origin=origin,
    )

def _parse_deps(parent: ET.Element | None, path: str, origin: str) -> list[DeclaredDependency]:
    out = []
    if parent is None:
        return out
    for dep_el in parent.findall(path, MAVEN_NS):
        dep = _parse_dep(dep_el, origin)
        if dep:
            out.append(dep)
    return out

def parse_pom(xml_text: str, source: str) -> RawPom:
    root = ET.fromstring(xml_text)
    pom = RawPom(
        source=source,
        group_id=_child_text(root, "m:groupId"),
        artifact_id=_child_text(root, "m:artifactId"),
        version=_child_text(root, "m:version"),
        packaging=_child_text(root, "m:packaging"),
    )

    parent_el = root.find("m:parent", MAVEN_NS)
    if parent_el is not None:
        pom.parent = _parse_dep(parent_el, source + "#parent")
        pom.relative_parent_path = _child_text(parent_el, "m:relativePath")

    props_el = root.find("m:properties", MAVEN_NS)
    if props_el is not None:
        for child in list(props_el):
            tag = child.tag.split("}", 1)[-1]
            pom.properties[tag] = (child.text or "").strip()

    pom.modules = [_strip(el.text) for el in root.findall("m:modules/m:module", MAVEN_NS) if _strip(el.text)]
    pom.dependencies = _parse_deps(root, "m:dependencies/m:dependency", source)
    pom.dependency_management = _parse_deps(root, "m:dependencyManagement/m:dependencies/m:dependency", source)
    pom.plugins = _parse_deps(root, "m:build/m:plugins/m:plugin", source)
    pom.plugin_management = _parse_deps(root, "m:build/m:pluginManagement/m:plugins/m:plugin", source)
    pom.extensions = _parse_deps(root, "m:build/m:extensions/m:extension", source)

    for repo_el in root.findall("m:repositories/m:repository", MAVEN_NS):
        url = _child_text(repo_el, "m:url")
        if url:
            pom.repositories.append(url)

    for profile_el in root.findall("m:profiles/m:profile", MAVEN_NS):
        pid = _child_text(profile_el, "m:id")
        if not pid:
            continue
        prof = RawProfile(profile_id=pid)
        props_el = profile_el.find("m:properties", MAVEN_NS)
        if props_el is not None:
            for child in list(props_el):
                tag = child.tag.split("}", 1)[-1]
                prof.properties[tag] = (child.text or "").strip()
        prof.dependencies = _parse_deps(profile_el, "m:dependencies/m:dependency", f"{source}#profile:{pid}")
        prof.dependency_management = _parse_deps(profile_el, "m:dependencyManagement/m:dependencies/m:dependency", f"{source}#profile:{pid}")
        prof.plugins = _parse_deps(profile_el, "m:build/m:plugins/m:plugin", f"{source}#profile:{pid}")
        prof.plugin_management = _parse_deps(profile_el, "m:build/m:pluginManagement/m:plugins/m:plugin", f"{source}#profile:{pid}")
        prof.extensions = _parse_deps(profile_el, "m:build/m:extensions/m:extension", f"{source}#profile:{pid}")
        pom.profiles.append(prof)

    return pom
