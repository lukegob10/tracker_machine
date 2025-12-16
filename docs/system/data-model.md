# Data Model

SQLite schema for Jira-lite with projects, solutions, and subcomponents. All timestamps stored as ISO8601 in UTC. Foreign keys are enforced (`PRAGMA foreign_keys = ON`). Pair this reference with `docs/api-documentation.md` for routes/payloads and `docs/ui-overview.md` for how the UI exercises these fields.

User attribution: `user_id` is populated from the authenticated user; legacy env fallback (`JIRA_LITE_USER_ID`/`USER`/`USERNAME`/`LOGNAME`) applies only to dev/seeding contexts.

## Entities at a Glance
- Project: top-level container with name, 4-char abbreviation, status, description, optional success criteria, and a required Sponsor; stores `project_id`, `user_id`, timestamps, and soft delete metadata but those fields are not surfaced in the UI.
- Solution: versioned deliverable that belongs to a project and is the primary trackable work item; carries Owner/Assignee, priority, optional due date, optional current phase, optional success criteria, and optional blockers/risks; can enable/disable phases to fit its workflow; stores `solution_id`, `user_id`, timestamps, and soft delete metadata.
- Subcomponent: optional task belonging to a project + solution; minimal fields (name, status, priority, due date, assignee). Subcomponents do **not** carry phases/progress.

## Table Definitions (simplified)

### projects
| Field             | Type     | Description                 |
| ----------------- | -------- | --------------------------- |
| project_id        | TEXT     | UUID                        |
| project_name      | TEXT     | Display name (unique)       |
| name_abbreviation | TEXT     | 4-character code            |
| status            | TEXT     | Project lifecycle status    |
| description       | TEXT     | Project summary             |
| success_criteria  | TEXT     | Optional definition of done |
| sponsor           | TEXT     | Accountable/Sponsor (required) |
| user_id           | TEXT     | Owner/user reference        |
| created_at        | DATETIME | Created timestamp           |
| updated_at        | DATETIME | Last updated timestamp      |
| deleted_at        | DATETIME | Soft delete timestamp       |

Allowed values
- status: `not_started`, `active`, `on_hold`, `complete`, `abandoned`
- check: enforce `name_abbreviation` length = 4 via validation/constraint

Validation & Defaults
- Required: `project_name`, `name_abbreviation`, `status`, `sponsor`; `description` and `success_criteria` optional.
- Defaults: `status` defaults to `not_started`; `sponsor` must be provided on create/import (UI-enforced; server stores empty string only for legacy/import edge cases).
- Normalization: enforce `name_abbreviation` length = 4; optionally uppercase in validation.
- Soft delete: `deleted_at` set instead of hard delete; default queries exclude soft-deleted rows.

Indexes
- Unique: `project_name`
- Index: `status`

### solutions
| Field             | Type     | Description                 |
| ----------------- | -------- | --------------------------- |
| solution_id       | TEXT     | UUID                        |
| solution_name     | TEXT     | Name within project         |
| project_id        | TEXT     | FK to project               |
| version           | TEXT     | Version string (e.g., 0.1.0)|
| status            | TEXT     | Solution lifecycle status   |
| priority          | INTEGER  | 0–5 priority (0 = highest)  |
| due_date          | DATE     | Optional target date (YYYY-MM-DD) |
| current_phase     | TEXT     | Optional phase slug (FK-like to `phases.phase_id`) |
| description       | TEXT     | Summary/notes               |
| success_criteria  | TEXT     | Optional definition of done |
| owner             | TEXT     | Solution Owner (R + A, required) |
| assignee          | TEXT     | Executor (optional)         |
| approver          | TEXT     | Gate/approver (optional)    |
| key_stakeholder   | TEXT     | Consulted stakeholder (optional) |
| blockers          | TEXT     | Blockers (optional)         |
| risks             | TEXT     | Risks (optional)            |
| completed_at      | DATETIME | When marked complete        |
| user_id           | TEXT     | Owner/user reference        |
| created_at        | DATETIME | Created timestamp           |
| updated_at        | DATETIME | Last updated timestamp      |
| deleted_at        | DATETIME | Soft delete timestamp       |

Allowed values
- status: `not_started`, `active`, `on_hold`, `complete`, `abandoned`

Validation & Defaults
- Required: `project_id`, `solution_name`, `version`, `status`, `owner`; most other fields optional (including `success_criteria`).
- Defaults: `status` defaults to `not_started`; `priority` defaults to 3; `due_date` and `current_phase` default to null.
- Uniqueness: `(project_id, solution_name, version)` must be unique among non-deleted rows.

Indexes
- Unique: `(project_id, solution_name, version)`
- Index: `(project_id, status)`, `(status)`, `(priority)`, `(due_date)`, `(current_phase)`, `(owner)`, `(assignee)`

