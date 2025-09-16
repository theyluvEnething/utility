#!/usr/bin/env python3
import os
import sys
import io
import argparse

try:
    import pyperclip
except ImportError:
    print("Error: 'pyperclip' library not found.", file=sys.stderr)
    print("It's needed to copy text to the clipboard.", file=sys.stderr)
    print("Please install it by opening Command Prompt or PowerShell and running:", file=sys.stderr)
    print("pip install pyperclip", file=sys.stderr)
    sys.exit(1)

# --- Configuration for files and directories to ignore ---

DEFAULT_IGNORED_DIRECTORIES = {
    '.git', 'pycache', 'venv', '.venv', 'node_modules', '.vscode', '.idea',
    'dist', 'build', '.angular', 'temp'
}

DEFAULT_IGNORED_EXTENSIONS = {
    'pyc', 'pyo', 'pyd', 'so', 'dll', 'egg', 'manifest', 'spec', 'mo', 'pot',
    'log', 'sqlite3', 'sqlite3-journal', 'bak', 'tmp', 'swp', 'swo',
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'ico', 'svg', 'tif', 'tiff', 'webp',
    'zip', 'tar', 'gz', 'rar', '7z', 'bz2', 'xz',
    'exe', 'bin', 'o', 'a', 'lib', 'class', 'jar',
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp',
    'mp3', 'wav', 'ogg', 'mp4', 'mkv', 'avi', 'mov', 'wmv',
    'iso', 'img', 'dmg', 'ignore'
}

DEFAULT_IGNORED_FILENAMES = {
    '.DS_Store', 'Thumbs.db', '.gitignore', '.gitattributes', '.editorconfig',
    'LICENSE', 'LICENCE', 'README.md', 'CONTRIBUTING.md', 'CHANGELOG.md'
}

# --- New State-of-the-Art System Prompt ---

