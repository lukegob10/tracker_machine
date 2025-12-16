# Change Log Plan (Immutable Audit Trail)

## Goal
Add an append-only change log that records who/when/old→new for critical fields, to support auditability and dispute resolution.

## Scope (Phase 1)
- Entities: projects, solutions, subcomponents, solution_phases (enable/disable). Optional: imports.
- Fields to track per entity:
  - Projects: status, sponsor, description, name_abbreviation, project_name (rename).
  - Solutions: status, owner, key_stakeholder, description, version, solution_name.
  - Subcomponents: status, priority, due_date, sub_phase, owner, assignee, approver, description, notes, category, dependencies, work_estimate, subcomponent_name.
  - Phases toggle: is_enabled, sequence_override.
- Actions: create, update, soft delete, restore.

## Data Model
- Table `change_log` (append-only):
  - `change_id` (UUID, PK)
  - `entity_type` (TEXT enum: project|solution|subcomponent|solution_phase)
  - `entity_id` (TEXT)
  - `action` (create|update|delete|restore)
  - `field` (TEXT; null for create/delete if not field-specific)
  - `old_value` (TEXT, nullable)
  - `new_value` (TEXT, nullable)
  - `user_id` (TEXT, FK to users.user_id)
  - `request_id` (TEXT, optional correlation id per request/import)
  - `created_at` (DATETIME)
- Indexes: `(entity_type, entity_id, created_at)`, `(user_id, created_at)`, `(request_id)` (optional).
- Immutability: no UPDATE/DELETE. DB trigger to block changes to existing rows (optional).

## Backend Changes
- Add helper `log_changes(session, *, entity_type, entity_id, user_id, action, changes: dict[field] = (old, new), request_id=None)` that inserts rows in the current transaction.
- Wrap all mutating endpoints (create/update/delete/restore) to:
  - Compute diffs (exclude unchanged fields).
  - Log one row per changed field on update; one row with minimal fields on create/delete/restore.
  - Use authenticated `user_id`; reject if missing.
- Bulk/import: supply a generated `request_id` and log per-row changes; limit to create/update actions.
- Soft delete/restore: log with `action=delete/restore`, `field=deleted_at`, old/new timestamps.

## API
- New read-only endpoint: `GET /api/audit` with filters: `entity_type`, `entity_id`, `field`, `user_id`, `since`, `until`, `limit` (paginate descending by created_at). No writes/exposes raw values only.
- Ensure existing endpoints remain unchanged except that they now emit log rows.

## UI
- Add an “Audit” drawer/tab on subcomponent detail and optionally project/solution detail.
- Show table: Time, User, Field, Old → New, Action. Filter by field/user/time.
- Keep audit read-only; no delete/edit.

## Security
- Require auth for all audit reads; restrict to Admins if RBAC is added later.
- Ensure values are sanitized to strings; avoid leaking secrets (none expected in current schema).
- Keep request_id to trace bulk operations.

## Testing
- Unit: diff helper logs only changed fields; create/delete actions log expected rows.
- Integration: PATCH/DELETE on each entity emits expected log entries; bulk import logs per-row creates/updates.
- API: `GET /api/audit` filtering and ordering.

## Rollout
- Migration to create `change_log` (and optional trigger to block update/delete).
- Deploy; verify login works; perform smoke mutations; check `change_log` rows and audit endpoint.
