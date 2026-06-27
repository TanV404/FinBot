# [PROJECT_NAME] Constitution
<!-- Example: Spec Constitution, TaskFlow Constitution, etc. -->

## Core Principles

### [PRINCIPLE_1_NAME]
<!-- Example: I. Library-First -->
[PRINCIPLE_1_DESCRIPTION]
<!-- Example: Every feature starts as a standalone library; Libraries must be self-contained, independently testable, documented; Clear purpose required - no organizational-only libraries -->

### [PRINCIPLE_2_NAME]
<!-- Example: II. CLI Interface -->
[PRINCIPLE_2_DESCRIPTION]
<!-- Example: Every library exposes functionality via CLI; Text in/out protocol: stdin/args → stdout, errors → stderr; Support JSON + human-readable formats -->

### Test-Driven Development (NON-NEGOTIABLE)

TDD is mandatory for all feature implementation:

1. **Write unit tests first** -- before any implementation code exists
2. **Verify tests fail (Red)** -- confirm tests correctly detect the missing functionality
3. **Implement code (Green)** -- write the minimum code to make tests pass
4. **Refactor** -- improve code quality while keeping all tests green
5. **No feature code is merged without passing tests** -- the test suite must be green before completion
6. **Coverage thresholds** -- define minimum coverage per project; aim for meaningful coverage, not vanity metrics

Integration tests are required for:
- New library/service contract tests
- Contract changes between components
- Inter-service communication
- Shared schemas and data models

<!-- This principle is pre-filled as a non-negotiable default. Projects may adjust coverage thresholds but must not disable TDD. -->

### [PRINCIPLE_3_NAME]
<!-- Example: III. Observability -->
[PRINCIPLE_3_DESCRIPTION]
<!-- Example: Text I/O ensures debuggability; Structured logging required -->

### [PRINCIPLE_4_NAME]
<!-- Example: IV. Versioning & Breaking Changes -->
[PRINCIPLE_4_DESCRIPTION]
<!-- Example: MAJOR.MINOR.BUILD format; Breaking changes require migration plan -->

### [PRINCIPLE_5_NAME]
<!-- Example: V. Simplicity -->
[PRINCIPLE_5_DESCRIPTION]
<!-- Example: Start simple, YAGNI principles; Complexity must be justified -->

## [SECTION_2_NAME]
<!-- Example: Additional Constraints, Security Requirements, Performance Standards, etc. -->

[SECTION_2_CONTENT]
<!-- Example: Technology stack requirements, compliance standards, deployment policies, etc. -->

## [SECTION_3_NAME]
<!-- Example: Development Workflow, Review Process, Quality Gates, etc. -->

[SECTION_3_CONTENT]
<!-- Example: Code review requirements, testing gates, deployment approval process, etc. -->

## Governance
<!-- Example: Constitution supersedes all other practices; Amendments require documentation, approval, migration plan -->

[GOVERNANCE_RULES]
<!-- Example: All PRs/reviews must verify compliance; Complexity must be justified; Use [GUIDANCE_FILE] for runtime development guidance -->

**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATION_DATE] | **Last Amended**: [LAST_AMENDED_DATE]
<!-- Example: Version: 2.1.1 | Ratified: 2025-06-13 | Last Amended: 2025-07-16 -->
