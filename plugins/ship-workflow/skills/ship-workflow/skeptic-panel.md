# Skeptic panel

Run lenses as parallel subagents (`superpowers:dispatching-parallel-agents`).
Always include ≥1 dedicated **red-team** lens whose only job is to find why this
fails.

## Decision-type → lenses

| Decision type | Lenses |
|---|---|
| **Technical plan** | staff-engineer · security/QA · maintainability/ops · product |
| **Product / scope** | PM · CEO · CTO · engineering |
| **Lean** (standard tier, low risk) | staff-engineer · red-teamer — escalate to the full four only at high-stakes |

## Per-lens subagent prompt (template)

> You are a skeptical **\<LENS>**. Read \<spec/plan paths>. Surface the strongest
> objections from your vantage only. Default to skeptical — assume it is flawed
> and prove it. Do NOT redesign. Return each concern as
> `{severity: high|med|low, rationale, suggested_mitigation}`. Be concise.

## Synthesis

Collect every concern and bin it:

- **must-fix** — high severity, or any severity with consensus across lenses.
- **nice-to-have** — real but optional; note and move on.
- **rejected** — out of scope / wrong / already handled (record the reason).

A **high-severity concern with no clear mitigation** is an escalation (a real
fork or a severe-risk briefing). Otherwise revise and continue.

## Adversarial stance (every lens + the §6 code review)

**FORCE stance:** assume the work contains defects. Starting hypothesis — this has
bugs, security gaps, or quality failures; surface what you can *prove*. Do NOT
validate that work was done.

**How reviewers go soft (catch yourself):**
- stopping at surface issues (a stray log, an empty `catch`) and assuming the rest is sound;
- accepting plausible-looking logic without tracing edge cases — nulls, empty collections, boundary values, error paths;
- treating "it compiles" / "tests pass" as evidence of *correctness*;
- reading only the file under review, not the functions it calls (which may carry the bug);
- downgrading a real BLOCKER to a WARNING to avoid seeming harsh.

**Output rule:** every finding carries a severity (must-fix / nice-to-have /
rejected). A finding without a severity is not valid output. Where mechanical
facts exist (grep / build / test output), treat them as ground truth the
narrative must build on, never contradict.

## Dispatch discipline (every subagent)

Spawn each lens as the **`ship-auditor`** agent type (read-only — it cannot edit
or mutate). In the prompt give it:
- `<required_reading>` — the exact files to load FIRST as primary context.
- `<structural_findings>` — mechanical facts already gathered (grep / build / test
  output) to treat as ground truth, so its narrative builds on them.
- a **context budget**: read those files and grep for specifics; do NOT slurp huge
  files (>~1000 lines) wholesale — load the relevant slices on demand.
