"""Shared library for the utility CLI toolkit.

Every command-line tool in this suite is a thin entry point that imports the
real logic from here. Keeping the shared pieces in one place means the ignore
rules, project walking, clipboard handling, and prompts live in exactly one
location instead of being copy-pasted across a dozen scripts.
"""

__all__ = [
    "config",
    "walk",
    "collate",
    "clipboard",
    "platform_ps",
    "ports",
    "prompts",
    "sessions",
    "ui",
]
