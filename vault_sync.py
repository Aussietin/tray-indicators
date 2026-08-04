#!/usr/bin/env python3
"""
vault_sync.py - tray light for the ProjectVault Google Drive sync.

Honest, machine-local signals only (no reverse-engineering Drive's internals):
  RED   "!"  - GoogleDriveFS.exe is not running -> edits are NOT propagating
  AMBER "n"  - n conflict files present in the vault
  GREEN ""   - syncing, nothing wrong; tooltip has time since last change

Square-shaped (vs dirty-repos' circle) so it's identifiable in the tray
without reading text. Text stays to a single glyph -- anything longer
doesn't survive Windows scaling this down to ~20px (confirmed 2026-08-04).
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tray_indicator import Indicator, State, GREEN, AMBER, RED

VAULT      = Path(r"G:\My Drive\ProjectVault")
DRIVE_PROC = "GoogleDriveFS.exe"
POLL       = 120
NO_WINDOW  = 0x08000000                       # CREATE_NO_WINDOW - no console flash
SKIP_DIRS  = {".git", ".obsidian", ".trash", ".smart-env", "node_modules"}


def gdrive_running():
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq " + DRIVE_PROC, "/NH"],
            capture_output=True, text=True, timeout=10,
            creationflags=NO_WINDOW).stdout
        return DRIVE_PROC.lower() in out.lower()
    except Exception:
        return True                            # on doubt, don't false-alarm


def scan_vault():
    """Return (newest_mtime, [conflict filenames])."""
    newest = 0.0
    conflicts = []
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in files:
            # Google Drive for desktop names real sync conflicts
            # "name (someone's conflicting copy 2026-01-01).md" -- match that
            # phrase, not the bare word "conflict", which false-positives on
            # any note whose own subject happens to be conflicts (e.g.
            # "Homelab Docker DNS and Tailscale Port Conflicts.md").
            if "conflicting copy" in fn.lower():
                conflicts.append(fn)
            try:
                m = os.path.getmtime(os.path.join(root, fn))
                if m > newest:
                    newest = m
            except OSError:
                continue
    return newest, conflicts


def fmt_age(seconds):
    m = int(seconds // 60)
    if m < 1:
        return "now"
    if m < 60:
        return "{}m".format(m)
    h = m // 60
    if h < 24:
        return "{}h".format(h)
    return "{}d".format(h // 24)


def poll():
    if not VAULT.exists():
        return State(fraction=1.0, text="?", color=RED,
                     tooltip="Vault path not found: " + str(VAULT),
                     menu_label="Vault not found",
                     notify=("Vault sync", "Vault path not found: " + str(VAULT)))

    if not gdrive_running():
        return State(fraction=1.0, text="!", color=RED,
                     tooltip="Google Drive NOT running - vault is not syncing",
                     menu_label="Drive OFF - vault not syncing",
                     notify=("Vault not syncing",
                             "Google Drive for desktop is not running."))

    newest, conflicts = scan_vault()
    if conflicts:
        n = len(conflicts)
        sample = ", ".join(conflicts[:3])
        label = str(n) if n < 10 else "9+"
        return State(fraction=1.0, text=label, color=AMBER,
                     tooltip="{} conflict file(s): {}".format(n, sample),
                     menu_label="{} conflict file(s) - {}".format(n, sample),
                     notify=("Vault conflicts",
                             "{} conflict file(s): {}".format(n, sample)))

    age = datetime.now().timestamp() - newest if newest else 0
    a = fmt_age(age)
    return State(fraction=1.0, text="", color=GREEN,
                 tooltip="Vault syncing - Drive on - last change {} ago".format(a),
                 menu_label="Syncing - Drive on - last change {} ago".format(a))


if __name__ == "__main__":
    Indicator("vault_sync", poll, poll_seconds=POLL, shape="square").run()
