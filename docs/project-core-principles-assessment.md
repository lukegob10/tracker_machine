# Project Core Principles Assessment

## Snapshot
- The core hierarchy (Project → Solution → Subcomponent) and lifecycle scaffolding via phases align with the structural intent, and the API is simple and discoverable.
- Biggest risks to adoption: governance/audit gaps, reporting that leans toward throughput metaphors (percent complete, Kanban) rather than approval/risk narratives, and a lack of executive-friendly outputs.
- Current UI branding and language (“Inventory Tool”, Kanban, Swimlanes) read as generic delivery tooling, not the calm treasury governance tracker described in the principles.

## Where We’re Aligned
- **Canonical hierarchy protected:** Project/Solution/Subcomponent enforced with uniqueness and soft deletes (backend/app/models.py, routes_* files); solution phases are enabled per solution by default (enable_all_phases) to keep a stable shallow model.
- **Lifecycle vs status separated in data model:** Global phases are seeded (backend/app/seed.py) and subcomponents validate sub_phase against enabled phases, preventing arbitrary phase drift (routes_subcomponents.py). Status enums capture execution truth separately from lifecycle.
- **Excel-friendly interoperability:** CSV import/export across projects/solutions/subcomponents (routes_* export/import) lowers friction with Excel/SharePoint workflows.
- **Lightweight stack and defaults:** No auth/setup required; sensible defaults (status defaults, abbreviation derivation, SAMPLE_SEED) reduce initial friction for pilots; WebSocket broadcast keeps views fresh without user effort.

## Gaps and Risks vs Principles
- **User reality & positioning (1–2):** UI copy and navigation (“Inventory Tool”, “Swimlanes”, “Kanban”) signal agile throughput tooling; no framing around approvals, sign-offs, or risk reduction that treasury users expect. Forms require many manual fields with little guidance/context.
- **Lifecycle vs status separation (4):** Frontend computes progress % from lifecycle (sub_phase) (frontend/js/app.js: orderedPhases/progress), so lifecycle position can masquerade as progress, contradicting principle 4. Checklist completion is not tied to progress or reporting, so status truth can still be overstated.
- **Timeboxing without agile theater (5):** No concept of monthly/quarterly review windows, period-over-period comparison, or “What moved/what didn’t?” prompts. Dashboard cards are throughput counts, not governance cadence.
- **Stickiness (6):** No one-click exec summaries, decision history, or comments. CSV round-trips are helpful but do not reduce status-reporting effort for leaders. No “make me look organized” outputs (PDF/PowerPoint/email summary).
- **Reporting that doesn’t lie (7):** Reporting is percent-complete and counts; no conservative signals (RAG), explicit blockers, or ambiguity surfacing as Amber. Overdue is the only risk signal. Complete status is allowed even if sub_phase/checklist isn’t reconciled.
- **Integration with existing ecosystem (8):** Only CSV import/export; no clean export to PowerPoint/Excel templates, no link/embed helpers, no document attachments.
- **Governance, risk, audit (9):** No immutable history, approvals, or ownership surfaced to users. user_id is auto-set but never updated on edits, and there is no change log. Soft deletes have no audit trail or cascade checks beyond manual filters. No explicit approval states or sign-offs on lifecycle transitions.
- **Final filter (10):** Some surfaced features (Kanban/Calendar views) may add noise without materially increasing DAU or reducing reporting friction; RACI (planned in docs/features_plan/raci-implementation.md) is not implemented, leaving ownership ambiguous.

## Prioritized Recommendations
1) **Reframe UI language and defaults to approval-driven governance:** Rename app and views to match treasury program tracking; replace “Kanban/Swimlanes” with “Lifecycle/Approvals”; emphasize sign-off states and blockers in tables and cards.
2) **Align reporting to conservative, trust-first signals:** Add RAG at project/solution levels, blocked/at-risk flags, and “What changed this period?” views; avoid using lifecycle-derived % as progress unless cross-checked with status/blockers.
3) **Introduce lightweight audit and ownership:** Persist user_id on create/update, add change log entries (who/what/when), and include explicit approval timestamps per phase; surface owner/approver per Project/Solution/Subcomponent.
4) **Add timeboxed review windows:** Support month/quarter slices with movement summaries (moved/not moved/why) and comparison to prior period; keep cadence labels governance-oriented, not sprint-themed.
5) **Deliver exec-ready outputs and integrations:** One-click exports to Excel/PPT/Email with conservative signals and history; allow attaching/reference docs/links to play nicely with Outlook/SharePoint.
6) **Implement RACI v1:** Add solution-level RACI fields per plan, surface read-only inheritance on subcomponents, and include in CSV import/export to clarify accountability immediately.
