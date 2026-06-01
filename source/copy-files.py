#!/usr/bin/env python3
import os
import sys
import io

try:
    import pyperclip
except ImportError:
    print("Error: 'pyperclip' library not found.")
    print("It is required to copy the output to the clipboard.")
    print("Please install it by running: pip install pyperclip")
    sys.exit(1)

DEFAULT_IGNORED_DIRECTORIES = {
    '.git', '.claude', '.planning', 'pycache', 'venv', '.venv',
    'node_modules', '.vscode', '.idea', 'dist', 'build', '.angular', 'temp',
    'libraries', 'target', 'gen', 'icons'
}

DEFAULT_IGNORED_EXTENSIONS = {
    'pyc', 'pyo', 'pyd', 'so', 'dll', 'egg', 'manifest', 'spec', 'mo', 'pot',
    'log', 'sqlite3', 'sqlite3-journal', 'bak', 'tmp', 'swp', 'swo',
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'ico', 'svg', 'tif', 'tiff', 'webp',
    'zip', 'tar', 'gz', 'rar', '7z', 'bz2', 'xz',
    'exe', 'bin', 'o', 'a', 'lib', 'class', 'jar',
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp',
    'mp3', 'wav', 'ogg', 'mp4', 'mkv', 'avi', 'mov', 'wmv',
    'iso', 'img', 'dmg', 'ignore',
    'xml',
    'mtl', 'obj', 'fbx', 'stl', 'gltf', 'glb', '3ds', 'blend', 'dae', 'ply',
    'usd', 'usdz', 'usda', 'usdc', 'max', 'ma', 'mb', 'c4d', 'wrl', 'abc'
}

DEFAULT_IGNORED_FILENAMES = {
    '.DS_Store', 'Thumbs.db', '.gitignore', '.gitattributes', '.editorconfig',
    'LICENSE', 'LICENCE', 'README.md', 'CONTRIBUTING.md', 'CHANGELOG.md'
}


def is_binary_file(file_path):
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
        return b'\0' in chunk
    except IOError:
        return True


def should_ignore(path, root_dir):
    abs_path = os.path.abspath(path)
    filename = os.path.basename(abs_path)

    try:
        relative_path = os.path.relpath(abs_path, root_dir)
    except ValueError:
        return True

    normalized_relative_path = relative_path.replace(os.sep, '/')
    path_parts = normalized_relative_path.split('/')

    if any(part in DEFAULT_IGNORED_DIRECTORIES for part in path_parts):
        return True

    if filename in DEFAULT_IGNORED_FILENAMES:
        return True

    if os.path.isfile(abs_path):
        _, ext = os.path.splitext(filename)
        normalized_ext = ext.lower().lstrip('.')
        if normalized_ext in DEFAULT_IGNORED_EXTENSIONS:
            return True

    try:
        script_abs_path = os.path.abspath(sys.argv[0])
        if os.path.exists(script_abs_path) and os.path.samefile(abs_path, script_abs_path):
            return True
    except (FileNotFoundError, OSError):
        if abs_path == os.path.abspath(sys.argv[0]):
            return True
    return False


def get_file_extension_filter():
    print("Enter file extension to filter (e.g., py, .txt).")
    print("Leave blank to include all files.")
    filter_input = input("Extension: ").strip().lower()

    if not filter_input:
        return ""

    if filter_input.startswith('.'):
        return filter_input
    else:
        return f".{filter_input}"


def should_include_file(filename, extension_filter):
    if not extension_filter:
        return True
    return filename.lower().endswith(extension_filter)


def format_file_block(relative_path, content):
    return (
        f'<file path="{relative_path}">\n'
        f'{content}\n'
        f'</file>'
    )


def main():
    extension_filter = get_file_extension_filter()
    print(f"Filtering for extension: '{extension_filter}' (leave blank for all files)")

    current_directory = os.getcwd()
    print(f"Scanning directory: {current_directory}")

    output_blocks = []
    processed_count = 0
    skipped_count = 0
    error_count = 0
    ignored_count = 0

    for root, dirs, files in os.walk(current_directory, topdown=True):
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), current_directory)]

        for filename in files:
            full_path = os.path.join(root, filename)
            relative_path = os.path.relpath(full_path, current_directory).replace('\\', '/')

            if should_ignore(full_path, current_directory):
                ignored_count += 1
                continue

            if is_binary_file(full_path):
                ignored_count += 1
                continue

            if should_include_file(filename, extension_filter):
                try:
                    with io.open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    output_blocks.append(format_file_block(relative_path, content))
                    processed_count += 1
                except Exception as e:
                    print(f"Error reading file {relative_path}: {e}")
                    error_count += 1
            else:
                skipped_count += 1

    if not output_blocks:
        print("\nNo files matched the criteria or were found.")
        if error_count > 0:
            print(f"Encountered errors reading {error_count} file(s).")
        sys.exit(0)

    full_output = "\n".join(output_blocks)

    try:
        pyperclip.copy(full_output)
        print("-" * 30)
        print(f"Successfully processed {processed_count} file(s).")
        print(f"Skipped {skipped_count} file(s) (due to extension filter).")
        print(f"Ignored {ignored_count} file(s) (binary, ignored dir/extension/filename).")
        if error_count > 0:
            print(f"Encountered errors reading {error_count} file(s).")
        print(f"\nFormatted content for {processed_count} file(s) copied to clipboard.")
    except pyperclip.PyperclipException as e:
        print(f"\nError: Could not copy to clipboard: {e}")
        print("Formatted content will be printed to console instead.")
        print("-" * 30)
        print(full_output)
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred during clipboard operation: {e}")
        print("Formatted content will be printed to console instead.")
        print("-" * 30)
        print(full_output)
        sys.exit(1)


if __name__ == "__main__":
    main()
