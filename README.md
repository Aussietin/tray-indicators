# tray-indicators

A tiny platform for Windows system-tray status lights. Write one `poll()`
function that returns a `State`; the harness owns the icon rendering, the
poll loop, the right-click menu, error handling, and one-shot toast
notifications on state change.

```python
from tray_indicator import Indicator, State, GREEN, AMBER, RED

def poll():
    return State(text="OK", color=GREEN, tooltip="all good",
                 menu_label="Everything fine")

Indicator("my_thing", poll, poll_seconds=30).run()
```

## Why

Small background facts — is my vault syncing, do I have uncommitted repos,
is the work timer running — each want a glanceable indicator, not a
notification and not an app window. Rather than build a bespoke tray app
per fact, this is the shared harness they all run on.

**Design rule (learned the hard way):** a tray light should measure honest,
machine-local signals — never reverse-engineer a number that an
authoritative system already owns.

## How it works

`tray_indicator.py` renders a ring/donut icon with a centre glyph, a
colour-coded ring (green / amber / red / grey), a tooltip, and a dynamic
right-click menu. Each light can also pick a **shape** (circle, rounded
square, diamond, hexagon, house) so several similar-coloured lights stay
distinguishable at real tray size (~20px), where colour and text alone
aren't enough. The harness fires a toast once per state change and
de-dupes until the state changes again; a `poll()` that raises is rendered
as a red `!` rather than crashing the tray.

## Included lights

| Light | Watches | Shape |
|---|---|---|
| `vault_git_light.py` | the vault's main git checkout: stuck rebase/merge, detached HEAD, behind origin, uncommitted or unpushed work | square |
| `dirty_repos_light.py` | git repos under a configured dir with uncommitted / unpushed work | circle |
| `homestead_light.py` | the self-hosted household-ops service: overdue / soon-due tasks, reachability | house |
| `machine_health_light.py` | kernel paged pool + access-token count (leak watch), commit charge, C: free; logs a sample each poll | diamond |
| `clockon_light.py` | whether a `clockon` time-tracking timer is running. Retired from startup 2026-11-05 (unused since July) | hexagon |

`vault_sync.py` (Google Drive vault sync) was removed 2026-11-05: the vault moved to git, and it was watching a
stale Drive copy.

These are the author's own lights and carry hardcoded local paths (e.g.
`dirty_repos_light.py`'s `SCAN_DIRS`, `start-trays.vbs`'s base and Python
path). Treat them as worked examples — point them at your own paths, or
copy the pattern for your own `poll()`.

## Run

```
pip install -r requirements.txt
pythonw tray_indicator.py               # a single light
```

`start-trays.vbs` launches the configured lights silently via
`pythonw` (no console windows) — edit its `base` / `pyw` paths, then
double-click it or drop a shortcut in `shell:startup` to run on login.

## License

MIT
