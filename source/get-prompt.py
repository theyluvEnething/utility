#!/usr/bin/env python3
import sys

try:
    import pyperclip
except ImportError:
    print("Error: 'pyperclip' library not found.")
    print("It's needed to copy text to the clipboard.")
    print("Please install it by opening Command Prompt or PowerShell and running:")
    print("pip install pyperclip")
    sys.exit(1)

# --- Updated Prompt Text ---
# Use a raw triple-quoted string (r""")
PROMPT_TEXT = r"""<SYSTEM>
YOU ARE a hyper-focused Format Adherence Engine. Your SOLE purpose is to process project information and generate output conforming EXACTLY to the specified Angle Bracket Format Specification. You are precise, literal, and unforgiving regarding format rules.

**I. USER INPUT FORMAT SPECIFICATION (MANDATORY FOR USER):**

When providing project context, YOU (the user) MUST adhere STRICTLY to the following format for EACH file:

1.  **Start Marker (User Input):** Begin EACH file block with EXACTLY:
    `--- <FILE path/to/your/file.ext> ---`
    *   Replace `[path/to/your/file.ext]` with the relative file path.
    *   Use forward slashes (`/`).
    *   NO extra whitespace.

2.  **File Content (User Input):** Immediately following the start marker, provide the raw, unmodified content of the file.

3.  **End Marker (User Input):** End EACH file block with EXACTLY:
    `--- </FILE path/to/your/file.ext> ---`
    *   The path MUST exactly match the corresponding Start Marker path.
    *   NO extra whitespace.

4.  **Separator (User Input):** Immediately after the End Marker, place a separator line consisting ONLY of five or more equals signs (`=====`).

**II. AI OUTPUT FORMAT SPECIFICATION (MANDATORY FOR AI):**

Your generated output MUST conform EXACTLY to the following format:

1.  **NO EXTRA TEXT:** Your response MUST contain ONLY the formatted file blocks and separators. NO introductory text, NO explanations, NO summaries, NO apologies, NO comments outside file content.
2.  **Start Marker (AI Output):** Each file block MUST begin with EXACTLY:
    `--- <path/to/your/file.ext> ---`
    *   Use relative paths with forward slashes (`/`).
    *   NO extra whitespace.
3.  **Raw File Content (AI Output):** Immediately following the start marker, include the complete, raw, unmodified file content, preserving all original formatting, line breaks, and special characters. NO JSON escaping.
4.  **End Marker (AI Output):** Each file block MUST end with EXACTLY:
    `--- </path/to/your/file.ext> ---`
    *   The path MUST exactly match the corresponding Start Marker path for that block.
    *   NO extra whitespace.
5.  **Separator (AI Output):** Immediately after EACH End Marker (except potentially the very last one), include a separator line consisting ONLY of five or more equals signs (`=====`).
6.  **Full Project Output:** When instructed to modify the project, you MUST output ALL project files (including unchanged ones) in this specified format. NEVER output only changed files, diffs, or snippets.

**Example AI Output Format:**

--- <path/to/file1.txt> ---
Content of file 1.
Line 2 of file 1.
--- </path/to/file1.txt> ---
=========================
--- <src/empty_file.js> ---

--- </src/empty_file.js> ---
=========================
--- <another/path/file2.py> ---
# Content for file 2
def main():
    print("Hello")
--- </another/path/file2.py> ---
=========================


**III. WORKFLOW PROTOCOL:**

1.  **Context Reception:** The user will provide the initial project context using the **User Input Format Specification** (Section I).
2.  **Acknowledgement:** After the user signals the end of context input, your ONLY valid response is: `Context received. Awaiting instructions.` Do NOT process or comment further.
3.  **Instruction:** Await specific instructions from the user (e.g., "Change function X in file Y", "Add file Z").
4.  **Execution & Output:** Execute the instructions. Generate the COMPLETE modified project structure as a single text block, adhering strictly to the **AI Output Format Specification** (Section II). If instructions are ambiguous, ask for clarification concisely, then await refined instructions before generating output.

FAILURE TO ADHERE TO ANY PART OF THESE SPECIFICATIONS IS UNACCEPTABLE. FOCUS SOLELY ON FORMAT AND WORKFLOW.
</SYSTEM>
<USER>
Provide me now with the complete project code from the previous response in the specified angle-bracket format as plain text, ready for copy-and-paste.
</USER>
"""

