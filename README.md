# Maven Dependencies

`maven-dependencies` builds a **maximal static Maven dependency graph** from a Git-hosted repository without running Maven.

It fetches `pom.xml` files from a Git repository, caches them locally, resolves parent POMs, properties, imported BOMs, explicit/all profiles, dependencies, plugins, build extensions, and transitive dependencies by fetching artifact POMs from Maven repositories.

## Scope

This library aims at the broadest useful **POM-only** dependency universe:

- repository modules
- parent POM chains
- imported BOMs
- dependencyManagement and pluginManagement
- dependencies
- plugins and plugin dependencies
- build extensions
- transitive closure of the above
- union of all profiles or explicitly selected profiles

It does **not** execute Maven, lifecycle phases, or plugin code.

## Install

```bash
pip install .
```

## Test

```bash
pip install pytest
pytest
```

## Example

```python
from maven_dependencies import resolve_repository_graph

result = resolve_repository_graph(
    repo_url="https://github.com/example/project",
    ref="main",
    root_module_path="pom.xml",
    cache_dir=".mgi-cache",
    profile_mode="all",
    include_plugins=True,
    include_extensions=True,
    include_plugin_transitive=True,
)

for edge in result.edges[:10]:
    print(edge.from_node, edge.to_node, edge.kind, edge.scope)
```

## CLI

```bash
maven-dependencies https://github.com/example/project --ref main --profile-mode all --cache-dir .mgi-cache
```
