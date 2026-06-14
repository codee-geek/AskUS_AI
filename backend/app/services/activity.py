"""Tracks the timestamp of the last real user request.

Used by the on-demand auto-stop script: an idle-watcher reads /activity and
stops the EC2 instance after a period of inactivity. Health checks are
excluded by the caller so they don't keep the box awake forever.
"""

import time
from pathlib import Path

STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage"
ACTIVITY_FILE = STORAGE_ROOT / ".last_activity"


def touch_activity() -> None:
    """Record 'now' as the most recent activity. Best-effort; never raises."""
    try:
        STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        ACTIVITY_FILE.write_text(str(time.time()))
    except OSError:
        pass


def get_last_activity() -> float:
    try:
        return float(ACTIVITY_FILE.read_text().strip())
    except (OSError, ValueError):
        return 0.0


def idle_seconds() -> float:
    """Seconds since last activity, or -1 if no activity has been recorded."""
    last = get_last_activity()
    if last <= 0:
        return -1.0
    return max(0.0, time.time() - last)
