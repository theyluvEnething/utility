#!/usr/bin/env python3
"""stop-port <PORT> — kill whatever is listening on a port and report it.

Kills immediately (no confirmation). ``--dry-run`` only shows what would be
killed, equivalent to ``check-port``.
"""
import sys

from utilkit import ports, ui


def main():
    args = sys.argv[1:]
    dry_run = False
    if "--dry-run" in args:
        dry_run = True
        args = [a for a in args if a != "--dry-run"]

    if len(args) != 1 or args[0] in ("-h", "--help"):
        print("Usage: stop-port <PORT> [--dry-run]")
        sys.exit(0 if len(args) == 1 else 1)

    try:
        port = int(args[0])
    except ValueError:
        ui.error(f"'{args[0]}' is not a valid port number.")
        sys.exit(1)

    entries = ports.on_port(port)
    if not entries:
        ui.info(f"Nothing is listening on port {ui.style(port, 'bold')}. Nothing to do.")
        sys.exit(0)

    if dry_run:
        ui.header(f"Would free port {port}")
        rows = [[e["process"], str(e["pid"]), e["cmdline"] or "—"] for e in entries]
        ui.table(rows, ["PROCESS", "PID", "PATH"], aligns=["l", "r", "l"])
        return

    ui.header(f"Freeing port {port}")
    seen_pids = set()
    failures = 0
    for entry in entries:
        pid = entry["pid"]
        if pid in seen_pids:
            continue
        seen_pids.add(pid)
        success, message = ports.kill(pid)
        label = f"{entry['process']} (PID {pid})"
        if success:
            ui.ok(f"killed {ui.style(label, 'bold')} on :{port}")
        else:
            ui.error(f"failed to kill {label}: {message}")
            failures += 1

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
