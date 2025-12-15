# Data Model

SQLite schema for Jira-lite with projects, solutions, and subcomponents. All timestamps stored as ISO8601 in UTC. Foreign keys are enforced (`PRAGMA foreign_keys = ON`). Pair this reference with `docs/api-documentation.md` for routes/payloads and `docs/ui-overview.md` for how the UI exercises these fields.

User attribution: `user_id` is auto-populated server-side (currently the server account or `JIRA_LITE_USER_ID`/`USER`/`USERNAME`/`LOGNAME` if set); clients do not pass it yet.

## Entities at a Glance
- Project: top-level container with name, 4-char abbreviation, status, description, and a required Sponsor; stores `project_id`, `user_id`, timestamps, and soft delete metadata but those fields are not surfaced in the UI.
- Solution: versioned deliverable that belongs to a project; carries required Solution Owner (R+A) and optional Key Stakeholder (Consulted); can enable/disable phases to fit its workflow; stores `solution_id`, `user_id`, timestamps, and soft delete metadata.
- Subcomponent: granular work item belonging to a project + solution; prioritized with status, priority, due date, and a `sub_phase` (phase slug) that drives progress; also captures Owner (accountable), Assignee (executing), and optional Approver (gate); optional per-phase checklist for UX; stores `subcomponent_id`, `user_id`, timestamps, and soft delete metadata.

## Table Definitions (simplified)

### projects
| Field             | Type     | Description                 |
| ----------------- | -------- | --------------------------- |
| project_id        | TEXT     | UUID                        |
| project_name      | TEXT     | Display name (unique)       |
| name_abbreviation | TEXT     | 4-character code            |
| status            | TEXT     | Project lifecycle status    |
| description       | TEXT     | Project summary             |
| sponsor           | TEXT     | Accountable/Sponsor (required) |
| user_id           | TEXT     | Owner/user reference        |
| created_at        | DATETIME | Created timestamp           |
| updated_at        | DATETIME | Last updated timestamp      |
| deleted_at        | DATETIME | Soft delete timestamp       |

Allowed values
- status: `not_started`, `active`, `on_hold`, `complete`, `abandoned`
- check: enforce `name_abbreviation` length = 4 via validation/constraint

Validation & Defaults
- Required: `project_name`, `name_abbreviation`, `status`, `sponsor`; `description` optional.
- Defaults: `status` defaults to `not_started`; `sponsor` must be provided on create/import (UI-enforced; server stores empty string only for legacy/import edge cases).
- Normalization: enforce `name_abbreviation` length = 4; optionally uppercase in validation.
- Soft delete: `deleted_at` set instead of hard delete; default queries exclude soft-deleted rows.

Indexes
- Unique: `project_name`
- Index: `status`

### solutions
| Field          | Type     | Description                 |
| -------------- | -------- | --------------------------- |
| solution_id    | TEXT     | UUID                        |
| solution_name  | TEXT     | Name within project         |
| project_id     | TEXT     | FK to project               |
| version        | TEXT     | Version string (e.g., 0.1.0)|
| status         | TEXT     | Solution lifecycle status   |
| description    | TEXT     | Summary/notes               |
| owner          | TEXT     | Solution Owner (R + A, required) |
| key_stakeholder| TEXT     | Consulted stakeholder (optional) |
| user_id        | TEXT     | Owner/user reference        |
| created_at     | DATETIME | Created timestamp           |
| updated_at     | DATETIME | Last updated timestamp      |
| deleted_at     | DATETIME | Soft delete timestamp       |

Allowed values
- status: `not_started`, `active`, `on_hold`, `complete`, `abandoned`

Validation & Defaults
- Required: `project_id`, `solution_name`, `version`, `status`, `owner`; `description` optional; `key_stakeholder` optional.
- Defaults: `status` defaults to `not_started`; `owner` required in UI/CSV; `key_stakeholder` may be null/blank.
- Uniqueness: `(project_id, solution_name, version)` must be unique among non-deleted rows.

Indexes
- Unique: `(project_id, solution_name, version)`
- Index: `(project_id, status)`

### phases (lookup)
| Field       | Type     | Description                        |
| ----------- | -------- | ---------------------------------- |
| phase_id    | TEXT     | Slug/UUID used as `sub_phase` value|
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
- Disabling a phase should also remove/update related checklist rows.

Best-practice rollup (simple):
- `phases` holds the canonical ordered list.
- `solution_phases` turns phases on/off per solution and can override order.
- `subcomponent_phase_status` creates one row per enabled phase per subcomponent to show/check completion; `sub_phase` on `subcomponents` marks the current active phase and drives progress.

