#!/usr/bin/env python3
import os
import sys
import re

try:
    import pyperclip
except ImportError:
    print("Error: 'pyperclip' library not found.", file=sys.stderr)
    print("It's needed to read text from the clipboard.", file=sys.stderr)
    print("Please install it by opening Command Prompt or PowerShell and running:", file=sys.stderr)
    print("pip install pyperclip", file=sys.stderr)
    sys.exit(1)

FILE_BLOCK_PATTERN = re.compile(
    r'<file path="(.+?)">\s*<!\[CDATA\[(.*?)]]>\s*</file>',
    re.DOTALL
)

def parse_project_structure(text_content):
    """Parses the project structure from text using the XML/CDATA format."""
    project_data = []
    parse_errors = []
    last_match_end = 0

    try:
        first_file_match = re.search(r'<file path=', text_content)
        if first_file_match:
            text_content = text_content[first_file_match.start():]
    except Exception:
        pass

    for match in FILE_BLOCK_PATTERN.finditer(text_content):
        filename = match.group(1).strip()
        content = match.group(2)

        content = re.sub(r'^\r?\n', '', content)
        content = re.sub(r'\r?\n$', '', content)

        if not filename:
            parse_errors.append(f"Error: Found file block with empty filename near position {match.start()}.")
            continue

        project_data.append({"filename": filename, "content": content})
        last_match_end = match.end()

    remaining_text = text_content[last_match_end:].strip()
    if remaining_text.endswith("</USER>"):
        remaining_text = remaining_text[:-len("</USER>")].strip()

    if remaining_text:
        parse_errors.append(
            f"Warning: Ignoring unrecognized text at the end of input:\n---\n"
            f"{remaining_text[:200]}{'...' if len(remaining_text) > 200 else ''}\n---"
        )

    if not project_data and not parse_errors:
        parse_errors.append("Error: No valid file blocks found. Check format: <file path=\"...\"><![CDATA[...]]></file>")

    return project_data, parse_errors


def main():
    print("Attempting to read project structure from clipboard...")

    try:
        clipboard_content = pyperclip.paste()
        if not clipboard_content or clipboard_content.isspace():
            print("Error: Clipboard is empty or contains only whitespace.")
            sys.exit(1)
    except pyperclip.PyperclipException as e:
        print(f"Error accessing clipboard: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Read {len(clipboard_content)} characters from clipboard.")
    print("Parsing project structure using the XML/CDATA format...")
    project_data, parse_errors = parse_project_structure(clipboard_content)

    if parse_errors:
        print("\n--- Parsing Issues Detected ---")
        for error in parse_errors:
            print(error)
        print("-------------------------------\n")

    if not project_data:
        print("Error: Could not parse any valid file data from the clipboard content.")
        print("Ensure the clipboard contains text formatted like:")
        print('<file path="path/to/file.ext">')
        print('<![CDATA[')
        print('File content goes here.')
        print(']]>')
        print('</file>')
        sys.exit(1)

    target_directory = os.getcwd()
    print(f"\nProject will be generated in the current directory: {target_directory}")
    print("-" * 30)
    print("Files to be created/overwritten:")

    valid_files = []
    for item in project_data:
        relative_path = os.path.normpath(item['filename'].strip()).replace('\\', '/')
        if os.path.isabs(relative_path) or ".." in relative_path.split('/'):
             print(f"  - SKIPPING INVALID PATH: {item['filename']} (Absolute paths or '..' are not allowed)")
             continue
        valid_files.append(item)
        print(f"  - {relative_path}")
    print("-" * 30)

    if not valid_files:
        print("No valid file paths found after filtering. Nothing to generate.")
        sys.exit(0)

    try:
        confirm = input(f"Proceed with generating {len(valid_files)} file(s) in '{target_directory}'? (y/n): ").strip().lower()
    except EOFError:
        print("\nNon-interactive mode detected. Aborting generation (requires confirmation).")
        sys.exit(1)

    if confirm != 'y':
        print("Operation cancelled by user.")
        sys.exit(0)

    print("\nStarting file generation...")
    created_count = 0
    error_count = 0
    skipped_count = len(project_data) - len(valid_files)

    for item in valid_files:
        relative_path = os.path.normpath(item['filename'].strip()).replace('\\', '/')
        content = item['content']

        try:
            full_path = os.path.join(target_directory, relative_path)

            real_target_dir = os.path.realpath(target_directory)
            real_full_path = os.path.realpath(os.path.dirname(full_path))
            if not real_full_path.startswith(real_target_dir):
                 raise OSError(f"Attempted path traversal detected for '{relative_path}'.")

            dir_path = os.path.dirname(full_path)
            if dir_path:
                if not os.path.exists(dir_path):
                    print(f"  Creating directory: {os.path.dirname(relative_path)} ... ", end="")
                    os.makedirs(dir_path, exist_ok=True)
                    print("Done.")
                elif not os.path.isdir(dir_path):
                    raise OSError(f"Cannot create directory '{os.path.dirname(relative_path)}': a file with that name exists.")

            print(f"  Writing file: {relative_path} ({len(content)} bytes) ... ", end="")
            with open(full_path, 'w', encoding='utf-8', newline='') as f:
                f.write(content)
            print("Done.")
            created_count += 1
        except (OSError, IOError) as e:
            print(f"\nError processing '{relative_path}': {e}")
            error_count += 1
        except Exception as e:
             print(f"\nAn unexpected error occurred with '{relative_path}': {e}")
             error_count += 1

    print("-" * 30)
    print("Generation finished.")
    print(f"  Successfully created: {created_count} file(s)")
    if skipped_count > 0:
         print(f"  Skipped invalid paths: {skipped_count} file(s)")
    if error_count > 0:
        print(f"  Encountered errors: {error_count} file(s)")
        sys.exit(1)
    else:
        print("Project generation completed successfully.")

if __name__ == "__main__":
    main()