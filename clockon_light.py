#!/usr/bin/env python3
"""
clockon_light.py - tray light for the clockon time tracker (vault: [[clockon]]).

Primary source: the clockon-status mirror on the homelab (clockon POSTs its
own state there on every start/stop, so it's fresh across machines - no
waiting on Drive sync). Fallback when the homelab is unreachable: this
machine's Drive-synced current.json. Honest signals both ways: clockon
publishes its own state, nothing is reverse-engineered.

  GREEN ""  - timer running; exact elapsed is in the tooltip, not the icon
              (text longer than one glyph doesn't survive Windows scaling
              this down to ~20px -- confirmed 2026-08-04)
  GREY  ""  - no timer running
  RED   "!" - poll failed entirely (harness renders this)

Hexagon-shaped (vs dirty-repos' circle, vault-sync's square) so it's
identifiable in the tray without reading text.

Toasts once per hour past 4h ("forgot to stop?").
Right-click: Stop timer / Continue last (runs clockon itself, which also
updates the homelab mirror).
"""

import json
import os
import subprocess
import sys
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pystray
from clockon_common import CLOCKON, NO_WINDOW, recent_entries, run_clockon
from tray_indicator import Indicator, State, GREEN, GREY

STATUS_URL = os.environ.get("CLOCKON_PUBLISH", "https://homelab.tailfbc9b9.ts.net:8422") + "/state"
CURRENT    = CLOCKON.parent / "data" / "current.json"
TIME_FMT   = "%Y-%m-%d %H:%M:%S"
POLL       = 60
LONG_HOURS = 4
NO_WINDOW  = 0x08000000                       # CREATE_NO_WINDOW - no console flash


def fetch_state():
    """Return (state_dict, source). Homelab mirror first, local file second."""
    try:
        with urllib.request.urlopen(STATUS_URL, timeout=3) as resp:
            return json.loads(resp.read()), "homelab"
    except (OSError, ValueError):
        pass
    if CURRENT.exists():                      # its existence means "running"
        return dict(json.loads(CURRENT.read_text("utf-8")), running=True), "local"
    return {"running": False}, "local"


def fmt_elapsed(seconds):
    m = int(seconds) // 60
    if m < 100:
        return "{}m".format(m)
    h, mm = divmod(m, 60)
    return "{}h{:02d}".format(h, mm)


def poll():
    st, src = fetch_state()
    via = "" if src == "homelab" else " (local fallback - homelab unreachable)"
    if not st.get("running"):
        return State(fraction=1.0, text="", color=GREY,
                     tooltip="clockon: no timer running" + via,
                     menu_label="No timer running")

    start = datetime.strptime(st["start"], TIME_FMT)
    secs = max(0.0, (datetime.now() - start).total_seconds())
    proj = st.get("project") or "(none)"
    desc = st.get("description", "")
    hours = int(secs // 3600)
    notify = None
    if hours >= LONG_HOURS:
        notify = ("clockon", "Timer running {}h+ - forgot to stop? "
                             "({} - {})".format(hours, proj, desc))
    return State(fraction=1.0, text="", color=GREEN,
                 tooltip="clockon: {} - {} - {} elapsed (started {}){}".format(
                     proj, desc, fmt_elapsed(secs), start.strftime("%H:%M"), via),
                 menu_label="Running: {} - {} ({})".format(
                     proj, desc, fmt_elapsed(secs)),
                 notify=notify)


def do_stop(icon):
    run_clockon("stop")
    ind._refresh(icon)


def do_continue(icon):
    run_clockon("continue")
    ind._refresh(icon)


def do_open(icon):
    webbrowser.open(STATUS_URL.rsplit("/state", 1)[0])


def do_new(icon):
    dialog = Path(__file__).resolve().parent / "clockon_start_dialog.py"
    subprocess.Popen([sys.executable, str(dialog)], creationflags=NO_WINDOW)


def _start_entry(entry):
    def action(icon, item):
        args = ["start", entry["description"]]
        if entry["project"]:
            args += ["-p", entry["project"]]
        if entry["tags"]:
            args += ["-t", entry["tags"]]
        run_clockon(*args)
        ind._refresh(icon)
    return action


def _recent_menu():
    entries = recent_entries()
    if not entries:
        yield pystray.MenuItem("(no history yet)", None, enabled=False)
    for e in entries:
        label = "{} - {}".format(e["project"] or "(none)", e["description"])[:60]
        yield pystray.MenuItem(label, _start_entry(e))


ind = Indicator("clockon", poll, poll_seconds=POLL, shape="hexagon",
                extra_items=[("New timer...", do_new),
                             ("Start recent", pystray.Menu(_recent_menu)),
                             ("Continue last", do_continue),
                             ("Stop timer", do_stop),
                             ("Open clockon", do_open)])

if __name__ == "__main__":
    ind.run()
