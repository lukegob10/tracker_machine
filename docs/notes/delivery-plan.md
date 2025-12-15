# Delivery Plan (Target: Jan 10)

## Pre-Delivery (now → Jan 10) — high-velocity solo mode
- **Fast pilot in dev (now):** Deploy to dev, invite a handful of friendly PMs/business/risk. Collect feedback in one list; triage daily; ship fixes in minutes/hours.
- **Scope guard:** Keep core stable; accept only critical/high-trust tweaks; push the rest to a post-launch backlog.
- **Data stability:** Move to a persistent DB (prefer Postgres/Oracle; PVC + WAL if SQLite). Seed baseline; enable daily backups.
- **Hardening:** HTTPS via nginx/Traefik + TLS; basic/reverse-proxy auth; disable debug/docs on prod.
- **Perf sanity:** DB WAL/timeout (SQLite) or tuned pool (Postgres/Oracle). 10–20 user smoke: CRUD + CSV + phase toggles.
- **QA pass (tight loop):** CRUD across Project/Solution/Component, RACI fields, phase toggles, CSV round-trip, dashboard labels (Component/Sponsor/Owner), dark/light toggle, selection persistence.
- **Runbook:** Start/stop commands, env vars (API base, DB URL, ports, user-id default), backup/restore steps, log locations.
- **Collateral:** 1-page “How to use” (hierarchy, ownership rules, blockers/approvals, CSV templates), 5-slide exec summary (problem → live now → impact → limits → roadmap).
- **Mini-freeze:** Last 2–3 days pre-Jan 10 for regressions/hardening only.
- **Stretch (if time allows):** 
  - Minimal change log (who/when/what for status/ownership/phase) surfaced per item.
  - Exec-ready summary export (PDF/PowerPoint-friendly) with RAG, owners, blockers.
  - Phase-aware signoff flag (Awaiting/Approved/Rejected) with approver/date/note; highlight overdue signoffs.
  - Automate daily backup/restore script and verify once.

## Delivery Day (Jan 10)
- Deploy with scripted steps; verify health check, auth, HTTPS, and a smoke (create/edit/export).
- Share access + quickstart + templates; run a 30–60 min onboarding with pilot teams.
- Announce known limits (single node, light auth, SQLite contention if applicable).

## Immediate Post-Delivery (Weeks 1–2)
- **Support:** Daily check-ins with pilot users; fix only critical bugs.
- **Metrics:** Active users, items created, import/export usage, time-to-approval (if captured), errors.
- **Feedback:** Weekly 15-min huddle; log issues/enhancements; keep scope tight.

## Stabilization (Weeks 3–4)
- Patch critical bugs; no new features.
- Test backup/restore.
- Prep adoption story: before/after on reporting time, ownership clarity, reduced escalations.

## Formalize & Scale
- Light governance: name a backup owner; document “how we work” (ownership rules, blockers/approvals, CSV guardrails).
- Exec brief: show metrics/impact; propose next steps (change log, signoff workflow, exec-ready export); formalize ownership under your role.
