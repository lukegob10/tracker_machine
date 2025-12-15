# Solution-Only Tracking Refactor Plan (Solution-Centric Mode)

## Why this exists
Today Jira-lite’s dashboards and planning views are **subcomponent-centric**:
- Master List, Kanban, Calendar, and most KPI math are computed from subcomponents.
- Solutions are more like containers/config (phases enabled, owner, status) and don’t carry enough tracking fields to stand alone.

If teams want to track **only Solutions** (no Subcomponents), the UI becomes sparse and metrics collapse to zeros. This plan refactors the app so a **Solution can be the primary trackable work item**, while optionally retaining subcomponents for teams that need task-level detail.

## Target outcome (acceptance criteria)
A user can create a Project + Solution (no subcomponents) and still:
- See meaningful items on Dashboard, Kanban, Calendar, and the primary “Master List” view.
- Track ownership, due dates, phase/progress, and blockers/risks at the Solution level.
- Export/import Solutions with the same governance fidelity currently expected for Subcomponents.
- Retain an optional “Subcomponents mode” for teams that want granular work items.

## Guiding principles
- **Solution-first**: a Solution must be sufficient for tracking delivery.
- **Minimal data duplication**: don’t store the same truth in two places long-term.
- **Backward compatible rollout**: ship in phases behind a feature flag until stable.
- **Predictable semantics**: “status”, “phase”, “owner”, “due date” should mean the same thing everywhere.
- **Single phase source of truth**: phase selection/progress is tracked at the Solution level only; Subcomponents are tasks and do not carry phases.

## Proposed approach (phased refactor)
### Phase 0 — Decide semantics (design lock)
Define the Solution-level equivalents of today’s subcomponent concepts.

**Required decisions (with suggested defaults):**
- **Solution due date**: add `solutions.due_date` as an optional deliverable target date (default: null).
- **Subcomponent due date**: keep `subcomponents.due_date` as an optional task-level target date (default: null). No enforcement relationship to solution due date (keep it simple).
- **Solution priority**: add `solutions.priority` 0–5 (default: 3).
- **Solution current phase**: add `solutions.current_phase` referencing `phases.phase_id` (default: null).
- **Solution progress**: derived from enabled phases + `current_phase` (same math as subcomponents).
- **Subcomponent phasing**: remove phasing from subcomponents entirely (no `subcomponents.sub_phase`, no per-subcomponent phase checklist). Phase enabling and “where we are” is represented at the Solution level only.
- **Subcomponent field scope**: subcomponents are optional tasks and only track: Project (inherited via Solution), Solution, Subcomponent (task), Priority, Due Date, Status, Assignee. Everything else is Solution-level and should be treated as inherited/read-only context on task views.
- **Solution execution roles**:
  - Keep `solutions.owner` as accountable owner.
  - Add `solutions.assignee` as executor (optional at first).
  - Keep `key_stakeholder` as consulted.
- **Blockers/risks**:
  - Add `solutions.blockers` (text) and `solutions.risks` (text) OR a single `solutions.blockers_risks` field initially.

Output: a short “field contract” that the backend + UI implement consistently.

### Phase 1 — Data model additions (non-destructive)
Add Solution-level tracking fields without removing Subcomponents yet.

**Schema updates (recommended set):**
- `solutions.due_date` (DATE)
- `solutions.priority` (INTEGER 0–5)
- `solutions.current_phase` (TEXT, FK-like to `phases.phase_id`)
- `solutions.assignee` (TEXT)
- `solutions.approver` (TEXT)
- `solutions.blockers` (TEXT)
- `solutions.risks` (TEXT)
- `solutions.completed_at` (DATETIME)

**Indexes (baseline):**
- `(status)`, `(due_date)`, `(priority)`, `(current_phase)`, `(owner)`, `(assignee)`

**Migration strategy**
The repo currently uses `create_all()` and has already hit “missing column” issues (e.g., `soeid`). For a refactor of this size, pick one:

1) **Adopt Alembic (recommended)**
   - Enables repeatable schema changes and backfills.
   - Best for corporate environments and avoids “delete DB” workflows.

2) **Ship an idempotent startup migration layer (minimal)**
   - On startup, run `PRAGMA table_info` checks + `ALTER TABLE ADD COLUMN ...` for missing fields.
   - Works for additive changes; limited for renames/drops.

Given the direction (solution-centric, future governance), Alembic is strongly preferred.

### Phase 2 — Backend API refactor (support solution-only)
Update the API so Solutions are first-class work items.

**Schema/payload updates**
- Extend `SolutionCreate`, `SolutionUpdate`, `SolutionRead` to include new tracking fields.
- Validate: priority bounds, date formats, `current_phase` must be enabled for the solution (if phases are enabled).
- If `status=complete`, set `completed_at` and set `current_phase` to last enabled phase (mirrors subcomponent rules).

**Subcomponents become non-phased tasks**
- Remove `sub_phase` from subcomponent create/update payloads and responses.
- Remove/retire the per-subcomponent checklist endpoints (currently phase-completion rows are subcomponent-scoped). If a “checklist” is still needed, re-scope it to the Solution instead of Subcomponents.
- Remove any validation coupling subcomponents to solution phases (since subcomponents no longer have phases).
- Keep subcomponent field scope minimal: Project (context), Solution (parent), Subcomponent (task), Priority, Due Date, Status, Assignee; all other governance/tracking fields live on the Solution.

