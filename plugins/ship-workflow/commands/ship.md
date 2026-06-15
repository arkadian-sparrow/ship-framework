---
description: One-command orchestrator — resume-or-start, then run the ship-workflow on a ticket.
argument-hint: <ticket-or-description>
---

You are the **/ship orchestrator**. Run these steps in order for `$ARGUMENTS`; each
step is a module you invoke (Skill / script). If `$ARGUMENTS` is empty, ask the user
which ticket or change to ship before doing anything else.

## 0. Resume check
A SessionStart notice may already have surfaced a saved handoff. Run
`python3 "${CLAUDE_PLUGIN_ROOT}"/hooks/handoff.py show` for this worktree. If a
resume exists, summarize it (ticket · next action · uncommitted files · age) and
**ASK the user whether to resume or start fresh** — never auto-execute a resume.

## 1. Run the workflow
**Arm the handoff first** — write an initial state so the checkpoint hooks capture
from the start (even before the first milestone, you get a git-facts resume):

```bash
echo '{"ticket":"<ticket>","status":"started"}' \
  | python3 "${CLAUDE_PLUGIN_ROOT}"/hooks/handoff.py state --cwd "$PWD"
```

Then invoke the **`ship-workflow`** skill for `$ARGUMENTS`: classify and announce
the tier, run the loop, and interrupt the user only on the four escalation triggers
(ready-to-merge · real fork · drift-changes-plan · stuck/severe-risk).

## 2. Keep state resumable (as you go)
At each milestone — tier set · a step finished · a decision made · the next action
known — record it so a future session can pick up. Pipe a JSON object to
`handoff.py state`:

```bash
echo '{"ticket":"<t>","tier":"<x>","status":"<step/phase>","next_action":"<what is next>","decisions":["..."],"blockers":["..."]}' \
  | python3 "${CLAUDE_PLUGIN_ROOT}"/hooks/handoff.py state --cwd "$PWD"
```

The PreCompact + throttled PostToolUse hooks snapshot this (plus git facts) into a
handoff automatically — you only keep the state current.

## 3. On completion
When shipped (the user approved the merge): clear the handoff so it doesn't
resurface: `python3 "${CLAUDE_PLUGIN_ROOT}"/hooks/handoff.py clear --cwd "$PWD"`.
