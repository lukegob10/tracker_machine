# Upload/Download for Projects, Solutions, Subcomponents

Goal: round-trip CSV import/export for the three core entities to bulk load and maintain cross-linked data using names (not IDs). Import should be idempotent where possible and create missing parents automatically.

## Scope
- Export: CSV for Projects, Solutions, Subcomponents with human-friendly headers. Includes relational columns by name (e.g., project_name on Solutions).
- Import: CSV ingest for each entity; uses names to find/create parents. Supports upsert-like behavior without IDs.
- Relationships: importing a child can create its missing parent(s) by name.

## File Shapes
- Projects CSV
  - Columns: project_name (req), name_abbreviation (req, 4 chars), status, description
- Solutions CSV
  - Columns: project_name (req), solution_name (req), version (req), status, description
- Subcomponents CSV
  - Columns: project_name (req), solution_name (req), version (optional, defaults to 0.1.0), subcomponent_name (req), status, priority, due_date (YYYY-MM-DD), sub_phase, description, notes
  - Optional: category, dependencies, work_estimate

## Import Behavior (implemented)
- Matching
  - Projects: match by project_name; if not found, create.
  - Solutions: match within project by (solution_name, version); if project_name missing in DB, create project first (needs a rule for name_abbreviation fallback, e.g., slug/first 4 chars).
  - Subcomponents: match within solution by subcomponent_name; if project/solution missing, create them.
- Status normalization: accept case-insensitive, underscore/space-insensitive values; map to enum values.
- Upsert rules: update editable fields when a match is found; otherwise create.
- Phases: if sub_phase provided, validate against enabled phases; if missing phases, enable all defaults when creating a new solution.
- User attribution: continue to stamp `user_id` from server/env (no client override yet).
- Validation: collect per-row errors and continue processing others; return a summary report.
- Duplication checks:
  - Within the same CSV: detect duplicate keys (e.g., same project_name; same project_name + solution_name + version; same project_name + solution_name + subcomponent_name) and report them. Process the first occurrence, treat later ones as errors to avoid silent overwrites.
  - Against DB: upsert behavior prevents silent loss—existing matches are updated, new ones created; conflicts are reported per-row.
- Policy: strict-first. Later duplicates within the same CSV are rejected (error) rather than “last wins,” to prevent accidental overwrites.
- Defaults/derivations:
  - Project abbreviation when missing: take the first 4 alphanumerics of project_name uppercased; pad with `X` if shorter; if collision, suffix with a digit sequence (e.g., ABCD1).
  - Solution version default when creating via subcomponent import: `0.1.0`.
  - Status defaults: project/solution → `not_started`; subcomponent → `to_do`; priority → `3`.

## Export Behavior
- One CSV per entity, using the above columns.
- Status values exported as enum slugs (e.g., `in_progress`); dates ISO (YYYY-MM-DD).
- Include project_name on Solutions/Subcomponents and solution_name on Subcomponents for context.

## API Surface (live)
- Projects: `POST /projects/import` (CSV upload), `GET /projects/export` (CSV download)
- Solutions: `POST /solutions/import`, `GET /solutions/export`
- Subcomponents: `POST /subcomponents/import`, `GET /subcomponents/export`
- Consider a combined import that accepts a zip with three CSVs, processed in order (projects → solutions → subcomponents).

## UI Hooks (live)
- Upload buttons on each view (Projects, Solutions, Subcomponents) to select CSV and show a result summary.
- Download buttons to fetch current data CSV.
- Display import report: counts (created/updated/skipped/errors) and per-row issues.

## Edge Cases & Decisions
- Abbreviation generation for new projects: derive from name (first 4 alphanumerics uppercased) if not provided; ensure uniqueness with suffix.
- Version when creating a solution from a subcomponent import: default `0.1.0` if absent.
- Priority default: 3 if missing; clamp to 0–5.
- Duplicates within the same CSV: process sequentially; later rows update earlier-created records.
- Transaction model: per-row try/except to avoid one bad row blocking all.
- Large files: stream parsing to avoid memory issues; set reasonable row limits to prevent abuse.
- Phase enabling: when creating a new solution during import, enable all phases by default (mirroring current behavior).
- Dependencies column (if used): free text for now; no resolution during import.

## Testing Plan
- Happy paths: import new projects/solutions/subcomponents; then export and diff.
- Upserts: re-import with changed descriptions/status; ensure updates apply and no duplicates.
- Missing parents: subcomponent import creates project+solution.
- Validation: bad status, bad date, short abbreviation; ensure errors are reported and others proceed.
- Phase validation: sub_phase not enabled -> error; sub_phase null allowed.

## Follow-ons (optional)
- Allow client-supplied user id via header to attribute imports.
- Add combined import/export endpoints and UI.
- Add dry-run mode to preview changes without writing. 
