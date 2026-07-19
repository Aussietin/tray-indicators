#!/usr/bin/env python3
"""Shared clockon paths/helpers for the tray light and the start dialog."""

import csv
import subprocess
import sys
from pathlib import Path

CLOCKON = Path(r"G:\My Drive\ProjectVault\02_Scripts_and_Tools\clockon\clockon.py")
DATA = CLOCKON.parent / "data"
NO_WINDOW = 0x08000000                        # CREATE_NO_WINDOW


def run_clockon(*args):
    """Run the clockon CLI silently (it also updates the homelab mirror)."""
    return subprocess.run([sys.executable, str(CLOCKON)] + list(args),
                          capture_output=True, timeout=30,
                          creationflags=NO_WINDOW)


def recent_entries(limit=8):
    """Distinct recent (project, description, tags) from the last two months,
    newest first. Reads the Drive-synced CSVs directly (read-only)."""
    files = sorted(DATA.glob("????-??.csv"))[-2:]
    rows = []
    for f in files:
        try:
            with f.open(newline="", encoding="utf-8") as fh:
                rows.extend(csv.DictReader(fh))
        except OSError:
            continue
    seen, out = set(), []
    for r in reversed(rows):
        key = (r.get("project", ""), r.get("description", ""), r.get("tags", ""))
        if not key[1] or key in seen:
            continue
        seen.add(key)
        out.append({"project": key[0], "description": key[1], "tags": key[2]})
        if len(out) >= limit:
            break
    return out
