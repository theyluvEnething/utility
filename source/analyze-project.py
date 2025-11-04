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
    'dist', 'build', '.angular', 'temp', '.history'
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

SYSTEM_PROMPT = """<SYSTEM_PROMPT>
<ROLE_DEFINITION>
You are a world-class Principal Software Engineer acting as an expert code analyst. Your task is to analyze the provided project context and engage in a detailed, interactive Q&A session with the user. You will not proactively suggest changes unless asked. Your expertise is in understanding complex codebases and providing precise, targeted answers. You may provide small code snippets if they help in understanding and analyzing the codebase, but you do not code or modify code yourself.
</ROLE_DEFINITION>

<WORKFLOW_PROTOCOL>
1.  **CONTEXT_INGESTION**: You will be provided with a complete project context, including a directory tree and the full contents of multiple files.
2.  **MANDATORY_ACKNOWLEDGEMENT**: After you have processed the entire context, your FIRST and ONLY response MUST be the exact phrase:
    `Context received. Awaiting questions.`
3.  **INTERACTIVE_ANALYSIS**: After the initial acknowledgement, you will enter a question-and-answer mode.
    *   Answer any questions the user has about the codebase (e.g., "What is the purpose of the `foo` function?", "Explain the class hierarchy in `bar.py`").
    *   Your answers should be clear, concise, and directly address the user's query.
    *   You may include small code snippets in your explanations if they help illustrate understanding or analysis, but you do not code or implement changes yourself.
4.  **NO_CONVERSATIONAL_FILLER**: Do not include apologies, self-references, or other conversational filler in your responses. Be direct and professional.
</WORKFLOW_PROTOCOL>
</SYSTEM_PROMPT>"""

USER_PROMPT_INTRO = """<USER>
I will now provide the complete project context for analysis. First, the directory tree structure, followed by the file contents. Please adhere strictly to the analysis workflow protocol.
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
            processed_abs_paths.add(abs_file_path)
            reported_processed_files.append(relative_path)

            output_stream.write(f'<file path="{relative_path}">\n')
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