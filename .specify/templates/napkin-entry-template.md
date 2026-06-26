# Napkin Entry Template

Use this template when recording a mistake/lesson with `/speckit.napkin-record`

---

## [YYYY-MM-DD HH:MM] | [CATEGORY] | [Short Title]

**Category**: One of: SPEC | PLAN | IMPLEMENTATION | TEST | CONSTITUTION | ARCHITECTURE | PERFORMANCE

**Context**: 
- Feature: [Feature name and branch]
- File(s): [Affected files]
- Component: [Affected component/module]

**What Went Wrong**:
[Detailed description of the problem, error, or mistake. Be specific about symptoms and when it was discovered.]

**What Fixed It**:
[The solution, workaround, or correction that resolved the issue. Include code snippets if relevant.]

**Lesson Learned**:
[Generalized principle that can be applied to future work. This should be actionable and clear. Examples:
- "Always validate localStorage schema before reading data"
- "Check napkin.md for API patterns before designing new endpoints"
- "Include edge cases in specification, not just happy path"]

**Impact**:
- Time Lost: [Estimate: minutes/hours/days]
- Severity: [LOW | MEDIUM | HIGH | CRITICAL]
- Likelihood of Recurrence: [LOW | MEDIUM | HIGH]

**Prevention**:
[How can we prevent this in the future? Should this become a workflow step? A constitution principle? A checklist item?]

**References**:
- Commit: [git commit hash if applicable]
- Handover: [Link to session handover if applicable]
- Related Napkin Entries: [Links to similar past issues]
- External Docs: [Links to relevant documentation]

**Tags**: #[tag1] #[tag2] #[tag3]
[Use tags for searchability: #typescript #react #zustand #testing #localStorage #api #ux #performance, etc.]

---

**Distillation Status**: [ ] Not reviewed | [ ] Reviewed | [ ] Constitutionalized

---

## Examples

### Good Entry Example

```markdown
## 2026-02-14 15:30 | IMPLEMENTATION | Zustand Middleware Order Breaks Undo

**Category**: IMPLEMENTATION

**Context**: 
- Feature: 001-hiring-workflow-viz
- File(s): src/store/workflowStore.ts
- Component: Store initialization

**What Went Wrong**:
Applied persist middleware before temporal (undo) middleware in Zustand store. This caused undo/redo to restore from localStorage instead of the undo stack, making undo operations persistent instead of transient.

**What Fixed It**:
Reordered middleware: `temporal(persist(storeCreator))` to `persist(temporal(storeCreator))`
This ensures undo stack operates on in-memory state, then persistence saves the result.

**Lesson Learned**:
Zustand middleware order matters: inner middleware wraps closer to state, outer middleware wraps the result. For undo + persistence: persist should wrap temporal, not vice versa.

**Impact**:
- Time Lost: 2 hours debugging
- Severity: HIGH
- Likelihood of Recurrence: MEDIUM

**Prevention**:
Add to plan template: "When using multiple Zustand middleware, document the order and rationale in plan.md Technical Context."

**References**:
- Commit: a3f2e8b
- Zustand Docs: https://docs.pmnd.rs/zustand/guides/typescript#middleware-that-changes-the-store-type

**Tags**: #zustand #middleware #undo #persistence #state-management

**Distillation Status**: [x] Reviewed | [ ] Constitutionalized
```

### What NOT to Do

**Too vague**:
```markdown
## 2026-02-14 | IMPLEMENTATION | Bug in store

Store didn't work. Fixed it.
```

**No lesson extracted**:
```markdown
## 2026-02-14 | IMPLEMENTATION | Import error

Got "Cannot find module" error. Added import statement.
```
(This doesn't teach us anything generalizable)

**Too implementation-specific**:
```markdown
## 2026-02-14 | IMPLEMENTATION | Line 47 had wrong variable

Changed `data` to `userData` on line 47.
```
(Extract the pattern: "Use descriptive variable names that indicate data type/purpose")
