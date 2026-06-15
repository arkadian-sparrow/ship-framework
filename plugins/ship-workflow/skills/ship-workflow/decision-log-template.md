# Decision log (per ticket)

Path: `<worktree>/tasks/ship/<ticket>.md`. Append to it as the loop runs, so
every briefing links to an auditable trail.

> Ephemeral by default — add `tasks/ship/` to your project's `.gitignore`, or
> commit it intentionally as an audit trail.

```
# <ticket> — ship log

## Tier
<trivial|standard|high-stakes> — <reasoning>

## Locked decisions (NON-NEGOTIABLE)
- <decision> — locked by the user <when>; do not re-open or drift without escalation

## Spec
<link>

## Audit (per lens)
- <lens>: <must-fix | nice-to-have | rejected> — <note>

## Pre-mortem
- <severity> <failure mode> → <mitigation>

## Plan
<link>

## Per-step review triage (REQUIRED — every step, every tier)
- Step <n>: reviewed [<diff scope>]; implemented [<…>]; rejected [<…> — why]

## Drift
- <finding> → <plan change or escalation>

## Escalations & decisions
- <trigger> → the user decided: <…>

## Lessons (lightweight)
- <what happened> → <takeaway for next time>
```