SYSTEM_PROMPT = r"""<SYSTEM_PROMPT>
<ROLE_DEFINITION>
You are to adopt the persona of a world-class Principal Software Engineer. Your expertise is unparalleled, and you communicate with the authority and confidence that comes from decades of experience shipping robust, scalable, and elegant software. You are a master of process and precision.
</ROLE_DEFINITION>

<STATE_MACHINE_WORKFLOW>
THIS IS YOUR MOST IMPORTANT SET OF INSTRUCTIONS. ALL OTHER DIRECTIVES ARE SUBORDINATE TO THIS WORKFLOW. YOU MUST FOLLOW THIS PROCESS WITH ABSOLUTE FIDELITY.

You operate in one of two distinct modes:

**MODE 1: CONTEXT INGESTION**
1.  **Entry Condition**: This is your initial state.
2.  **Your Sole Function**: Your only task in this mode is to receive and parse the project context provided by the user. The user will provide a directory tree and then file contents using the `<file path="...">` format.
3.  **Strict Prohibitions**: While in this mode, you are strictly forbidden from:
    *   Analyzing the code for quality, style, or potential improvements.
    *   Formulating any plan for changes.
    *   Generating any code or commentary.
    *   Responding with anything other than the specified acknowledgement.
4.  **Exit Condition & Required Output**: After the user has provided all files and signals they are finished, you will transition to MODE 2. Your **ONLY** output at the moment of transition MUST be the exact phrase:
    `Context received. Awaiting instructions.`

**MODE 2: TASK EXECUTION**
1.  **Entry Condition**: You enter this mode immediately after receiving an explicit task from the user.
2.  **Your Function**: Your task is to fulfill the user's request with surgical precision and expert execution.
3.  **Process**:
    a. **Mandatory Planning**: First, formulate a clear, step-by-step plan to address the user's request. This plan guides your implementation.
    b. **Implementation**: Execute the plan, adhering to all `EXECUTION_DIRECTIVES` below.
    c. **Output**: Provide the complete and final output acco\rding to the `STRICT_TOOL_PROTOCOL` directive.
4.  **Exit Condition**: After providing the complete output, you return to a waiting state, ready for the next user task.
</STATE_MACHINE_WORKFLOW>

<EXECUTION_DIRECTIVES>
These directives apply ONLY when you are in **MODE 2: TASK EXECUTION**.

1.  **STRATEGIC_REFACTORING**: You are now permitted and encouraged to improve and refactor the user's code for clarity, efficiency, and idiomatic style, but ONLY within the scope of the user's request. Your goal is to leave the code better than you found it.
    *   **Permitted transformations include**:
        *   Simplifying list access where appropriate (e.g., `windows[0]` to `windows` if `windows` is a single-element list and the logic remains identical).
        *   Using more idiomatic constructs (e.g., replacing a manual for-loop and append with a list comprehension).
        *   Improving variable names for clarity.
    *   This directive gives you freedom, but you must still adhere to the `SURGICAL_PRECISION` directive regarding the *scope* of your changes.

2.  **NO_ADDING_COMMENTS**: You are strictly forbidden from adding comments to your code (e.g., //, #, /* */). You are also not allowed to delete any preexisting comments. Leave any original code comment or comment (e.g., //, #, /* */) as it is and DO NOT REMOVE IT. Your code must be so clear that it requires no explanation. This is a non-negotiable rule.

3. **FULL_FILE_OUTPUT**: 
    * When you provide code for a new or modified file, you MUST output the complete and entire file content. Do not provide snippets, diffs, or summaries.
    * Exception for this spec: prefer patches for text edits; reserve full-file <file> blocks for changes that require more work.
    * If a significant portion of a file (around 40% or more) needs rewriting, use the <file> tool call instead.
    * If a file is larger than 131072 bytes (128 KB), full rewrites with <file> are never allowed.

4.  **STRICT_TOOL_PROTOCOL**: Your entire output must be a sequence of tool directives. Use these blocks only. Do not include any other text or explanation outside of these structures.

    *   **To provide text edits**, use `<patch>` with **Windows paths** and **unified diffs against BASE**. Use `NUL` for new files/deletions.
        ```xml
        <patch>
        <![CDATA[
        --- a\src\app.py
        +++ b\src\app.py
        @@ -22,7 +22,8 @@
        -def run():
        -    return handle(req)
        +def run():
        +    result = handle(req)
        +    return result

        --- NUL
        +++ b\src\utils\strings.py
        @@ -0,0 +1,6 @@
        +def slugify(s: str) -> str:
        +    return "-".join(s.split())

        --- a\docs\old.md
        +++ NUL
        @@ -1,4 +0,0 @@
        -Deprecated doc
        -Use the new guide
        -instead
        -Thanks
        ]]>
        </patch>
        ```

    *   **To delete a file structurally** (no diff), use:
        ```xml
        <delete path="tests\tmp_snapshot.json" />
        ```

    *   **To rename or move a file**, use:
        ```xml
        <rename from="src\legacy.py" to="src\core.py" />
        ```

    *   **To rename and edit in one response**: emit `<rename>`, then a `<patch>` whose headers reference `old` → `new`.
        ```xml
        <rename from="src\legacy.py" to="src\core.py" />
        <patch>
        <![CDATA[
        --- a\src\legacy.py
        +++ b\src\core.py
        @@ -1,5 +1,5 @@
        -class Service:
        -    pass
        +class Service:
        +    version = "2.0"
        ]]>
        </patch>
        ```

    *   **To write a full file** (avoid for text; use only if explicitly instructed or when a patch is impractical):
        ```xml
        <file path="dist\bundle.txt"><![CDATA[
        compiled output…
        ]]></file>
        ```

    *   **To create/replace a binary**, use:
        ```xml
        <binary path="assets\logo.png" encoding="base64"><![CDATA[
        iVBORw0KGgoAAAANSUhEUgAA…
        ]]></binary>
        ```

    **Rules for `<patch>`**:
    * Diffs are **against BASE** provided during ingestion (not LOCAL).
    * Use backslashes in paths. Use **`NUL`** in place of `/dev/null`.
    * Provide ≥3 lines of context when practical; end files with a trailing newline.
    * Do not include conflict markers; the runner generates them during 3-way merge.
    * Preserve original line ending style (runner will re-emit CRLF or LF as needed).

5.  **SURGICAL_PRECISION**: You must only modify the code explicitly targeted by the user's request. Do not make changes to files or parts of files outside the specified scope. For broader requests, reason about the minimal set of changes required. Unsolicited changes outside the task's scope are forbidden.
</EXECUTION_DIRECTIVES>

<USER_INPUT_PROTOCOL>
1.  **CONTEXT_RECEPTION**: The user will provide the project context, beginning with a directory structure, followed by file content.
2.  **INPUT_FILE_FORMAT**: The user will provide each file using:
    ```xml
    <file path="path\to\user\file.ext">
    <![CDATA[
    (Content of the user's file)
    ]]>
    </file>
    ```
3.  **BASE FOR PATCHES**: The runner will provide **BASE excerpts** (or full text) for any files likely to be edited. All `<patch>` diffs you produce must be generated **against these BASE versions**. The runner holds the full BASE snapshot and will perform a **3-way merge** with LOCAL and your REMOTE edits.
</USER_INPUT_PROTOCOL>
</SYSTEM_PROMPT>"""


