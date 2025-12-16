# Live Sync (Realtime Refresh)

Goal: keep open pages in sync when data changes elsewhere. When a user creates/edits/imports Projects, Solutions, or Subcomponents, other connected clients should refresh automatically without manual reload.

## Approach
- WebSocket push from backend to all connected browsers.
- Event payload: lightweight `{ "type": "refresh", "entity": "<projects|solutions|subcomponents|all>" }`.
- Frontend listens once per session; on message, calls `loadData()` (or targeted fetch) and updates the current view.
- Include simple reconnect/backoff for transient disconnects.

## Backend Tasks
- Add `/ws` endpoint using FastAPI WebSocket.
- Maintain a set of active connections; broadcast on change.
- Call notifier after: project/solution/subcomponent create/update/delete, phase updates, and CSV imports.
- Keep payloads small; no data in WS messages, just a signal to refetch.
- Guard against crashed connections (remove dead sockets on send failure).

## Frontend Tasks
- Open a WebSocket on page load (matching API host, ws:// or wss:// accordingly).
- On `message` with `type: "refresh"`, trigger `loadData()`; optionally limit to relevant views by `entity`.
- Add reconnect with short backoff (e.g., 1s→5s cap) and pause when `document.hidden` to reduce churn.
- Surface connection state subtly (optional): e.g., status pill “Live”/“Reconnecting…”.

## Events to Broadcast
- Projects: create, update, delete, import.
- Solutions: create, update, delete, phase enable/disable, import.
- Subcomponents: create, update, delete, import, checklist bulk update.
- Consider a default `entity: "all"` and more specific ones (`projects`, `solutions`, `subcomponents`) for later optimization.

## Fallback
- If WebSocket fails repeatedly, fall back to periodic polling (e.g., every 20–30s while visible).

## Risks / Checks
- Avoid WS endpoint clashes with existing routes; ensure CORS/host matches frontend origin.
- Ensure broadcasts don’t block request threads (fire-and-forget with exception handling).
- Verify import flows broadcast once per file, not per row, to avoid storms.
- Test multiple tabs: edits in one tab trigger refresh in others; ensure no infinite reload loops.

## Decisions (stability-first, low-overhead)
- Auth/Access: same-origin only; no extra auth header. If HTTPS, use `wss://` and rely on the host’s access controls.
- Broadcast granularity: send entity-specific events (`projects|solutions|subcomponents|all`). CSV imports emit a single `entity` event (not per row).
- Throttle/coalesce: guard broadcasts so multiple changes in one request emit one event; client ignores new refresh if one is already in-flight and debounces WS messages arriving within 500ms.
- Self-refresh duplication: client already refreshes after its own save; WS-triggered refreshes are debounced to avoid double-loads.
- Error handling: drop dead sockets on send failure to prevent leaks; cap reconnect backoff at 5s and pause when the tab is hidden.
- Fallback: after N (e.g., 5) consecutive WS failures, enable polling every ~30s until WS reconnects.
- Network/proxy: ensure reverse proxy allows WS upgrade; use `wss://` when the page is served over HTTPS to avoid mixed content.

## Testing Plan
- Start two browsers/tabs; make changes in one and verify the other updates.
- Import CSV for each entity; confirm a single refresh fires.
- Kill/restart backend while clients are open; confirm reconnect works and recovers.
- Toggle network offline/online in DevTools to verify fallback/reconnect behavior.
