#!/usr/bin/env python3
"""PostToolUse(Edit|Write|MultiEdit): arm the verify-gate when a CODE file changes.

Marker files live in /tmp/claude-verify-gate/ named "<project>__<session_id>" so
a human glancing at the dir can tell parallel sessions apart. Lookup is by the
unique session-id suffix, so a session whose cwd changes mid-run still resolves
to one marker. Non-code files (.md/.json/.yaml/...) are ignored.
"""
import sys, json, os, re, glob

CODE = ('.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.mts', '.cts', '.py',
        '.go', '.rs', '.java', '.rb', '.php', '.c', '.cc', '.cpp', '.h', '.hpp',
        '.swift', '.kt', '.scala', '.sql', '.sh', '.bash', '.zsh', '.lua',
        '.ex', '.exs', '.dart', '.vue', '.svelte')
DIR = "/tmp/claude-verify-gate"

try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)

sid = d.get("session_id", "")
fp = (d.get("tool_input") or {}).get("file_path", "")
if not sid or not fp or not fp.endswith(CODE):
    sys.exit(0)

os.makedirs(DIR, exist_ok=True)
# Reuse an existing marker for this session (robust to cwd changes); otherwise
# create one prefixed with the project basename for legibility.
existing = glob.glob(f"{DIR}/*__{sid}")
if existing:
    path = existing[0]
else:
    proj = re.sub(r'[^A-Za-z0-9._-]', '-',
                  os.path.basename((d.get("cwd") or "").rstrip("/"))) or "session"
    path = f"{DIR}/{proj}__{sid}"
with open(path, "a") as f:
    f.write(fp + "\n")
