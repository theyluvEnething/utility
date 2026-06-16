#!/usr/bin/env python3
"""get-programming-prompt — copy the standard 'engineer + file contract' prompt."""
from utilkit import clipboard, prompts, ui


def main():
    clipboard.copy(prompts.PROGRAMMING_PROMPT)
    ui.ok("Programming prompt copied to clipboard.")


if __name__ == "__main__":
    main()
