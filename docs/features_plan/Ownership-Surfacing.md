# Ownership Surfacing Plan

## Goal
Make ownership obvious everywhere and enable “who owns this?” filtering across projects, solutions, and subcomponents.

## Scope
- Display owners inline in all core views.
- Add owner-based filters per entity.
- Keep roles consistent: Project = Sponsor; Solution = Owner; Subcomponent = Owner (accountable) and Assignee (executor).

## UI Changes
- Master List: add columns/pills for Sponsor (project), Solution Owner, Subcomponent Owner, Assignee; add filters for Owner and Assignee.
- Projects view: show Sponsor column; add Sponsor filter; ensure Sponsor field is prominent in the form.
- Solutions view: show Owner column; add Owner filter; keep Owner required in the form.
- Subcomponents view: show Owner and Assignee columns; add filters for Owner and Assignee.
- Kanban: cards show Owner and Assignee; optionally include Sponsor/Solution Owner as small meta.
- Calendar: entries show Owner and Assignee.
- Dashboard: summary counts by Owner/Sponsor (optional), and “Owned by me” quick slice if user identity is available.
- Consistent labels: “Sponsor” (projects), “Solution Owner” (solutions), “Owner” and “Assignee” (subcomponents).

## API/Data
- No schema changes; use existing fields: `projects.sponsor`, `solutions.owner`, `subcomponents.owner`, `subcomponents.assignee`.
- Filtering: expose/query params for owner/assignee where missing:
  - Projects: filter by `sponsor`.
  - Solutions: filter by `owner`.
  - Subcomponents: filter by `owner` and `assignee` (and keep existing filters).

## Backend Tasks
- Add optional query params to list endpoints:
  - `/api/projects?sponsor=` (case-insensitive match).
  - `/api/projects/{project_id}/solutions?owner=`.
  - `/api/solutions/{solution_id}/subcomponents?owner=&assignee=`.
- Ensure existing responses include owner fields (they already do).

## Frontend Tasks
- Add filters and render owner fields in tables/cards:
  - Master list filter for Owner and Assignee; show Sponsor/Solution Owner/Owner/Assignee columns.
  - Projects table: add Sponsor column and filter.
  - Solutions table: add Owner column and filter.
  - Subcomponents table: add Owner/Assignee columns and filters.
  - Kanban/Calendar cards: include Owner/Assignee meta.
- Optional: “Mine” toggle to filter by current user’s name (if available from `/api/auth/me`).

## Testing
- Backend: verify new filters return expected rows; case-insensitive matches; existing filters unaffected.
- Frontend: filters combine with existing status/phase/dates; owner fields render in all views.

## Rollout
- Ship backend filters first (safe addition).
- Update frontend rendering and filters.

