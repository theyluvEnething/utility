"""One consistent clipboard path for every tool.

Wraps pyperclip so the missing-dependency message and the copy-failure
fallback are written once instead of in each script.
"""
import sys

from . import ui


def _require_pyperclip():
    try:
        import pyperclip

        return pyperclip
    except ImportError:
        ui.error("The 'pyperclip' library is required to use the clipboard.")
        print("  Install it with: pip install pyperclip", file=sys.stderr)
        sys.exit(1)


def copy(text, *, on_overflow_print=True):
    """Copy ``text`` to the clipboard.

    If the payload is too large for the clipboard, optionally print it to
    stdout as a fallback and exit non-zero (matching the prior behavior).
    """
    pyperclip = _require_pyperclip()
    try:
        pyperclip.copy(text)
        return True
    except pyperclip.PyperclipException as exc:
        ui.error(f"Could not copy to clipboard: {exc}")
        if on_overflow_print:
            print("\n" + "=" * 60, file=sys.stderr)
            print(text, file=sys.stderr)
            print("=" * 60, file=sys.stderr)
        sys.exit(1)


def paste():
    pyperclip = _require_pyperclip()
    try:
        return pyperclip.paste()
    except pyperclip.PyperclipException as exc:
        ui.error(f"Could not read from clipboard: {exc}")
        sys.exit(1)
