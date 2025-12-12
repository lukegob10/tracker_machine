# Jira-lite API

Base URL (dev): `http://127.0.0.1:8000`  
Docs: `/docs` (Swagger), `/redoc`  
Auth: none (local/dev)  
Content-Type: `application/json`

## Common
- Errors: `{ "detail": "message" }`
- Soft deletes: `DELETE` sets `deleted_at`; list/get skip soft-deleted rows.
- Timestamps: ISO8601 UTC. Seeded phases on startup.
- User attribution: `user_id` is set server-side to the host account (or env override `JIRA_LITE_USER_ID`/`USER`/`USERNAME`/`LOGNAME`). Clients do not send a user header yet.

## Health
- `GET /health` → `{ "status": "ok" }`

## Projects
- `GET /projects?status=<not_started|active|on_hold|complete|abandoned>`
- `POST /projects`
```json
{ "project_name": "Data Platform", "name_abbreviation": "DPLT", "status": "active", "description": "..." }
```
- `GET /projects/{project_id}`
- `PATCH /projects/{project_id}` (partial: status, name_abbreviation, project_name, description)
- `DELETE /projects/{project_id}` (soft delete)
- Responses include `user_id` set by the server account/env.
- Bulk CSV: `POST /projects/import` (fields: project_name, name_abbreviation, status, description; strict-first duplicate detection), `GET /projects/export` (CSV download)

## Solutions (scoped to project)
- `GET /projects/{project_id}/solutions?status=<not_started|active|on_hold|complete|abandoned>`
- `POST /projects/{project_id}/solutions`
```json
{ "solution_name": "Access Controls", "version": "0.2.0", "status": "active", "description": "..." }
```
- `GET /solutions/{solution_id}`
- `PATCH /solutions/{solution_id}` (partial: solution_name, version, status, description)
- `DELETE /solutions/{solution_id}` (soft delete)
- Responses include `user_id` set by the server account/env.
- Bulk CSV: `POST /solutions/import` (fields: project_name, solution_name, version, status, description; creates missing projects; strict-first duplicates), `GET /solutions/export` (CSV download)

## Phases (global) and Solution Phases
- `GET /phases` → ordered list `{ phase_id, phase_group, phase_name, sequence }`
- `GET /solutions/{solution_id}/phases` → enabled phases for that solution (ordered by `sequence_override` if set, else `sequence`)
- `POST /solutions/{solution_id}/phases` (upsert enable/disable + override)
```json
{ "phases": [
  { "phase_id": "backlog", "is_enabled": true },
  { "phase_id": "requirements", "is_enabled": true, "sequence_override": 2 },
  { "phase_id": "uat_deploy", "is_enabled": false }
] }
```

## Subcomponents (scoped to solution)
- `GET /solutions/{solution_id}/subcomponents`
  - Filters: `status=<to_do|in_progress|on_hold|complete|abandoned>`, `priority=<0-5>`, `sub_phase=<phase_id>`, `due_before=YYYY-MM-DD`, `due_after=YYYY-MM-DD`
- `POST /solutions/{solution_id}/subcomponents`
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
- `GET /subcomponents/{subcomponent_id}`
- `PATCH /subcomponents/{subcomponent_id}` (partial: name, status, priority, due_date, sub_phase, description, notes, category, dependencies, work_estimate)
- `DELETE /subcomponents/{subcomponent_id}` (soft delete)
- Rules: `sub_phase` must be among enabled phases for the solution; name unique per solution; `priority` 0–5.
- Responses include `user_id` set by the server account/env.
- Bulk CSV: `POST /subcomponents/import` (fields: project_name, solution_name, version (optional, defaults to 0.1.0), subcomponent_name, status, priority, due_date, sub_phase, description, notes, category, dependencies, work_estimate; creates missing projects/solutions; strict-first duplicates), `GET /subcomponents/export` (CSV download)

## Checklist (subcomponent phase completion)
- `GET /subcomponents/{subcomponent_id}/phases` → syncs rows to enabled phases, returns `{ solution_phase_id, phase_id, is_complete, completed_at }`
- `POST /subcomponents/{subcomponent_id}/phases/bulk`
```json
{ "updates": [
  { "solution_phase_id": "uuid-phase-1", "is_complete": true },
  { "solution_phase_id": "uuid-phase-2", "is_complete": false }
] }
```
- If a phase is disabled later, its checklist rows are removed on sync.

## Status defaults
- Project status: `not_started` if omitted.
- Solution status: `not_started` if omitted.
- Subcomponent: `status=to_do`, `priority=3` if omitted.
- Abbreviation must be 4 chars.

## Seeding
On startup: create tables and seed global phases (Backlog → Closure) idempotently.

## Static frontend
Root (`/`) serves files from `frontend/`; adjust `frontend/js/app.js` API base if hosting differently.
