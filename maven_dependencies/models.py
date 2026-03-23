from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class Coordinate:
    group_id: str
    artifact_id: str
    version: str

    @property
    def gav(self) -> str:
        return f"{self.group_id}:{self.artifact_id}:{self.version}"

    @property
    def ga(self) -> str:
        return f"{self.group_id}:{self.artifact_id}"

@dataclass(frozen=True)
class DependencyKey:
    group_id: str
    artifact_id: str

    @property
    def ga(self) -> str:
        return f"{self.group_id}:{self.artifact_id}"

@dataclass
class DeclaredDependency:
    group_id: str
    artifact_id: str
    version: str | None = None
    scope: str | None = None
    optional: bool = False
    type: str | None = None
    classifier: str | None = None
    exclusions: list[DependencyKey] = field(default_factory=list)
    origin: str = ""

@dataclass
class RawProfile:
    profile_id: str
    properties: dict[str, str] = field(default_factory=dict)
    dependencies: list[DeclaredDependency] = field(default_factory=list)
    dependency_management: list[DeclaredDependency] = field(default_factory=list)
    plugins: list[DeclaredDependency] = field(default_factory=list)
    plugin_management: list[DeclaredDependency] = field(default_factory=list)
    extensions: list[DeclaredDependency] = field(default_factory=list)

@dataclass
class RawPom:
    source: str
    group_id: str | None = None
    artifact_id: str | None = None
    version: str | None = None
    packaging: str | None = None
    parent: DeclaredDependency | None = None
    relative_parent_path: str | None = None
    properties: dict[str, str] = field(default_factory=dict)
    modules: list[str] = field(default_factory=list)
    dependencies: list[DeclaredDependency] = field(default_factory=list)
    dependency_management: list[DeclaredDependency] = field(default_factory=list)
    plugins: list[DeclaredDependency] = field(default_factory=list)
    plugin_management: list[DeclaredDependency] = field(default_factory=list)
    extensions: list[DeclaredDependency] = field(default_factory=list)
    profiles: list[RawProfile] = field(default_factory=list)
    repositories: list[str] = field(default_factory=list)

@dataclass
class EffectivePom:
    source: str
    coordinate: Coordinate
    packaging: str | None
    parent_chain: list[Coordinate]
    properties: dict[str, str]
    dependencies: list[DeclaredDependency]
    dependency_management: list[DeclaredDependency]
    plugins: list[DeclaredDependency]
    plugin_management: list[DeclaredDependency]
    extensions: list[DeclaredDependency]

@dataclass
class GraphNode:
    id: str
    node_type: str
    display: str
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class GraphEdge:
    from_node: str
    to_node: str
    kind: str
    scope: str | None = None
    optional: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ResolutionIssue:
    level: str
    code: str
    message: str
    context: dict[str, str] = field(default_factory=dict)

@dataclass
class GraphResult:
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)
    issues: list[ResolutionIssue] = field(default_factory=list)

    def add_node(self, node: GraphNode) -> None:
        self.nodes.setdefault(node.id, node)

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges.append(edge)

    def add_issue(self, level: str, code: str, message: str, **context: str) -> None:
        self.issues.append(ResolutionIssue(level=level, code=code, message=message, context=context))
