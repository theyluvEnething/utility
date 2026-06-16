"""Persistent SSH session store for ``connect-server``.

Stores only connection coordinates — host, user, port, optional identity-file
path, label, and last-used timestamp. Never stores passwords; authentication is
delegated entirely to the system ``ssh`` client.
"""
import json
import time
from pathlib import Path

from . import config


def _path():
    return config.sessions_file()


def load():
    path = _path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def save(sessions):
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2)
    tmp.replace(path)


def _key(entry):
    return (entry.get("user", ""), entry.get("host", ""), int(entry.get("port", 22)))


def record(host, user, port=22, identity_file=None, label=None):
    """Insert or update a session, stamping ``last_used`` to now."""
    sessions = load()
    new = {
        "host": host,
        "user": user,
        "port": int(port),
        "identity_file": identity_file,
        "label": label,
        "last_used": time.time(),
    }
    sessions = [s for s in sessions if _key(s) != _key(new)]
    sessions.append(new)
    save(sessions)
    return new


def most_recent_first():
    return sorted(load(), key=lambda s: s.get("last_used", 0), reverse=True)


def remove(index):
    """Remove the entry at a 1-based index in the most-recent-first listing."""
    ordered = most_recent_first()
    if not 1 <= index <= len(ordered):
        return None
    target = ordered[index - 1]
    save([s for s in load() if _key(s) != _key(target)])
    return target


def display_name(entry):
    base = f"{entry.get('user')}@{entry.get('host')}"
    if int(entry.get("port", 22)) != 22:
        base += f":{entry['port']}"
    if entry.get("label"):
        base = f"{entry['label']} ({base})"
    return base


def humanize_age(ts):
    if not ts:
        return "never"
    delta = max(0, int(time.time() - ts))
    for unit, secs in (("d", 86400), ("h", 3600), ("m", 60)):
        if delta >= secs:
            return f"{delta // secs}{unit} ago"
    return "just now"
