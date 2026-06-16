"""Collate a project into the XML file format and assemble full LLM prompts."""
import os
import sys

from . import ui, walk


def collate_files(root, *, extra_exts=None, only_exts=None, report=True):
    """Walk the project and return ``(xml_text, included, ignored_count)``.

    When ``report`` is True, prints each file as it is processed so the user can
    watch progress, just like the original tools did.
    """
    blocks = []
    included = []
    ignored = 0

    for rel, full in walk.iter_text_files(root, extra_exts=extra_exts, only_exts=only_exts):
        if report:
            print(f"  {ui.style('+', 'green')} {rel}")
        try:
            with open(full, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError as exc:
            ui.warn(f"could not read {rel}: {exc}")
            ignored += 1
            continue
        blocks.append(f'<file path="{rel}">\n<![CDATA[\n{content}\n]]>\n</file>')
        included.append(rel)

    return "\n".join(blocks), included, ignored


def build_prompt(system_prompt, *, root, include_tree=True,
                 extra_exts=None, only_exts=None, report=True):
    """Assemble a complete prompt: system prompt + optional tree + file contents."""
    parts = [system_prompt, "\n\n<context>\n"]

    if include_tree:
        if report:
            ui.info("building directory tree")
        parts.append("Directory tree:\n\n")
        parts.append(walk.render_tree(root, extra_exts=extra_exts, only_exts=only_exts))
        parts.append("\nFile contents:\n\n")

    if report:
        ui.info("collating files")
    xml, included, ignored = collate_files(
        root, extra_exts=extra_exts, only_exts=only_exts, report=report
    )
    parts.append(xml)
    parts.append("\n</context>")

    return "".join(parts), included, ignored


def parse_extension_list(raw):
    """Parse ``py`` or ``[py,js,css]`` into a set of bare extensions."""
    result = set()
    if not raw:
        return result
    items = raw if isinstance(raw, list) else [raw]
    for item in items:
        item = item.strip()
        if item.startswith("[") and item.endswith("]"):
            result.update(e.strip().lstrip(".") for e in item[1:-1].split(",") if e.strip())
        elif item:
            result.add(item.lstrip("."))
    return result


def summarize_run(root, included, ignored):
    """Print a tidy summary of what was collated."""
    ui.rule()
    ui.kv("Root", root)
    ui.kv("Included", f"{len(included)} file(s)")
    if ignored:
        ui.kv("Skipped", f"{ignored} file(s)")
