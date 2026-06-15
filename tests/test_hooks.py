#!/usr/bin/env python3
"""Tests for the ship-workflow safety hooks. Pure standard library — run with:

    python3 tests/test_hooks.py

Each hook is exercised the way Claude Code invokes it: a JSON payload on stdin,
with assertions on stdout / exit code / side effects. HOME is redirected to a
temp dir so handoff state and the guard log never touch the real ~/.claude. The
verify-gate marker dir (/tmp/claude-verify-gate) is global, so tests use unique
session ids and clean up after themselves.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HOOKS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "plugins", "ship-workflow", "hooks",
)
MARKER_DIR = "/tmp/claude-verify-gate"


def run(hook, payload, *args, env=None, cwd=None):
    p = subprocess.run(
        [sys.executable, os.path.join(HOOKS, hook), *args],
        input=json.dumps(payload), capture_output=True, text=True,
        env=env, cwd=cwd, timeout=15,
    )
    return p.returncode, p.stdout, p.stderr


def write(path, text, mode="w"):
    with open(path, mode) as f:
        f.write(text)


def read(path):
    with open(path) as f:
        return f.read()


def git(cwd, *a):
    subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, check=True)


def make_repo(path):
    os.makedirs(path)
    git(path, "init", "-q")
    git(path, "config", "user.email", "t@t.t")
    git(path, "config", "user.name", "t")
    write(os.path.join(path, "f.txt"), "x")
    git(path, "add", "-A")
    git(path, "commit", "-qm", "init")


class VerifyGateMark(unittest.TestCase):
    def setUp(self):
        self.sid = "shiptest-mark-" + str(os.getpid())
        self._clean()

    def tearDown(self):
        self._clean()

    def _clean(self):
        for f in glob.glob(f"{MARKER_DIR}/*__{self.sid}"):
            try:
                os.remove(f)
            except OSError:
                pass

    def _mark(self, fp):
        run("verify-gate-mark.py",
            {"session_id": self.sid, "cwd": "/tmp", "tool_input": {"file_path": fp}})
        return glob.glob(f"{MARKER_DIR}/*__{self.sid}")

    def test_code_file_arms_marker(self):
        m = self._mark("/tmp/foo.py")
        self.assertTrue(m, "a .py edit should arm the gate")
        self.assertIn("/tmp/foo.py", read(m[0]))

    def test_shell_file_arms_marker(self):       # L7 regression
        self.assertTrue(self._mark("/tmp/deploy.sh"), ".sh must arm the gate")

    def test_vue_file_arms_marker(self):         # L7 regression
        self.assertTrue(self._mark("/tmp/App.vue"), ".vue must arm the gate")

    def test_non_code_ignored(self):
        self.assertFalse(self._mark("/tmp/README.md"))

    def test_no_session_id_noop(self):
        rc, out, _ = run("verify-gate-mark.py",
                         {"tool_input": {"file_path": "/tmp/x.py"}})
        self.assertEqual(rc, 0)


class VerifyGateClear(unittest.TestCase):
    def setUp(self):
        self.sid = "shiptest-clear-" + str(os.getpid())
        os.makedirs(MARKER_DIR, exist_ok=True)
        self.marker = f"{MARKER_DIR}/proj__{self.sid}"

    def tearDown(self):
        try:
            os.remove(self.marker)
        except OSError:
            pass

    def _clear(self, cmd):
        write(self.marker, "/tmp/foo.py\n")
        run("verify-gate-clear.py",
            {"session_id": self.sid, "tool_input": {"command": cmd}})
        return not os.path.exists(self.marker)

    def test_pytest_clears(self):
        self.assertTrue(self._clear("pytest -q"))

    def test_make_test_clears(self):             # L8 regression
        self.assertTrue(self._clear("make test"))

    def test_mvn_test_clears(self):              # L8 regression
        self.assertTrue(self._clear("mvn test"))

    def test_non_check_keeps_marker(self):
        self.assertFalse(self._clear("echo hello"))


class VerifyGateStop(unittest.TestCase):
    def setUp(self):
        self.sid = "shiptest-stop-" + str(os.getpid())
        os.makedirs(MARKER_DIR, exist_ok=True)
        self.marker = f"{MARKER_DIR}/proj__{self.sid}"

    def tearDown(self):
        try:
            os.remove(self.marker)
        except OSError:
            pass

    def test_blocks_when_unverified(self):
        write(self.marker, "/tmp/foo.py\n")
        _, out, _ = run("verify-gate-stop.py", {"session_id": self.sid})
        self.assertIn('"decision": "block"', out)

    def test_no_block_when_stop_hook_active(self):
        write(self.marker, "/tmp/foo.py\n")
        _, out, _ = run("verify-gate-stop.py",
                        {"session_id": self.sid, "stop_hook_active": True})
        self.assertNotIn("block", out)

    def test_no_block_without_marker(self):
        _, out, _ = run("verify-gate-stop.py", {"session_id": self.sid})
        self.assertNotIn("block", out)


class WorktreeGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="shiptest-wg-")
        self.home = tempfile.mkdtemp(prefix="shiptest-wghome-")
        self.env = {**os.environ, "HOME": self.home}
        self.env.pop("SHIP_GUARD_EXCLUDE", None)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        shutil.rmtree(self.home, ignore_errors=True)

    def _repo_with_worktree(self):
        main = os.path.join(self.tmp, "repo")
        make_repo(main)
        wt = os.path.join(self.tmp, "repo-wt")
        git(main, "worktree", "add", "-q", wt, "-b", "feature")
        return main, wt

    def _guard(self, cwd, fp, env=None):
        return run("worktree-guard.py",
                   {"cwd": cwd, "tool_input": {"file_path": fp}},
                   env=env or self.env)

    def test_main_checkout_asks(self):
        main, _ = self._repo_with_worktree()
        _, out, _ = self._guard(main, os.path.join(main, "f.txt"))
        self.assertIn('"permissionDecision": "ask"', out)

    def test_worktree_allowed(self):
        _, wt = self._repo_with_worktree()
        _, out, _ = self._guard(wt, os.path.join(wt, "f.txt"))
        self.assertNotIn("ask", out)

    def test_non_repo_allowed(self):
        _, out, _ = self._guard(self.tmp, os.path.join(self.tmp, "loose.py"))
        self.assertNotIn("ask", out)

    def test_exclude_env_honored(self):          # SHIP_GUARD_EXCLUDE
        main, _ = self._repo_with_worktree()
        env = {**self.env, "SHIP_GUARD_EXCLUDE": os.path.realpath(main)}
        _, out, _ = self._guard(main, os.path.join(main, "f.txt"), env=env)
        self.assertNotIn("ask", out)


class Handoff(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="shiptest-ho-")
        self.home = tempfile.mkdtemp(prefix="shiptest-hohome-")
        self.env = {**os.environ, "HOME": self.home}
        self.repo = os.path.join(self.tmp, "repo")
        make_repo(self.repo)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        shutil.rmtree(self.home, ignore_errors=True)

    def _h(self, *args, payload=None):
        return run("handoff.py", payload or {}, *args, env=self.env, cwd=self.repo)

    def _dirty(self):
        write(os.path.join(self.repo, "f.txt"), "y", mode="a")

    def test_state_checkpoint_show_clear_roundtrip(self):
        self._h("state", "--cwd", self.repo, payload={"ticket": "T-1", "status": "wip"})
        self._dirty()                                   # uncommitted WIP → resumable
        self._h("checkpoint", "--cwd", self.repo, payload={"cwd": self.repo})
        _, out, _ = self._h("show", "--cwd", self.repo)
        self.assertIn("T-1", out)
        self._h("clear", "--cwd", self.repo)
        _, out, _ = self._h("show", "--cwd", self.repo)
        self.assertIn("no handoff", out)

    def test_checkpoint_noop_without_active_run(self):  # scoping
        self._h("checkpoint", "--cwd", self.repo, payload={"cwd": self.repo})
        _, out, _ = self._h("show", "--cwd", self.repo)
        self.assertIn("no handoff", out)

    def test_tasks_ship_dir_activates_checkpoint(self):  # robust resume trigger
        os.makedirs(os.path.join(self.repo, "tasks", "ship"))
        self._dirty()
        self._h("checkpoint", "--cwd", self.repo, payload={"cwd": self.repo})
        _, out, _ = self._h("show", "--cwd", self.repo)
        self.assertNotIn("no handoff", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
