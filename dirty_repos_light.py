#!/usr/bin/env python3
"""
dirty_repos_light.py - tray light for uncommitted / unpushed git work.

GREEN "0"  - every repo clean
AMBER "n"  - 1-2 repos need attention
RED   "n"  - 3+ repos need attention
Centre = number of dirty repos; tooltip lists them. Windows Dev tree only
(WSL repos are skipped to avoid hangs when WSL is off - same rule as dirty-repos).
"""

import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tray_indicator import Indicator, State, GREEN, AMBER, RED, GREY

SCAN_DIRS = [Path(r"C:\Users\AustinCrozier\Dev")]
MAX_DEPTH = 3
POLL      = 120
NO_WINDOW = 0x08000000


def find_repos(base, max_depth=MAX_DEPTH):
    repos = []
    base = Path(base)
    if not base.exists():
        return repos

    def walk(d, depth):
        if depth > max_depth:
            return
        if (d / ".git").exists():
            repos.append(d)                    # don't descend into a repo
            return
        try:
            for child in d.iterdir():
                if child.is_dir() and not child.name.startswith("."):
                    walk(child, depth + 1)
        except OSError:
            return

    walk(base, 0)
    return repos


def repo_needs_attention(repo):
    """True if the repo has uncommitted changes or local commits not pushed."""
    try:
        st = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True, text=True, timeout=8, creationflags=NO_WINDOW)
        if st.returncode != 0:
            return False
        if st.stdout.strip():
            return True
        ahead = subprocess.run(
            ["git", "-C", str(repo), "rev-list", "--count", "@{u}..HEAD"],
            capture_output=True, text=True, timeout=8, creationflags=NO_WINDOW)
        if ahead.returncode == 0 and ahead.stdout.strip() not in ("", "0"):
            return True
        return False
    except Exception:
        return False


def poll():
    repos = []
    for base in SCAN_DIRS:
        repos.extend(find_repos(base))
    total = len(repos)

    if total == 0:
        return State(fraction=1.0, text="0", color=GREY,
                     tooltip="No git repos found under " + str(SCAN_DIRS[0]),
                     menu_label="No repos found")

    dirty = [r.name for r in repos if repo_needs_attention(r)]
    n = len(dirty)

    if n == 0:
        return State(fraction=1.0, text="0", color=GREEN,
                     tooltip="All {} repos clean".format(total),
                     menu_label="All {} repos clean".format(total))

    color = AMBER if n <= 2 else RED
    sample = ", ".join(dirty[:4])
    frac = max(0.12, n / total)
    return State(fraction=frac, text=str(n), color=color,
                 tooltip="{} of {} repos need attention: {}".format(n, total, sample),
                 menu_label="{} of {} need attention - {}".format(n, total, sample))


if __name__ == "__main__":
    Indicator("dirty_repos", poll, poll_seconds=POLL).run()
