#!/usr/bin/env python3
"""
clockon_light.py - tray light for the clockon time tracker (vault: [[clockon]]).

Primary source: the clockon-status mirror on the homelab (clockon POSTs its
own state there on every start/stop, so it's fresh across machines - no
waiting on Drive sync). Fallback when the homelab is unreachable: this
machine's Drive-synced current.json. Honest signals both ways: clockon
publishes its own state, nothing is reverse-engineered.

  GREEN "1h05" - timer running; centre shows elapsed
  GREY  "--"   - no timer running
  RED   "!"    - poll failed entirely (harness renders this)

Toasts once per hour past 4h ("forgot to stop?").
Right-click: Stop timer / Continue last (runs clockon itself, which also
updates the homelab mirror).
"""

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tray_indicator import Indicator, State, GREEN, GREY

STATUS_URL = os.environ.get("CLOCKON_PUBLISH", "http://homelab:8422") + "/state"
CLOCKON    = Path(r"G:\My Drive\ProjectVault\02_Scripts_and_Tools\clockon\clockon.py")
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
        return State(fraction=1.0, text="--", color=GREY,
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
    return State(fraction=1.0, text=fmt_elapsed(secs), color=GREEN,
                 tooltip="clockon: {} - {} (started {}){}".format(
                     proj, desc, start.strftime("%H:%M"), via),
                 menu_label="Running: {} - {} ({})".format(
                     proj, desc, fmt_elapsed(secs)),
                 notify=notify)


def _run_clockon(*args):
    subprocess.run([sys.executable, str(CLOCKON)] + list(args),
                   capture_output=True, timeout=30, creationflags=NO_WINDOW)


def do_stop(icon):
    _run_clockon("stop")
    ind._refresh(icon)


def do_continue(icon):
    _run_clockon("continue")
    ind._refresh(icon)


ind = Indicator("clockon", poll, poll_seconds=POLL,
                extra_items=[("Stop timer", do_stop),
                             ("Continue last", do_continue)])

if __name__ == "__main__":
    ind.run()
