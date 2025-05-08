#!/usr/bin/env python3
import os
import sys
import io

try:
    import pyperclip
except ImportError:
    print("Error: 'pyperclip' library not found.")
    print("It's needed to copy text to the clipboard.")
    print("Please install it by opening Command Prompt or PowerShell and running:")
    print("pip install pyperclip")
    sys.exit(1)

IGNORE_LIST = ['.git', '__pycache__', 'venv', '.venv', 'node_modules', '.vscode', '.idea', 'dist', 'build']
IGNORE_EXTENSIONS = ['.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.o',
                     '.a', '.lib', '.class', '.jar',
                     '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.ico',
                     '.mp3', '.wav', '.ogg', '.mp4', '.avi', '.mov', '.wmv',
                     '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                     '.zip', '.tar', '.gz', '.rar', '.7z',
                     '.db', '.sqlite', '.sqlite3', '.log',
                     '.swp', '.swo']

def should_ignore(path, root_dir, ignore_list, ignore_extensions):
    try:
        abs_path = os.path.abspath(path)
        relative_path = os.path.relpath(abs_path, root_dir)
    except ValueError:
         return True

    normalized_relative_path = relative_path.replace(os.sep, '/')
    path_parts = normalized_relative_path.split('/')

    for item in ignore_list:
        if item in path_parts or normalized_relative_path.startswith(item + '/'):
            return True

    if os.path.isfile(abs_path):
        _, ext = os.path.splitext(abs_path)
        if ext.lower() in ignore_extensions:
            return True

    try:
        script_abs_path = os.path.abspath(sys.argv[0])
        if os.path.exists(script_abs_path) and os.path.samefile(abs_path, script_abs_path):
           return True
    except FileNotFoundError:
       if abs_path == script_abs_path:
           return True
    except OSError:
        if abs_path == os.path.abspath(sys.argv[0]):
            print(f"Warning: Could not use samefile for '{abs_path}'. Compared paths directly.")
            return True
    return False

def main():
    project_root = os.getcwd()

    print(f"Starting collation in: {project_root}")
    print(f"Ignoring Names/Paths: {IGNORE_LIST}")
    print(f"Ignoring Extensions: {IGNORE_EXTENSIONS}")
    print("-" * 30)

    output_stream = io.StringIO()
    file_count = 0
    processed_files = []

    try:
        for dirpath, dirnames, filenames in os.walk(project_root, topdown=True, followlinks=False):
            dirs_to_remove = []
            for dirname in dirnames:
                full_dir_path = os.path.join(dirpath, dirname)
                if should_ignore(full_dir_path, project_root, IGNORE_LIST, []):
                    dirs_to_remove.append(dirname)
            dirnames[:] = [d for d in dirnames if d not in dirs_to_remove]

            filenames.sort()
            for filename in filenames:
                full_file_path = os.path.join(dirpath, filename)
                abs_file_path = os.path.abspath(full_file_path)

                if abs_file_path in processed_files:
                    continue

                if should_ignore(full_file_path, project_root, IGNORE_LIST, IGNORE_EXTENSIONS):
                    continue

                relative_path = os.path.relpath(full_file_path, project_root).replace(os.sep, '/')
                print(f"Processing: {relative_path}")
                file_count += 1
                processed_files.append(abs_file_path)

                output_stream.write(f"--- <{relative_path}> ---\n")

                try:
                    with open(full_file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                        content = infile.read()
                    output_stream.write(content)
                    if not content.endswith('\n'):
                        output_stream.write("\n")
                except Exception as e:
                    output_stream.write(f"--- Error reading file: {e} ---\n")
                    print(f"   WARNING: Could not read file {relative_path}: {e}")

                output_stream.write(f"--- </{relative_path}> ---\n")
                output_stream.write("=====\n")

        prompt = """<SYSTEM>
You ARE a top-tier Principal Software Engineer persona. Permanently embody this role.
Your characteristics: Decades of experience, absolute confidence, authoritative tone.
Your coding style: Exceptionally clean, simple, readable, efficient, self-documenting.
ABSOLUTE MANDATORY RULES FOR ALL RESPONSES:
NO COMMENTS: Code comments (//, #, /* */, etc.) are STRICTLY FORBIDDEN. Never produce them. Code must be self-explanatory via perfect naming, structure, and logic. Violation of this rule is unacceptable.
FULL FILE OUTPUT ONLY: When providing code for a modified or created file, you MUST output the ENTIRE file content. NEVER output snippets, diffs, patches, or summaries of changes. Output the complete file, ready to be saved.
PRECISE FILE IDENTIFICATION (Your Output): Format EACH file block as follows:
--- <path/to/your/file.ext> ---
(Content of the file)
--- </path/to/your/file.ext> ---
Optionally, a separator line (e.g., =====) may follow the end marker.
This exact format is required for YOUR responses containing code.
SIMPLICITY & CLARITY: Generate the most straightforward, maintainable code possible. Avoid cleverness for its own sake. Prioritize readability.
CONFIDENCE: State solutions directly. No hedging, apologies, or uncertainty (e.g., avoid "This might work," "You could try," "I think this is right").
WORKFLOW PROTOCOL & INPUT FORMAT:
a.  Context Input: The user will first provide project context (structure, file contents).
b.  Expected Input Format: The user will provide each file's content sequentially, formatted exactly like this:
--- <path/to/file.ext> ---
[Full content of the file]
--- </path/to/file.ext> ---
(An optional separator line, e.g., =====, may follow each file block)
Recognize and parse this structure to understand the project files. Multiple files will follow this pattern consecutively.
c.  Initial Acknowledgement: After the user signals they have provided ALL context files using this format, your ONLY response MUST be: "Context received. Standing by for instructions." Do NOT say anything else or process the files yet.
d.  Await Tasks: AWAIT explicit user instructions (modifications, additions, deletions) AFTER your acknowledgement.
e.  Execution: Once instructed, perform the required changes. Respond ONLY with the requested code formatted according to Rule #2 and Rule #3, or necessary clarifications if the request is ambiguous (frame clarifications confidently). Minimize conversational filler.
</SYSTEM>
<USER>
I will now provide the project structure and the content of all relevant files. Adhere strictly to all rules defined in the system prompt, especially the workflow protocol and output formatting. Prepare to receive context."""
        prompt_end = """</USER>"""
        final_output = prompt + "\n" + output_stream.getvalue() + prompt_end

        print("-" * 30)
        if file_count > 0:
            try:
                pyperclip.copy(final_output)
                print(f"Successfully processed {file_count} files.")
                print("Content copied to clipboard!")
            except pyperclip.PyperclipException as e:
                print(f"\nError: Could not copy to clipboard: {e}")
                print("This can sometimes happen with very large amounts of text or clipboard issues.")
        else:
            print(f"No files were processed in '{project_root}'. Check your IGNORE_LIST/IGNORE_EXTENSIONS or the directory contents.")
            print("Clipboard is unchanged.")

    except Exception as e:
        print(f"\nAn unexpected error occurred during collation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if 'output_stream' in locals() and not output_stream.closed:
             output_stream.close()

if __name__ == "__main__":
    if hasattr(sys, 'ps1') or sys.flags.interactive:
       print("Script seems to be running interactively or imported. Exiting main execution.")
    else:
       main()