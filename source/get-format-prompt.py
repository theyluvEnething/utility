#!/usr/bin/env python3
import sys

try:
    import pyperclip
except ImportError:
    print("Error: 'pyperclip' library not found.", file=sys.stderr)
    print("It is required to copy the prompt to the clipboard.", file=sys.stderr)
    print("Please install it by running: pip install pyperclip", file=sys.stderr)
    sys.exit(1)

PROMPT_TEXT = """Your previous response deviated from your core directives. This is a formatting and protocol enforcement command.

You MUST adhere to the following rules without exception:
1.  **Persona Adherence**: You are a world-class Principal Software Engineer. All responses must reflect this persona.
2.  **Strict Formatting**: Every file you output MUST be enclosed in the specified XML-style format. This is non-negotiable.

<file path="path/to/your/file.ext">
<![CDATA[
(The full and complete content of the file)
]]>
</file>

Regenerate your entire previous response now. Ensure it is 100% compliant with all persona and formatting rules. Do not include any conversational filler or apologies. Provide only the corrected output.
"""

def main():
    try:
        pyperclip.copy(PROMPT_TEXT)
        print("AI format-correction prompt copied to clipboard.")
    except pyperclip.PyperclipException as e:
        print(f"Error: Could not copy to clipboard: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()