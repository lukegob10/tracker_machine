# Jira-lite Frontend UI Overview (API-aligned, implementation-ready)

## Foundation
- API base prefix: `/api`
- Serve static frontend from `/` via FastAPI `StaticFiles` (directory `frontend/`).
- All forms and lists use live API data; no offline cache or mutations queue.
- Error handling: surface API errors in a visible status pill or toast.

## Endpoints
- Projects: `GET/POST /api/projects`, `PATCH /api/projects/{project_id}`
- Solutions: `GET/POST /api/projects/{project_id}/solutions`, `GET/PATCH /api/solutions/{solution_id}`
- Phases: `GET /api/phases`, `GET/POST /api/solutions/{solution_id}/phases`
- Subcomponents: `GET/POST /api/solutions/{solution_id}/subcomponents`, `GET/PATCH /api/subcomponents/{subcomponent_id}`
- Checklist (optional UI): `GET /api/subcomponents/{id}/phases`, `POST /api/subcomponents/{id}/phases/bulk`

## Data shapes (read)
- Project: `{ project_id, project_name, name_abbreviation, status, description, created_at, updated_at }`
- Solution: `{ solution_id, project_id, solution_name, version, status, description, created_at, updated_at }`
- Phase: `{ phase_id, phase_group, phase_name, sequence }`
- SolutionPhase: `{ solution_phase_id, solution_id, phase_id, is_enabled, sequence_override, created_at, updated_at }`
- Subcomponent: `{ subcomponent_id, project_id, solution_id, subcomponent_name, status, priority, due_date, sub_phase, description, notes, created_at, updated_at }`
- Checklist row: `{ subcomponent_phase_id, subcomponent_id, solution_phase_id, phase_id, is_complete, completed_at, created_at, updated_at }`

## Views & UX
- **Master List**: Subcomponent table with filters (status, project, solution, sub_phase, priority ≤, search text). Columns: Project, Solution, Name, Subphase, Priority, Due, Status, Progress (computed from enabled phases).
- **Dashboard**: KPI cards (Projects, Solutions, Subcomponents, Overdue), summaries (projects/solutions), “Needs Attention” (overdue), “Upcoming” (by due_date), tags placeholder. 

- **Projects + Solutions (same stacked view)**:
  - Entry form at top: project_name, name_abbreviation (4 chars), status (`not_started|active|on_hold|complete|abandoned`), description.
  - List below: table of projects; clicking a row loads that project into the form for editing.
  - Solutions block below the projects list (same page):
    - Entry form: project_id (select), solution_name, version, status, description. Clicking a solution row loads it into the form.
    - List below the form: solutions table (with project name, version, status).
    - Phase toggles under the solutions list: checklist of global phases with checkboxes to enable/disable per selected solution. POST `{ phases: [{ phase_id, is_enabled, sequence_override? }] }` to `/api/solutions/{solution_id}/phases`.
- **Subcomponents (own view)**:
  - Entry form at top: project_id, solution_id, subcomponent_name, status (`to_do|in_progress|on_hold|complete|abandoned`), priority (0–5), due_date, sub_phase (enabled phases), description, notes. Clicking a subcomponent row loads it into the form.
  - List below: table of subcomponents; selecting a row populates the form for editing.
- **Kanban**: Columns by subcomponent.status; cards show name, project, solution, priority, sub_phase/status, due_date. Remain as a separate view.
- **Calendar**: Group subcomponents by due_date.

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
- Enforce: project abbreviation length = 4; subcomponent priority 0–5; required fields per schema.
- Display API errors via status pill/alert; show loading state on initial fetch.

## Styling/Structure
- Dark/light theme with a palette anchored on RGB(0, 58, 114) and variants (see `frontend/styles.css` for base/soft/strong/accent tokens).
- Sidebar navigation toggles views; topbar status pills show connection/data counts.
- Responsive layout: sidebar collapses on small screens; grids collapse to single column on mobile.
