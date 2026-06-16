#!/usr/bin/env python3
"""ports — list every listening TCP port with its owning process."""
import sys

from utilkit import ports as backend
from utilkit import ui


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("Usage: ports")
        print("Lists all listening TCP ports and the process that owns each.")
        sys.exit(0)

    entries = backend.list_listening()
    if not entries:
        ui.info("No listening TCP ports found.")
        return

    ui.header(f"Listening ports ({len(entries)})")
    rows = [
        [str(e["port"]), e["process"], str(e["pid"]), e["cmdline"] or "—"]
        for e in entries
    ]
    ui.table(rows, ["PORT", "PROCESS", "PID", "PATH"], aligns=["r", "l", "r", "l"])


if __name__ == "__main__":
    main()
