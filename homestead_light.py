#!/usr/bin/env python3
"""
homestead_light.py - tray light for the homestead household hub
(vault: [[homestead]], app: http://homelab:8425).

  RED   "n"  - n overdue tasks (toast once per count change)
  AMBER "n"  - n due within 30 days
  GREEN "ok" - nothing due soon
  RED   "!"  - homestead unreachable (harness renders poll errors)

Right-click: Open homestead.
"""

import json
import os
import sys
import urllib.request
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tray_indicator import Indicator, State, GREEN, AMBER, RED

BASE = os.environ.get("HOMESTEAD_URL", "http://homelab:8425")
POLL = 300


def poll():
    with urllib.request.urlopen(BASE + "/api/summary", timeout=5) as resp:
        s = json.loads(resp.read())
    overdue, soon = s.get("overdue", 0), s.get("due_soon", 0)
    nxt = s.get("next") or {}
    nxt_txt = ""
    if nxt:
        nxt_txt = "next: {} ({}) {}".format(
            nxt.get("title"), nxt.get("asset") or "-", nxt.get("due"))
    if overdue:
        return State(fraction=1.0, text=str(overdue), color=RED,
                     tooltip="homestead: {} overdue - {}".format(overdue, nxt_txt),
                     menu_label="{} overdue - {}".format(overdue, nxt_txt),
                     notify=("homestead",
                             "{} household task(s) overdue".format(overdue)))
    if soon:
        return State(fraction=1.0, text=str(soon), color=AMBER,
                     tooltip="homestead: {} due in 30d - {}".format(soon, nxt_txt),
                     menu_label="{} due soon - {}".format(soon, nxt_txt))
    return State(fraction=1.0, text="ok", color=GREEN,
                 tooltip="homestead: nothing due soon",
                 menu_label="Nothing due soon")


def open_app(icon):
    webbrowser.open(BASE)


if __name__ == "__main__":
    Indicator("homestead", poll, poll_seconds=POLL,
              extra_items=[("Open homestead", open_app)]).run()