**Filtering**
Add query params to support owner-centric and exec views:
- `GET /api/projects/{project_id}/solutions?status=&owner=&assignee=&due_before=&due_after=&phase=`

**Progress computation**
- Implement Solution progress derived from `current_phase` relative to enabled phases.
- Decide where it lives:
  - Computed property in response (recommended first).
  - Optional stored `solutions.progress` later if performance becomes an issue.

**CSV import/export**
- Extend Solutions CSV to include the new tracking fields.
- Keep strict-first duplicate detection consistent.

### Phase 3 — Audit log expansion
The immutable change log should track the new Solution fields.
- Add the new fields to the solution field allowlist used for logging.
- Ensure bulk imports log `request_id` and capture old→new.

### Phase 4 — Frontend refactor (solution-first UI)
Refactor the UI so the primary workflow doesn’t require subcomponents.

**New/updated primary views**
- **Master List** becomes a “Solutions Master List” (optionally a toggle between Solutions/Subcomponents).
  - Columns: Project, Sponsor, Solution, Owner, Assignee, Current Phase, Priority, Due, Status, Progress, Blockers.
  - Filters: status/project/owner/assignee/phase/priority/due.

- **Kanban** becomes Solution-based by phase group (or status lanes):
  - Cards: Solution name, project, owner/assignee, due date, blockers badge.

- **Calendar** shows Solutions by due date.

- **Dashboard** KPIs computed from Solutions when in solution-centric mode:
  - Overdue solutions, due soon, on hold, avg priority, RAG (optional).

**Solutions form**
- Add inputs for: due_date, priority, current_phase (dropdown of enabled phases), assignee/approver, blockers/risks, next decision.

**Subcomponents UI**
- Keep as “Advanced / Optional” (feature-flagged) for teams that want task-level breakdown.
- Remove subphase selection from the subcomponent form and any subphase columns from subcomponent tables/cards.
- In task lists/tables, keep the default subcomponent columns minimal: Project, Solution, Subcomponent, Priority, Due Date, Status, Assignee.
- If users still need “where is this task?”, show the parent Solution’s current phase as context (read-only), not as a task-level phase.

### Phase 5 — Backfill and cutover
If you already have subcomponents and want to transition:

**Backfill policy (deterministic defaults):**
- `solutions.due_date`: optional; if deriving from existing subcomponents, use the latest non-null subcomponent due date (or leave null).
- `solutions.priority`: minimum priority (highest urgency) among subcomponents (or default 3).
- `solutions.current_phase`: set to null (or first enabled phase) since subcomponents no longer track phases.
- `solutions.status`: derived worst-of: abandoned > on_hold > active/in_progress > not_started/to_do > complete.
- `solutions.blockers`: concatenate top N on_hold notes or a “blocked summary” field.

Provide a one-time admin script/endpoint to:
- Compute + apply backfill.
- Emit audit log entries with a `request_id` indicating migration.

**Cutover**
- Flip UI default to Solutions Master List.
- Hide subcomponents view unless enabled.

### Phase 6 — Cleanup / deprecation (optional)
Once adoption is proven:
- Deprecate subcomponent-only dashboards.
- Keep subcomponents as optional child tasks (not required).
- Update docs and training to “Solution-first.”

## Risks and mitigations
- **Loss of granularity**: teams may miss task-level tracking.
  - Mitigation: keep subcomponents as optional; provide a toggle.

- **Semantic drift**: “status” meaning differs between solution and subcomponent.
  - Mitigation: document mapping; keep enums aligned; enforce clear UI labels.

- **Loss of task-level phase**: teams used to seeing subcomponents move through phases.
  - Mitigation: treat subcomponents as tasks; show parent Solution phase as context; if a checklist is needed, attach it to the Solution instead.

- **Migration complexity**: existing SQLite DBs lack columns.
  - Mitigation: adopt Alembic or ship idempotent additive migrations; avoid drops/renames.

- **Dashboard confusion**: mixed-mode (some solutions have subcomponents, others don’t).
  - Mitigation: pick a rule: solution-centric mode always uses solution fields; subcomponent mode uses subcomponents; don’t mix silently.

## Implementation checklist (ordered)
1. Add solution tracking columns + indexes (migration).
2. Extend Solution schemas/routes + validation.
3. Update solution CSV import/export.
4. Extend audit log coverage for new solution fields.
5. Add UI: solution fields in Solutions form.
6. Refactor Master List/Dashboard/Kanban/Calendar to support solution-centric mode.
7. Add a feature flag (env var) to switch default mode.
8. Backfill script for existing data.
9. Update docs + user guide.

## Estimated effort
- Backend schema/API + audit + CSV: 2–4 days.
- Frontend view refactor: 2–5 days.
- Migration/backfill + validation/testing: 2–4 days.

Total: ~1–2 weeks depending on migration approach and how much UI is redesigned.
