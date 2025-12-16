# Backlog Enhancement Prioritization (Flow & Durable Power Aligned)

**Objective**  
Embed the system into decision flow, regulatory comfort, and executive routines *before* expanding feature surface. Prioritize trust, interpretability, and unavoidable usage over sophistication.  
(Source: Backlog Enhancements) :contentReference[oaicite:0]{index=0}

---

## Phase 1 — Flow Lock-In (0–6 weeks)
*Make the system unavoidable for status, ownership, and decisions.*

1. **Blockers / Risks Callout + “Needs Attention”**
   - Lightweight blocker fields (owner, ETA)
   - Dashboard surfacing for immediate escalation

2. **One-Click Exec Summary Export**
   - PDF/PPT-ready snapshot with RAG, owners, blockers, next decisions
   - Locks distribution and eliminates shadow decks

---

## Phase 2 — Governance Gravity (6–12 weeks)
*Turn usage into institutional reliance.*

3. **CSV / Excel Import-Export Polish**
   - Prevalidated templates, import preview with errors
   - Lowers friction for cross-Treasury onboarding

4. **Owner Dashboards**
   - Owner-centric view of projects, blockers, approvals pending
   - Drives daily habit formation

5. **Dependency Visibility (“Blocked by”)**
   - Simple dependency tags with overdue warnings
   - Surfaces second-order risk and interaction failures

---

## Phase 3 — Control Without Bureaucracy (12–20 weeks)
*Add just enough process to satisfy governance—no more.*

6. **Approval Checkpoints**
   - “Awaiting Approval” status with approver attribution
   - Highlight overdue approvals

7. **Review Cadence (Monthly / Quarterly)**
    - Prompts: what moved / what didn’t / why
    - Rolling comparisons in dashboards

8. **Phase-Aware Signoff Workflow (Lightweight)**
    - Single approver, timestamp, note
    - Optional block on completion until signoff

---

## Phase 4 — Optional (Pull-Driven Only)
*Add only if adoption warrants.*

9. **Comment / Decision History**
10. **Light Notifications (Email / Teams)**
11. **Directory Assist (Owner Lookup)**

---

## Completed (Implemented)
- Conservative Auto-RAG (Solutions): default Amber; auto rules (Complete→Green, Abandoned/Overdue→Red); manual override requires reason; reset to auto supported.

---

## Guardrails (Non-Negotiable)
- No extra hierarchy levels (keep Project → Solution → Component)
- No Agile jargon
- Avoid heavy customization; prefer conservative defaults

---

## Dashboard Build Order
1. Executive / Sponsor (exportable snapshot)
2. PM / Delivery cockpit
3. “My Items” panel
4. Governance / Audit feed (after change log)
