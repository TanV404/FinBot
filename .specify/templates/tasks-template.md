---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests follow TDD by default -- unit tests are written before implementation code. Pass `skip-tests` in arguments to omit test tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] [Est:N?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- **[Est:N]**: Estimated effort in story points (1/2/3/5/8/13) — Fibonacci scale
  - 1-2: Simple file creation, config change, boilerplate
  - 3: Standard implementation (model, service, single endpoint)
  - 5: Complex implementation (multi-file, integration logic)
  - 8: High-complexity (cross-cutting, multiple integrations)
  - 13: Very high complexity (architectural changes, migration)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

<!-- 
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.
  
  The /speckit.tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/
  
  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment
  
  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize [language] project with [framework] dependencies
- [ ] T003 [P] Configure linting and formatting tools
- [ ] T004 [P] Configure test framework and test runner (e.g., pytest, jest, vitest)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T005 Setup database schema and migrations framework
- [ ] T006 [P] Implement authentication/authorization framework
- [ ] T007 [P] Setup API routing and middleware structure
- [ ] T008 Create base models/entities that all stories depend on
- [ ] T009 Configure error handling and logging infrastructure
- [ ] T010 Setup environment configuration management

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Unit Tests for User Story 1 (TDD -- write before implementation)

> **RED phase: Write these tests FIRST. They MUST FAIL before implementation begins.**

- [ ] T011 [P] [US1] Unit test for [Entity1] model in tests/unit/test_[entity1].py
- [ ] T012 [P] [US1] Unit test for [Entity2] model in tests/unit/test_[entity2].py
- [ ] T013 [P] [US1] Unit test for [Service] in tests/unit/test_[service].py
- [ ] T014 [P] [US1] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T015 [P] [US1] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 1

> **GREEN phase: Implement code to make the tests above pass.**

- [ ] T016 [P] [US1] Create [Entity1] model in src/models/[entity1].py
- [ ] T017 [P] [US1] Create [Entity2] model in src/models/[entity2].py
- [ ] T018 [US1] Implement [Service] in src/services/[service].py (depends on T016, T017)
- [ ] T019 [US1] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T020 [US1] Add validation and error handling
- [ ] T021 [US1] Add logging for user story 1 operations

### Verify User Story 1

- [ ] T022 [US1] Run unit tests for User Story 1 and report pass/fail results
- [ ] T023 [US1] Fix any failing tests for User Story 1 (iterate until green)

**Checkpoint**: At this point, User Story 1 should be fully functional with all tests passing

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Unit Tests for User Story 2 (TDD -- write before implementation)

> **RED phase: Write these tests FIRST. They MUST FAIL before implementation begins.**

- [ ] T024 [P] [US2] Unit test for [Entity] model in tests/unit/test_[entity].py
- [ ] T025 [P] [US2] Unit test for [Service] in tests/unit/test_[service].py
- [ ] T026 [P] [US2] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T027 [P] [US2] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 2

> **GREEN phase: Implement code to make the tests above pass.**

- [ ] T028 [P] [US2] Create [Entity] model in src/models/[entity].py
- [ ] T029 [US2] Implement [Service] in src/services/[service].py
- [ ] T030 [US2] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T031 [US2] Integrate with User Story 1 components (if needed)

### Verify User Story 2

- [ ] T032 [US2] Run unit tests for User Story 2 and report pass/fail results
- [ ] T033 [US2] Fix any failing tests for User Story 2 (iterate until green)
- [ ] T034 [US2] Run regression tests for User Story 1 to confirm no breakage

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently with all tests passing

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Unit Tests for User Story 3 (TDD -- write before implementation)

> **RED phase: Write these tests FIRST. They MUST FAIL before implementation begins.**

- [ ] T035 [P] [US3] Unit test for [Entity] model in tests/unit/test_[entity].py
- [ ] T036 [P] [US3] Unit test for [Service] in tests/unit/test_[service].py
- [ ] T037 [P] [US3] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T038 [P] [US3] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 3

> **GREEN phase: Implement code to make the tests above pass.**

- [ ] T039 [P] [US3] Create [Entity] model in src/models/[entity].py
- [ ] T040 [US3] Implement [Service] in src/services/[service].py
- [ ] T041 [US3] Implement [endpoint/feature] in src/[location]/[file].py

### Verify User Story 3

- [ ] T042 [US3] Run unit tests for User Story 3 and report pass/fail results
- [ ] T043 [US3] Fix any failing tests for User Story 3 (iterate until green)
- [ ] T044 [US3] Run regression tests for User Stories 1 and 2 to confirm no breakage

**Checkpoint**: All user stories should now be independently functional with all tests passing

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX Run full test suite across all user stories and report coverage
- [ ] TXXX Fix any test regressions or coverage gaps
- [ ] TXXX [P] Documentation updates in docs/
- [ ] TXXX Code cleanup and refactoring (keep tests green)
- [ ] TXXX Performance optimization across all stories
- [ ] TXXX Security hardening
- [ ] TXXX Run quickstart.md validation
- [ ] TXXX Final test suite run -- confirm all tests pass, report summary

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story (TDD Cycle)

- Unit tests MUST be written and FAIL before implementation (Red phase)
- Implement code to make tests pass (Green phase)
- Models before services
- Services before endpoints
- Core implementation before integration
- Run tests and report pass/fail after implementation
- Fix any failures before moving on
- Story complete (all tests green) before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# TDD Red phase -- launch all unit tests for User Story 1 together:
Task: "Unit test for [Entity1] model in tests/unit/test_[entity1].py"
Task: "Unit test for [Entity2] model in tests/unit/test_[entity2].py"
Task: "Unit test for [Service] in tests/unit/test_[service].py"

# TDD Green phase -- launch all models for User Story 1 together:
Task: "Create [Entity1] model in src/models/[entity1].py"
Task: "Create [Entity2] model in src/models/[entity2].py"

# Verify -- run tests and fix failures:
Task: "Run unit tests for User Story 1 and report pass/fail results"
Task: "Fix any failing tests for User Story 1"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- TDD is the default: write tests first (Red), implement (Green), refactor
- Pass `skip-tests` in arguments to generate tasks without test tasks
- Verify tests fail before implementing (Red phase is critical)
- Run tests after implementation and fix failures before proceeding
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
