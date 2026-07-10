#!/usr/bin/env python3
"""
tray_indicator.py - reusable Windows system-tray indicator harness.

Extracted from claude-tray. Renders a donut/ring icon with centre text, a
colour-coded ring, a tooltip, a dynamic right-click menu, and one-shot toast
notifications. You supply a poll function that returns a State; the harness
owns rendering, the poll loop, the menu, error handling, and toast de-dup.

    from tray_indicator import Indicator, State, GREEN, AMBER, RED, GREY

    def poll():
        return State(fraction=1.0, text="OK", color=GREEN,
                     tooltip="all good", menu_label="Everything fine")

    Indicator("my_thing", poll, poll_seconds=30).run()

Design rule learned the hard way (see vault: claude-tray): a tray light should
measure honest, machine-local signals - never reverse-engineer a number that an
authoritative system already owns.
"""

import threading
import time
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont
import pystray

FONT_PATH = "C:/Windows/Fonts/segoeuib.ttf"

# Shared palette (RGBA)
GREEN = (76, 175, 80, 255)
AMBER = (255, 193, 7, 255)
RED   = (244, 67, 54, 255)
GREY  = (120, 120, 120, 255)
BLUE  = (33, 150, 243, 255)


@dataclass
class State:
    """One snapshot of an indicator. Returned by a poll function."""
    fraction: float = 1.0          # ring fill 0..1 (use 1.0 for a status light)
    text: str = ""                 # centre label
    color: tuple = GREEN           # ring colour
    tooltip: str = ""              # hover tooltip
    menu_label: str = ""           # first (disabled) line of the right-click menu
    notify: tuple = None           # (title, message) - fired once until it changes


def _build_icon(state, font_path):
    sz, pad, hole = 128, 4, 24
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ring track
    d.ellipse([pad, pad, sz - pad, sz - pad], fill=(70, 70, 70, 255))

    frac = max(0.0, min(state.fraction, 1.0))
    if frac > 0.005:
        d.pieslice([pad, pad, sz - pad, sz - pad],
                   start=-90, end=-90 + frac * 360, fill=state.color)

    # hole
    d.ellipse([hole, hole, sz - hole, sz - hole], fill=(24, 24, 24, 255))

    label = state.text or ""
    if label:
        n = len(label)
        font_size = 46 if n <= 1 else 30 if n <= 2 else 24 if n <= 4 else 18
        try:
            font = ImageFont.truetype(font_path, font_size)
        except OSError:
            font = ImageFont.load_default()
        bbox = d.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.text(((sz - tw) // 2 - bbox[0], (sz - th) // 2 - bbox[1]),
               label, fill=(240, 240, 240, 255), font=font)
    return img


class Indicator:
    def __init__(self, name, poll, *, poll_seconds=60, font_path=FONT_PATH,
                 extra_items=()):
        """
        name         - stable id used by pystray.
        poll         - callable returning a State. Exceptions are caught and
                       rendered as a red "!" so a flaky poll never kills the icon.
        extra_items  - iterable of (label, callback) where callback takes the
                       pystray icon, inserted above Refresh/Quit.
        """
        self.name = name
        self.poll = poll
        self.poll_seconds = poll_seconds
        self.font_path = font_path
        self.extra_items = tuple(extra_items)
        self._state = State(text="...", color=GREY,
                            tooltip=name + " - loading...", menu_label="Loading...")
        self._last_notify = None

    def _safe_poll(self):
        try:
            s = self.poll()
            if not isinstance(s, State):
                raise TypeError("poll() must return a State")
            return s
        except Exception as e:                       # never let a bad poll kill the icon
            return State(fraction=1.0, text="!", color=RED,
                         tooltip="{} - error: {}".format(self.name, e),
                         menu_label="Error: {}".format(e))

    def _apply(self, icon, state):
        self._state = state
        icon.icon = _build_icon(state, self.font_path)
        icon.title = state.tooltip or self.name
        icon.update_menu()
        if state.notify and state.notify != self._last_notify:
            self._last_notify = state.notify
            title, message = state.notify
            icon.notify(message, title)
        elif not state.notify:
            self._last_notify = None

    def _refresh(self, icon):
        self._apply(icon, self._safe_poll())

    def _loop(self, icon):
        while True:
            time.sleep(self.poll_seconds)
            self._apply(icon, self._safe_poll())

    def run(self):
        self._state = self._safe_poll()
        icon = pystray.Icon(self.name, _build_icon(self._state, self.font_path),
                            self._state.tooltip or self.name)

        items = [
            pystray.MenuItem(lambda _: self._state.menu_label or self.name,
                             None, enabled=False),
            pystray.Menu.SEPARATOR,
        ]
        for label, cb in self.extra_items:
            items.append(pystray.MenuItem(
                label, (lambda c: (lambda i, _: c(i)))(cb)))
        items += [
            pystray.MenuItem("Refresh now", lambda i, _: self._refresh(i)),
            pystray.MenuItem("Quit",        lambda i, _: i.stop()),
        ]
        icon.menu = pystray.Menu(*items)

        threading.Thread(target=self._loop, args=(icon,), daemon=True).start()
        icon.run()
