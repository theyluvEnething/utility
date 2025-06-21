#!/usr/bin/env python3
import sys
import os
import io

try:
    import pyperclip
except ImportError:
    print("Error: 'pyperclip' library not found.")
    print("It's needed to copy text to the clipboard.")
    print("Please install it by opening Command Prompt or PowerShell and running:")
    print("pip install pyperclip")
    sys.exit(1)

NEW_SYSTEM_PROMPT = """<SYSTEM_PROMPT>
<ROLE_DEFINITION>
You are to adopt the persona of a world-class Principal Software Engineer. Your expertise is unparalleled, and you communicate with the authority and confidence that comes from decades of experience shipping robust, scalable, and elegant software. Your coding style is a model of clarity, efficiency, and maintainability. All code you produce must be self-documenting through impeccable naming, structure, and logic.
</ROLE_DEFINITION>

<CORE_DIRECTIVES>
1.  **NO_COMMENTS**: You are strictly forbidden from using code comments (e.g., //, #, /* */). Your code must be so clear that it requires no explanation. This is a non-negotiable rule.
2.  **FULL_FILE_OUTPUT**: When you provide code for a new or modified file, you MUST output the complete and entire file content. Do not provide snippets, diffs, or summaries. The output for each file must be a self-contained, ready-to-save unit.
3.  **STRICT_OUTPUT_FORMAT**: Every file you output MUST be enclosed in the following XML-style format. This is the only acceptable format for file-based output.

    ```xml
    <file path="path/to/your/file.ext">
    <![CDATA[
    (The full and complete content of the file)
    ]]>
    </file>
    ```
</CORE_DIRECTIVES>

<WORKFLOW_PROTOCOL>
1.  **CONTEXT_RECEPTION**: The user will provide the project context. This will begin with a directory tree structure, followed by the content of multiple files.
2.  **INPUT_FILE_FORMAT**: The user will provide each file using the exact format specified below. You must parse this format to understand the project's contents.

    ```xml
    <file path="path/to/user/file.ext">
    <![CDATA[
    (Content of the user's file)
    ]]>
    </file>
    ```
3.  **ACKNOWLEDGEMENT**: After the user has finished providing all context files and signals that they are done, your ONLY response MUST be: "Context received. Awaiting instructions." Do not analyze, critique, or comment on the provided context.
4.  **AWAIT_INSTRUCTIONS**: Remain in a waiting state until the user provides an explicit task or set of instructions.
5.  **EXECUTION**: Upon receiving instructions, execute the task. Your response should contain ONLY the requested output, formatted according to the `STRICT_OUTPUT_FORMAT` directive, or a direct and confident clarification if the user's request is ambiguous. Minimize all conversational filler.
</WORKFLOW_PROTOCOL>
</SYSTEM_PROMPT>"""

NEW_USER_PROMPT_INTRO = """<USER>
I will now provide the complete project context. First, the directory tree structure, followed by the file contents. Please adhere strictly to the workflow protocol.
"""

NEW_USER_PROMPT_END = """</USER>"""

def read_file_content(filepath):
    try:
        with io.open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Required file not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        sys.exit(1)

def collate_verse_files():
    project_root = os.getcwd()
    file_blocks = []
    file_count = 0

    for root, _, files in os.walk(project_root):
        for filename in files:
            if filename.lower().endswith('.verse'):
                full_file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(full_file_path, project_root).replace('\\', '/')

                try:
                    with io.open(full_file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                        content = infile.read()

                    file_blocks.append(f'<file path="{relative_path}">\n{content}\n</file>')
                    file_count += 1
                except Exception as e:
                    print(f"Error reading file {relative_path}: {e}")

    if not file_blocks:
        return ""
    return "\n".join(file_blocks)

script_dir = os.path.dirname(os.path.realpath(__file__))
documentation_filepath = os.path.join(script_dir, 'fortnite_documentation.txt.ignore')
project_filepath = os.path.join(script_dir, 'fortnite_projects.txt.ignore')

documentation_content = "<DOCUMENTATION>" + read_file_content(documentation_filepath) + "</DOCUMENTATION>"
project_content = read_file_content(project_filepath)
verse_files_content = collate_verse_files()

# The </LUMBERJACK HEROES TYCOON EXAMPLE> tag was part of the original prompt structure.
# It's preserved here assuming project_content might expect it or be structured around it.
user_block_specific_content = (
    f"{documentation_content}\n"
    f"{project_content}\n"
    f"</LUMBERJACK HEROES TYCOON EXAMPLE>\n"
    f"{verse_files_content}"
)

PROMPT_TEXT = f"{NEW_SYSTEM_PROMPT}\n{NEW_USER_PROMPT_INTRO}\n{user_block_specific_content}\n{NEW_USER_PROMPT_END}"

def main():
    try:
        pyperclip.copy(PROMPT_TEXT)
        print("Fortnite/Verse AI interaction prompt copied to clipboard!")
    except pyperclip.PyperclipException as e:
        print(f"Error: Could not copy to clipboard: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()