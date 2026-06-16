"""Parse and apply <file>/<delete>/<rename> operation blocks.

Used by generate-project to turn an LLM response (pasted from the clipboard)
into filesystem changes, with path-safety checks that keep operations inside
the target directory.
"""
import os
import re
import shutil

FILE_BLOCK = re.compile(r'<file path="(.+?)">\s*<!\[CDATA\[(.*?)]]>\s*</file>', re.DOTALL)
DELETE_TAG = re.compile(r'<delete\s+path="([^"]+)"\s*/>', re.DOTALL)
RENAME_TAG = re.compile(r'<rename\s+from="([^"]+)"\s+to="([^"]+)"\s*/>', re.DOTALL)


def parse(text):
    """Return ``(operations, warnings)`` parsed from ``text`` in document order."""
    matches = []
    for pattern, kind in ((FILE_BLOCK, "create"), (DELETE_TAG, "delete"), (RENAME_TAG, "rename")):
        for m in pattern.finditer(text):
            matches.append((m, kind))
    matches.sort(key=lambda pair: pair[0].start())

    operations = []
    warnings = []
    for match, kind in matches:
        if kind == "create":
            path = match.group(1).strip()
            content = re.sub(r"^\r?\n", "", match.group(2))
            content = re.sub(r"\r?\n$", "", content)
            if path:
                operations.append({"type": "create", "path": path, "content": content})
            else:
                warnings.append("<file> tag with empty path skipped.")
        elif kind == "delete":
            path = match.group(1).strip()
            if path:
                operations.append({"type": "delete", "path": path})
            else:
                warnings.append("<delete> tag with empty path skipped.")
        elif kind == "rename":
            src, dst = match.group(1).strip(), match.group(2).strip()
            if src and dst:
                operations.append({"type": "rename", "from": src, "to": dst})
            else:
                warnings.append("<rename> tag with empty from/to skipped.")

    if not operations and not warnings:
        warnings.append("No <file>, <delete>, or <rename> blocks found.")
    return operations, warnings


def is_safe(path):
    """Reject absolute paths and any parent-directory traversal."""
    norm = os.path.normpath(path).replace("\\", "/")
    return not (os.path.isabs(norm) or norm == ".." or norm.startswith("../") or "/../" in norm)


def apply(operations, root):
    """Apply parsed operations under ``root``. Returns a counts dict."""
    counts = {"created": 0, "deleted": 0, "renamed": 0, "errors": 0}

    for op in operations:
        if op["type"] == "rename":
            try:
                src = os.path.join(root, os.path.normpath(op["from"]))
                dst = os.path.join(root, os.path.normpath(op["to"]))
                os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
                os.replace(src, dst)
                counts["renamed"] += 1
            except OSError:
                counts["errors"] += 1
        elif op["type"] == "delete":
            try:
                path = os.path.join(root, os.path.normpath(op["path"]))
                if os.path.islink(path) or os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                counts["deleted"] += 1
            except OSError:
                counts["errors"] += 1
        elif op["type"] == "create":
            try:
                path = os.path.join(root, os.path.normpath(op["path"]))
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(op["content"])
                counts["created"] += 1
            except OSError:
                counts["errors"] += 1

    return counts
