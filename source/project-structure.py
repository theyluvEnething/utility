#!/usr/bin/env python3
"""project-structure — print the directory tree and copy it to the clipboard."""
import argparse
import os

from utilkit import clipboard, collate, ui, walk


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", default=None,
                        help="Include only these extension(s), e.g. py or [py,js].")
    parser.add_argument("--no-copy", action="store_true",
                        help="Print the tree only; do not touch the clipboard.")
    parser.add_argument("--only-folders", action="store_true",
                        help="Show folders only; ignore files.")
    parser.add_argument("--depth", type=int, default=None,
                        help="Limit tree depth (1 = current folder's contents, 2 = their subfolders, ...).")
    args = parser.parse_args()

    root = os.getcwd()
    only = collate.parse_extension_list(args.only)

    tree = walk.render_tree(root, only_exts=only,
                            only_folders=args.only_folders, depth=args.depth)
    ui.header("Project structure")
    print(tree)

    if not args.no_copy:
        clipboard.copy(tree)
        ui.ok("Structure copied to clipboard.")


if __name__ == "__main__":
    main()
