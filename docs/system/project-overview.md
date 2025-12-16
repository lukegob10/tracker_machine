# Jira-lite Project Overview (Comprehensive)

## Purpose and Value
- Lightweight tracker for Projects → Solutions → Subcomponents with phase-aware progress, CSV import/export, and a static UI. Optimized for small teams (10–25 users) and fast, low-dependency setup.
- Bank fit: keeps data local (SQLite by default), pure JSON APIs, soft deletes with timestamps, and no external SaaS dependencies in the baseline.

## Scope and Boundaries
- In scope: CRUD for projects/solutions/subcomponents; per-solution phase toggles and solution-level progress via `current_phase`; CSV import/export; cookie-based local auth; static frontend served by FastAPI.
- Out of scope today: RBAC, SSO/IdP integration, PII tagging, DLP, encryption at rest, audit log streaming to SIEM, backups/DR, HA/failover, workflow/approvals, notifications.

## Current Readiness (dev)
- AuthN/AuthZ: cookie-based local accounts using SOEID (email derived as `<soeid>@citi.com`). No RBAC/project scoping. Needs enterprise auth (OIDC/SAML/LDAP) and RBAC before production.
- Data/storage: SQLite by default (`db/app.db`), configurable via `JIRA_LITE_DATABASE_URL`; no at-rest encryption; no backups or retention policy.
- Observability: standard FastAPI logging only; no structured audit/event logs or metrics.
- Availability: single instance + SQLite; no clustering/replication; no DR plan.
- Compliance gaps: no secrets management, no change controls, no vulnerability management pipeline.

## Architecture and Runtime
- Backend: FastAPI + Uvicorn; routes under `/api`; health at `/health`; interactive docs at `/docs` and `/redoc`.
- Frontend: static HTML/JS served from `/frontend` mounted at `/`.
- Database: SQLite by default (`db/app.db`, configurable via `JIRA_LITE_DATABASE_URL`); tables auto-created on startup; phases seeded; optional sample data via `SAMPLE_SEED=true`.
- Packaging: Python dependencies in `backend/requirements.txt`; no container spec committed yet.

## High-level Architecture (Simplified)
```mermaid
flowchart LR
  Browser[User Browser<br/>(Static UI)]
  API[FastAPI App<br/>(serves UI + /api + /api/ws)]
  DB[(SQLite DB<br/>db/app.db)]

  Browser <-->|HTTP + WebSocket<br/>Auth cookies| API
  API <-->|SQLAlchemy / SQL| DB
```

## Data Model (summary; see `docs/data-model.md`)
- Projects: `project_name`, 4-char `name_abbreviation`, `status`, `description`, optional `success_criteria`, `sponsor` (required); soft delete; `user_id` set server-side.
- Solutions: belong to Project and are the primary trackable work item; `solution_name`, `version`, `status`, `priority`, optional `due_date`, optional `current_phase`, optional `success_criteria`, `owner` (required), optional `assignee/approver/key_stakeholder`, optional `blockers/risks`; soft delete; `completed_at` when done.
- Phases: global ordered list; per-solution enable/disable via `solution_phases`. Progress is derived from `solutions.current_phase` relative to enabled phases.
- Subcomponents: optional tasks under a Solution; minimal fields: `subcomponent_name`, `status`, `priority` (0–5), optional `due_date`, `assignee` (required); soft delete; `completed_at` when done.

## API Surface (see `docs/api-documentation.md`)
- Projects: `GET/POST/PATCH/DELETE /api/projects`; CSV `POST /api/projects/import`, `GET /api/projects/export`.
- Solutions: `GET /api/solutions` and `GET/POST /api/projects/{project_id}/solutions`, `GET/PATCH/DELETE /api/solutions/{solution_id}`; CSV import/export.
- Phases: `GET /api/phases`; per-solution toggles `GET/POST /api/solutions/{solution_id}/phases`.
- Subcomponents: `GET /api/subcomponents` and `GET/POST /api/solutions/{solution_id}/subcomponents`, `GET/PATCH/DELETE /api/subcomponents/{subcomponent_id}`; CSV import/export.
- Errors: JSON `{ "detail": "message" }`. Soft deletes hide rows from list/get.

## Frontend Flows (see `docs/ui-overview.md`)
- Projects view: enforce sponsor (projects) and abbreviation constraints.
- Solutions view: solution-first tracking (priority/due/current phase) with phase toggles per solution.
- Subcomponents view: optional tasks under a solution (assignee required).
- Deliverables, Swimlanes, and Calendar are solution-first (filters on status/project/current phase/priority/due).

## Positioning within a Bank Environment
- Data classification: currently untagged; assume non-PII until reviewed. No masking/DLP.
- Identity & access: must add SSO (OIDC/SAML), user accounts, roles (Admin/Editor/Viewer at minimum), and project-level scoping before production.
- Auditability: needs structured audit logs for auth, CRUD, imports/exports, and checklist changes; ship to SIEM.
- Security & secrets: add TLS termination, secrets manager for config, at-rest encryption (DB/files), and CSRF protection if forms evolve.
- Resilience: move to Postgres, add migrations, backups (PITR), DR runbook; deploy behind LB with health checks.
- Change management: CI with lint/tests, tagged releases, environment promotion, infra-as-code.
- Third-party exposure: none beyond Python packages; verify supply-chain scanning.

## Integration Hooks (future)
- Webhooks or message bus for downstream systems (e.g., GRC, reporting).
- Export formats: CSV exists; add PDF/Excel if governance requires.
- API tokens/keys once auth is in place.

## Risks and Gaps to Close for Enterprise Use
- No auth/RBAC; open endpoints.
- No encryption at rest or backups.
- No audit/event logging.
- Single-node SQLite; not HA.
- No vulnerability scanning policy beyond pinned requirements.
- No operational runbooks or DR/BCP.

## Roadmap (proposed)
- Short term: add auth + RBAC, switch to Postgres, implement audit logs, backups, and config via env/secret manager.
- Mid term: API tokens, webhooks, improved CSV validation, metrics/dashboard, SLOs.
- Long term: workflow/approvals, notifications, richer reporting, role-scoped sharing.

## Deployment Notes
- Dev: `uvicorn backend.app.main:app --reload` (API at `/api`, UI at `/`).
- Env vars: `SAMPLE_SEED=true` for demo data; `JIRA_LITE_USER_ID` to override user attribution; `JIRA_LITE_DATABASE_URL` to override the default SQLite path.
- Host: mount persistent volume for DB; lock file permissions; run behind HTTPS with TLS termination.

## Related Docs
- `docs/api-documentation.md`: canonical routes, payloads, CSV behaviors.
- `docs/data-model.md`: field definitions, enums, constraints.
- `docs/ui-overview.md`: UI flows and validation.
- `docs/project-core-principles-assessment.md`: delivery/quality guardrails.
