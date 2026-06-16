#!/usr/bin/env python3
"""get-format-prompt — copy a 'please re-emit in the file format' prompt."""
from utilkit import clipboard, prompts, ui


def main():
    clipboard.copy(prompts.FORMAT_CORRECTION_PROMPT)
    ui.ok("Format-correction prompt copied to clipboard.")


if __name__ == "__main__":
    main()
