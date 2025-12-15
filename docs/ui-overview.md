# Jira-lite Frontend UI Overview (API-aligned, implementation-ready)

## Foundation
- API base prefix: `/api` (health check lives at `/health`). Use `docs/api-documentation.md` for exact routes/payloads and CSV import/export details; `docs/data-model.md` for field constraints.
- Serve static frontend from `/` via FastAPI `StaticFiles` (directory `frontend/`).
- All forms and lists use live API data; no offline cache or mutations queue.
- Error handling: surface API errors in a visible status pill or toast.
- Pre-app auth screen with login/register toggle; uses cookie-based auth (access + refresh) and hides the app shell until signed in.

## Endpoints
- Projects: `GET/POST/PATCH/DELETE /api/projects`, plus `POST /api/projects/import` and `GET /api/projects/export` (CSV).
- Solutions: `GET/POST /api/projects/{project_id}/solutions`, `GET/PATCH/DELETE /api/solutions/{solution_id}`, plus CSV import/export.
- Phases: `GET /api/phases`, `GET/POST /api/solutions/{solution_id}/phases`.
- Subcomponents: `GET/POST /api/solutions/{solution_id}/subcomponents`, `GET/PATCH/DELETE /api/subcomponents/{subcomponent_id}`, plus CSV import/export.
- Checklist (optional UI): `GET /api/subcomponents/{id}/phases`, `POST /api/subcomponents/{id}/phases/bulk`.

## Data shapes (read)
- Project: `{ project_id, project_name, name_abbreviation, status, description, sponsor, user_id, created_at, updated_at }`
- Solution: `{ solution_id, project_id, solution_name, version, status, description, owner, key_stakeholder, user_id, created_at, updated_at }`
- Phase: `{ phase_id, phase_group, phase_name, sequence }`
- SolutionPhase: `{ solution_phase_id, solution_id, phase_id, is_enabled, sequence_override, created_at, updated_at }`
- Subcomponent: `{ subcomponent_id, project_id, solution_id, subcomponent_name, status, priority, due_date, sub_phase, description, notes, category, dependencies, work_estimate, owner, assignee, approver, completed_at, user_id, created_at, updated_at }`
- Checklist row: `{ subcomponent_phase_id, subcomponent_id, solution_phase_id, phase_id, is_complete, completed_at, created_at, updated_at }`
- Writes: Projects require `project_name`, `name_abbreviation` (4 chars), `status`, `sponsor`; Solutions require `solution_name`, `version`, `status`, `owner`; Subcomponents require `subcomponent_name`, `status`, `priority`, `owner`, `assignee`.

## Views & UX
- **Master List**: Subcomponent table with filters (status, project, solution, sub_phase, priority ≤, search text). Columns: Project, Solution, Name, Subphase, Priority, Due, Status, Progress (computed from enabled phases).
- **Dashboard**: KPI cards (Projects, Solutions, Subcomponents, Overdue), summaries (projects/solutions), “Needs Attention” (overdue), “Upcoming” (by due_date), tags placeholder. 

- **Projects + Solutions (same stacked view)**:
  - Entry form at top: project_name, name_abbreviation (4 chars), sponsor (required), status (`not_started|active|on_hold|complete|abandoned`), description.
  - List below: table of projects; clicking a row loads that project into the form for editing.
  - Solutions block below the projects list (same page):
    - Entry form: project_id (select), solution_name, version, status, description, owner (required), key_stakeholder (optional). Clicking a solution row loads it into the form.
    - List below the form: solutions table (with project name, version, status).
    - Phase toggles under the solutions list: checklist of global phases with checkboxes to enable/disable per selected solution. POST `{ phases: [{ phase_id, is_enabled, sequence_override? }] }` to `/api/solutions/{solution_id}/phases`.
- **Subcomponents (own view)**:
  - Entry form at top: project_id, solution_id, subcomponent_name, status (`to_do|in_progress|on_hold|complete|abandoned`), priority (0–5), due_date, sub_phase (enabled phases), description, notes, category, dependencies, work_estimate, owner (required), assignee (required), approver (optional). Clicking a subcomponent row loads it into the form.
  - List below: table of subcomponents; selecting a row populates the form for editing.
- **Kanban**: Columns by subcomponent.status; cards show name, project, solution, priority, sub_phase/status, due_date. Remain as a separate view.
- **Calendar**: Group subcomponents by due_date.
- **CSV import/export (optional)**: entry points can be tucked under a secondary menu to call the import/export endpoints for projects/solutions/subcomponents.

## Load flow
1. GET `/api/phases`
2. GET `/api/projects`
3. For each project: GET `/api/projects/{project_id}/solutions`
4. For each solution: GET `/api/solutions/{solution_id}/phases` and GET `/api/solutions/{solution_id}/subcomponents`

## Create/Update calls
- Project: POST `/api/projects`, PATCH `/api/projects/{id}`
- Solution: POST `/api/projects/{project_id}/solutions`, PATCH `/api/solutions/{id}`
- Subcomponent: POST `/api/solutions/{solution_id}/subcomponents`, PATCH `/api/subcomponents/{id}`
- Solution phases: POST `/api/solutions/{solution_id}/phases` with `{ phases: [...] }`
- Checklist (optional): GET `/api/subcomponents/{id}/phases`, POST `/api/subcomponents/{id}/phases/bulk` with `{ updates: [{ solution_phase_id, is_complete }] }`

## Progress logic
- If subcomponent.status == "complete": 100%
- Else: order enabled phases by `sequence_override` if set, else global `sequence`. If `sub_phase` missing or not enabled: 0%. Otherwise, progress = ((index_of_sub_phase + 1) / enabled_count) * 100.

## UI behaviors & validation
- Populate selects from live data (projects, solutions, phases).
- Subphase select shows only enabled phases for the selected solution.
- Table row click populates corresponding form for editing.
- Filters re-render master list immediately.
- Enforce: project abbreviation length = 4; sponsor required on projects; owner required on solutions; owner and assignee required on subcomponents; priority 0–5; required fields per schema.
- Deletes are soft; after `DELETE`, refresh lists and omit soft-deleted rows.
- Display API errors via status pill/alert; show loading state on initial fetch.

## Styling/Structure
- Dark/light theme with a palette anchored on RGB(0, 58, 114) and variants (see `frontend/styles.css` for base/soft/strong/accent tokens).
- Sidebar navigation toggles views; topbar status pills show connection/data counts.
- Responsive layout: sidebar collapses on small screens; grids collapse to single column on mobile.
