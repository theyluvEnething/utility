"""Project walking: ignore decisions, directory-tree rendering, binary detection.

Extracted from the four context tools that each carried their own copy. The
ignore sets come from :mod:`utilkit.config`; per-invocation extra ignores and
an ``only`` allow-list are passed in by the caller.
"""
import io
import os
import sys

from . import config, ui


def is_binary(path):
    try:
        with open(path, "rb") as f:
            return b"\0" in f.read(1024)
    except OSError:
        return True


def _ext(filename):
    return os.path.splitext(filename)[1].lower().lstrip(".")


def should_ignore(path, root, *, extra_exts=None, only_exts=None):
    """Return True if ``path`` should be excluded from collation/tree output."""
    extra_exts = extra_exts or set()
    only_exts = only_exts or set()
    abs_path = os.path.abspath(path)
    filename = os.path.basename(abs_path)

    try:
        rel = os.path.relpath(abs_path, root)
    except ValueError:
        return True

    parts = rel.replace(os.sep, "/").split("/")
    if any(part in config.IGNORED_DIRECTORIES for part in parts):
        return True
    if filename in config.IGNORED_FILENAMES:
        return True

    if os.path.isfile(abs_path):
        ext = _ext(filename)
        if ext in config.IGNORED_EXTENSIONS or ext in extra_exts:
            return True
        if only_exts and ext not in only_exts:
            return True

    try:
        script = os.path.abspath(sys.argv[0])
        if os.path.exists(script) and os.path.samefile(abs_path, script):
            return True
    except (OSError, ValueError):
        pass
    return False


def render_tree(root, *, extra_exts=None, only_exts=None, only_folders=False, depth=None):
    """Return a string drawing of the directory tree rooted at ``root``.

    ``only_folders`` excludes files from the output. ``depth`` limits how many
    levels are shown (1 = immediate children of ``root``, 2 = their children, ...).
    """
    out = io.StringIO()
    seen = set()

    tee = ui.glyph("tee") + " "
    elbow = ui.glyph("elbow") + " "
    pipe = ui.glyph("pipe") + "   "

    def recurse(current, prefix, level):
        if depth is not None and level > depth:
            return
        try:
            real = os.path.realpath(current)
            if real in seen:
                out.write(f"{prefix}{elbow}[symlink cycle: {os.path.basename(current)}]\n")
                return
            seen.add(real)
            entries = sorted(os.listdir(current), key=str.lower)
        except OSError:
            return

        items = []
        for entry in entries:
            full = os.path.join(current, entry)
            is_dir = os.path.isdir(full)
            if only_folders and not is_dir:
                continue
            if not should_ignore(full, root, extra_exts=extra_exts, only_exts=only_exts):
                items.append((entry, full, is_dir))

        for i, (name, full, is_dir) in enumerate(items):
            last = i == len(items) - 1
            connector = elbow if last else tee
            suffix = "/" if is_dir else ""
            out.write(f"{prefix}{connector}{name}{suffix}\n")
            if is_dir:
                recurse(full, prefix + ("    " if last else pipe), level + 1)

    out.write(f"{os.path.basename(os.path.abspath(root)) or root}/\n")
    recurse(root, "", 1)
    return out.getvalue()


def iter_text_files(root, *, extra_exts=None, only_exts=None):
    """Yield ``(relative_path, absolute_path)`` for each includable text file."""
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        dirnames[:] = [
            d for d in dirnames
            if not should_ignore(os.path.join(dirpath, d), root,
                                  extra_exts=extra_exts, only_exts=only_exts)
        ]
        for filename in sorted(filenames):
            full = os.path.join(dirpath, filename)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if should_ignore(full, root, extra_exts=extra_exts, only_exts=only_exts):
                continue
            if is_binary(full):
                continue
            yield rel, full
