#!/usr/bin/env python3
"""PreToolUse(Bash): before `gh pr create` (or `gh pr ready`), nudge if code was
edited with no test/typecheck/lint run since. Reuses the verify-gate marker.

It can confirm a check RAN, not that it PASSED — Claude Code does not expose a
command's exit code to hooks. The real "all green before merge" enforcement is
GitHub branch protection + required status checks (see the plugin README).

Fail-open: any error -> allow. Decision is 'ask', never 'deny'.
"""
import sys, json, glob

DIR = "/tmp/claude-verify-gate"

try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)

sid = d.get("session_id", "")
cmd = (d.get("tool_input") or {}).get("command", "")
if not sid or ("gh pr create" not in cmd and "gh pr ready" not in cmd):
    sys.exit(0)

if not glob.glob(f"{DIR}/*__{sid}"):     # no armed marker -> a check ran since the last edit
    sys.exit(0)

reason = ("You're opening a PR but no test / typecheck / lint has run since your "
          "last code edit. Run the full suite + typecheck first — don't open a red "
          "PR. (This gate confirms a check ran, not that it passed; the real "
          "all-green gate is GitHub branch protection + required status checks.)")
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": reason,
}}))
