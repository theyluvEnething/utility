#!/usr/bin/env python3
"""show-port <PORT> — show what is listening on a port, without touching it.

Also available under the alias ``check-port``.
"""
import os
import sys

from utilkit import ports, ui


def _format_uptime(seconds):
    seconds = int(seconds or 0)
    if seconds <= 0:
        return "—"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def _cpu_color(pct):
    if pct >= 50:
        return "bright_red"
    if pct >= 15:
        return "bright_yellow"
    return "bright_green"


def _render_process(entry, port):
    pid = entry["pid"]
    detail = ports.process_detail(pid)
    name = (detail or {}).get("name") or entry["process"]
    exe = f"{name}.exe" if not name.endswith(".exe") else name

    fields = [("PID", ui.style(str(pid), "bold"))]

    if detail:
        path = detail.get("path") or entry.get("cmdline") or "—"
        mem = detail.get("memory_mb")
        cpu_pct = detail.get("cpu_percent") or 0
        cpu_sec = detail.get("cpu_seconds") or 0
        fields.append(("Location", path))
        if detail.get("description"):
            fields.append(("Description", detail["description"]))
        fields.append((None, None))
        fields.append(("Memory", f"{mem} MB" if mem is not None else "—"))
        fields.append((
            "CPU",
            f"{ui.style(f'{cpu_pct}%', _cpu_color(cpu_pct))} "
            f"{ui.style(f'(avg over {cpu_sec}s used)', 'dim')}",
        ))
        fields.append(("Threads", str(detail.get("threads", "—"))))
        fields.append(("Uptime", _format_uptime(detail.get("uptime_sec"))))
    else:
        fields.append(("Location", entry.get("cmdline") or "—"))

    ui.card(f"{exe}  ·  :{port}  {entry['state']}", fields)


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

    listening = ports.list_listening()
    entries = [r for r in listening if r["port"] == port]

    if not entries:
        owned = [r for r in listening if r["pid"] == port]
        if owned:
            listed = ", ".join(str(e["port"]) for e in owned)
            name = owned[0]["process"]
            ui.info(
                f"{ui.style(port, 'bold')} is a PID ({name}), not a port — "
                f"it is listening on: {ui.style(listed, 'bold')}"
            )
            print(f"  Try:  {ui.style(f'{prog} {owned[0]['port']}', 'bold')}")
        else:
            ui.info(f"Nothing is listening on port {ui.style(port, 'bold')}.")
        sys.exit(1)

    seen = set()
    for entry in entries:
        if entry["pid"] in seen:
            continue
        seen.add(entry["pid"])
        _render_process(entry, port)

    print()
    ui.info(f"To free it:  {ui.style(f'stop-port {port}', 'bold')}")


if __name__ == "__main__":
    main()
