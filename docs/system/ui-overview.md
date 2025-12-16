# Jira-lite Frontend UI Overview (Solution-first)

## Foundation
- API base prefix: `/api` (health check lives at `/health`). Use `docs/system/api-documentation.md` for exact routes/payloads and CSV import/export details; `docs/system/data-model.md` for field constraints.
- Static frontend is served from `/` via FastAPI `StaticFiles` (directory `frontend/`).
- Pre-app auth screen with login/register toggle; uses cookie-based auth (access + refresh) and hides the app shell until signed in.
- All views render from live API data; there is no offline cache or background sync queue.

## Endpoints (used by the UI)
- Projects: `GET/POST/PATCH/DELETE /api/projects`, plus `POST /api/projects/import` and `GET /api/projects/export` (CSV).
- Solutions:
  - `GET /api/solutions` (all solutions across projects)
  - `GET/POST /api/projects/{project_id}/solutions`
  - `GET/PATCH/DELETE /api/solutions/{solution_id}`
  - `GET/POST /api/solutions/{solution_id}/phases` (enable/disable phases per solution)
  - CSV: `POST /api/solutions/import`, `GET /api/solutions/export`
- Subcomponents (tasks):
  - `GET /api/subcomponents` (all subcomponents across solutions)
  - `GET/POST /api/solutions/{solution_id}/subcomponents`
  - `GET/PATCH/DELETE /api/subcomponents/{subcomponent_id}`
  - CSV: `POST /api/subcomponents/import`, `GET /api/subcomponents/export`

## Data shapes (read)
- Project: `{ project_id, project_name, name_abbreviation, status, description, success_criteria, sponsor, user_id, created_at, updated_at }`
- Solution: `{ solution_id, project_id, solution_name, version, status, rag_status, rag_source, rag_reason, priority, due_date, current_phase, description, success_criteria, owner, assignee, approver, key_stakeholder, blockers, risks, completed_at, user_id, created_at, updated_at }`
- Phase: `{ phase_id, phase_group, phase_name, sequence }`
- SolutionPhase: `{ solution_phase_id, solution_id, phase_id, is_enabled, sequence_override, created_at, updated_at }`
- Subcomponent: `{ subcomponent_id, project_id, solution_id, subcomponent_name, status, priority, due_date, assignee, completed_at, user_id, created_at, updated_at }`

## Views & UX
- **Deliverables**: Solution-first table across projects. Filters: status, project, current phase, priority ≤, owner, assignee, search. Columns: Project, Sponsor, Solution, Version, Owner, Assignee, Current Phase, Priority, Due, RAG, Status, Progress.
- **Dashboard**: solution-based KPI cards (projects/solutions/subcomponents counts, overdue, active, complete, on hold, no due date, avg priority) plus project and solution summary tables and attention/upcoming panels.
- **Projects**: CRUD form + table. Sponsor is required; abbreviation must be 4 chars.
- **Solutions**:
  - CRUD form + table.
  - Tracks the primary delivery fields: status, priority, due date, current phase, owner/assignee, optional success criteria, and optional blockers/risks.
  - RAG (Solutions): auto by default; can be manually overridden with a reason and reset back to auto.
  - Phase toggles: per selected solution, enable/disable phases. Disabling the currently selected `current_phase` clears it server-side.
- **Subcomponents** (tasks): optional task tracking under a solution. Form + table; minimal fields: task name, status, priority, due date, assignee.
- **Swimlanes**: solution cards grouped by Project and then by Phase Group (derived from `solution.current_phase`).
- **Calendar**: solutions grouped by `due_date`.

## Load flow
1. `GET /api/phases`
2. `GET /api/projects`
3. `GET /api/solutions`
4. `GET /api/subcomponents`
5. On-demand (when editing phase toggles): `GET /api/solutions/{solution_id}/phases`

## Progress logic (solution)
- If `solution.status == "complete"`: progress = 100%.
- Else: if `solution.current_phase` is empty or not recognized: progress = 0%.
- Otherwise: order enabled phases by `sequence_override` if set, else global `sequence`; progress = `((index_of(current_phase) + 1) / enabled_count) * 100`.

## UI behaviors & validation
- Populate selects from live data (projects, solutions, phases).
- Enforce: project abbreviation length = 4; sponsor required on projects; owner required on solutions; assignee required on subcomponents; priority clamped 0–5.
- Deletes are soft; after `DELETE`, refresh lists and omit soft-deleted rows.
- Display API errors via status pill/alert; show loading state on initial fetch.
