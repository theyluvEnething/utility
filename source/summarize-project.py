#!/usr/bin/env python3
import os
import sys
import argparse

try:
    import pyperclip
except ImportError:
    print("Error: 'pyperclip' library not found.", file=sys.stderr)
    print("It is required to copy the summary to the clipboard.", file=sys.stderr)
    print("Please install it by running: pip install pyperclip", file=sys.stderr)
    sys.exit(1)

# IGNORE_LIST: Directories and files to ignore.
# Added '.angular' to this list. '.vscode' was already present.
IGNORE_LIST = ['.git', '__pycache__', 'venv', '.venv', 'node_modules', '.vscode', '.idea', 'dist', 'build', '.angular', 'temp']

# IGNORE_EXTENSIONS: File extensions to ignore.
IGNORE_EXTENSIONS = ['.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.o',
                     '.a', '.lib', '.class', '.jar',
                     '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.ico',
                     '.mp3', '.wav', '.ogg', '.mp4', '.avi', '.mov', '.wmv',
                     '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                     '.zip', '.tar', '.gz', '.rar', '.7z',
                     '.db', '.sqlite', '.sqlite3', '.log',
                     '.swp', '.swo', '.webp', '.ignore']

DEFAULT_IGNORED_EXTENSIONS = {
    'pyc', 'pyo', 'pyd', 'so', 'dll', 'egg', 'manifest', 'spec', 'mo', 'pot',
    'log', 'sqlite3', 'sqlite3-journal', 'bak', 'tmp', 'DS_Store',
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'ico', 'svg', 'tif', 'tiff',
    'zip', 'tar', 'gz', 'rar', '7z', 'bz2', 'xz',
    'exe', 'bin', 'o', 'a', 'lib', 'class', 'jar',
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp',
    'mp3', 'wav', 'ogg', 'mp4', 'mkv', 'avi', 'mov', 'wmv',
    'iso', 'img', 'dmg'
}

def is_binary_file(file_path):
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\0' in chunk
    except IOError:
        return True

def create_project_summary(root_dir, user_ignore_extensions):
    normalized_user_ignores = {ext.lstrip('.') for ext in user_ignore_extensions}
    all_ignored_extensions = DEFAULT_IGNORED_EXTENSIONS.union(normalized_user_ignores)

    output_blocks = []
    processed_files = []
    ignored_files = []

    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in DEFAULT_IGNORED_DIRECTORIES]

        for filename in sorted(filenames):
            full_path = os.path.join(dirpath, filename)
            relative_path = os.path.relpath(full_path, root_dir)
            formatted_path = relative_path.replace(os.sep, '/')

            file_extension = os.path.splitext(filename)[1].lstrip('.')

            if filename in DEFAULT_IGNORED_FILENAMES:
                ignored_files.append(formatted_path)
                continue
            if file_extension in all_ignored_extensions:
                ignored_files.append(formatted_path)
                continue
            if is_binary_file(full_path):
                ignored_files.append(f"{formatted_path} (binary)")
                continue

            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                file_block = (
                    f"--- <{formatted_path}> ---\n"
                    f"{content}\n"
                    f"--- </{formatted_path}> ---"
                )
                output_blocks.append(file_block)
                processed_files.append(formatted_path)
            except Exception as e:
                print(f"Warning: Could not read file {full_path}: {e}", file=sys.stderr)

    if processed_files:
        print("\nIncluded files in summary:")
        for f in processed_files:
            print(f"  - {f}")

    if ignored_files:
        print("\nIgnored files:")
        for f in ignored_files:
            print(f"  - {f}")

    return "\n=========================\n".join(output_blocks)

def main():
    parser = argparse.ArgumentParser(
        description="Summarize a project's text files into a single string for AI context."
    )
    parser.add_argument(
        '--ignore',
        action='append',
        default=[],
        help="File extension to ignore (e.g., 'json' or '.py'). Can be specified multiple times."
    )

    args = parser.parse_args()
    root_directory = os.getcwd()

    print(f"Scanning project in: {root_directory}")
    if args.ignore:
        print(f"Ignoring user-specified extensions: {', '.join(args.ignore)}")

    summary_text = create_project_summary(root_directory, args.ignore)

    if not summary_text:
        print("\nNo files found to summarize after applying ignore rules.")
        sys.exit(0)

    try:
        pyperclip.copy(summary_text)
        print("\nProject summary copied to clipboard.")
    except pyperclip.PyperclipException as e:
        print(f"\nError: Could not copy to clipboard: {e}", file=sys.stderr)
        print("The summary is printed below for manual copying:", file=sys.stderr)
        print("-" * 30, file=sys.stderr)
        print(summary_text)
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred during clipboard operation: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
