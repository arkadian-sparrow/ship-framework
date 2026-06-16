---
name: ship-workflow
description: Use for any non-trivial coding task (feature, bugfix, refactor, migration) or when the user runs /ship. Runs a disciplined loop — brainstorm, plan, skeptical audit + pre-mortem, TDD, per-step review, drift check — and interrupts the user only to merge or for a real decision.
---

# ship-workflow

Autonomous engineering loop. For non-trivial coding, run this end-to-end and
interrupt the user only at the four escalation triggers. Pairs with the
recommended permission setup (see the plugin README: merges and pushes-to-main
gated, destructive ops denied, edits in shared main checkouts gated) so most work
runs hands-free while the dangerous moments still ask.

## 0. Worktree precondition (hard gate)

Before any code change or git op in a repo that uses worktrees: operate only in
the ticket's **isolated worktree**, never the main checkout. Run
`git worktree list`; if a worktree for the ticket exists, `cd` into it and assert
HEAD matches the expected branch; otherwise create one
(`git worktree add ../<repo>-<ticket> <branch>`) and work exclusively there. The
main checkout may be shared — other agents or sessions can shift HEAD under you.
Enforced by the `worktree-guard` PreToolUse hook (prompts on main-checkout edits
in worktree-using repos; honors the `SHIP_GUARD_EXCLUDE` env var for repos you
legitimately work in directly). A project's own CLAUDE.md may add stricter rules.

## 1. Classify the tier (announce it)

Signals: files touched · blast radius · reversibility · existing test coverage.
State `Tier: <x> — because …` up front. The user can override.

| Tier | What | Process |
|------|------|---------|
| **trivial** | typo / copy / comment / one-line config; low blast radius; trivially reversible | Skip ceremony: change → diff self-review → verify → merge still gated. No audit/pre-mortem. |
| **micro** | provably-equivalent / mechanical change — rename, import swap, dedup; behavior preserved and equivalence mechanically checkable | Skip the skeptic panel; **replace TDD (step 5) with an equivalence proof** — e.g. for a rename, `git diff --stat` shows only renames/moves; for a dedup or import-swap, the existing suite stays green + a diff review confirms no behavior change; brainstorm/plan collapse to a one-line "approach fixed". Keep the verification gate + the merge escalation. |
| **standard** | feature/bugfix in one subsystem, a few files, normal reversibility | Full loop, lean→standard skeptic panel. |
| **high-stakes** | schema/migration, auth/billing/security, cross-subsystem, data-destructive, public-facing-at-scale | Full loop, full 4-lens panel + an extra `superpowers:verification-before-completion` gate before the merge ping. |

**Code review is NON-SKIPPABLE at every tier** — only its *weight* scales (diff
self-review for trivial/micro; a focused structured review for standard;
dispatched `requesting-code-review` subagents for high-stakes or large diffs).
Skipping review is the #1 observed failure mode; the ready-to-merge briefing MUST
carry the review record (see step 6 + `briefing-template.md`), so its absence is
visible to the user even when no hook is enforcing it.

## 2. The loop (standard / high-stakes)

*If a `superpowers:` skill named below isn't installed, follow the step's name as
a checklist — the loop still works; you only lose that skill's scaffolding.*

1. **Brainstorm** — `superpowers:brainstorming` (right-sized) → spec. Batch
   clarifying questions via `AskUserQuestion`; never drip them one at a time.
2. **Spec audit + pre-mortem** — run the adaptive skeptic panel and the
   pre-mortem as parallel subagents (see `skeptic-panel.md`, `pre-mortem.md`).
   Synthesize must-fix / nice-to-have / rejected; a severe unmitigated risk →
   escalate. Revise the spec.
3. **Plan** — `superpowers:writing-plans` → step-by-step with tests. **Plans are
   prompts, not documents:** each step must be directly executable — exact files,
   complete code, exact commands — so an executor needs zero interpretation. No
   placeholders, no "figure out X later."
4. **Light plan audit** — sequencing / test-coverage / hidden-coupling only
   (not a second full panel).
5. **Execute per step** — `superpowers:executing-plans` (or
   `subagent-driven-development`) with `superpowers:test-driven-development`:
   write test → implement → green.
