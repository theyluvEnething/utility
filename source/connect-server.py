#!/usr/bin/env python3
"""connect-server [target] — persistent SSH session manager.

  connect-server user@host [-p PORT] [-i KEYFILE] [--label NAME]
      Connect via the system ssh client and remember the session.
  connect-server
      Pick a previously used server from a most-recent-first list.
  connect-server --list
      Show saved servers without connecting.
  connect-server --remove <n>
      Remove the server at position <n> in the list.

Only connection details are stored — never passwords. Authentication is handled
entirely by ssh (keys, ssh-agent, or its own prompt).
"""
import os
import shutil
import subprocess
import sys

from utilkit import sessions, ui


def _parse_target(args):
    """Parse ``user@host`` plus optional ``-p``/``-i``/``--label`` flags."""
    target = None
    port = 22
    identity = None
    label = None
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-p", "--port") and i + 1 < len(args):
            port = int(args[i + 1]); i += 2
        elif a in ("-i", "--identity") and i + 1 < len(args):
            identity = args[i + 1]; i += 2
        elif a == "--label" and i + 1 < len(args):
            label = args[i + 1]; i += 2
        elif not a.startswith("-"):
            target = a; i += 1
        else:
            ui.error(f"unknown option: {a}")
            sys.exit(1)
    if target is None:
        ui.error("expected a target like user@host")
        sys.exit(1)
    user, _, host = target.partition("@")
    if not host:
        ui.error("target must be in the form user@host")
        sys.exit(1)
    return host, user, port, identity, label


def _connect(entry):
    if not shutil.which("ssh"):
        ui.error("the 'ssh' client was not found on PATH.")
        if os.name == "nt":
            print("  Install it via: Settings → Apps → Optional Features → OpenSSH Client")
        sys.exit(1)

    cmd = ["ssh"]
    if int(entry.get("port", 22)) != 22:
        cmd += ["-p", str(entry["port"])]
    if entry.get("identity_file"):
        cmd += ["-i", entry["identity_file"]]
    cmd.append(f"{entry['user']}@{entry['host']}")

    sessions.record(
        entry["host"], entry["user"], entry.get("port", 22),
        entry.get("identity_file"), entry.get("label"),
    )
    ui.info(f"connecting to {ui.style(sessions.display_name(entry), 'bold')} …")
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        return 130


def _show_list(ordered):
    ui.header("Saved servers")
    rows = [
        [str(i), sessions.display_name(e), sessions.humanize_age(e.get("last_used"))]
        for i, e in enumerate(ordered, 1)
    ]
    ui.table(rows, ["#", "SERVER", "LAST USED"], aligns=["r", "l", "l"])


def _pick(ordered):
    _show_list(ordered)
    print()
    try:
        choice = input(ui.style("Connect to # (Enter to cancel): ", "cyan")).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if not choice:
        return None
    try:
        idx = int(choice)
        if 1 <= idx <= len(ordered):
            return ordered[idx - 1]
    except ValueError:
        pass
    ui.error("invalid selection.")
    return None


def main():
    args = sys.argv[1:]

    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        return

    if args and args[0] == "--list":
        ordered = sessions.most_recent_first()
        if not ordered:
            ui.info("No saved servers yet. Connect with: connect-server user@host")
            return
        _show_list(ordered)
        return

    if args and args[0] == "--remove":
        if len(args) < 2:
            ui.error("usage: connect-server --remove <n>")
            sys.exit(1)
        try:
            removed = sessions.remove(int(args[1]))
        except ValueError:
            ui.error("position must be a number.")
            sys.exit(1)
        if removed:
            ui.ok(f"removed {sessions.display_name(removed)}")
        else:
            ui.error("no server at that position.")
            sys.exit(1)
        return

    if args:
        host, user, port, identity, label = _parse_target(args)
        sys.exit(_connect({
            "host": host, "user": user, "port": port,
            "identity_file": identity, "label": label,
        }))

    ordered = sessions.most_recent_first()
    if not ordered:
        ui.info("No saved servers yet.")
        print(f"  Connect with: {ui.style('connect-server user@host', 'bold')}")
        return
    entry = _pick(ordered)
    if entry:
        sys.exit(_connect(entry))


if __name__ == "__main__":
    main()
