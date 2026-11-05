#!/usr/bin/env python3
"""
usage_light.py - tray light for Claude Max 5x weekly usage pace.

Estimates this week's % used from local transcript tokens (claude-config/tools/usage_ledger.py)
and compares it with the elapsed fraction of the week (resets Tue 12:00 AEST). The tokens-per-%
ratio comes from recorded live snapshots (usage/snapshots.csv, written by the usage-ledger
skill); with none, the max of the last 4 completed weeks counts as 100%.
  projected = used% / elapsed fraction
  RED   used >= 85%
  AMBER projected >= 100% (would cap before reset) or used >= 70%
  GREEN under pace
Card-shaped. Polls every 10 minutes; each poll is an incremental transcript scan.
"""
import os
import statistics
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, r"C:\Users\AustinCrozier\Dev\claude-config\tools")
from tray_indicator import Indicator, State, GREEN, AMBER, RED
import usage_ledger as ul

POLL = 600
WEEK = timedelta(days=7)


def tok(w):
    return w["output"] + w["cache_write"]


def estimate(s, now):
    """Return (used_pct, elapsed_frac, basis) from a usage_ledger.summary() dict."""
    weeks, snaps, cur = s["weeks"], s["snapshots"], s["current"]
    cur_tok = tok(weeks[cur]) if cur in weeks else 0
    ratios = []
    for r in snaps:
        try:
            p, t = float(r["percent_used"]), float(r["out_plus_cache_write_tokens"])
        except (KeyError, ValueError):
            continue
        if p >= 10 and t > 0:
            ratios.append(t / p)
    last = [r for r in snaps if r.get("week_start_aest") == cur]
    if ratios:
        ratio = statistics.median(ratios[-3:])
        basis = "snapshots"
        if last:
            p, t = float(last[-1]["percent_used"]), float(last[-1]["out_plus_cache_write_tokens"])
            used = p + max(cur_tok - t, 0) / ratio
        else:
            used = cur_tok / ratio
    else:
        done = [tok(weeks[k]) for k in sorted(weeks) if k < cur][-4:]
        ratio = max(done) / 100 if done else 1
        basis = "no snapshots: last-4-week max = 100%"
        used = cur_tok / ratio
    start = ul.week_start(now)
    return used, (now - start) / WEEK, basis, start


def poll():
    now = datetime.now(timezone.utc)
    used, el, basis, start = estimate(ul.summary(), now)
    el = max(el, 0.02)
    proj = used / el
    tip = "Claude week: ~{:.0f}% used, {:.0f}% elapsed, projected {:.0f}% ({})".format(used, el * 100, proj, basis)
    if proj >= 100:
        cap = (start + WEEK * (100 / proj)).astimezone(ul.AEST)
        tip += " | caps ~{:%a %H:%M}".format(cap)
    text = "{:.0f}".format(min(used, 99))
    if used >= 85:
        return State(text=text, color=RED, tooltip=tip, menu_label=tip,
                     notify=("Claude usage", "~{:.0f}% of the weekly limit used".format(used)))
    if proj >= 100 or used >= 70:
        return State(text=text, color=AMBER, tooltip=tip, menu_label=tip)
    return State(text=text, color=GREEN, tooltip=tip, menu_label=tip)


if __name__ == "__main__":
    Indicator("usage", poll, poll_seconds=POLL, shape="card").run()
