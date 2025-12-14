# RACI Implementation Plan (Solution-Level, Text-Based)

Goal: capture clear ownership with minimal friction, aligned to the core hierarchy and governance needs (Sponsor at Project, Solution Owner + Key Stakeholder at Solution, Owner/Assignee/Approver at Subcomponent) without adding process noise or auth requirements yet.

Guiding fit:
- Clear ownership on every object (audit/credibility).
- Keep hierarchy shallow and obvious; avoid over-engineering.
- Minimize fields to reduce friction; prefer conservative defaults and read-friendly displays.

## Scope (initial, per level)
- Project: single Accountable/Sponsor (required). No R/C/I at this level.
- Solution: Solution Owner (combined R+A, required) plus Key Stakeholder (Consulted, optional). No Informed at this level.
- Subcomponent: Owner (required, accountable) + Assignee (required, executing) + Approver (optional gate). No full R/C/I here.
- Identity: free-text (names/emails); no auth/user directory yet.

## RACI Basics (applied here)
- Responsible (R): does the work → Solution Owner at solution level; Subcomponent Assignee at execution level.
- Accountable (A): owns the outcome → Project Sponsor; Solution Owner; Subcomponent Owner (overall) and Approver for gate sign-off (optional).
- Consulted (C): input before action (“Key Stakeholder”) → optional on solutions.
- Informed (I): not collected in this iteration.
- Rules: one Accountable per object; keep C lean; clarify scope in notes if multiple people are implied.

## Data Model / API
- Projects: required `sponsor` text field. Include in CRUD and Projects CSV.
- Solutions: required `owner` (R+A) plus optional `key_stakeholder` text fields. Include in CRUD and Solutions CSV.
- Subcomponents: required `owner` (accountable), required `assignee` (executing), optional `approver` (gate). Include in CRUD and Subcomponents CSV.
- Schemas/Routes: accept/read/write per above; extend import/export columns; imports stay strict-first.

## Frontend
- Projects: required Sponsor input.
- Solutions: required Solution Owner input; optional Key Stakeholder (secondary/collapsible). Show in table/detail.
- Subcomponents: Owner (required) + Assignee (required) + Approver (optional); display effective ownership on Subcomponents/Master; optionally show inherited Solution Owner read-only.
- CSV: projects/solutions/subcomponents CSVs round-trip their respective fields.
- Validation: simple free-text; enforce required fields only.

## Testing
- API: create/update/read per-level fields; import/export round-trip.
- UI: edit/save/reload; verify display on Solutions and Subcomponents/Master.
- CSV: export → edit → import → verify values. 
