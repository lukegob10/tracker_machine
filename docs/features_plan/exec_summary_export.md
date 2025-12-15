# Exec Summary Export Plan (One-Click)

## Goal
Generate a PDF/PPT-ready snapshot with RAG status, owners, blockers, and next decisions to eliminate manual “shadow decks.”

## Output
- Format: PDF (first), with a simple slide-like layout. Consider PPTX export later via a library if required.
- Contents (per run):
  - Title block with timestamp, generator, and optional project/portfolio scope.
  - RAG summary: overall RAG + counts by status for projects/solutions/subcomponents.
  - Ownership: key owners (Sponsors, Solution Owners, Component Owners/Assignees).
  - Blockers: top N open blockers/issues (if no blockers field exists, use “on_hold/abandoned” items with notes).
  - Next decisions: top N upcoming items (due soon) and explicit “next decision” notes if available.
  - Key metrics: counts, overdue items, in-progress, complete.
  - Filters applied (scope, date, owner) for traceability.

## Scope / Data Sources
- Projects: name, sponsor, status.
- Solutions: name, project, owner, status, version.
- Subcomponents: name, project, solution, owner, assignee, status, priority, due_date, sub_phase, notes.
- Blockers proxy: subcomponents with status `on_hold`/`abandoned` and any non-empty notes.
- Upcoming decisions proxy: subcomponents with due dates in next X days and status not complete/abandoned; optionally surface “notes” as decision text.
- RAG: derive from statuses (default mapping: complete=Green; active/in_progress=Green; on_hold=Amber; to_do/not_started=Amber; abandoned=Red). Make mapping configurable later.

## API / Backend
- Add export endpoint: `GET /api/exec-summary?project_id=&owner=&assignee=&due_before=&status=` returning a PDF (content-disposition attachment).
- Implementation: server-side render (e.g., HTML → PDF with a library like WeasyPrint or reportlab). If adding a new dep is off-scope, start with a simplified HTML/PDF response.
- Include filter echo in the payload/footers.
- Keep it read-only; requires auth.

## Frontend
- Add “Export Exec Summary” button (e.g., topbar) that calls the endpoint and downloads the PDF. Optional filter modal to scope by project/owner/date.
- Show a toast/spinner while generating; handle errors gracefully.

## RAG/Content Rules (initial)
- Overall RAG: worst-of child statuses (Red > Amber > Green).
- Blockers list: up to 5 items; include owner, note, and age.
- Next decisions: up to 5 items due in next 14 days; include owner and due date.
- Ownership: list top owners by count of active items.

## Security
- Auth required; same session as app.
- No PII expected; keep within app data.

## Testing
- Backend: endpoint returns 200 with a PDF; respects filters; includes timestamp/filter metadata.
- RAG logic unit tests (status → RAG, overall rollup).
- Frontend: download works, filename includes timestamp.

## Open Questions
- Preferred RAG mapping and thresholds?
- Do we need PPTX as a first-class format, or is PDF sufficient?
- Should blockers/decisions draw from a dedicated field, or is status/notes proxy acceptable?
