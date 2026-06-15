#!/usr/bin/env python3
"""Stop: block once if code was edited but no check has run since.

Reads this session's marker by unique session-id suffix. Opportunistically sweeps
orphaned markers from dead sessions (mtime > 24h) — conservative enough that a
live session (which rewrites its marker mtime on every edit) is never touched.
Loop-safe via stop_hook_active.
"""
import sys, json, os, glob, time

DIR = "/tmp/claude-verify-gate"

try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)

# Orphan sweep: markers untouched for >24h belong to dead sessions.
try:
    now = time.time()
    for f in glob.glob(f"{DIR}/*"):
        try:
            if now - os.path.getmtime(f) > 86400:
                os.remove(f)
        except OSError:
            pass
except Exception:
    pass

sid = d.get("session_id", "")
if not sid or d.get("stop_hook_active"):
    sys.exit(0)

files = set()
for path in glob.glob(f"{DIR}/*__{sid}"):
    try:
        files.update(l.strip() for l in open(path) if l.strip())
    except OSError:
        pass
if not files:
    sys.exit(0)

lst = "\n".join("  - " + f for f in sorted(files)[:20])
reason = (
    "You edited code this turn but no test/lint/typecheck/build has run since the "
    "last edit:\n" + lst +
    "\n\nRun the relevant checks now (evidence before a 'done' claim). If "
    "verification genuinely doesn't apply (docs-only change, waiting on the user, "
    "or mid-step), say so explicitly and stop again."
)
print(json.dumps({"decision": "block", "reason": reason}))
