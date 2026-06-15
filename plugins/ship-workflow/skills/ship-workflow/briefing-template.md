# Briefing template (phone-friendly)

Lead with the answer. Keep it skimmable on a phone.

---

**TL;DR** — \<1–2 lines: the situation and what I recommend>

**Context** — \<which step / decision, and why now>

**Options** (for a fork)

- **A — \<name>** · panel verdict: \<…> · pre-mortem: \<…>
- **B — \<name>** · panel verdict: \<…> · pre-mortem: \<…>

**Recommendation** — \<A/B>, because \<one line grounded in the panel>

**Decision log** — \<path to the per-ticket trail>

---

For a **ready-to-merge** briefing, "Options" becomes a short diff summary plus
the green-check evidence, and "Recommendation" is simply *merge* or *hold*.

It **must** also carry a **Review (required)** line:

> **Review** — \<what was reviewed (diff scope)> · \<findings> · \<triage:
> implemented / rejected + why>

A ready-to-merge briefing without a Review line is **incomplete** — do not merge.
This is what makes a skipped code review visible to the user when no hook is
enforcing it.