def main():
    """Copies the predefined prompt text to the clipboard."""
    try:
        pyperclip.copy(PROMPT_TEXT)
        # Update confirmation message slightly
        print("AI prompt text for multi-file (angle-bracket format) generation copied to clipboard!")
    except pyperclip.PyperclipException as e:
        print(f"Error: Could not copy to clipboard: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

# Removed the large commented-out section for JSON prompt.

# #!/usr/bin/env python3
# import sys

# try:
    # import pyperclip
# except ImportError:
    # print("Error: 'pyperclip' library not found.")
    # print("It's needed to copy text to the clipboard.")
    # print("Please install it by opening Command Prompt or PowerShell and running:")
    # print("pip install pyperclip")
    # sys.exit(1)

# PROMPT_TEXT = r"""Format Specification for Project Generation Text:

# Please generate the output as a single block of plain text, adhering strictly to the following multi-file format:

# 1.  **File Structure:** Each file MUST be represented by a block starting with a marker line, followed by the file content, and ending with another marker line and a separator.

# 2.  **Start Marker:** Each file block MUST begin *exactly* with a line formatted as:
    # `--- File: [path/to/your/file.ext] ---`
    # *   Replace `[path/to/your/file.ext]` with the actual relative path for the file.
    # *   Use forward slashes (/) as path separators, regardless of the operating system (e.g., `src/components/Button.js`, NOT `src\components\Button.js`).
    # *   The path MUST be relative to the project root.
    # *   There should be NO leading or trailing whitespace on this line.

# 3.  **File Content:** Immediately following the start marker line (on the next line), include the *raw, unmodified* content of the file.
    # *   Do NOT apply any JSON escaping (like replacing `\` with `\\` or `"` with `\"`). Output the content exactly as it should appear in the file.
    # *   Preserve all original line breaks, indentation, and special characters from the source code or text.

# 4.  **End Marker:** After the complete file content, the block MUST end *exactly* with a line formatted as:
    # `--- End File: [path/to/your/file.ext] ---`
    # *   Crucially, the path here MUST *exactly match* the path used in the corresponding Start Marker line for that file block.
    # *   There should be NO leading or trailing whitespace on this line.

# 5.  **Separator:** Immediately following the End Marker line, there MUST be a line consisting only of multiple equals signs (`=`), typically 5 or more. This separates one file block from the next. Example:
    # `======================================`

# 6.  **Multiple Files:** Repeat steps 2-5 for each file you need to generate. Ensure the separator line exists between consecutive file blocks.

# 7.  **Final Output:** The final output should consist *only* of these formatted blocks, one after another. Do NOT include any introductory text, summaries, or explanations before the first `--- File: ... ---` marker or after the last separator line.

# Example of Correct Format:

# --- File: README.md ---
# # My Project

# This is the main readme file.
# It includes lines with "quotes" and backslashes like C:\path\to\somewhere.
# --- End File: README.md ---
# ======================================
# --- File: src/utils/helpers.js ---
# function greet(name) {
  # // Simple greeting function
  # console.log(`Hello, ${name}!`);
# }

# // Example of regex:
# const whitespaceRegex = /\s+/g;

# module.exports = { greet };
# --- End File: src/utils/helpers.js ---
# ======================================
# --- File: data/config.json ---
# {
  # "version": "1.0",
  # "enabled": true,
  # "settings": {
    # "timeout": 30,
    # "paths": [
      # "/usr/local/bin",
      # "/opt/app/data"
    # ]
  # }
# }
# --- End File: data/config.json ---
# ======================================

# Summary for AI:

# *   Output ONLY the file blocks in the specified format.
# *   Use `--- File: path/file.ext ---` to start.
# *   Provide RAW file content without extra escaping.
# *   Use `--- End File: path/file.ext ---` to end (matching start path).
# *   Use `=================` (or similar) as a separator between files.
# *   Use forward slashes `/` for paths.
# *   No text before the first block or after the last separator.
# """

# def main():
    # """Copies the predefined prompt text to the clipboard."""
    # try:
        # pyperclip.copy(PROMPT_TEXT)
        # print("AI prompt text for multi-file text generation copied to clipboard!")
    # except pyperclip.PyperclipException as e:
        # print(f"Error: Could not copy to clipboard: {e}")
        # sys.exit(1)
    # except Exception as e:
        # print(f"An unexpected error occurred: {e}")
        # sys.exit(1)

# if __name__ == "__main__":
    # main()











# # # --- Filename: get-prompt.py ---
# # #!/usr/bin/env python3
# # import sys

# # # --- Dependencies ---
# # try:
    # # import pyperclip
# # except ImportError:
    # # print("Error: 'pyperclip' library not found.")
    # # print("It's needed to copy text to the clipboard.")
    # # print("Please install it by opening Command Prompt or PowerShell and running:")
    # # print("pip install pyperclip")
    # # sys.exit(1) # Exit if library is missing

# # # --- The Prompt Text ---
# # # Use a raw triple-quoted string (r""") to ensure backslashes within the text
# # # (like in the examples) are treated literally and not as Python escape sequences.
# # PROMPT_TEXT = r"""Format Specification for Project Generation JSON:

# # Please generate the output as a single, valid JSON string adhering strictly to the following format:

# # 1.  Root Element: The top-level element MUST be a JSON array (a list enclosed in [...]).

# # 2.  Array Elements: Each element within the array MUST be a JSON object (enclosed in {...}), representing a single file in the project.

# # 3.  Object Keys: Each file object MUST contain exactly two keys:
    # # *   "filename"
    # # *   "content"

# # 4.  "filename" Value:
    # # *   The value associated with the "filename" key MUST be a JSON string.
    # # *   This string MUST represent the relative path of the file from the project's root directory.
    # # *   CRUCIALLY, use forward slashes (/) as path separators, regardless of the operating system (e.g., "src/components/Button.tsx", NOT "src\components\Button.tsx").
    # # *   The filename string cannot be empty or contain only whitespace.

# # 5.  "content" Value:
    # # *   The value associated with the "content" key MUST be a JSON string.
    # # *   This string MUST contain the entire, raw text content intended for the file.
    # # *   CRITICAL Escaping Rule: All special characters within the file's content MUST be properly escaped according to standard JSON string rules before being placed into the JSON string value. Pay very close attention to the following:
        # # *   Literal double quotes (") within the file content must be escaped as \".
        # # *   Literal backslashes (\) within the file content must be escaped as \\. (This is extremely important for file content that includes regular expressions, Windows paths, or other uses of backslashes).
        # # *   Actual newline characters within the file content must be represented as \n.
        # # *   Actual tab characters within the file content must be represented as \t.
        # # *   Other standard JSON escapes like \r, \b, \f, \/ (optional for slash) are also valid if needed, but quotes, backslashes, and newlines are the most common source of errors if not handled correctly.

# # Example of Correct Format:

# # [
  # # {
    # # "filename": "README.md",
    # # "content": "# My Project\n\nThis is the main readme file.\nIt includes lines with \"quotes\" and backslashes like C:\\path\\to\\somewhere.\n"
  # # },
  # # {
    # # "filename": "src/utils/helpers.js",
    # # "content": "function greet(name) {\n  // Simple greeting function\n  console.log(`Hello, ${name}!`);\n}\n\n// Example of regex needing escaped backslash in JSON:\n// const whitespaceRegex = /\s+/g; \n// JSON representation below:\nconst whitespaceRegex = /\\s+/g;\n\nmodule.exports = { greet };\n"
  # # },
  # # {
    # # "filename": "data/config.json",
    # # "content": "{\n  \"version\": \"1.0\",\n  \"enabled\": true,\n  \"settings\": {\n    \"timeout\": 30,\n    \"paths\": [\n      \"/usr/local/bin\",\n      \"/opt/app/data\"\n    ]\n  }\n}"
  # # }
# # ]

# # Summary for AI:

# # *   Output a single JSON array [...].
# # *   Each element is an object {...} with "filename" and "content" keys only.
# # *   "filename" is a string with relative paths using /.
# # *   "content" is a string containing the file text, with all necessary JSON string escapes applied (especially \" for quotes, \\ for backslashes, \n for newlines).
# # *   Ensure the final output is nothing but this valid JSON structure.
# # """

# # def main():
    # # """Copies the predefined prompt text to the clipboard."""
    # # try:
        # # pyperclip.copy(PROMPT_TEXT)
        # # print("AI prompt text for JSON generation copied to clipboard!")
    # # except pyperclip.PyperclipException as e:
        # # print(f"Error: Could not copy to clipboard: {e}")
        # # sys.exit(1)
    # # except Exception as e:
        # # print(f"An unexpected error occurred: {e}")
        # # sys.exit(1)

# # if __name__ == "__main__":
    # # main()