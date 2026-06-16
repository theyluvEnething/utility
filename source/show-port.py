#!/usr/bin/env python3
"""show-port <PORT> — show what is listening on a port, without touching it.

Also available under the alias ``check-port``.
"""
import os
import sys

from utilkit import ports, ui


def main():
    prog = os.path.splitext(os.path.basename(sys.argv[0]))[0] or "show-port"
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(f"Usage: {prog} <PORT>")
        sys.exit(0 if len(sys.argv) == 2 else 1)

    try:
        port = int(sys.argv[1])
    except ValueError:
        ui.error(f"'{sys.argv[1]}' is not a valid port number.")
        sys.exit(1)

    entries = ports.on_port(port)
    if not entries:
        ui.info(f"Nothing is listening on port {ui.style(port, 'bold')}.")
        sys.exit(1)

    ui.header(f"Port {port}")
    rows = [
        [e["process"], str(e["pid"]), e["state"], e["cmdline"] or "—"]
        for e in entries
    ]
    ui.table(rows, ["PROCESS", "PID", "STATE", "PATH"], aligns=["l", "r", "l", "l"])
    print()
    ui.info(f"To free it:  {ui.style(f'stop-port {port}', 'bold')}")


if __name__ == "__main__":
    main()
