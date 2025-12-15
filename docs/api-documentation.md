# Jira-lite API

Base URL (dev): `http://127.0.0.1:8000`  
API base path: `/api` (all routes below assume this prefix)  
Docs: `/docs` (Swagger), `/redoc`  
Auth: none (local/dev)  
Content-Type: `application/json`  
See `docs/data-model.md` for field definitions/constraints.

## Common
- Errors: `{ "detail": "message" }`
- Auth: cookie-based. Use `/api/auth/login` or `/api/auth/register` to obtain HttpOnly `access_token` + `refresh_token`. All routes below require auth except `/health` and the `/api/auth/*` endpoints.
- Soft deletes: `DELETE` sets `deleted_at`; list/get skip soft-deleted rows.
- Timestamps: ISO8601 UTC. Phases are seeded on startup.
- User attribution: `user_id` is set from the authenticated user; legacy env fallback (`JIRA_LITE_USER_ID`/`USER`/`USERNAME`/`LOGNAME`) applies only where explicitly noted for dev data.
- Static frontend is served from `/`; keep API under `/api` to avoid path collisions.

## Auth
- `POST /api/auth/register` → create a local user (`soeid`, `display_name`, `password`); email is derived as `<soeid>@citi.com`; sets auth cookies and returns the user.
- `POST /api/auth/login` → verify credentials with `soeid` + password; sets `access_token` (short TTL) + `refresh_token` (longer TTL) cookies; returns the user.
- `POST /api/auth/refresh` → rotate access/refresh using the refresh cookie; returns the user.
- `POST /api/auth/logout` → clears cookies.
- `GET /api/auth/me` → returns the current authenticated user.
- Lockout: after repeated failed logins, account is temporarily locked; `is_active` must be true.

## Audit Log
- `GET /api/audit` (auth required) → append-only change log; filters: `entity_type`, `entity_id`, `field`, `user_id`, `since`, `until`, `limit` (default 100). Records captures: who/when/action and old→new for tracked fields.

## Health
- `GET /health` → `{ "status": "ok" }` (only endpoint without the `/api` prefix)

## Projects
- `GET /api/projects?status=<not_started|active|on_hold|complete|abandoned>`
- `POST /api/projects`
```json
{ "project_name": "Data Platform", "name_abbreviation": "DPLT", "status": "active", "sponsor": "CFO Office", "description": "..." }
```
- `GET /api/projects/{project_id}`
- `PATCH /api/projects/{project_id}` (partial: status, name_abbreviation, project_name, description, sponsor)
- `DELETE /api/projects/{project_id}` (soft delete)
- Responses include `user_id` set by the server account/env.
- Bulk CSV: `POST /api/projects/import` (fields: project_name, name_abbreviation, status, description, sponsor; strict-first duplicate detection), `GET /api/projects/export` (CSV download)

## Solutions (scoped to project)
- `GET /api/projects/{project_id}/solutions?status=<not_started|active|on_hold|complete|abandoned>`
- `POST /api/projects/{project_id}/solutions`
```json
{ "solution_name": "Access Controls", "version": "0.2.0", "status": "active", "owner": "Solution Owner", "key_stakeholder": "Finance Ops", "description": "..." }
```
- `GET /api/solutions/{solution_id}`
- `PATCH /api/solutions/{solution_id}` (partial: solution_name, version, status, description, owner, key_stakeholder)
- `DELETE /api/solutions/{solution_id}` (soft delete)
- Responses include `user_id` set by the server account/env.
- Bulk CSV: `POST /api/solutions/import` (fields: project_name, solution_name, version, status, description, owner (required), key_stakeholder; creates missing projects; strict-first duplicates), `GET /api/solutions/export` (CSV download)

## Phases (global) and Solution Phases
- `GET /api/phases` → ordered list `{ phase_id, phase_group, phase_name, sequence }`
- `GET /api/solutions/{solution_id}/phases` → enabled phases for that solution (ordered by `sequence_override` if set, else `sequence`)
- `POST /api/solutions/{solution_id}/phases` (upsert enable/disable + override)
```json
{ "phases": [
  { "phase_id": "backlog", "is_enabled": true },
  { "phase_id": "requirements", "is_enabled": true, "sequence_override": 2 },
  { "phase_id": "uat_deploy", "is_enabled": false }
] }
```

## Subcomponents (scoped to solution)
- `GET /api/solutions/{solution_id}/subcomponents`
  - Filters: `status=<to_do|in_progress|on_hold|complete|abandoned>`, `priority=<0-5>`, `sub_phase=<phase_id>`, `due_before=YYYY-MM-DD`, `due_after=YYYY-MM-DD`
- `POST /api/solutions/{solution_id}/subcomponents`
```json
{
  "subcomponent_name": "Define RBAC roles",
  "status": "in_progress",
  "priority": 1,
  "due_date": "2024-02-01",
  "sub_phase": "requirements",
  "description": "Document role matrix",
  "notes": "Align with security",
  "owner": "Subcomponent Owner",
  "assignee": "Engineer A",
  "approver": "Risk Lead"
}
```
- `GET /api/subcomponents/{subcomponent_id}`
- `PATCH /api/subcomponents/{subcomponent_id}` (partial: name, status, priority, due_date, sub_phase, description, notes, category, dependencies, work_estimate, owner, assignee, approver)
- `DELETE /api/subcomponents/{subcomponent_id}` (soft delete)
- Rules: `sub_phase` must be among enabled phases for the solution; name unique per solution; `priority` 0–5.
- Responses include `user_id` set by the server account/env.
- Bulk CSV: `POST /api/subcomponents/import` (fields: project_name, solution_name, version (optional, defaults to 0.1.0), subcomponent_name, status, priority, due_date, sub_phase, description, notes, category, dependencies, work_estimate, owner (required), assignee (required), approver; creates missing projects/solutions; strict-first duplicates), `GET /api/subcomponents/export` (CSV download)

## Checklist (subcomponent phase completion)
- `GET /api/subcomponents/{subcomponent_id}/phases` → syncs rows to enabled phases, returns `{ solution_phase_id, phase_id, is_complete, completed_at }`
- `POST /api/subcomponents/{subcomponent_id}/phases/bulk`
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
