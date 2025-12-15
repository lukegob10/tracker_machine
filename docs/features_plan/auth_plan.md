# Authentication Plan (Local-first with optional SSO)

## Goal
Add authentication so users must log in before accessing the app, with a simple login/create-account screen. Default to local accounts (username/email + password) to reduce integration friction; keep the design SSO-ready for future corporate IdP hookup.

## Scope (Phase 1: Local Auth)
- Add a `users` table and auth endpoints for register, login, logout, refresh, and current-user.
- Protect all existing API routes; require an authenticated user and propagate `user_id` from the request context (no more server default).
- Frontend: pre-app login page with toggle between “Log in” and “Create account”.
- Session model: short-lived access token + refresh token in HttpOnly cookies (JWT or signed sessions).
- Roles: start with `admin` vs `user` to permit future RBAC; default new users to `user`.

## Data Model Changes
- `users` table:
  - `user_id` (UUID), `soeid` (corp id, unique), `email` (derived: `<soeid>@citi.com`, unique), `display_name`, `password_hash`, `role` (`admin`|`user`), `is_active`, `failed_attempts`, `locked_until`, `created_at`, `updated_at`, `last_login_at`, optional `external_id` (for future SSO subject).
- Update existing tables to rely on authenticated `user_id` (no payload field from clients; server injects).

## Backend Endpoints (Phase 1)
- `POST /api/auth/register` → create user, returns sanitized user; requires email + password + display_name; role defaults to `user`.
- `POST /api/auth/login` → verify credentials; set HttpOnly `access` (short TTL) and `refresh` (longer TTL) cookies; return current user.
- `POST /api/auth/refresh` → rotate tokens using refresh cookie.
- `POST /api/auth/logout` → revoke/clear cookies.
- `GET /api/auth/me` → returns current user from token.
- All existing routes: require auth middleware to set `request.state.user` and reject unauthenticated (401).

## Security/Controls
- Password hashing: Argon2id (preferred) or bcrypt with strong work factor; never store plaintext; optional app-level pepper.
- Validation: minimum length, complexity per bank policy; block common passwords if feasible.
- Brute-force protection: increment `failed_attempts`, lockout after N tries for T minutes; add per-IP rate limiting at ingress if available.
- Session hardening: HttpOnly + Secure cookies, `SameSite=Lax` (or `Strict` if it doesn’t break), short access TTL (e.g., 15m), refresh TTL (e.g., 7d), rotation on refresh.
- CSRF: cookie-based auth requires CSRF token (double-submit or header-based with same-site strictness).
- Logging: log auth failures and lockouts; redact sensitive fields.

## Frontend Changes
- Add `/login` (or landing) view before app content; toggle between Login and Create Account.
- Store auth state (current user) in JS; call `/api/auth/me` on load; redirect to login if 401.
- Include CSRF token/header in mutating requests when using cookie auth.
- Show current user and a logout control in the app shell; block UI actions until authenticated.

## Middleware / Request Context
- Auth middleware extracts/validates access token, loads user (ensure `is_active`, not locked), sets `request.state.user`.
- All POST/PATCH/DELETE routes use `request.state.user.user_id` for `user_id` attribution; reject if missing.

## Migration Notes
- Add migration to create `users`.
- Create an initial admin user via env vars or one-time CLI (only when no users exist).
- Remove reliance on environment `JIRA_LITE_USER_ID` once auth is live; keep as a dev fallback flag if needed.

## Testing
- Unit: password hashing/verification, lockout logic, token issuance/rotation/expiry.
- Integration: unauthenticated requests return 401; authenticated requests succeed and set `user_id`; refresh rotates tokens; lockout after repeated failures.
- Frontend: login/registration flows, redirect to login on 401, logout clears state.

## SSO Readiness (Phase 2)
- Add `external_id` and `idp` fields to `users`; map IdP claims → user record; skip local password for SSO users.
- Token verification against IdP JWKS; user auto-provisioning (just-in-time) or SCIM sync.
- Decide precedence rules when the same email exists locally and in IdP.

## Notes
- If email isn’t wired up yet, start with admin/CLI password resets only and add email-based reset later once the mail path is validated.