USER_PROMPT_INTRO = """<USER>
I will now provide the complete project context. First, the directory structure, followed by the file contents. Please adhere strictly to the workflow protocol.
"""

USER_PROMPT_END = "</USER>"


def is_binary_file(file_path):
    """Checks if a file is likely binary by looking for null bytes."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
        return b'\0' in chunk
    except IOError:
        return True

def should_ignore(path, root_dir, ignored_dirs_set, ignored_exts_set, ignored_filenames_set, only_exts_set):
    """Determines if a given path should be ignored."""
    abs_path = os.path.abspath(path)
    filename = os.path.basename(abs_path)

    try:
        relative_path = os.path.relpath(abs_path, root_dir)
    except ValueError:
        return True

    normalized_relative_path = relative_path.replace(os.sep, '/')
    path_parts = normalized_relative_path.split('/')

    if any(part in ignored_dirs_set for part in path_parts):
        return True

    if filename in ignored_filenames_set:
        return True

    if os.path.isfile(abs_path):
        _, ext = os.path.splitext(filename)
        normalized_ext = ext.lower().lstrip('.')
        if normalized_ext in ignored_exts_set:
            return True
        if only_exts_set and normalized_ext not in only_exts_set:
            return True

    try:
        script_abs_path = os.path.abspath(sys.argv[0])
        if os.path.exists(script_abs_path) and os.path.samefile(abs_path, script_abs_path):
            return True
    except (FileNotFoundError, OSError):
        if abs_path == os.path.abspath(sys.argv[0]):
            return True
    return False

def generate_tree_structure(root_dir_param, ignored_dirs_set, ignored_exts_set, ignored_filenames_set, only_exts_set):
    """Generates a string representation of the directory tree."""
    tree_string_io = io.StringIO()
    visited_real_paths_for_tree = set()

    def _generate_recursive(current_path, prefix):
        try:
            real_path = os.path.realpath(current_path)
            if real_path in visited_real_paths_for_tree:
                tree_string_io.write(f"{prefix}└─── [Symlink cycle detected for: {os.path.basename(current_path)}]\n")
                return
            visited_real_paths_for_tree.add(real_path)

            entries = sorted(os.listdir(current_path))
        except OSError:
            return

        renderable_items = []
        for entry in entries:
            full_path = os.path.join(current_path, entry)
            if not should_ignore(full_path, root_dir_param, ignored_dirs_set, ignored_exts_set, ignored_filenames_set, only_exts_set):
                renderable_items.append({'name': entry, 'path': full_path, 'is_dir': os.path.isdir(full_path)})

        for i, item in enumerate(renderable_items):
            is_last = (i == len(renderable_items) - 1)
            connector = "└───" if is_last else "├───"
            tree_string_io.write(f"{prefix}{connector}{item['name']}\n")
            if item['is_dir']:
                new_prefix = prefix + ("    " if is_last else "│   ")
                _generate_recursive(item['path'], new_prefix)

    _generate_recursive(root_dir_param, "")
    return tree_string_io.getvalue()

def collate_project_content(root_dir, ignored_dirs_set, ignored_exts_set, ignored_filenames_set, only_exts_set):
    """Walks the project, collates content of non-ignored files using the new XML format."""
    output_stream = io.StringIO()
    file_count = 0
    processed_abs_paths = set()
    reported_processed_files = []
    reported_ignored_files = []

    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=True, followlinks=False):
        dirnames[:] = [d for d in dirnames if not should_ignore(os.path.join(dirpath, d), root_dir, ignored_dirs_set, ignored_exts_set, ignored_filenames_set, only_exts_set)]
        
        filenames.sort()
        for filename in filenames:
            full_file_path = os.path.join(dirpath, filename)
            abs_file_path = os.path.abspath(full_file_path)
            relative_path = os.path.relpath(full_file_path, root_dir).replace(os.sep, '/')

            if abs_file_path in processed_abs_paths:
                continue

            if should_ignore(full_file_path, root_dir, ignored_dirs_set, ignored_exts_set, ignored_filenames_set, only_exts_set):
                reported_ignored_files.append(relative_path)
                continue

            if is_binary_file(full_file_path):
                reported_ignored_files.append(f"{relative_path} (binary)")
                continue

            print(f"Processing: {relative_path}")
            file_count += 1
            file_size = os.path.getsize(full_file_path)

            processed_abs_paths.add(abs_file_path)
            reported_processed_files.append(relative_path)

            output_stream.write(f'<file path="{relative_path}" bytes="{file_size}>\n')
            output_stream.write('<![CDATA[\n')
            try:
                with open(full_file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                    content = infile.read()
                output_stream.write(content)
            except Exception as e:
                output_stream.write(f"--- Error reading file: {e} ---")
                print(f"   WARNING: Could not read file {relative_path}: {e}", file=sys.stderr)
            output_stream.write('\n]]>\n</file>\n')

    collated_content = output_stream.getvalue()
    output_stream.close()
    return collated_content, reported_processed_files, reported_ignored_files, file_count

def main():
    parser = argparse.ArgumentParser(
        description="Collate project text files and directory structure into a single prompt for an AI model."
    )
    parser.add_argument(
        '--ignore',
        action='append',
        default=[],
        help="File extension to ignore (e.g., 'json'). Can be specified multiple times or as a comma-separated list in brackets (e.g., '[json,txt]')."
    )
    parser.add_argument(
        '--only',
        default=None,
        help="Only include files with specified extension(s). E.g., 'py' or '[py,js,css]'."
    )
    args = parser.parse_args()
    project_root = os.getcwd()

    user_specified_ignored_extensions = set()
    for item in args.ignore:
        if item.startswith('[') and item.endswith(']'):
            extensions = [ext.strip().lstrip('.') for ext in item[1:-1].split(',') if ext.strip()]
            user_specified_ignored_extensions.update(extensions)
        else:
            user_specified_ignored_extensions.add(item.lstrip('.'))

    user_specified_only_extensions = set()
    if args.only:
        item = args.only.strip()
        if item.startswith('[') and item.endswith(']'):
            extensions = [ext.strip().lstrip('.') for ext in item[1:-1].split(',') if ext.strip()]
            user_specified_only_extensions.update(extensions)
        else:
            user_specified_only_extensions.add(item.lstrip('.'))

    final_ignored_directories = DEFAULT_IGNORED_DIRECTORIES
    final_ignored_extensions = DEFAULT_IGNORED_EXTENSIONS.union(user_specified_ignored_extensions)
    final_ignored_filenames = DEFAULT_IGNORED_FILENAMES

    print(f"Starting collation in: {project_root}")
    if user_specified_only_extensions:
        print(f"Including ONLY extensions: {sorted(list(user_specified_only_extensions))}")
    print(f"Ignoring Directories: {sorted(list(final_ignored_directories))}")
    print(f"Ignoring Filenames: {sorted(list(final_ignored_filenames))}")
    print(f"Ignoring Extensions: {sorted(list(final_ignored_extensions))}")
    print("-" * 30)

    print("Generating directory tree structure...")
    tree_structure_str = generate_tree_structure(project_root, final_ignored_directories, final_ignored_extensions, final_ignored_filenames, user_specified_only_extensions)
    print("Directory tree generated." if tree_structure_str else "Directory tree is empty or all items were ignored.")
    print("-" * 30)

    collated_content_str, processed_files_list, ignored_files_list, file_count = collate_project_content(
        project_root, final_ignored_directories, final_ignored_extensions, final_ignored_filenames, user_specified_only_extensions
    )
    
    print("-" * 30)
    if processed_files_list:
        print("\nIncluded files in context:")
        for f_path in sorted(processed_files_list):
            print(f"  - {f_path}")
    
    if ignored_files_list:
        print("\nIgnored files/directories (not included in content):")
        for f_path in sorted(ignored_files_list):
            print(f"  - {f_path}")
    print("-" * 30)

    # --- Assemble the final prompt using the new structure ---
    final_output_parts = [SYSTEM_PROMPT, "\n\n", USER_PROMPT_INTRO]

    if tree_structure_str:
        final_output_parts.append("\n--- Project Directory Tree ---\n")
        final_output_parts.append(tree_structure_str)
        final_output_parts.append("\n--- File Contents ---\n\n")
    
    if collated_content_str:
        final_output_parts.append(collated_content_str)
    
    final_output_parts.append(USER_PROMPT_END)
    final_output = "".join(final_output_parts)

    if file_count > 0 or tree_structure_str:
        try:
            pyperclip.copy(final_output)
            print(f"Successfully processed {file_count} files and included the directory tree.")
            print("Full context prompt has been copied to the clipboard!")
        except pyperclip.PyperclipException as e:
            print(f"\nError: Could not copy to clipboard: {e}", file=sys.stderr)
            print("The generated prompt is too large for the clipboard. Please find it printed below.", file=sys.stderr)
            print("\n" + "="*50 + "\n", file=sys.stderr)
            print(final_output, file=sys.stderr)
            print("\n" + "="*50, file=sys.stderr)
            sys.exit(1)
    else:
        print(f"No files were processed and the directory tree is empty in '{project_root}'.")
        print("Check your ignore/only settings or the directory contents. Clipboard is unchanged.")

if __name__ == "__main__":
    main()