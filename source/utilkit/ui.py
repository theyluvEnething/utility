"""Shared terminal-presentation helpers.

Gives every tool the same polished, colorized look that ``ls`` already has.
Colors auto-disable when output is not a TTY, when ``NO_COLOR`` is set, or on a
terminal that cannot handle ANSI, so piped output stays clean. Box-drawing
glyphs fall back to ASCII when the console encoding cannot represent them.
"""
import os
import shutil
import sys


def _prefer_utf8():
    """Try to switch stdout/stderr to UTF-8 so Unicode glyphs work everywhere."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError, OSError):
            pass


_prefer_utf8()


def _unicode_ok(stream):
    encoding = getattr(stream, "encoding", None) or ""
    return encoding.lower().replace("-", "") in ("utf8", "utf16", "utf32")


_GLYPHS = {
    "rule": ("─", "-"),
    "ok": ("✓", "+"),
    "warn": ("!", "!"),
    "error": ("✗", "x"),
    "info": ("•", ">"),
    "tee": ("├──", "+--"),
    "elbow": ("└──", "`--"),
    "pipe": ("│", "|"),
}


def glyph(name):
    fancy, plain = _GLYPHS[name]
    return fancy if _unicode_ok(sys.stdout) else plain


_RESET = "\033[0m"

_CODES = {
    "bold": "1",
    "dim": "2",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_cyan": "96",
}


def _enable_windows_ansi():
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        for handle_id in (-11, -12):
            handle = kernel32.GetStdHandle(handle_id)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        return True
    except Exception:
        return False


def colors_enabled(stream=None):
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR"):
        return False
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False
    return _enable_windows_ansi()


_COLOR = colors_enabled()


def style(text, *names):
    if not _COLOR or not names:
        return text
    codes = ";".join(_CODES[n] for n in names if n in _CODES)
    if not codes:
        return text
    return f"\033[{codes}m{text}{_RESET}"


def term_width(default=80):
    try:
        return shutil.get_terminal_size((default, 24)).columns
    except OSError:
        return default


def header(title):
    """A bold, underlined section title with a full-width rule beneath it."""
    width = min(term_width(), 80)
    line = style(glyph("rule") * width, "dim")
    print(style(title, "bold", "cyan"))
    print(line)


def rule(char=None):
    print(style((char or glyph("rule")) * min(term_width(), 80), "dim"))


def kv(key, value, key_width=14):
    print(f"  {style(key.ljust(key_width), 'dim')} {value}")


def ok(message):
    print(f"{style(glyph('ok'), 'bright_green')} {message}")


def warn(message):
    print(f"{style(glyph('warn'), 'bright_yellow')} {message}", file=sys.stderr)


def error(message):
    print(f"{style(glyph('error'), 'bright_red')} {message}", file=sys.stderr)


def info(message):
    print(f"{style(glyph('info'), 'cyan')} {message}")


def table(rows, headers, aligns=None):
    """Print an aligned, lightly colorized table.

    ``rows`` is a list of string sequences; ``headers`` labels each column.
    ``aligns`` is an optional per-column ``"l"``/``"r"`` list.
    """
    if not rows:
        return
    columns = len(headers)
    aligns = aligns or ["l"] * columns
    widths = [len(h) for h in headers]
    for row in rows:
        for i in range(columns):
            widths[i] = max(widths[i], len(str(row[i])))

    def fmt(cells, styler=None):
        parts = []
        last = len(cells) - 1
        for i, cell in enumerate(cells):
            text = str(cell)
            pad = widths[i] - len(text)
            if aligns[i] == "r":
                text = " " * pad + text
            elif i != last:
                text = text + " " * pad
            parts.append(styler(text) if styler else text)
        return "  ".join(parts).rstrip()

    print(fmt(headers, lambda t: style(t, "bold")))
    print(style("  ".join(glyph("rule") * w for w in widths), "dim"))
    for row in rows:
        print(fmt(row))
