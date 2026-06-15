#!/usr/bin/env python3
"""PreToolUse(Edit|Write|MultiEdit): prompt before editing a repo's MAIN checkout.

Repo-agnostic worktree guard. For the edit target, asks git whether the file is in
a MAIN checkout (git-dir == git-common-dir) vs a linked WORKTREE (different) vs no
repo. A MAIN checkout that HAS linked worktrees (a worktree workflow is in use) and
is not excluded -> prompt ('ask'); everything else -> defer silently.

Scope: only repos that use worktrees. To exclude specific repos (e.g. a multi-repo
umbrella/meta-repo whose main checkout you legitimately work in), set the env var
SHIP_GUARD_EXCLUDE to a colon-separated list of absolute repo-root paths, e.g.
  export SHIP_GUARD_EXCLUDE="/path/to/meta-repo:/path/to/other"
By default nothing is excluded.

NOTE: this guards FILE EDITS only. Destructive Bash git ops (reset --hard, clean,
rm -rf) should be covered by your permission deny list, NOT this hook.

Fail-OPEN everywhere: any error/timeout -> allow. Decision: 'ask' (never 'deny', so
the user is never locked out; a headless agent that can't answer is effectively
blocked). Every decision is logged so a dead, fail-open guard is detectable.
"""
import sys, json, os, subprocess, time

EXCLUDE_ROOTS = {
    os.path.realpath(p)
    for p in os.environ.get("SHIP_GUARD_EXCLUDE", "").split(":")
    if p.strip()
}
LOG = os.path.join(os.path.expanduser("~"), ".claude", "ship", "logs",
                   "worktree-guard.log")
LOG_CAP = 1_000_000  # bytes; past this, truncate to the recent tail


def log(decision, repo, fp):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as f:  # O_APPEND + short line -> atomic across sessions
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {decision} {repo} {fp}\n")
        if os.path.getsize(LOG) > LOG_CAP:        # bounded growth: keep the tail
            with open(LOG) as f:
                tail = f.readlines()[-2000:]
            with open(LOG, "w") as f:
                f.writelines(tail)
    except Exception:
        pass


def git(d, *args):
    return subprocess.run(["git", "-C", d, *args], capture_output=True,
                          text=True, timeout=2).stdout.strip()


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    fp = (data.get("tool_input") or {}).get("file_path")
    if not fp:
        return 0
    if not os.path.isabs(fp):
        fp = os.path.join(data.get("cwd") or os.getcwd(), fp)

    # nearest existing ancestor dir (handles new / nested files)
    d = os.path.dirname(fp)
    while d and not os.path.isdir(d):
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    if not d or not os.path.isdir(d):
        return 0

    try:
        gitdir = git(d, "rev-parse", "--absolute-git-dir")
        if not gitdir:
            log("allow-notrepo", "-", fp); return 0
        common = git(d, "rev-parse", "--path-format=absolute", "--git-common-dir")
        if not common:
            log("allow-err", "-", fp); return 0
        gitdir = os.path.realpath(gitdir)
        common = os.path.realpath(common)
    except Exception:
        log("allow-err", "-", fp); return 0

    if gitdir != common:                                    # linked worktree
        log("allow-worktree", os.path.dirname(common), fp); return 0

    root = os.path.dirname(common)                          # MAIN: <root>/.git -> <root>
    if os.path.realpath(root) in EXCLUDE_ROOTS:
        log("allow-excluded", root, fp); return 0
    wt = os.path.join(common, "worktrees")
    try:
        has_worktrees = os.path.isdir(wt) and bool(os.listdir(wt))
    except OSError:
        has_worktrees = False
    if not has_worktrees:
        log("allow-no-worktrees", root, fp); return 0

    log("ASK", root, fp)
    reason = (f"Editing the MAIN checkout of '{os.path.basename(root)}' ({root}). "
              f"This repo uses worktrees — work in the ticket's worktree instead, "
              f"or approve to edit main.")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": reason,
    }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