6. **Per-step review (NON-SKIPPABLE — every tier).** Review the diff for
   correctness, edge cases, and the risk classes the change touches — weight
   scales with tier (diff self-review for trivial/micro; a focused structured
   inline review for standard; dispatched `superpowers:requesting-code-review`
   subagents for high-stakes or large diffs). Then **triage** every finding via
   `superpowers:receiving-code-review`: implement all that survive verification;
   list rejected with a one-line why — never blind implement-all. Apply the
   **adversarial stance** (`skeptic-panel.md`): assume defects, never treat
   "compiles/tests-pass" as correctness, every finding gets a severity. **Record
   the review (scope · findings · triage)** in the decision log and the
   ready-to-merge briefing. No review record → the step is not done.
7. **Drift check** — compare code to plan; a material change to future steps →
   escalate; otherwise update the plan and continue.
8. **Step done — green before the PR.** `superpowers:verification-before-completion`:
   the unit-test suite, typecheck, and lint must be **green** before you open or
   merge a PR — never open a red PR. For high-stakes this is the extra gate. Then
   escalate the ready-to-merge briefing — which **MUST include the step-6 review
   record + the green-check evidence** (no review record → the step isn't done) —
   and wait for the user. *Hooks confirm a check ran, not that it passed; the real
   all-green gate is GitHub branch protection + required status checks (see README).*

## 3. Skeptic panel + pre-mortem

Adaptive lenses mapped to the decision type, always ≥1 dedicated red-team lens,
dispatched as parallel subagents (use the bundled `ship-auditor` agent — it is
read-only). See `skeptic-panel.md` and `pre-mortem.md`.

## 4. Escalation — the only stops (everything else auto-continues)

Interrupt the user — with a briefing (`briefing-template.md`) — only when:

1. **Ready to merge** — step complete; the suite, typecheck, and lint are green (never open a red PR).
2. **Real fork / design decision** — a branching path needs the user's call.
3. **Drift changes the plan** — implementation materially alters future steps.
4. **Stuck or severe risk** — can't get a step green after honest attempts, or a
   severe unmitigated risk surfaced.

Hard caps (anti-thrash): ≤3 honest attempts per step before a "stuck"
escalation; ≤1 automatic re-plan before escalating drift.

## 5. Briefing + decision log

Every escalation uses the phone-friendly briefing (`briefing-template.md`):
TL;DR · context · options with panel verdicts + pre-mortem already run ·
recommendation + why · decision-log link. Maintain the per-ticket trail
(`decision-log-template.md`, written to `tasks/ship/<ticket>.md`) so every
briefing is backed by an auditable record. The log is ephemeral by default —
add `tasks/ship/` to your project's `.gitignore`, or commit it intentionally as
an audit trail.

Decisions the user **locks** are NON-NEGOTIABLE — record them under "Locked
decisions" in the log; never re-litigate or quietly drift from them. Changing a
locked decision is a real fork → escalate.

## 6. Capture lessons (lightweight)

When the user corrects you, a review finding recurs, drift changes the plan, a
process step didn't fit, or a pre-mortem risk comes true — record a one-line
lesson in the decision log (`tasks/ship/<ticket>.md`) so the pattern is visible
next time. Don't log routine successes. (A fuller version of this framework adds
an automated, cross-session learning loop; this core ships the manual habit.)

## 7. Resumability

The handoff hooks make a run resumable across sessions. At milestones (tier set ·
step done · a decision · the next action known) record the state so a future
session can pick up — the `/ship` orchestrator does this for you:

```bash
echo '{"ticket":"<t>","status":"<step>","next_action":"<next>"}' \
  | python3 "${CLAUDE_PLUGIN_ROOT}"/hooks/handoff.py state --cwd "$PWD"
```

The PreCompact + throttled PostToolUse hooks snapshot that state plus git facts;
on a fresh session the SessionStart hook surfaces it and asks before resuming
(never auto-executes). Clear it when shipped:
`python3 "${CLAUDE_PLUGIN_ROOT}"/hooks/handoff.py clear --cwd "$PWD"`.
