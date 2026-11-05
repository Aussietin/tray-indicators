#!/usr/bin/env python3
"""
vault_git_light.py - tray light for the ProjectVault main checkout (the folder Obsidian
opens and the Drive phone mirror copies). Replaces vault_sync.py, which watched the old
pre-git Drive copy and stayed green while this checkout sat mid-rebase for 9 days
(2026-10-26 -> 11-05) and the auto-checkpoint skipped it.

Honest, machine-local signals from git itself:
  RED   "!"  - rebase/merge in progress or detached HEAD (auto-checkpoint skips it), or
               changes left uncommitted for over a day
  AMBER "n"  - n commits behind origin (Obsidian shows a stale vault), or n uncommitted
               files / unpushed commits
  GREEN ""   - in sync with origin, nothing uncommitted
Fetches origin every 30 min; every other poll is local-only.
Square-shaped, like the light it replaces.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tray_indicator import Indicator, State, GREEN, AMBER, RED

VAULT     = Path(r"C:\Users\AustinCrozier\Dev\ProjectVault")
POLL      = 120
FETCH     = 1800
STALE_H   = 24
NO_WINDOW = 0x08000000
_last_fetch = {"t": 0.0}


def git(*args, timeout=20):
    r = subprocess.run(["git", "-C", str(VAULT), *args], capture_output=True, text=True,
                       timeout=timeout, creationflags=NO_WINDOW)
    return r.stdout.strip() if r.returncode == 0 else ""


def poll():
    git_dir = git("rev-parse", "--absolute-git-dir")
    if not git_dir:
        return State(text="?", color=RED, tooltip="Not a git repo: " + str(VAULT),
                     menu_label="Vault repo not found")

    for marker in ("rebase-merge", "rebase-apply", "MERGE_HEAD"):
        if os.path.exists(os.path.join(git_dir, marker)):
            msg = "Vault checkout stuck mid-{} - auto-checkpoint skips it".format(
                "merge" if marker == "MERGE_HEAD" else "rebase")
            return State(text="!", color=RED, tooltip=msg, menu_label=msg, notify=("Vault git", msg))

    if time.time() - _last_fetch["t"] > FETCH:
        git("fetch", "-q", "origin", timeout=60)
        _last_fetch["t"] = time.time()

    branch = git("branch", "--show-current")
    if not branch:
        msg = "Vault checkout on a detached HEAD - auto-checkpoint can't pull or push"
        return State(text="!", color=RED, tooltip=msg, menu_label=msg, notify=("Vault git", msg))

    dirty = [l[3:] for l in git("status", "--porcelain").splitlines() if l]
    counts = git("rev-list", "--left-right", "--count", "HEAD...origin/" + branch).split()
    ahead, behind = (int(counts[0]), int(counts[1])) if len(counts) == 2 else (0, 0)

    oldest_h = 0.0
    for p in dirty:
        try:
            oldest_h = max(oldest_h, (time.time() - os.path.getmtime(VAULT / p.strip('"'))) / 3600)
        except OSError:
            continue

    bits = []
    if behind:
        bits.append("{} behind origin".format(behind))
    if ahead:
        bits.append("{} unpushed".format(ahead))
    if dirty:
        bits.append("{} uncommitted (oldest {:.0f}h)".format(len(dirty), oldest_h))
    summary = ", ".join(bits) or "in sync, clean"

    if dirty and oldest_h > STALE_H:
        return State(text="!", color=RED, tooltip="Vault: " + summary, menu_label=summary,
                     notify=("Vault git", "Changes uncommitted for over a day: " + summary))
    if bits:
        n = behind or ahead or len(dirty)
        return State(text=str(n) if n < 10 else "9+", color=AMBER, tooltip="Vault: " + summary,
                     menu_label=summary)
    return State(text="", color=GREEN, tooltip="Vault: " + summary, menu_label=summary)


if __name__ == "__main__":
    Indicator("vault_git", poll, poll_seconds=POLL, shape="square").run()
