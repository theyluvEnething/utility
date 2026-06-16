"""Listening-port lookup and process termination, cross-platform.

A single internal model — a list of dicts with keys ``port``, ``pid``,
``process``, ``state``, ``cmdline`` — is produced per platform, and the
``check-port`` / ``stop-port`` / ``ports`` tools format it. Windows uses
PowerShell (Get-NetTCPConnection); Linux/macOS use ss/lsof.
"""
import json
import os
import re
import shutil
import subprocess

from . import platform_ps

_PS_LIST = r"""
$ErrorActionPreference = 'SilentlyContinue'
$conns = Get-NetTCPConnection -State Listen
$out = foreach ($c in $conns) {
    $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
    [pscustomobject]@{
        port    = $c.LocalPort
        pid     = $c.OwningProcess
        process = if ($p) { $p.ProcessName } else { 'unknown' }
        state   = 'LISTEN'
        cmdline = if ($p) { $p.Path } else { '' }
    }
}
$out | ConvertTo-Json -Compress -Depth 3
"""


def _from_powershell():
    code, out, _ = platform_ps.run(_PS_LIST)
    if code != 0 or not out.strip():
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = [data]
    rows = []
    for item in data:
        rows.append({
            "port": int(item.get("port", 0)),
            "pid": int(item.get("pid", 0)),
            "process": item.get("process") or "unknown",
            "state": item.get("state") or "LISTEN",
            "cmdline": (item.get("cmdline") or "").strip(),
        })
    return rows


_SS_RE = re.compile(r":(\d+)\s.*users:\(\(\"([^\"]+)\",pid=(\d+)")


def _from_ss():
    if not shutil.which("ss"):
        return None
    try:
        out = subprocess.run(
            ["ss", "-ltnp"], capture_output=True, text=True, timeout=15
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    rows = []
    for line in out.splitlines()[1:]:
        m = _SS_RE.search(line)
        if m:
            rows.append({
                "port": int(m.group(1)), "pid": int(m.group(3)),
                "process": m.group(2), "state": "LISTEN", "cmdline": "",
            })
    return rows


def _from_lsof():
    if not shutil.which("lsof"):
        return None
    try:
        out = subprocess.run(
            ["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"],
            capture_output=True, text=True, timeout=15,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    rows = []
    for line in out.splitlines()[1:]:
        cols = line.split()
        if len(cols) < 9:
            continue
        port_match = re.search(r":(\d+)$", cols[8])
        if not port_match:
            continue
        rows.append({
            "port": int(port_match.group(1)), "pid": int(cols[1]),
            "process": cols[0], "state": "LISTEN", "cmdline": "",
        })
    return rows


def list_listening():
    """Return all listening TCP ports with their owning process, sorted by port."""
    if os.name == "nt":
        rows = _from_powershell()
    else:
        rows = _from_ss()
        if rows is None:
            rows = _from_lsof()
        if rows is None:
            rows = []
    seen = set()
    unique = []
    for r in rows:
        key = (r["port"], r["pid"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    unique.sort(key=lambda r: (r["port"], r["pid"]))
    return unique


def on_port(port):
    """Return the listening entries (possibly several) bound to ``port``."""
    return [r for r in list_listening() if r["port"] == port]


def kill(pid):
    """Terminate a process by PID. Returns ``(ok, message)``."""
    if os.name == "nt":
        code, _, err = platform_ps.run(
            f"Stop-Process -Id {int(pid)} -Force -ErrorAction Stop"
        )
        return (code == 0), (err.strip() or ("killed" if code == 0 else "failed"))
    try:
        import signal

        os.kill(int(pid), signal.SIGKILL)
        return True, "killed"
    except (OSError, ProcessLookupError) as exc:
        return False, str(exc)
