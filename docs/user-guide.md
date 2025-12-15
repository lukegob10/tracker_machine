# Jira-lite User Guide (Frontend)

## Getting In
- Browse to the app URL (default: http://localhost:8000).
- Sign in with your SOEID + password. Create an account with SOEID (email auto-derives to `<soeid>@citi.com`) and a password. Use the toggle between Log in / Create account.
- After sign-in, you’ll see the app shell (sidebar, top status, views). If you see “Sign in required,” log in first.

## Navigation & Views
- Sidebar views: Master List, Dashboard, Projects, Solutions, Subcomponents, Swimlanes (Kanban), Calendar.
- Top bar: connection pill (Online/Error), current user, Logout, theme toggle (dark/light).
- Status pills or alerts show load errors; try reloading if needed.

## Filters & Search
- Master List filters: Status, Project, Solution, Subphase, Priority ≤, Owner, Assignee, text search. Filters update instantly.
- Other views have entity-specific filters (e.g., tables can be sorted/filtered via headers/controls where shown).

## Projects
- Form: Project name, Abbreviation (4 chars), Sponsor (required), Status, Description.
- Create: fill the form and click Save. New clears/loads into the form.
- Edit: click a row to load it into the form, change fields, Save.
- CSV: Download/Upload buttons; upload results show success/errors.
- Table shows Project, Abbrev, Sponsor, Status.

## Solutions
- Form: Project (select), Solution name, Version, Status, Description, Owner (required), Key Stakeholder (optional).
- Create: select a Project, fill fields, Save.
- Edit: click a row to load, edit, Save.
- Phases: use the phase checklist under the table to enable/disable phases per solution.
- CSV: Download/Upload available.
- Table shows Solution, Project, Version, Owner, Key Stakeholder, Status.

## Subcomponents
- Form: Project, Solution, Subphase (enabled phases), Priority (0–5), Due Date, Status, Owner (required), Assignee (required), Approver (optional), Name, Description, Notes.
- Create: select Project + Solution, fill required fields, Save.
- Edit: click a row to load, edit, Save.
- CSV: Download/Upload available.
- Table shows Component, Project, Solution, Owner, Assignee, Status, Priority.

## Master List
- Unified table across all subcomponents with project/solution context.
- Columns include Project, Sponsor, Solution, Solution Owner, Subcomponent, Owner, Assignee, Subphase, Priority, Due, Status, Progress.
- Use filters to answer “who owns this?” or narrow by phase/priority/dates.

## Kanban (Swimlanes)
- Groups subcomponents by project → solution, then shows cards by phase group.
- Each card shows name, project/solution, owner/assignee, priority/status, due date. Empty columns show “Empty.”

## Calendar
- Groups subcomponents by due date.
- Entries show subcomponent name, status, Owner, Assignee.

## Dashboard
- Summary cards: counts (projects, solutions, subcomponents), overdue, in-progress, complete, on hold, no due date, avg priority.
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
- Validation errors: check required fields (Sponsor on projects; Owner on solutions; Owner/Assignee on subcomponents; abbreviation = 4 chars; priority 0–5).
- No phases: enable phases for a solution in the Solutions view before selecting a subphase on subcomponents.
- CSV errors: check header names and required fields as shown in each view’s description.
