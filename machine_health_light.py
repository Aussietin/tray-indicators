#!/usr/bin/env python3
"""
machine_health_light.py - tray light for this laptop's memory and disk headroom.

Watches the kernel access-token leak found 2026-11-04 (pool tag Toke grew to 3.46 M live
tokens / 16.5 GB paged pool and pushed commit to the limit; vault:
[[2026-11-04 C drive and Google Drive cleanup]], [[Kernel Pool Tag Check]]):
  RED   "!"  - paged pool > 4 GB, commit > 85% of limit, or C: < 50 GB free: restart / clean up
  AMBER "!"  - paged pool > 2.5 GB, or C: < 100 GB free
  GREEN ""   - fine; tooltip has the numbers
Every poll also appends a line to SystemMaintenance\\token_sample.log with live tokens and
counts of the heavy apps running, to find which workload the leak tracks. A tray light
instead of a scheduled task: console tasks freeze on this laptop (2026-11-05).
Diamond-shaped.
"""

import collections
import ctypes
import os
import shutil
import subprocess
import sys
from ctypes import wintypes
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tray_indicator import Indicator, State, GREEN, AMBER, RED

POLL      = 600
LOG       = r"C:\Users\AustinCrozier\Scripts\SystemMaintenance\token_sample.log"
WATCH     = ("Unity", "Godot", "codex", "claude", "git", "node", "python", "pwsh", "java", "vmmem")
NO_WINDOW = 0x08000000
GB        = 1 << 30


class PerfInfo(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD)] + [(n, ctypes.c_size_t) for n in (
        "CommitTotal", "CommitLimit", "CommitPeak", "PhysicalTotal", "PhysicalAvailable",
        "SystemCache", "KernelTotal", "KernelPaged", "KernelNonpaged", "PageSize")] + [
        ("HandleCount", wintypes.DWORD), ("ProcessCount", wintypes.DWORD), ("ThreadCount", wintypes.DWORD)]


class Tag(ctypes.Structure):
    _fields_ = [("Tag", ctypes.c_char * 4), ("PagedAllocs", ctypes.c_ulong), ("PagedFrees", ctypes.c_ulong),
                ("PagedUsed", ctypes.c_size_t), ("NonPagedAllocs", ctypes.c_ulong), ("NonPagedFrees", ctypes.c_ulong),
                ("NonPagedUsed", ctypes.c_size_t)]


def live_tokens():
    nt, size = ctypes.WinDLL("ntdll"), 1 << 21
    while True:
        buf, ret = ctypes.create_string_buffer(size), ctypes.c_ulong()
        st = nt.NtQuerySystemInformation(22, buf, size, ctypes.byref(ret)) & 0xFFFFFFFF  # SystemPoolTagInformation
        if st != 0xC0000004:  # STATUS_INFO_LENGTH_MISMATCH
            break
        size = max(size * 2, ret.value + 4096)
    count = ctypes.c_ulong.from_buffer(buf).value
    for t in (Tag * count).from_buffer(buf, ctypes.sizeof(ctypes.c_size_t)):
        if t.Tag == b"Toke":
            return (t.PagedAllocs - t.PagedFrees) + (t.NonPagedAllocs - t.NonPagedFrees)
    return 0


def log_sample(toke, paged, commit, limit):
    try:
        out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True,
                             timeout=60, creationflags=NO_WINDOW).stdout
        names = [l.split('","')[0].strip('"').lower() for l in out.splitlines() if l]
        c = collections.Counter(next((w for w in WATCH if n.startswith(w.lower())), None) for n in names)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("{:%Y-%m-%d %H:%M} toke {} paged {:.1f} GB commit {:.0f}/{:.0f} procs {} | {}\n".format(
                datetime.now(), toke, paged, commit, limit, len(names),
                " ".join("{}={}".format(w, c[w]) for w in WATCH if c[w])))
    except Exception:
        pass  # logging must never break the light


def poll():
    pi = PerfInfo(cb=ctypes.sizeof(PerfInfo))
    ctypes.WinDLL("psapi").GetPerformanceInfo(ctypes.byref(pi), pi.cb)
    commit, limit = pi.CommitTotal * pi.PageSize / GB, pi.CommitLimit * pi.PageSize / GB
    paged = pi.KernelPaged * pi.PageSize / GB
    free = shutil.disk_usage("C:\\").free / GB
    toke = live_tokens()
    log_sample(toke, paged, commit, limit)

    summary = "pool {:.1f} GB ({:,} tokens) | commit {:.0f}/{:.0f} GB | C: {:.0f} GB free".format(
        paged, toke, commit, limit, free)
    red = [m for c, m in ((paged > 4, "kernel pool {:.1f} GB - restart soon".format(paged)),
                          (commit / limit > 0.85, "commit {:.0f}/{:.0f} GB".format(commit, limit)),
                          (free < 50, "C: {:.0f} GB free".format(free))) if c]
    if red:
        return State(text="!", color=RED, tooltip=summary, menu_label="; ".join(red),
                     notify=("Laptop health", "; ".join(red)))
    if paged > 2.5 or free < 100:
        return State(text="!", color=AMBER, tooltip=summary, menu_label=summary)
    return State(text="", color=GREEN, tooltip=summary, menu_label=summary)


if __name__ == "__main__":
    Indicator("machine_health", poll, poll_seconds=POLL, shape="diamond").run()
