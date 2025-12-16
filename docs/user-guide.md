# Jira-lite User Guide (Frontend)

## Getting In
- Browse to the app URL (default: http://localhost:8000).
- Sign in with your SOEID + password. Create an account with SOEID (email auto-derives to `<soeid>@citi.com`) and a password. Use the toggle between Log in / Create account.
- After sign-in, you’ll see the app shell (sidebar, top status, views). If you see “Sign in required,” log in first.

## Navigation & Views
- Sidebar views: Deliverables, Dashboard, Projects, Solutions, Subcomponents, Swimlanes (Kanban), Calendar.
- Top bar: connection pill (Online/Error), current user, Logout, theme toggle (dark/light).
- Status pills or alerts show load errors; try reloading if needed.

## Filters & Search
- Deliverables filters: Status, Project, Current Phase, Priority ≤, Owner, Assignee, text search. Filters update instantly.
- Other views have entity-specific filters (e.g., tables can be sorted/filtered via headers/controls where shown).

## Projects
- Form: Project name, Abbreviation (4 chars), Sponsor (required), Status, Description, Success Criteria.
- Create: fill the form and click Save. New clears/loads into the form.
- Edit: click a row to load it into the form, change fields, Save.
- CSV: Download/Upload buttons; upload results show success/errors.
- Table shows Project, Abbrev, Sponsor, Status.

## Solutions
- Form: Project (select), Solution name, Version, Status, Priority, Due Date, Current Phase, Owner (required), Assignee/Approver (optional), Key Stakeholder (optional), Description, Success Criteria, Blockers, Risks, plus RAG (see below).
- RAG (Solutions):
  - Default is **Auto** (conservative): Amber unless Complete (Green), Abandoned (Red), or Due Date is set and overdue (Red).
  - Switch to **Manual** to set Red/Amber/Green yourself; a reason is required.
  - Switch back to **Auto** to reset and let the system recompute.
- Create: select a Project, fill fields, Save.
- Edit: click a row to load, edit, Save.
- Phases: use the phase checklist under the table to enable/disable phases per solution (this controls which phases can be selected as Current Phase).
- CSV: Download/Upload available.
- Table shows Solution, Project, Version, Owner, Assignee, Phase, Due, RAG, Status.

## Subcomponents
- Subcomponents are optional task rows under a Solution.
- Form: Project, Solution, Task name, Priority (0–5), Due Date, Status, Assignee (required).
- Create: select Project + Solution, fill required fields, Save.
- Edit: click a row to load, edit, Save.
- CSV: Download/Upload available.
- Table shows Task, Project, Solution, Assignee, Status, Priority, Due.

## Deliverables
- Unified table across all solutions with project context.
- Columns include Project, Sponsor, Solution, Version, Owner, Assignee, Current Phase, Priority, Due, RAG, Status, Progress.
- Use filters to answer “who owns this?” or narrow by phase/priority.

## Kanban (Swimlanes)
- Groups solutions by project, then shows cards by phase group (derived from Current Phase).
- Each card shows solution name/version, owner/assignee, priority, phase, due date, and status. Empty columns show “Empty.”

## Calendar
- Groups solutions by due date.
- Entries show solution name, status, Owner, Assignee.

## Dashboard
- Summary cards: counts (projects, solutions, subcomponents), overdue, active, complete, on hold, no due date, avg priority.
- Summaries for projects/solutions and “attention”/“upcoming” panels.

## CSV Import/Export
- Projects: import/export button on Projects view.
- Solutions: import/export button on Solutions view.
- Subcomponents: import/export button on Subcomponents view.
- After upload, review the result message for created/updated counts and errors.

## Live Updates
- Websocket auto-refreshes data when changes occur; if it disconnects, status pill shows warning and retries.

## Troubleshooting
- 401/unauthenticated: log in again; ensure cookies are allowed for the app host.
- Validation errors: check required fields (Sponsor on projects; Owner on solutions; Assignee on subcomponents; abbreviation = 4 chars; priority 0–5).
- CSV errors: check header names and required fields as shown in each view’s description.
