#!/usr/bin/env python3
"""Tiny 'clock on' dialog: description + project + tags -> clockon start.

Spawned by clockon_light's "New timer..." menu item as its own process so
tkinter never shares a thread with pystray.
"""

import tkinter as tk
from tkinter import ttk

from clockon_common import known_projects, run_clockon


def main():
    projects = known_projects()

    root = tk.Tk()
    root.title("Clock on")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    frm = ttk.Frame(root, padding=14)
    frm.grid()

    ttk.Label(frm, text="What are you working on?").grid(
        column=0, row=0, columnspan=2, sticky="w")
    desc = ttk.Entry(frm, width=40)
    desc.grid(column=0, row=1, columnspan=2, pady=(2, 10), sticky="we")
    desc.focus()

    ttk.Label(frm, text="Project").grid(column=0, row=2, sticky="w")
    proj = ttk.Combobox(frm, width=20, values=projects)
    proj.grid(column=0, row=3, sticky="w", padx=(0, 10))
    ttk.Label(frm, text="Tags (a,b)").grid(column=1, row=2, sticky="w")
    tags = ttk.Entry(frm, width=16)
    tags.grid(column=1, row=3, sticky="w")

    msg = ttk.Label(frm, text="", foreground="#c62828")
    msg.grid(column=0, row=4, columnspan=2, sticky="w", pady=(6, 0))

    def go(*_):
        d = desc.get().strip()
        if not d:
            msg.config(text="Description required")
            return
        args = ["start", d]
        if proj.get().strip():
            args += ["-p", proj.get().strip()]
        if tags.get().strip():
            args += ["-t", tags.get().strip()]
        run_clockon(*args)
        root.destroy()

    ttk.Button(frm, text="Clock on", command=go).grid(
        column=0, row=5, columnspan=2, pady=(12, 0))
    root.bind("<Return>", go)
    root.bind("<Escape>", lambda e: root.destroy())
    root.eval("tk::PlaceWindow . center")
    root.mainloop()


if __name__ == "__main__":
    main()