### phases (lookup)
| Field       | Type     | Description                        |
| ----------- | -------- | ---------------------------------- |
| phase_id    | TEXT     | Slug/UUID used as `current_phase` value |
| phase_group | TEXT     | High-level bucket (e.g., Planning) |
| phase_name  | TEXT     | Specific phase label               |
| sequence    | INTEGER  | Ordering for progress calculations |
| created_at  | DATETIME | Created timestamp                  |
| updated_at  | DATETIME | Last updated timestamp             |

Indexes
- Index: `sequence`

Validation & Defaults
- Required: `phase_id`, `phase_group`, `phase_name`, `sequence`.
- `sequence` is an integer; keep unique ordering in the canonical list.
- `phase_id` is a stable slug/UUID; avoid edits that break existing references.

### solution_phases (per-solution phase toggles)
| Field              | Type     | Description                                    |
| ------------------ | -------- | ---------------------------------------------- |
| solution_phase_id  | TEXT     | UUID                                           |
| solution_id        | TEXT     | FK to solution                                 |
| phase_id           | TEXT     | FK to phases                                   |
| is_enabled         | INTEGER  | 0/1 flag to include/exclude the phase          |
| sequence_override  | INTEGER  | Optional per-solution ordering override        |
| created_at         | DATETIME | Created timestamp                              |
| updated_at         | DATETIME | Last updated timestamp                         |

Indexes
- Unique: `(solution_id, phase_id)`
- Index: `(solution_id, sequence_override)`

Validation & Defaults
- Required: `solution_id`, `phase_id`; both must exist.
- Defaults: `is_enabled` defaults to 1; `sequence_override` optional (null).
- `sequence_override` must be a positive integer when provided.
- Disabling a phase should also clear `solutions.current_phase` if it is set to a now-disabled phase.

Best-practice rollup (simple):
- `phases` holds the canonical ordered list.
- `solution_phases` turns phases on/off per solution and can override order.
- `solutions.current_phase` represents “where we are” and drives progress; subcomponents are tasks and do not carry phases.

### subcomponents
| Field             | Type     | Description                     |
| ----------------- | -------- | ------------------------------- |
| subcomponent_id   | TEXT     | UUID                            |
| project_id        | TEXT     | FK to project                   |
| solution_id       | TEXT     | FK to solution                  |
| subcomponent_name | TEXT     | Name within solution            |
| status            | TEXT     | Subcomponent lifecycle status   |
| priority          | INTEGER  | 0-5 priority (0 = highest)      |
| due_date          | DATE     | Target date (YYYY-MM-DD)        |
| assignee          | TEXT     | Executing individual (required) |
| created_at        | DATETIME | Created timestamp               |
| updated_at        | DATETIME | Last updated timestamp          |
| completed_at      | DATETIME | When marked complete            |
| user_id           | TEXT     | Owner/user reference            |
| deleted_at        | DATETIME | Soft delete timestamp           |

Allowed values
- status: `to_do`, `in_progress`, `on_hold`, `complete`, `abandoned`
- priority: `0` (highest) to `5` (lowest)

Validation & Defaults
- Required: `project_id`, `solution_id`, `subcomponent_name`, `status`, `assignee`.
- Defaults: `status` defaults to `to_do`; `priority` defaults to 3 (mid); `due_date` optional.
- Constraints: `priority` must be between 0 and 5 inclusive.
- Uniqueness: `(solution_id, subcomponent_name)` must be unique among non-deleted rows.
- Soft delete: `deleted_at` set instead of hard delete; default queries exclude soft-deleted rows.

Indexes
- Index: `(solution_id, status)`
- Index: `(due_date)`
- Index: `(priority)`
- Unique: `(solution_id, subcomponent_name)`

## Progress Logic
- If `solution.status = 'complete'`, progress = 100%.
- Otherwise, derive enabled phases for the solution (`solution_phases.is_enabled = 1` ordered by `sequence_override` when set, else `phases.sequence`). If no phases are enabled, progress = 0 and `solution.current_phase` must be null.
- Progress when phases exist: `progress = ((position_of(current_phase) + 1) / enabled_phase_count) * 100`; if `current_phase` is null, progress = 0.
- Subcomponents do not contribute to phase/progress; they are tasks under the solution.

## Seed Data (optional)
- One sample project with abbreviation and active status.
- A solution under that project with an initial version.
- A few subcomponents spanning statuses and priorities to validate UI and filtering.

## Potential Enhancements
- Cached progress: optional numeric `progress` column on solutions (derived from enabled `current_phase` ordering) to speed board queries; recompute on phase/status change.
- Comments: add a `comments` table keyed to solutions and/or subcomponents for discussion history.

## Notes
- `updated_at` should be set via triggers or application logic on updates.
- Consider a soft unique constraint on `subcomponent_name` within a solution if naming collisions are a concern.
- Cascade deletes clean up dependent solutions/subcomponents when a project or solution is removed.