### subcomponent_phase_status (per-subcomponent phase checklist)
| Field                 | Type     | Description                                      |
| --------------------- | -------- | ------------------------------------------------ |
| subcomponent_phase_id | TEXT     | UUID                                             |
| subcomponent_id       | TEXT     | FK to subcomponents                              |
| solution_phase_id     | TEXT     | FK to solution_phases (enabled phase for solution)|
| phase_id              | TEXT     | FK to phases (denormalized for easier joins)     |
| is_complete           | INTEGER  | 0/1 flag; checked when phase is done             |
| completed_at          | DATETIME | When the phase was checked complete              |
| created_at            | DATETIME | Created timestamp                                |
| updated_at            | DATETIME | Last updated timestamp                           |

Indexes
- Unique: `(subcomponent_id, solution_phase_id)`
- Index: `(subcomponent_id, is_complete)`
- Index: `(subcomponent_id, phase_id)`

Validation & Defaults
- Required: `subcomponent_id`, `solution_phase_id`; both must exist.
- Defaults: `is_complete` defaults to 0; `completed_at` required only when `is_complete = 1`.
- Keep rows in sync when phases are enabled/disabled or when `sub_phase` changes.

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
| sub_phase         | TEXT     | Phase slug (FK to phases.phase_id) for current/active phase |
| description       | TEXT     | Summary                         |
| notes             | TEXT     | Freeform notes                  |
| category          | TEXT     | Optional category               |
| dependencies      | TEXT     | Related subcomponent IDs/list   |
| work_estimate     | REAL     | Estimate (hours/points)         |
| owner             | TEXT     | Accountable owner (required)    |
| assignee          | TEXT     | Executing individual (required) |
| approver          | TEXT     | Gate/approver (optional)        |
| created_at        | DATETIME | Created timestamp               |
| updated_at        | DATETIME | Last updated timestamp          |
| completed_at      | DATETIME | When marked complete            |
| user_id           | TEXT     | Owner/user reference            |
| deleted_at        | DATETIME | Soft delete timestamp           |

Allowed values
- status: `to_do`, `in_progress`, `on_hold`, `complete`, `abandoned`
- priority: `0` (highest) to `5` (lowest)
- sub_phase: slug from `phases.phase_id` (ordered by `sequence`; solutions can enable/disable via `solution_phases`)
  - Backlog: Backlog
  - Planning: Requirements, Controls & Scoping; Resourcing & Timeline; PoC; Delivery and Success Criteria
  - Development: Design, Build & Documentation; Sandbox Deployment; Socialization & Signoff
  - Deployment & Testing: Deployment Preparation; DEV Deployment; UAT Deployment; PROD Deployment
  - Closure: Go Live; Closure and Signoff; Handoff and offboarding
- Checklist: one `subcomponent_phase_status` row per enabled `solution_phase` to show phases and check off completion; keep the checked phase at or before the current `sub_phase`.

Validation & Defaults
- Required: `project_id`, `solution_id`, `subcomponent_name`, `status`, `owner`, `assignee`; `description` optional.
- Defaults: `status` defaults to `to_do`; `priority` defaults to 3 (mid); `owner`/`assignee` required in UI/CSV; `sub_phase` null when no phases are enabled.
- Constraints: `priority` must be between 0 and 5 inclusive; `sub_phase` must be one of the enabled phases for the solution when set.
- Progress state: if `status = complete`, set `completed_at` and `sub_phase` to the last enabled phase; reject `sub_phase` when no phases are enabled.
- Uniqueness: `(solution_id, subcomponent_name)` must be unique among non-deleted rows.
- Soft delete: `deleted_at` set instead of hard delete; default queries exclude soft-deleted rows.

Indexes
- Index: `(solution_id, status)`
- Index: `(solution_id, sub_phase)`
- Index: `(due_date)`
- Index: `(priority)`
- Unique: `(solution_id, subcomponent_name)`

## Progress Logic
- If `status = 'complete'`, progress = 100%.
- Otherwise, derive enabled phases for the solution (`solution_phases.is_enabled = 1` ordered by `sequence_override` when set, else `phases.sequence`). If no phases are enabled, progress = 0 and `sub_phase` should be null.
- Progress when phases exist: `progress = ((position_of(sub_phase) + 1) / enabled_phase_count) * 100`; if `sub_phase` is null, progress = 0.
- `subcomponent_phase_status` powers the checklist UI; keep rows in sync with enabled phases and `sub_phase` (phases at or before `sub_phase` can be checked).

## Seed Data (optional)
- One sample project with abbreviation and active status.
- A solution under that project with an initial version.
- A few subcomponents spanning statuses and priorities to validate UI and filtering.

## Potential Enhancements
- Cached progress: optional numeric `progress` column on subcomponents (derived from enabled `sub_phase` ordering) to speed board queries; recompute on phase/status change.
- Assignees: add `assignee_id` (user ref) on subcomponents to support ownership and filtering.
- Comments: add a `comments` table keyed to subcomponents for discussion history.

## Notes
- `updated_at` should be set via triggers or application logic on updates.
- Consider a soft unique constraint on `subcomponent_name` within a solution if naming collisions are a concern.
- Cascade deletes clean up dependent solutions/subcomponents when a project or solution is removed.
