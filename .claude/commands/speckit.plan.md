---
description: Execute the implementation planning workflow using the plan template to generate design artifacts.
handoffs: 
  - label: Create Tasks
    agent: speckit.tasks
    prompt: Break the plan into tasks
    send: true
  - label: Create Checklist
    agent: speckit.checklist
    prompt: Create a checklist for the following domain...
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

0. **Load Memory Context** (Continuous Learning check):

   - **Check napkin for planning/architecture lessons**:
     - Read `.specify/memory/napkin.md` (skip if doesn't exist)
     - Filter for entries with categories: `PLAN`, `ARCHITECTURE`, `IMPLEMENTATION`
     - Extract lessons about tech stack choices, architecture patterns, integration pitfalls, design mistakes
     - If relevant lessons found (2+), note them and apply proactively during planning
   - **Cross-reference with current feature's technology**:
     - If napkin contains lessons about libraries/frameworks mentioned in spec, highlight them

1. **Setup**: Run `.specify/scripts/bash/setup-plan.sh --json` from repo root and parse JSON for FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Load context**: Read FEATURE_SPEC and `.specify/memory/constitution.md`. Load IMPL_PLAN template (already copied).

3. **Execute plan workflow**: Follow the structure in IMPL_PLAN template to:
   - Fill Technical Context (mark unknowns as "NEEDS CLARIFICATION")
   - Fill Constitution Check section from constitution
   - Evaluate gates (ERROR if violations unjustified)
   - Phase 0: Generate research.md (resolve all NEEDS CLARIFICATION)
   - Phase 1: Generate data-model.md, contracts/, quickstart.md
   - Phase 1: Update agent context by running the agent script
   - Re-evaluate Constitution Check post-design

4. **Stop and report**: Command ends after Phase 2 planning. Report branch, IMPL_PLAN path, and generated artifacts.

## Phases

### Phase 0: Outline & Research

1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:

   ```text
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

### Phase 1: Design & Contracts

**Prerequisites:** `research.md` complete

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Agent context update**:
   - Run `.specify/scripts/bash/update-agent-context.sh claude`
   - These scripts detect which AI agent is in use
   - Update the appropriate agent-specific context file
   - Add only new technology from current plan
   - Preserve manual additions between markers

**Output**: data-model.md, /contracts/*, quickstart.md, agent-specific file

### Phase 1.5: Seed Dependency Graph

**Prerequisites:** Phase 1 design artifacts complete

If `.specify/graphs/` directory exists (depgraph extension installed):

1. **Extract entity nodes** from `data-model.md`:
   - Each entity → node with `type: "entity"`, ID format `ENT-{EntityName}`
   - Entity relationships → `depends-on` edges between entity nodes

2. **Extract requirement nodes** from `spec.md`:
   - Each FR-xxx → node with `type: "requirement"`, ID format matching spec ID
   - Map requirements to entities they reference → `depends-on` edges

3. **Extract endpoint nodes** from `contracts/` (if exists):
   - Each API endpoint → node with `type: "endpoint"`, ID format `EP-{METHOD}-{path}`
   - Map endpoints to entities they consume/produce → `reads` / `creates` edges
   - Map endpoints to requirements they fulfill → `implemented-by` edges

4. **Extract file nodes** from project structure in `plan.md`:
   - Each planned source file → node with `type: "file"`, ID format `FILE-{path}`

5. **Create initial dependency-graph.json**:
   - Assemble all nodes and edges into the graph schema format
   - Set `feature` to current feature branch name
   - Set `generated_at` to current timestamp
   - Write to `FEATURE_DIR/dependency-graph.json`

6. **Merge into global index**:
   - If `.specify/graphs/index.json` exists, merge the new feature graph into it
   - Preserve existing nodes from other features

**Output**: FEATURE_DIR/dependency-graph.json

## Key rules

- Use absolute paths
- ERROR on gate failures or unresolved clarifications
