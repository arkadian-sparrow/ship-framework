# Pre-mortem

One subagent, dispatched alongside the skeptic panel.

## Prompt (template)

> Assume it is later and this work **shipped and then failed badly**. Read
> \<spec/plan paths>. Enumerate the most likely **failure modes** that caused it.
> For each, return `{severity: high|med|low, failure_mode, earliest_signal,
> mitigation}`. Be specific to this change, not generic. Do not redesign.

## Severity scale

- **high** — data loss, a security/billing breach, a user-facing outage, or
  anything irreversible.
- **med** — degraded but recoverable behavior; needs a follow-up.
- **low** — cosmetic, or easily caught later.

## Escalation threshold

Any **high-severity failure mode with no clear mitigation** → stop and escalate
(a severe-risk briefing). Otherwise fold the mitigations into the plan.
Pre-mortem output is recorded in the decision log.
