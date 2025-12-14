# Design Focus Points for a Treasury-Focused Project Management Tool

## Purpose
This document defines the **non-negotiable thinking points** that should guide decisions as this tool evolves. It is intentionally opinionated and constrained. The goal is not to build a powerful system — it is to build a system that **gets adopted, trusted, and used daily** by treasury and finance users in a large-bank environment.

Success is defined as:
- Regular, habitual use (not mandated use)
- Credibility with senior stakeholders
- Low resistance from risk, audit, and governance functions
- Clear differentiation from Jira / Excel / MS Project

---

## 1. User Reality (Anchor Point)

### Who the user is
- Treasury, finance, risk, or operations professionals
- High domain expertise, low tolerance for tooling friction
- Lives in Outlook, Excel, PowerPoint, SharePoint, internal dashboards

### How they think about work
- Work is **approval-driven**, not throughput-driven
- Progress is measured by **risk reduction and sign-off**, not speed
- Deadlines matter, but **dependencies and blockers matter more**

### Design implication
> If the tool requires training, certification, or “process buy-in”, it will fail.

The system must feel:
- Obvious
- Calm
- Administrative, not performative

---

## 2. Conceptual Positioning (What This Tool Is — and Is Not)

### This tool IS:
- A **lightweight execution and governance tracker**
- A system of record for project truth
- A bridge between teams and senior management

### This tool IS NOT:
- A software delivery tool
- An Agile coaching platform
- A replacement for Excel modeling

### Design implication
> Borrow mechanics from Agile and Waterfall silently — never the language.

---

## 3. Core Structural Model (Protect This)

### Canonical hierarchy
- **Project** → outcome / initiative
- **Solution** → workstream / deliverable area
- **Subcomponent** → concrete unit of execution

This hierarchy must remain:
- Shallow
- Stable
- Intuitive

No additional layers unless forced by real usage data.

---

## 4. Lifecycle vs Status (Critical Separation)

### Lifecycle (Process Phases)
- Represent *how work is expected to progress*
- Phase-gated, auditable, review-friendly
- Examples: Draft → Review → Validation → Approval → Complete

### Status (Execution Truth)
- Represent *what is actually happening now*
- Must allow blocked, stalled, and backward movement
- Status is the **source of truth** for reporting

### Design implication
> Never let lifecycle position masquerade as progress.

---

## 5. Timeboxing Without Agile Theater

### What to include
- Solution-level review windows (monthly / quarterly)
- Clear period-over-period comparison
- Explicit questions: “What moved?”, “What didn’t?”, “Why?”

### What to avoid
- Sprint jargon
- Velocity
- Burndowns
- Commit theater

### Design implication
> Cadence should feel like governance, not ritual.

---

## 6. The Stickiness Rule (Why Users Come Back)

Users will return if the tool:
- Saves them time in status reporting
- Prevents unpleasant surprises
- Makes them look organized and credible

### High-stickiness features
- One-click status summaries
- Auto-generated exec-ready views
- Persistent comments and decision history

### Low-stickiness features (avoid)
- Deep customization
- Over-automation
- Complex workflows

---

## 7. Reporting That Doesn’t Lie

### Required views
- Project-level RAG status
- Solution-level progress and blockers
- Subcomponent-level execution truth

### Reporting principles
- Prefer **simple, conservative signals**
- Ambiguity should surface as Amber, not Green
- Forecasts should be directional, not precise

### Design implication
> A report that feels “too optimistic” will destroy trust.

---

## 8. Integration Into the User’s App Ecosystem

### Reality
This tool will not replace:
- Email
- Excel
- PowerPoint

### It must instead:
- Export cleanly
- Embed links cleanly
- Accept documents without friction

### Design implication
> Be a hub, not a destination island.

---

## 9. Governance, Risk, and Audit Compatibility

### Non-negotiables
- Clear ownership on every object
- Immutable history (who changed what, when)
- Explicit approval states

### Design implication
> If Risk and Audit don’t object, adoption accelerates.

---

## 10. Final Filter

Before building any feature, ask:

1. Will this materially increase daily or weekly active use?
2. Will this reduce status-reporting friction?
3. Will this make a senior stakeholder more comfortable?
4. Can this be explained in one sentence?

If the answer is “no” to two or more — **really think deeply on need**.

---

## Closing Principle

> **Simplicity earns adoption. Truth earns trust. Trust earns career capital.**

This tool should feel boring in the best possible way — predictable, reliable, and quietly indispensable.

