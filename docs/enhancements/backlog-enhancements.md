# Backlog Enhancements (Principle-Aligned)

These items are prioritized to increase stickiness, credibility, and governance clarity without bloating the workflow.

## Near-Term (low friction, high trust)
- **Immutable change log:** capture who changed status/ownership/phase, when, and old→new values (visible per Project/Solution/Subcomponent). Drives audit comfort and team trust.
- **One-click exec summary export:** PDF/PowerPoint-ready snapshot of Projects/Solutions with RAG, owners, blockers, and next decisions. Saves status-report time.
- **Blockers/risks callout:** lightweight fields on Solutions and Subcomponents to mark blocker/owner/ETA; surfaced in dashboard “Needs Attention.”
- **Ownership surfacing:** show Sponsor/Solution Owner/Component Owner inline on cards/tables; filter by owner to answer “whose item is this?” quickly.
- **CSV/Excel polish:** prevalidated template download (with required columns highlighted) and import preview that lists errors before commit.

## Mid-Term (governance and reporting depth)
- **Review cadence:** optional Solution-level review window (monthly/quarterly) with “what moved/what didn’t/why” prompts; rolling comparison in dashboard.
- **Approval checkpoints:** explicit “Awaiting Approval” status flag per Subcomponent with Approver attribution; highlight overdue approvals.
- **RAG at Project/Solution:** conservative auto-RAG (default Amber unless status/risks justify Green), editable with reason text.
- **Dependency visibility:** simple dependency tags and “blocked by” chips in tables/cards; warn when a dependency is overdue.
- **Owner dashboards:** owner-centric view showing their Projects/Solutions/Subcomponents, blockers, and approvals pending.
- **Signoff workflow (phase-aware):** lightweight approvals tied to phases/subphases with a single Approver, date, and note. Default “Awaiting Signoff” when entering an approval-required phase; track Approved/Rejected with timestamp/user. Show overdue signoffs in dashboards and block “complete” until approval recorded (configurable per solution).

## Later (only if adoption warrants)
- **Comment/decision history:** threaded notes with timestamp/user; helps narrative for audits and execs.
- **Light notifications:** email/Teams webhook for critical changes (blocker added, approval requested/overdue) configurable per user.
- **Directory assist:** optional lookup/autocomplete for owners/approvers from company directory (keeps fields free-text until enabled).

## Guardrails (do not add unless forced)
- No extra hierarchy levels; keep Project→Solution→Component.
- No Agile jargon (sprints/velocity/burndown).
- Avoid heavy customization; prefer clear defaults and conservative signals.

## Dashboards (high-impact)
- **Executive/Sponsor:**
  - Projects by RAG (derived from status + overdue counts), showing Sponsor/Solution Owner.
  - Top blockers (notes/description) and awaiting vs approved signoffs (when available).
  - Upcoming vs overdue milestones (due dates), with counts per project.
  - Exportable snapshot for exec updates.
- **PM/Delivery:**
  - Phase progress by Solution (% complete by enabled phases).
  - Overdue and due-this-week Components; items with no due date.
  - Workload by Owner/Assignee split by status (to_do/in_progress/on_hold/complete).
  - Dependencies/blocked flags; highlight missing due dates.
- **Business/User (“My items”):**
  - Items where the user is Owner/Assignee by status and due date.
  - Attention list: oldest in_progress/on_hold, no-due-date items.
  - One-click CSV/PDF export of the user’s portfolio.
- **Governance/Audit:**
  - Recent changes feed (status/owner/phase) with who/when (needs change log).
  - Approval trail (awaiting/approved/rejected) once signoff exists.
  - Data-quality gaps: missing Owner/Assignee/Sponsor/due date; duplicate-name flags.
- **Build order:** 1) Exec summary; 2) PM cockpit; 3) My items panel; 4) Audit/change feed after change log.
