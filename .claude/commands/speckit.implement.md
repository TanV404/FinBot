---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

0. **Load Memory Context** (Continuous Learning check):

   - **Check napkin for implementation lessons**:
     - Read `.specify/memory/napkin.md` (skip if doesn't exist)
     - Filter for categories: `IMPLEMENTATION`, `TEST`, `PERFORMANCE`
     - Extract lessons about common bugs, integration errors, testing pitfalls, performance issues
     - Note lessons specific to the tech stack in this feature's plan.md

1. Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Check checklists status** (if FEATURE_DIR/checklists/ exists):
   - Scan all checklist files in the checklists/ directory
   - For each checklist, count:
     - Total items: All lines matching `- [ ]` or `- [X]` or `- [x]`
     - Completed items: Lines matching `- [X]` or `- [x]`
     - Incomplete items: Lines matching `- [ ]`
   - Create a status table:

     ```text
     | Checklist | Total | Completed | Incomplete | Status |
     |-----------|-------|-----------|------------|--------|
     | ux.md     | 12    | 12        | 0          | ✓ PASS |
     | test.md   | 8     | 5         | 3          | ✗ FAIL |
     | security.md | 6   | 6         | 0          | ✓ PASS |
     ```

   - Calculate overall status:
     - **PASS**: All checklists have 0 incomplete items
     - **FAIL**: One or more checklists have incomplete items

   - **If any checklist is incomplete**:
     - Display the table with incomplete item counts
     - **STOP** and ask: "Some checklists are incomplete. Do you want to proceed with implementation anyway? (yes/no)"
     - Wait for user response before continuing
     - If user says "no" or "wait" or "stop", halt execution
     - If user says "yes" or "proceed" or "continue", proceed to step 3

   - **If all checklists are complete**:
     - Display the table showing all checklists passed
     - Automatically proceed to step 3

3. **Impact Analysis Gate** (if `.specify/graphs/index.json` exists):
   - Load the current feature's `dependency-graph.json` and the global graph index
   - Compare the current feature's file, entity, and endpoint nodes against all other features in the global graph
   - Classify overlaps by severity:
     - **CRITICAL**: Same file modified with incompatible changes across features; direct requirement contradiction
     - **HIGH**: Shared entity with schema changes; same API endpoint modified differently
     - **MEDIUM**: Read/write overlap on shared files; compatible endpoint changes
     - **LOW**: Transitive dependency (2+ hops); entity read-only overlap
   - **If CRITICAL conflicts found**: STOP and display conflict report with affected features. Ask: "Critical cross-feature conflicts detected. Resolve before proceeding? (yes to stop / no to proceed at your own risk)"
   - **If HIGH conflicts found**: Display warnings with affected features. Ask: "High-severity cross-feature overlaps detected. Proceed with implementation? (yes/no)"
   - **If only MEDIUM/LOW**: Display brief summary and proceed automatically
   - **If no conflicts or no graph**: Proceed to step 4
   - **Post-task enrichment**: After each task completion during step 7, if the task modifies a file not yet present as a node in the feature graph, add it as a `file` node with `legacy: true`

4. Load and analyze the implementation context:
   - **REQUIRED**: Read tasks.md for the complete task list and execution plan
   - **REQUIRED**: Read plan.md for tech stack, architecture, and file structure
   - **IF EXISTS**: Read data-model.md for entities and relationships
   - **IF EXISTS**: Read contracts/ for API specifications and test requirements
   - **IF EXISTS**: Read research.md for technical decisions and constraints
   - **IF EXISTS**: Read quickstart.md for integration scenarios

5. **Project Setup Verification**:
   - **REQUIRED**: Create/verify ignore files based on actual project setup:

   **Detection & Creation Logic**:
   - Check if the following command succeeds to determine if the repository is a git repo (create/verify .gitignore if so):

     ```sh
     git rev-parse --git-dir 2>/dev/null
     ```

   - Check if Dockerfile* exists or Docker in plan.md → create/verify .dockerignore
   - Check if .eslintrc* exists → create/verify .eslintignore
   - Check if eslint.config.* exists → ensure the config's `ignores` entries cover required patterns
   - Check if .prettierrc* exists → create/verify .prettierignore
   - Check if .npmrc or package.json exists → create/verify .npmignore (if publishing)
   - Check if terraform files (*.tf) exist → create/verify .terraformignore
   - Check if .helmignore needed (helm charts present) → create/verify .helmignore

   **If ignore file already exists**: Verify it contains essential patterns, append missing critical patterns only
   **If ignore file missing**: Create with full pattern set for detected technology

   **Common Patterns by Technology** (from plan.md tech stack):
   - **Node.js/JavaScript/TypeScript**: `node_modules/`, `dist/`, `build/`, `*.log`, `.env*`
   - **Python**: `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `dist/`, `*.egg-info/`
   - **Java**: `target/`, `*.class`, `*.jar`, `.gradle/`, `build/`
   - **C#/.NET**: `bin/`, `obj/`, `*.user`, `*.suo`, `packages/`
   - **Go**: `*.exe`, `*.test`, `vendor/`, `*.out`
   - **Ruby**: `.bundle/`, `log/`, `tmp/`, `*.gem`, `vendor/bundle/`
   - **PHP**: `vendor/`, `*.log`, `*.cache`, `*.env`
   - **Rust**: `target/`, `debug/`, `release/`, `*.rs.bk`, `*.rlib`, `*.prof*`, `.idea/`, `*.log`, `.env*`
   - **Kotlin**: `build/`, `out/`, `.gradle/`, `.idea/`, `*.class`, `*.jar`, `*.iml`, `*.log`, `.env*`
   - **C++**: `build/`, `bin/`, `obj/`, `out/`, `*.o`, `*.so`, `*.a`, `*.exe`, `*.dll`, `.idea/`, `*.log`, `.env*`
   - **C**: `build/`, `bin/`, `obj/`, `out/`, `*.o`, `*.a`, `*.so`, `*.exe`, `Makefile`, `config.log`, `.idea/`, `*.log`, `.env*`
   - **Swift**: `.build/`, `DerivedData/`, `*.swiftpm/`, `Packages/`
   - **R**: `.Rproj.user/`, `.Rhistory`, `.RData`, `.Ruserdata`, `*.Rproj`, `packrat/`, `renv/`
   - **Universal**: `.DS_Store`, `Thumbs.db`, `*.tmp`, `*.swp`, `.vscode/`, `.idea/`

   **Tool-Specific Patterns**:
   - **Docker**: `node_modules/`, `.git/`, `Dockerfile*`, `.dockerignore`, `*.log*`, `.env*`, `coverage/`
   - **ESLint**: `node_modules/`, `dist/`, `build/`, `coverage/`, `*.min.js`
   - **Prettier**: `node_modules/`, `dist/`, `build/`, `coverage/`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
   - **Terraform**: `.terraform/`, `*.tfstate*`, `*.tfvars`, `.terraform.lock.hcl`
   - **Kubernetes/k8s**: `*.secret.yaml`, `secrets/`, `.kube/`, `kubeconfig*`, `*.key`, `*.crt`

6. Parse tasks.md structure and extract:
   - **Task phases**: Setup, Tests, Core, Integration, Polish
   - **Task dependencies**: Sequential vs parallel execution rules
   - **Task details**: ID, description, file paths, parallel markers [P]
   - **Execution flow**: Order and dependency requirements

7. Execute implementation following the TDD task plan:
   - **Phase-by-phase execution**: Complete each phase before moving to the next
   - **Respect dependencies**: Run sequential tasks in order, parallel tasks [P] can run together
   - **TDD Red-Green-Refactor cycle** (mandatory for each user story):
     1. **Red**: Write unit tests first. Verify they FAIL (confirms tests detect missing functionality)
     2. **Green**: Implement the minimum code to make all tests pass
     3. **Refactor**: Improve code quality, remove duplication -- all tests must stay green
     4. **Report**: Run the story's test suite, display pass/fail summary with counts
     5. **Fix**: If any tests fail, iterate on the implementation until all pass
   - **File-based coordination**: Tasks affecting the same files must run sequentially
   - **Validation checkpoints**: Verify each phase completion before proceeding

8. Implementation execution rules:
   - **Setup first**: Initialize project structure, dependencies, configuration, test framework
   - **Tests before code (Red phase)**: Write unit tests for models, services, contracts, and integration scenarios
   - **Core development (Green phase)**: Implement models, services, CLI commands, endpoints to make tests pass
   - **Integration work**: Database connections, middleware, logging, external services
   - **Run tests after each story**: Execute the test suite, capture and display results
   - **Fix failures before proceeding**: If any tests fail, fix the implementation and re-run until green
   - **Polish and validation**: Run full test suite with coverage, performance optimization, documentation

9. Progress tracking and error handling:
   - Report progress after each completed task
   - Halt execution if any non-parallel task fails
   - For parallel tasks [P], continue with successful tasks, report failed ones
   - Provide clear error messages with context for debugging
   - Suggest next steps if implementation cannot proceed
   - **IMPORTANT** For completed tasks, make sure to mark the task off as [X] in the tasks file.

10. Completion validation:
   - Verify all required tasks are completed
   - Check that implemented features match the original specification
   - **Run the full test suite** and display a summary:
     ```text
     Test Results:
     | Story | Tests | Passed | Failed | Coverage |
     |-------|-------|--------|--------|----------|
     | US1   | 12    | 12     | 0      | 87%      |
     | US2   | 8     | 8      | 0      | 82%      |
     | Total | 20    | 20     | 0      | 85%      |
     ```
   - **All unit tests must pass** -- do not report completion with failing tests
   - **No regressions** -- earlier stories' tests must still pass after later story implementations
   - Confirm the implementation follows the technical plan
   - Report final status with summary of completed work and test results

Note: This command assumes a complete task breakdown exists in tasks.md. If tasks are incomplete or missing, suggest running `/speckit.tasks` first to regenerate the task list.
