#!/usr/bin/env python3
import os
import sys

try:
    import pyperclip
except ImportError:
    print("Error: 'pyperclip' library not found.", file=sys.stderr)
    print("It is required to copy the output to the clipboard.", file=sys.stderr)
    print("Please install it by running: pip install pyperclip", file=sys.stderr)
    sys.exit(1)

IGNORE_DIRS = {
    '__pycache__', 'node_modules', '.git', 'venv', '.venv',
    'build', 'dist', 'builds', '.vscode', '.idea', 'target'
}
IGNORE_EXTENSIONS = {'.pyc', '.log', '.tmp', '.swp', '.egg-info'}
IGNORE_FILES = {'.DS_Store'}

def _build_tree_recursive(path, prefix, include_files):
    try:
        all_items = os.listdir(path)
    except OSError:
        return

    dirs = []
    files = []
    for item in all_items:
        if os.path.isdir(os.path.join(path, item)):
            if item not in IGNORE_DIRS:
                dirs.append(item)
        elif include_files:
            if item not in IGNORE_FILES and os.path.splitext(item)[1] not in IGNORE_EXTENSIONS:
                files.append(item)

    dirs.sort()
    files.sort()

    entries = dirs + files
    for i, entry in enumerate(entries):
        is_last = (i == len(entries) - 1)
        connector = "└── " if is_last else "├── "
        yield prefix + connector + entry

        if entry in dirs:
            extension = "    " if is_last else "│   "
            yield from _build_tree_recursive(
                os.path.join(path, entry), prefix + extension, include_files
            )

def generate_tree_lines(root_path, include_files):
    tree = [os.path.basename(root_path) + os.sep]
    tree_generator = _build_tree_recursive(root_path, "", include_files)
    tree.extend(list(tree_generator))
    return tree

def main():
    include_files = '--no-files' not in sys.argv
    current_directory = os.getcwd()

    tree_lines = generate_tree_lines(current_directory, include_files)
    output = "\n".join(tree_lines)

    print("--- Project Structure ---")
    print(output)
    print("-------------------------")

    try:
        pyperclip.copy(output)
        print("Project structure copied to clipboard.")
    except pyperclip.PyperclipException as e:
        print(f"\nError: Could not copy to clipboard: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()