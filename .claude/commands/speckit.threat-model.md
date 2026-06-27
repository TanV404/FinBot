---
description: "Generate a STRIDE-based threat model for the feature, mapping attack surface from spec, plan, and dependency graph"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Produce a structured threat model for the current feature using the STRIDE methodology. Identifies threats across all components (endpoints, entities, external integrations) and generates mitigation recommendations. If a dependency graph exists, uses it to auto-map the attack surface.

## Operating Constraints

- **Writes threat-model.md**: Creates `FEATURE_DIR/threat-model.md`.
- **May update graph**: If `dependency-graph.json` exists, adds threat nodes with `threatens` edges.
- **Security-focused**: Apply defense-in-depth thinking; assume external inputs are untrusted.

## Execution Steps

### 0. Load Memory Context

- Read `.specify/memory/napkin.md` (skip if doesn't exist)
- Filter for entries about security issues, vulnerabilities, or threat modeling
- Apply lessons to focus on historically problematic security areas

### 1. Initialize Context

Run `.specify/scripts/bash/check-prerequisites.sh --json` from repo root and parse JSON for FEATURE_DIR and AVAILABLE_DOCS.

Required: `spec.md`, `plan.md`
Optional: `data-model.md`, `contracts/`, `dependency-graph.json`, `research.md`

### 2. Map Attack Surface

**From spec.md**:
- User roles and authentication requirements
- Data inputs and validation scenarios
- External integrations mentioned
- Compliance or regulatory requirements

**From plan.md**:
- Tech stack (known vulnerability patterns per technology)
- Security Considerations section (if present)
- External dependencies and their trust boundaries

**From contracts/** (if exists):
- Every API endpoint → attack entry point
- Input parameters → injection targets
- Authentication requirements per endpoint

**From data-model.md** (if exists):
- Entities with sensitive fields (PII, credentials, financial data)
- Data relationships that could expose information
- State transitions that could be exploited

**From dependency-graph.json** (if exists):
- All endpoint nodes → comprehensive attack entry points
- External dependency edges → third-party trust boundaries
- Entity nodes with sensitive metadata → data protection targets
- Hub file nodes → high-value targets for attackers

### 3. Apply STRIDE Analysis

For each component in the attack surface, evaluate all six STRIDE categories:

| Category | Question | Examples |
|----------|----------|---------|
| **S**poofing | Can an attacker pretend to be someone else? | Authentication bypass, session hijacking, token theft |
| **T**ampering | Can an attacker modify data they shouldn't? | SQL injection, parameter manipulation, CSRF |
| **R**epudiation | Can an attacker deny performing an action? | Missing audit logs, unsigned transactions |
| **I**nformation Disclosure | Can an attacker access unauthorized data? | Data leaks, verbose errors, insecure storage |
| **D**enial of Service | Can an attacker disrupt availability? | Resource exhaustion, rate limit bypass, DDoS |
| **E**levation of Privilege | Can an attacker gain unauthorized access? | Broken access control, privilege escalation, IDOR |

### 4. Classify Threats

For each identified threat:

- **ID**: THR-NNN (sequential)
- **STRIDE Category**: S/T/R/I/D/E
- **Component**: Which endpoint, entity, or service
- **Severity**: CRITICAL / HIGH / MEDIUM / LOW
  - CRITICAL: Direct path to data breach or system compromise
  - HIGH: Exploitable with moderate effort; significant impact
  - MEDIUM: Requires specific conditions; limited impact
  - LOW: Theoretical risk; minimal real-world impact
- **Mitigation Status**: Mitigated / Partially Mitigated / Unmitigated
- **Mitigation**: Specific countermeasure

### 5. Generate Threat Model Report

Write to `FEATURE_DIR/threat-model.md`:

```markdown
# Threat Model: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`
**Created**: [DATE]
**STRIDE Analysis**: Complete
**Risk Level**: [Overall risk assessment]

## Attack Surface Summary

| Category | Count | Entry Points |
|----------|-------|-------------|
| API Endpoints | [N] | [list] |
| Data Entities (sensitive) | [N] | [list] |
| External Integrations | [N] | [list] |
| User Input Fields | [N] | [list] |

## Trust Boundaries

[Describe the trust boundaries — where does trusted code interact with untrusted input?]

## Threat Inventory

| ID | STRIDE | Component | Threat | Severity | Mitigation | Status |
|----|--------|-----------|--------|----------|------------|--------|
| THR-001 | S | POST /api/login | Credential stuffing | HIGH | Rate limiting + account lockout | Unmitigated |
| THR-002 | T | PUT /api/users/:id | IDOR — modify other users | CRITICAL | Authorization check on user_id | Unmitigated |
| THR-003 | I | GET /api/users | Data over-exposure | MEDIUM | Field-level filtering per role | Unmitigated |

## Attack Surface Diagram

[Mermaid diagram showing components, trust boundaries, and threat vectors]

## Mitigation Recommendations

### Critical (Must Address Before Implementation)

1. **THR-002**: Implement authorization middleware that validates resource ownership

### High (Should Address During Implementation)

1. **THR-001**: Add rate limiting to authentication endpoints

### Medium (Address in Polish Phase)

1. **THR-003**: Implement response field filtering based on user role

## Compliance Considerations

[Any regulatory requirements from spec — GDPR, HIPAA, PCI-DSS, etc.]

## Security Testing Recommendations

- [ ] Penetration testing for [specific areas]
- [ ] Input validation fuzzing for [endpoints]
- [ ] Access control matrix testing for [roles]
- [ ] Dependency vulnerability scanning
```

### 6. Update Dependency Graph (if exists)

If `FEATURE_DIR/dependency-graph.json` exists:

- Add threat nodes: `type: "threat"`, ID format `THR-NNN`
- Add `threatens` edges from threat nodes to affected component nodes
- Set severity in edge metadata
- Write updated graph back to `FEATURE_DIR/dependency-graph.json`

### 7. Report

Output:
- Path to generated threat-model.md
- Summary: [N] threats identified ([C] critical, [H] high, [M] medium, [L] low)
- Unmitigated critical threats that must be addressed before implementation
- Suggestion: "Review threat model with security team before `/speckit.implement`"

## Guidelines

- Assume all external inputs are hostile
- Focus on threats specific to this feature, not generic security best practices
- Reference specific endpoints, entities, and components — not abstract concepts
- If the feature handles no sensitive data and has no authentication, state this explicitly rather than generating artificial threats
- Cross-reference with constitution security principles if they exist
