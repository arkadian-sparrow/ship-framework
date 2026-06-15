# Ship Workflow

**Plan it. Prove it. Ship it.** — a disciplined, autonomous engineering loop for [Claude Code](https://claude.com/claude-code).

[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-D97757?style=for-the-badge)](https://claude.com/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/arkadian-sparrow/ship-framework?style=for-the-badge&logo=github&color=181717)](https://github.com/arkadian-sparrow/ship-framework)

Ship Workflow turns "go write some code" into the loop a senior engineer would actually run: brainstorm the spec, audit it adversarially, plan, build test-first, review every diff, and prove it works — then it interrupts you only to merge or to make a real decision. Everything else runs hands-free, behind safety rails that block a "done" claim with no evidence, keep parallel sessions from stomping each other, and resume your work after a restart.

## How it works

Every non-trivial change runs the same loop. Ceremony scales to the blast radius (a typo skips the audit; a migration gets the full panel), but the spine never changes.

```text
┌────────────────────────────────────────────────────────────┐
│       /ship <ticket>   ·   or any non-trivial change       │
└────────────────────────────────────────────────────────────┘
                              ↓                               
                      classify the tier                       
           trivial · micro · standard · high-stakes           
                              ↓                               
┌──────────────────  THE LOOP · per step  ───────────────────┐
│                                                            │
│  1 · brainstorm         →  a written spec                  │
│  2 · audit + pre-mortem →  skeptic panel + red-team lens   │
│  3 · plan               →  an executable "plan as a prompt"│
│  4 · build (TDD)        →  red → green → refactor          │
│  5 · review             →  adversarial · NON-SKIPPABLE     │
│  6 · drift check        →  re-plan, or escalate            │
│                                                            │
└────────────────────────────────────────────────────────────┘
                              ↓                               
            verify gate  ·  evidence before "done"            
                              ↓                               
┌───────  stop & brief you — the only four triggers  ────────┐
│  • ready to merge              • a real fork / decision    │
│  • drift changes the plan      • stuck, or a severe risk   │
└────────────────────────────────────────────────────────────┘

    always-on rails:   worktree-guard  ·  handoff / resume    
```

1. **Classify the tier** — `trivial · micro · standard · high-stakes`. The amount of process scales with the risk; the tier is announced up front and you can override it.
2. **Brainstorm → spec** — step back and pin down what's actually being built before any code.
3. **Audit + pre-mortem** — an adaptive skeptic panel (always with a dedicated red-team lens) and a pre-mortem run as read-only subagents, assuming the work is flawed and trying to prove it.
4. **Plan as a prompt** — a step-by-step plan executable with zero interpretation: exact files, exact commands, no "figure it out later."
5. **Build, test-first** — `red → green → refactor` per step.
6. **Review — non-skippable** — every diff is reviewed adversarially and every finding triaged (implemented, or rejected with a reason). A skipped review is made *visible* in the merge briefing, so it can't quietly vanish.
7. **Drift check** — if the implementation outgrows the plan, re-plan or escalate.
8. **Verify, then stop** — prove the checks actually ran, then surface a phone-friendly briefing and hand back control.

## Quickstart

Run inside Claude Code (not your host shell):

```
/plugin marketplace add arkadian-sparrow/ship-framework
/plugin install ship-workflow@ship-framework
```

Then **restart Claude Code** — hooks and agents load at session start. Kick off work with:

```
/ship <ticket or description>
```

…or just start a non-trivial task and the `ship-workflow` skill triggers on its own.

## What's inside

| Component | Type | What it does |
|---|---|---|
| `ship-workflow` | skill | The loop. Triggers on non-trivial work or `/ship`. |
| `/ship` | command | One-command orchestrator: resume-or-start → run the loop → clear. |
| `ship-auditor` | agent | Adversarial auditor powering the audit & pre-mortem lenses. No edit/write tools; uses Bash for read-only inspection only. |
| evidence gate | Stop hook | Blocks a "done" stop if code changed but no test/lint/typecheck/build ran since. |
| worktree guard | PreToolUse hook | Prompts before editing a shared *main* checkout in a repo that uses worktrees. |
| handoff / resume | hooks | Snapshots state + git facts on compact/edit; offers to resume on a fresh session. |

## Why it works

Most "AI just writes the code" failures are process failures. Ship Workflow targets the specific ones:

- **Skipped reviews** — the most common quality miss. Review is non-skippable at every tier, and its record is required in the merge briefing, so its *absence* is visible to you even when no hook is enforcing it.
- **"Done" with no proof** — the evidence gate refuses a stop after a code edit with no check run, so "it should work" never stands in for "the tests ran."
- **Parallel sessions stomping each other** — the worktree guard prompts before you edit a shared main checkout, instead of silently shifting HEAD under another session.
- **Lost context on `/compact` and restarts** — handoff/resume snapshots where you were and offers to pick it up, so a long task survives a context reset.
- **Unfocused, soft audits** — the skeptic panel and pre-mortem run as read-only subagents with a forced adversarial stance, every finding carrying a severity.

## Recommended setup

A plugin can't write your settings or your `CLAUDE.md`, so two optional pieces ship as copy-in snippets in [`docs/`](docs/):

1. **Permissions** — copy the `deny` / `ask` arrays from [`docs/recommended-permissions.json`](docs/recommended-permissions.json) into your `~/.claude/settings.json`. This gates merges and pushes, denies destructive ops, and (via `defaultMode: "auto"`) lets the loop run without a prompt on every step. Without it the workflow still works; you'll just approve more, and the safety denials won't be in force.
2. **CLAUDE.md nudge** — [`docs/CLAUDE-snippet.md`](docs/CLAUDE-snippet.md) adds an explicit "non-trivial coding → ship-workflow" instruction plus a general-conduct base layer. The skill auto-triggers without it, so this is reinforcement, not a requirement.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `SHIP_GUARD_EXCLUDE` | Colon-separated absolute repo roots the worktree guard should *not* prompt on (e.g. a multi-repo umbrella whose main checkout you work in directly). | nothing excluded |

```bash
export SHIP_GUARD_EXCLUDE="/path/to/meta-repo:/path/to/other"
```

The per-ticket decision log is written to `tasks/ship/<ticket>.md` in your repo —
`.gitignore` it (ephemeral) or commit it as an audit trail.

## Requirements

- **Claude Code** with plugin support.
- **Python 3** on `PATH` — the hooks are pure standard-library Python (no third-party packages).
- **[superpowers](https://github.com/obra/superpowers)** *(recommended)* — the loop delegates to `superpowers:` skills (`brainstorming`, `writing-plans`, `test-driven-development`, `requesting-code-review`, `verification-before-completion`). Without it the loop still guides you, but those specific steps act as named checklists rather than callable skills.

State lives under `~/.claude/ship/`, independent of where the plugin installs, so it survives updates.

## Updating

```
/plugin update ship-workflow@ship-framework
```

## Development

The hooks ship with a dependency-free test harness (pipes known payloads to each
hook and asserts the output, exit code, and side effects):

```bash
python3 tests/test_hooks.py
```

## License

MIT — see [LICENSE](LICENSE).
