#!/usr/bin/env python3
"""PostToolUse(Bash): disarm the verify-gate when a check command runs.

SEMANTICS — enforces "a check was RUN", not "a check PASSED". Claude Code does
not expose a command's exit code to hooks (the PostToolUse payload carries only
stdout/stderr/interrupted/isImage/noOutputExpected — verified empirically), so a
failing command is indistinguishable from a passing one here. A failing check
still surfaces its failure to the agent via output; correctness is the per-step
code review's job, not this gate's.

Clears by unique session-id suffix, matching the "<project>__<session_id>"
marker naming.
"""
import sys, json, os, re, glob

DIR = "/tmp/claude-verify-gate"
PAT = re.compile(
    r'(pnpm|npm|yarn|npx)\s+(run\s+)?(test|lint|typecheck|build)'
    r'|jest|vitest|eslint|tsc\b|pytest|go\s+test|cargo\s+(test|build|check)'
    r'|next\s+build'
    r'|make\s+(test|build|check|lint|ci|all)\b'
    r'|gradlew?\s+\S*(test|build|check)|mvn\s+(test|verify|package|install)'
    r'|dotnet\s+(test|build)'
    # Lightweight syntax/compile checks count for script-type code with no
    # test/lint/build target (hooks, shell, config-as-code):
    r'|py_compile|node\s+--check|bash\s+-n|sh\s+-n|shellcheck|ruby\s+-c|perl\s+-c',
    re.I,
)

try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)

sid = d.get("session_id", "")
cmd = (d.get("tool_input") or {}).get("command", "")
if sid and cmd and PAT.search(cmd):
    for path in glob.glob(f"{DIR}/*__{sid}"):
        try:
            os.remove(path)
        except OSError:
            pass
