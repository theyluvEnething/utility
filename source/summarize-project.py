#!/usr/bin/env python3
"""summarize-project — collate the project + a code-generation prompt to clipboard.

Same collation as analyze-project, but the system prompt puts the model in
'make the change and output full files' mode, paired with generate-project.
"""
import argparse
import os

from utilkit import clipboard, collate, prompts, ui


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ignore", action="append", default=[],
                        help="Extra extension(s) to ignore, e.g. json or [json,txt].")
    parser.add_argument("--only", default=None,
                        help="Include only these extension(s), e.g. py or [py,js].")
    parser.add_argument("--no-tree", action="store_true",
                        help="Omit the directory tree from the prompt.")
    args = parser.parse_args()

    root = os.getcwd()
    extra = collate.parse_extension_list(args.ignore)
    only = collate.parse_extension_list(args.only)

    ui.header("summarize-project")
    ui.kv("Root", root)
    if only:
        ui.kv("Only", ", ".join(sorted(only)))
    print()

    prompt, included, ignored = collate.build_prompt(
        prompts.GENERATE_SYSTEM_PROMPT, root=root, include_tree=not args.no_tree,
        extra_exts=extra, only_exts=only,
    )

    collate.summarize_run(root, included, ignored)
    if not included:
        ui.warn("No files matched. Clipboard unchanged.")
        return
    clipboard.copy(prompt)
    ui.ok(f"Generation prompt for {len(included)} file(s) copied to clipboard.")


if __name__ == "__main__":
    main()
