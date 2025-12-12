# Jira-lite Project Overview

## Goal
A lightweight tracker with a static HTML/JavaScript frontend and a FastAPI backend served by Uvicorn. Uses SQLite (created at startup) to keep setup simple for a small team (10–25 users).

## Tech Stack
- Backend: Python, FastAPI, Uvicorn, SQLAlchemy for SQLite.
- Frontend: Static HTML + vanilla JavaScript (Fetch API), minimal CSS; served as static files by FastAPI.
- Database: SQLite file in `./db/app.db`; WAL mode recommended for concurrency.

## Data Model (current)
- Projects: `project_name`, `name_abbreviation` (4-char), `status`, `description`; metadata: `project_id`, `user_id`, timestamps, `deleted_at`; unique on `project_name`.
- Solutions: belong to a project; `solution_name`, `version`, `status`, `description`; metadata: `solution_id`, `user_id`, timestamps, `deleted_at`; unique on (`project_id`, `solution_name`, `version`); can enable/disable phases and override ordering.
- Phases: global ordered list of sub-phases (Backlog, Planning, Development, Deployment & Testing, Closure) with `phase_id` slugs used as `sub_phase` values.
- Solution phases: per-solution toggles and optional sequence overrides to define enabled phases for progress.
- Subcomponents: belong to a project + solution; `subcomponent_name`, `status`, `priority` (0 highest), `due_date` (YYYY-MM-DD), `sub_phase`, `description`, `notes`; optional `category`, `dependencies`, `work_estimate`; metadata: `subcomponent_id`, `user_id`, timestamps, `deleted_at`; unique name within a solution.
- Subcomponent phase status: optional checklist rows per enabled phase to show phases and check off completion; keep aligned with `sub_phase`.
- Progress: if status = complete, 100%; otherwise derived from the position of `sub_phase` within enabled phases.
- Soft deletes (`deleted_at`) on core tables; see `docs/data-model.md` for full field definitions.
- User attribution: `user_id` is set server-side from the host account or env override (`JIRA_LITE_USER_ID`/`USER`/`USERNAME`/`LOGNAME`); clients do not pass a user header yet.

## API Surface (Option A: minimal)
- Health: `GET /health`.
- Projects: `GET/POST /projects`, `GET/PATCH/DELETE /projects/{project_id}` (DELETE = soft delete).
- Solutions: `GET/POST /projects/{project_id}/solutions`, `GET/PATCH/DELETE /solutions/{solution_id}`.
- Phases: `GET /phases` (global list), `GET/POST /solutions/{solution_id}/phases` to enable/disable and set sequence.
- Subcomponents: `GET/POST /solutions/{solution_id}/subcomponents`, `GET/PATCH/DELETE /subcomponents/{subcomponent_id}`; filters on `status`, `sub_phase`, `priority`, `due_before`, `due_after`.
- Checklist: `GET /subcomponents/{subcomponent_id}/phases` (enabled phases + completion flags), `POST /subcomponents/{subcomponent_id}/phases/bulk` to mark complete/incomplete.
- Filters (query params on list endpoints): `status`, `sub_phase`, `priority`, `due_before`, `due_after`, `search`.
- All responses JSON; errors return JSON with `detail`.

## API Payload Examples

Projects
- Create `POST /projects`
```json
{
  "project_name": "Data Platform",
  "name_abbreviation": "DPLT",
  "status": "active",
  "description": "Modernize data stack"
}
```
- Response (201)
```json
{
  "project_id": "uuid",
  "project_name": "Data Platform",
  "name_abbreviation": "DPLT",
  "status": "active",
  "description": "Modernize data stack",
  "user_id": "server_user",
  "created_at": "2024-01-10T12:00:00Z",
  "updated_at": "2024-01-10T12:00:00Z"
}
```
- Update `PATCH /projects/{project_id}` (partial)
```json
{ "status": "on_hold", "description": "Waiting on budget" }
```

