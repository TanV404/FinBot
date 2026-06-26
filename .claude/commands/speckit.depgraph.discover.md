---
description: "Reverse-engineer a dependency graph from existing code for brownfield bootstrapping"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Analyze an existing codebase and produce an initial dependency graph at `.specify/graphs/index.json`. This is the primary entry point for **brownfield** projects where code exists without specs, plans, or tasks. The resulting graph enables impact analysis for all future features.

## Operating Constraints

- **Write-only to graph files**: Do not modify any source code. Only create/update graph JSON files.
- **Best-effort analysis**: The AI agent performs semantic code analysis — not traditional static analysis. Results are approximate but architecturally meaningful.
- **Legacy tagging**: All discovered nodes are tagged `legacy: true` since they have no backing spec artifacts.

## Execution Steps

### 0. Load Memory Context

- Read `.specify/memory/napkin.md` (skip if doesn't exist)
- Filter for entries about codebase structure, architecture, or discovery
- Apply any lessons learned from previous discovery runs

### 1. Determine Scan Scope

Parse `$ARGUMENTS` to determine what to scan:

- If a directory path is provided (e.g., `src/`), scan only that directory
- If `--full` or no path specified, scan the entire repository source tree
- If `--federated` is specified, also look for sibling repo graphs (see Cross-Repo Discovery below)
- Exclude common non-source directories: `node_modules/`, `.venv/`, `dist/`, `build/`, `__pycache__/`, `.git/`, `.specify/`, `_build/`, `deps/`, `.terraform/`, `target/`, `vendor/`, `zig-cache/`, `zig-out/`, `.dart_tool/`, `.pub-cache/`
- Respect `.gitignore` patterns if git is available

### 2. Detect Technology Stack

Before scanning code, identify the project's technology stack:

- Check for package manifest files: `package.json`, `requirements.txt`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `pom.xml`, `build.gradle`, `build.sbt`, `project.clj`, `*.csproj`, `Gemfile`, `composer.json`, `mix.exs`, `rebar.config`, `pubspec.yaml`, `Package.swift`, `build.zig`, `*.nimble`, `Makefile.PL`, `cpanfile`, `DESCRIPTION` (R), `Project.toml` (Julia)
- Check for IaC manifests: `*.tf`, `terraform.tfvars`, `main.bicep`, `serverless.yml`, `pulumi.*`
- Check for database schemas: `*.sql`, `migrations/`, `db/migrate/`, `alembic/`
- Check for framework indicators: `next.config.*`, `angular.json`, `vue.config.*`, `django`, `flask`, `fastapi`, `express`, `spring`, `phoenix`, `gin`, `echo`, `fiber`, `rails`, `laravel`, `flutter`
- Record the primary language and framework for context-aware parsing

### 3. Scan and Classify Source Files

For each source file in scope, extract structural elements and create graph nodes:

**Entity Nodes** (`type: "entity"`):
- Database models (ORM classes, schema definitions, migration files)
- Data classes, structs, or type definitions that represent domain objects
- ID format: `ENT-{EntityName}` (e.g., `ENT-User`, `ENT-Order`)

**File Nodes** (`type: "file"`):
- Every source file scanned becomes a file node
- ID format: `FILE-{relative-path}` (e.g., `FILE-src/models/user.py`)

**Endpoint Nodes** (`type: "endpoint"`):
- API route definitions (REST, GraphQL, gRPC)
- CLI command handlers
- Event handlers / message consumers
- ID format: `EP-{method}-{path}` (e.g., `EP-POST-/api/users`, `EP-GET-/api/orders/:id`)

**Requirement Nodes**: Not created during discovery (these come from specs)

### 4. Extract Relationships (Edges)

For each file, analyze imports and dependencies to create edges:

**`imports` edges**: File A imports/requires File B
- Parse import statements, require calls, use statements
- Create: `FILE-A --imports--> FILE-B`

**`depends-on` edges**: Higher-level component dependencies
- Service A calls Service B
- Controller depends on Service
- Create: `FILE-controller --depends-on--> FILE-service`

**`creates` / `modifies` edges**: Entity lifecycle
- Migration creates Entity
- Service modifies Entity
- Create: `FILE-migration --creates--> ENT-User`

**`reads` edges**: Data access patterns
- Service reads Entity
- Endpoint returns Entity data
- Create: `EP-GET-/api/users --reads--> ENT-User`

### 5. Compute Graph Metrics

After building the initial graph, compute and report:

**Hub Analysis** (high fan-in nodes):
- Files imported by 5+ other files → mark as hubs in metadata
- These are high-risk modification targets

**Orphan Detection**:
- Files with zero incoming or outgoing edges
- May indicate dead code or standalone utilities

**Circular Dependency Detection**:
- Identify cycles in the import graph
- Report each cycle with the involved files

**Coupling Clusters**:
- Groups of files with dense interconnections
- Potential module/service boundaries

### 6. Build Graph JSON

Assemble all nodes and edges into the graph schema format:

```json
{
  "version": "1.0",
  "generated_at": "ISO-8601-timestamp",
  "nodes": [...],
  "edges": [...],
  "external_dependencies": [...]
}
```

- Set `legacy: true` on all nodes
- Set `feature: "discovery"` on all nodes
- Write to `.specify/graphs/index.json`

### 7. Create Discovery Snapshot

Save a timestamped copy to `.specify/graphs/snapshots/YYYY-MM-DD_discovery.json`

### 8. Produce Discovery Report

Output a structured report (do not write to file — display to user):

```markdown
## Dependency Graph Discovery Report

**Scanned**: [N] files across [M] directories
**Technology**: [detected stack]
**Generated**: [timestamp]

### Graph Summary

| Metric | Count |
|--------|-------|
| Total Nodes | [N] |
| - Entity Nodes | [N] |
| - File Nodes | [N] |
| - Endpoint Nodes | [N] |
| Total Edges | [N] |
| Hub Modules (fan-in >= 5) | [N] |
| Orphan Modules | [N] |
| Circular Dependencies | [N] |

### Hub Modules (High-Risk Modification Targets)

| File | Fan-In | Dependents |
|------|--------|------------|
| src/models/user.py | 14 | [list of dependent files] |

### Circular Dependencies

1. A -> B -> C -> A
2. ...

### Coupling Clusters

1. **Cluster: Auth** — [file list]
2. **Cluster: Orders** — [file list]

### Recommendations

- [Actionable recommendations based on findings]
- "Run `/speckit.specify` to create specs for hub modules first"
- "Consider breaking circular dependency between X and Y"
```

### Cross-Repo Discovery (Optional)

If `$ARGUMENTS` contains `--federated`:

1. Scan for `.specify/graphs/index.json` in sibling directories (monorepo) or declared dependencies
2. For each external graph found:
   - Extract endpoint nodes as potential import targets
   - Extract entity nodes as shared data models
3. Build federated edge list: local imports → external endpoints
4. Write export manifest to `.specify/graphs/exports.json`:

```json
{
  "repo": "current-repo-name",
  "exports": [
    { "id": "EP-POST-/api/users", "type": "endpoint", "contract": "specs/001-auth/contracts/users.yaml" }
  ],
  "imports": [
    { "id": "external-service/EP-GET-/api/tokens", "type": "endpoint", "required": true }
  ]
}
```

## Guidelines

- Focus on **architectural** dependencies, not every function call
- When in doubt about a relationship, include it with lower confidence metadata
- Large codebases (1000+ files): summarize by directory/module rather than individual files
- Report zero findings gracefully if the codebase is empty or trivial
- This command can be re-run to refresh the graph as code evolves
