#!/usr/bin/env python3
"""copy-files — copy XML-wrapped file contents (no tree) to the clipboard.

Optionally filter by extension. Unlike analyze/summarize, this emits just the
<file> blocks with no system prompt, for when you want to paste raw context.
"""
import argparse
import os

from utilkit import clipboard, collate, ui


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", default=None,
                        help="Include only these extension(s), e.g. py or [py,js].")
    parser.add_argument("--ignore", action="append", default=[],
                        help="Extra extension(s) to ignore.")
    args = parser.parse_args()

    root = os.getcwd()
    only = collate.parse_extension_list(args.only)
    extra = collate.parse_extension_list(args.ignore)

    ui.header("copy-files")
    ui.kv("Root", root)
    if only:
        ui.kv("Only", ", ".join(sorted(only)))
    print()

    xml, included, ignored = collate.collate_files(
        root, extra_exts=extra, only_exts=only, report=True
    )

    collate.summarize_run(root, included, ignored)
    if not included:
        ui.warn("No files matched. Clipboard unchanged.")
        return
    clipboard.copy(xml)
    ui.ok(f"{len(included)} file(s) copied to clipboard.")


if __name__ == "__main__":
    main()