Solutions
- Create `POST /projects/{project_id}/solutions`
```json
{
  "solution_name": "Access Controls",
  "version": "0.2.0",
  "status": "active",
  "description": "Iterate on RBAC and audit logging"
}
```
- Response (201)
```json
{
  "solution_id": "uuid",
  "project_id": "uuid",
  "solution_name": "Access Controls",
  "version": "0.2.0",
  "status": "active",
  "description": "Iterate on RBAC and audit logging",
  "user_id": "server_user",
  "created_at": "2024-01-10T12:05:00Z",
  "updated_at": "2024-01-10T12:05:00Z"
}
```
- Update `PATCH /solutions/{solution_id}` (partial)
```json
{ "status": "complete", "description": "Shipped in v0.2.0" }
```

Phases and Solution Phases
- List global phases `GET /phases` → array of `{ phase_id, phase_group, phase_name, sequence }`.
- Get enabled phases for a solution `GET /solutions/{solution_id}/phases`.
- Set enabled phases + ordering `POST /solutions/{solution_id}/phases`
```json
{
  "phases": [
    { "phase_id": "backlog", "is_enabled": true },
    { "phase_id": "requirements", "is_enabled": true, "sequence_override": 2 },
    { "phase_id": "uat_deployment", "is_enabled": false }
  ]
}
```
- Response echoes enabled phases with applied order.

Subcomponents
- Create `POST /solutions/{solution_id}/subcomponents`
```json
{
  "subcomponent_name": "Define RBAC roles",
  "status": "in_progress",
  "priority": 1,
  "due_date": "2024-02-01",
  "sub_phase": "requirements",
  "description": "Document role matrix",
  "notes": "Align with security"
}
```
- Response (201)
```json
{
  "subcomponent_id": "uuid",
  "project_id": "uuid",
  "solution_id": "uuid",
  "subcomponent_name": "Define RBAC roles",
  "status": "in_progress",
  "priority": 1,
  "due_date": "2024-02-01",
  "sub_phase": "requirements",
  "description": "Document role matrix",
  "notes": "Align with security",
  "user_id": "server_user",
  "created_at": "2024-01-10T12:10:00Z",
  "updated_at": "2024-01-10T12:10:00Z"
}
```
- Update `PATCH /subcomponents/{subcomponent_id}` (partial)
```json
{ "status": "complete", "sub_phase": "closure", "priority": 2 }
```
- List with filters: `GET /solutions/{solution_id}/subcomponents?status=in_progress&priority=0&sub_phase=requirements`

Checklist
- Get checklist `GET /subcomponents/{subcomponent_id}/phases` → enabled phases with completion flags.
- Bulk update `POST /subcomponents/{subcomponent_id}/phases/bulk`
```json
{
  "updates": [
    { "solution_phase_id": "uuid-phase-1", "is_complete": true },
    { "solution_phase_id": "uuid-phase-2", "is_complete": false }
  ]
}
```
- Response returns updated checklist rows with `is_complete` and `completed_at`.

Errors
- All errors return JSON: `{ "detail": "message" }`.

## Initialization Flow
1. On startup, ensure `db/app.db` exists; enable WAL.
2. Create tables via SQLAlchemy metadata.
3. Seed: global phases with sequence on startup (idempotent).
4. Optional sample data: set `SAMPLE_SEED=true` to create a sample project, solution, and subcomponents (idempotent if already present).

## Frontend Plan
- Single-page HTML served at `/` that fetches via the API.
- Views:
  - Projects: list/create.
  - Solutions within a project: list/create; configure enabled phases and ordering.
  - Subcomponents within a solution: list/create; update status, priority, due date, current `sub_phase`.
  - Phase checklist per subcomponent: show enabled phases and allow check/uncheck.
- Use vanilla JS modules for fetch/update; keep payloads small and cache phase lists client-side.

## Local Development
- Install deps: `pip install fastapi uvicorn[standard] sqlmodel`.
- Run dev server: `uvicorn backend.app.main:app --reload`.
- SQLite lives in `db/app.db` (ignored by VCS unless we choose to commit seed data).
- API docs available at `/docs` (Swagger) and `/redoc`.

## Next Steps
- Scaffold FastAPI app (`app/main.py`, `app/models.py`, `app/routes/*.py`).
- Implement DB init with WAL and seeding of phases + sample data.
- Build API routes for projects, solutions, phases, subcomponents, and phase checklist.
- Add HTML/JS frontend and hook up API calls.
- Add smoke tests for core endpoints.
