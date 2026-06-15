#!/usr/bin/env python3
"""Session handoff / resume for the ship-workflow orchestrator.

~/.claude/ship/
  state/<key>.json     live ship state — the orchestrator writes it at milestones
                       (ticket, tier, current step, decisions, next_action, blockers).
  handoffs/<key>.json  a checkpoint = state + git facts; written by PreCompact /
                       throttled PostToolUse, read on SessionStart.
<key> = sanitized realpath(cwd); resume is worktree-scoped. State lives under
~/.claude/ship/ (a stable user dir) so it is independent of where the plugin is
installed and survives plugin updates.

SCOPING: checkpoint is a no-op unless a state file exists (a ship run is active),
so non-ship sessions never spawn spurious resumes.

Modes (argv[1]): state | checkpoint [--throttle] | session-start | show | clear
cwd: stdin payload "cwd" -> --cwd -> $PWD. All best-effort, fail-open, never raises.
"""
import sys, os, json, re, time, subprocess, hashlib

BASE = os.path.join(os.path.expanduser("~"), ".claude", "ship")
STATE_D = os.path.join(BASE, "state")
HAND_D = os.path.join(BASE, "handoffs")


def stdin_json():
    # Never block: only read stdin if data is immediately available (hook payloads
    # are piped + closed). CLI modes (show/clear --cwd) have no piped input.
    try:
        import select
        if sys.stdin is None:
            return {}
        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
        if not ready:
            return {}
        d = sys.stdin.read()
        return json.loads(d) if d.strip() else {}
    except Exception:
        return {}


def resolve_cwd(payload):
    cwd = payload.get("cwd") if isinstance(payload, dict) else None
    if not cwd:
        for i, a in enumerate(sys.argv):
            if a == "--cwd" and i + 1 < len(sys.argv):
                cwd = sys.argv[i + 1]
    return cwd or os.getcwd()


def key_for(cwd):
    rp = os.path.realpath(cwd)
    s = re.sub(r'[^A-Za-z0-9._-]', '-', rp)
    if len(s) > 180:                         # disambiguate same-180-prefix deep paths
        s = s[:150] + "-" + hashlib.sha1(rp.encode()).hexdigest()[:8]
    return s or "root"


def atomic_write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp-{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, path)


def git(cwd, *a):
    try:
        return subprocess.run(["git", "-C", cwd, *a], capture_output=True,
                              text=True, timeout=4).stdout.strip()
    except Exception:
        return ""


def load(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    payload = stdin_json()
    cwd = resolve_cwd(payload)
    k = key_for(cwd)
    sp = os.path.join(STATE_D, f"{k}.json")
    hp = os.path.join(HAND_D, f"{k}.json")

    if mode == "state":
        st = load(sp)
        for kk, vv in (payload or {}).items():
            if kk != "cwd":
                st[kk] = vv
        st["cwd"] = cwd
        st["updated"] = time.time()
        try:
            atomic_write(sp, st)
        except Exception:
            pass
        return 0

    if mode == "checkpoint":
        # Active run = orchestrator wrote state OR a ship decision log (tasks/ship/)
        # exists in this repo. The latter is a plain file the skill creates, so resume
        # works even if the state-write step didn't run in this environment.
        if not (os.path.exists(sp) or os.path.isdir(os.path.join(cwd, "tasks", "ship"))):
            return 0
        if "--throttle" in sys.argv:
            try:
                if os.path.exists(hp) and time.time() - os.path.getmtime(hp) < 60:
                    return 0
            except Exception:
                pass
        try:
            st = load(sp)
            dirty = [l for l in git(cwd, "status", "--porcelain").splitlines() if l.strip()]
            if not dirty and not st:        # no WIP and no explicit state → nothing
                return 0                    # worth resuming (avoids resurfacing a clear)
            ho = dict(st)
            ho.update({
                "ts": time.time(),
                "cwd": cwd,
                "branch": git(cwd, "rev-parse", "--abbrev-ref", "HEAD") or st.get("branch", "?"),
                "uncommitted_files": [l[3:] for l in dirty][:50],
                "uncommitted_count": len(dirty),
                "recent_commits": [l for l in git(cwd, "log", "-3", "--oneline").splitlines() if l.strip()],
            })
            atomic_write(hp, ho)
        except Exception:
            pass
        return 0

    if mode == "session-start":
        try:
            if not os.path.exists(hp):
                return 0
            ho = load(hp)
            age_m = int((time.time() - ho.get("ts", time.time())) // 60)
            nxt = ho.get("next_action") or ho.get("status") or "in-flight work"
            tkt = f", {ho['ticket']}" if ho.get("ticket") else ""
            ctx = (f"⏸ RESUME AVAILABLE for this worktree ({ho.get('branch', '?')}{tkt}, "
                   f"saved {age_m}m ago): {nxt}. {ho.get('uncommitted_count', 0)} uncommitted "
                   "file(s). Surface this to the user and ASK whether to resume before doing "
                   "anything else (e.g. via /ship). Do NOT auto-execute.")
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "SessionStart", "additionalContext": ctx}}))
        except Exception:
            pass
        return 0

    if mode == "show":
        ho = load(hp)
        print(json.dumps(ho, indent=2) if ho else "(no handoff for this worktree)")
        return 0

    if mode == "clear":
        for p in (hp, sp):
            try:
                os.remove(p)
            except Exception:
                pass
        print("cleared")
        return 0

    print("usage: handoff.py {state|checkpoint|session-start|show|clear}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
