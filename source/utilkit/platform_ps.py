"""Run PowerShell commands portably and capture their output.

On Windows this finds ``powershell.exe`` (Windows PowerShell) or ``pwsh``;
elsewhere it looks for ``pwsh`` (PowerShell Core) if present. Used by the port
tools on Windows; the Unix port path uses ss/lsof instead and does not need this.
"""
import shutil
import subprocess


def powershell_executable():
    for candidate in ("pwsh", "powershell"):
        path = shutil.which(candidate)
        if path:
            return path
    return None


def run(command, *, timeout=15):
    """Execute a PowerShell command, returning ``(returncode, stdout, stderr)``.

    Returns ``(127, "", message)`` if no PowerShell interpreter is available.
    """
    exe = powershell_executable()
    if not exe:
        return 127, "", "PowerShell interpreter not found on PATH."
    try:
        proc = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True, text=True, timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "PowerShell command timed out."
    except OSError as exc:
        return 1, "", str(exc)
