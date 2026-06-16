#!/usr/bin/env python3
"""generate-project — apply <file>/<delete>/<rename> blocks from the clipboard.

Reads an LLM response from the clipboard, previews the file operations it
describes, and applies them to the current directory after you confirm.
"""
import os
import sys

from utilkit import clipboard, fileops, ui


def main():
    content = clipboard.paste()
    if not content or content.isspace():
        ui.error("Clipboard is empty.")
        sys.exit(1)

    operations, warnings = fileops.parse(content)
    for w in warnings:
        ui.warn(w)

    safe, unsafe = [], []
    for op in operations:
        paths = [op["from"], op["to"]] if op["type"] == "rename" else [op["path"]]
        (safe if all(fileops.is_safe(p) for p in paths) else unsafe).append(op)

    if not safe:
        ui.error("No safe operations to apply.")
        sys.exit(1)

    root = os.getcwd()
    ui.header("generate-project")
    ui.kv("Target", root)
    print()

    renames = [o for o in safe if o["type"] == "rename"]
    deletes = [o for o in safe if o["type"] == "delete"]
    creates = [o for o in safe if o["type"] == "create"]

    for op in renames:
        print(f"  {ui.style('rename', 'yellow')}  {op['from']} -> {op['to']}")
    for op in deletes:
        print(f"  {ui.style('delete', 'bright_red')}  {op['path']}")
    for op in creates:
        size = len(op["content"])
        print(f"  {ui.style('write ', 'green')}  {op['path']} ({size} bytes)")
    for op in unsafe:
        label = f"{op.get('from')} -> {op.get('to')}" if op["type"] == "rename" else op.get("path")
        ui.warn(f"unsafe path skipped: {label}")

    print()
    try:
        answer = input(ui.style(f"Apply {len(safe)} operation(s)? [y/N] ", "cyan")).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        ui.warn("Aborted.")
        sys.exit(1)
    if answer != "y":
        ui.warn("Cancelled.")
        sys.exit(0)

    counts = fileops.apply(safe, root)
    print()
    ui.rule()
    ui.kv("Created", str(counts["created"]))
    ui.kv("Deleted", str(counts["deleted"]))
    ui.kv("Renamed", str(counts["renamed"]))
    if counts["errors"]:
        ui.error(f"{counts['errors']} operation(s) failed.")
        sys.exit(1)
    ui.ok("All operations applied.")


if __name__ == "__main__":
    main()
