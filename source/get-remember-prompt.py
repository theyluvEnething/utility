#!/usr/bin/env python3
"""get-remember-prompt — copy a short 'keep using the file format' reminder."""
from utilkit import clipboard, prompts, ui


def main():
    clipboard.copy(prompts.REMEMBER_PROMPT)
    ui.ok("Reminder prompt copied to clipboard.")


if __name__ == "__main__":
    main()
