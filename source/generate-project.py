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
DELETE_TAG_PATTERN = re.compile(r'<delete\s+path="([^"]+)"\s*/>', re.DOTALL)
RENAME_TAG_PATTERN = re.compile(r'<rename\s+from="([^"]+)"\s+to="([^"]+)"\s*/>', re.DOTALL)

def parse_operations(text_content):
    operations = []
    parse_errors = []

    all_matches = []
    for pattern, op_type in [
        (FILE_BLOCK_PATTERN, 'create'),
        (DELETE_TAG_PATTERN, 'delete'),
        (RENAME_TAG_PATTERN, 'rename')
    ]:
        for match in pattern.finditer(text_content):
            all_matches.append({'match': match, 'type': op_type})

    all_matches.sort(key=lambda x: x['match'].start())

    last_match_end = 0
    for item in all_matches:
        match = item['match']
        op_type = item['type']
        
        unrecognized_text = text_content[last_match_end:match.start()].strip()
        if unrecognized_text:
            parse_errors.append(f"Warning: Ignoring unrecognized text block ending at position {match.start()}.")

        if op_type == 'create':
            path = match.group(1).strip()
            content = re.sub(r'^\r?\n', '', match.group(2))
            content = re.sub(r'\r?\n$', '', content)
            if path:
                operations.append({'type': 'create', 'path': path, 'content': content})
            else:
                parse_errors.append(f"Error: Found <file> tag with empty path at position {match.start()}.")

        elif op_type == 'delete':
            path = match.group(1).strip()
            if path:
                operations.append({'type': 'delete', 'path': path})
            else:
                parse_errors.append(f"Error: Found <delete> tag with empty path at position {match.start()}.")

        elif op_type == 'rename':
            from_path = match.group(1).strip()
            to_path = match.group(2).strip()
            if from_path and to_path:
                operations.append({'type': 'rename', 'from': from_path, 'to': to_path})
            else:
                parse_errors.append(f"Error: Found <rename> tag with empty 'from' or 'to' at position {match.start()}.")
        
        last_match_end = match.end()

    remaining_text = text_content[last_match_end:].strip()
    if remaining_text:
        parse_errors.append(f"Warning: Ignoring {len(remaining_text)} bytes of unrecognized text at the end of input.")

    if not operations and not parse_errors:
        parse_errors.append("Error: No valid operation tags (<file>, <delete>, <rename>) found.")

    return operations, parse_errors

def is_safe_path(path_str):
    normalized_path = os.path.normpath(path_str).replace('\\', '/')
    return not (os.path.isabs(normalized_path) or normalized_path.startswith('../') or '..' in normalized_path.split('/'))

def main():
    print("Attempting to read operation directives from clipboard...")
    try:
        clipboard_content = pyperclip.paste()
        if not clipboard_content or clipboard_content.isspace():
            print("Error: Clipboard is empty or contains only whitespace.", file=sys.stderr)
            sys.exit(1)
    except pyperclip.PyperclipException as e:
        print(f"Error accessing clipboard: {e}", file=sys.stderr)
        sys.exit(1)

    operations, parse_errors = parse_operations(clipboard_content)

    if parse_errors:
        print("\n--- Parsing Issues Detected ---", file=sys.stderr)
        for error in parse_errors:
            print(error, file=sys.stderr)
        print("-------------------------------\n", file=sys.stderr)

    if not operations:
        print("Error: Could not parse any valid operations from the clipboard content.", file=sys.stderr)
        sys.exit(1)

    target_directory = os.getcwd()
    print(f"\nOperations will be executed in: {target_directory}")
    print("-" * 40)

    creations = []
    deletions = []
    renames = []
    skipped_ops = []

    for op in operations:
        if op['type'] == 'create':
            if is_safe_path(op['path']):
                creations.append(op)
            else:
                skipped_ops.append(f"SKIPPING INVALID CREATE/UPDATE: {op['path']}")
        elif op['type'] == 'delete':
            if is_safe_path(op['path']):
                deletions.append(op)
            else:
                skipped_ops.append(f"SKIPPING INVALID DELETE: {op['path']}")
        elif op['type'] == 'rename':
            if is_safe_path(op['from']) and is_safe_path(op['to']):
                renames.append(op)
            else:
                skipped_ops.append(f"SKIPPING INVALID RENAME: from '{op['from']}' to '{op['to']}'")

    total_valid_ops = len(creations) + len(deletions) + len(renames)
    if total_valid_ops == 0:
        print("No valid operations to perform after filtering for safe paths.")
        for item in skipped_ops:
            print(f"  - {item}")
        sys.exit(0)

    if renames:
        print("Files to be Renamed / Moved:")
        for op in renames:
            print(f"  - FROM: {op['from']}\n    TO:   {op['to']}")
    if deletions:
        print("Files to be Deleted:")
        for op in deletions:
            print(f"  - {op['path']}")
    if creations:
        print("Files to be Created / Overwritten:")
        for op in creations:
            print(f"  - {op['path']}")
    if skipped_ops:
        print("Skipped Invalid Operations:")
        for item in skipped_ops:
            print(f"  - {item}")
    print("-" * 40)

    try:
        confirm = input(f"Proceed with {total_valid_ops} operation(s)? (y/n): ").strip().lower()
    except EOFError:
        print("\nNon-interactive mode detected. Aborting generation.", file=sys.stderr)
        sys.exit(1)

    if confirm != 'y':
        print("Operation cancelled by user.")
        sys.exit(0)

    print("\nStarting execution...")
    counts = {'renamed': 0, 'deleted': 0, 'created': 0, 'errors': 0}

    for op in renames:
        try:
            from_path = os.path.join(target_directory, os.path.normpath(op['from']))
            to_path = os.path.join(target_directory, os.path.normpath(op['to']))
            print(f"  Renaming: {op['from']} -> {op['to']} ... ", end="")
            os.makedirs(os.path.dirname(to_path), exist_ok=True)
            os.rename(from_path, to_path)
            print("Done.")
            counts['renamed'] += 1
        except (OSError, IOError) as e:
            print(f"\nError renaming file: {e}")
            counts['errors'] += 1

    for op in deletions:
        try:
            path = os.path.join(target_directory, os.path.normpath(op['path']))
            print(f"  Deleting: {op['path']} ... ", end="")
            if os.path.exists(path):
                os.remove(path)
                print("Done.")
            else:
                print("Skipped (not found).")
            counts['deleted'] += 1
        except (OSError, IOError) as e:
            print(f"\nError deleting file: {e}")
            counts['errors'] += 1

    for op in creations:
        try:
            path = os.path.join(target_directory, os.path.normpath(op['path']))
            dir_path = os.path.dirname(path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            print(f"  Writing file: {op['path']} ({len(op['content'])} bytes) ... ", end="")
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(op['content'])
            print("Done.")
            counts['created'] += 1
        except (OSError, IOError) as e:
            print(f"\nError writing file: {e}")
            counts['errors'] += 1

    print("-" * 40)
    print("Execution finished.")
    print(f"  Created/Updated: {counts['created']} file(s)")
    print(f"  Deleted: {counts['deleted']} file(s)")
    print(f"  Renamed/Moved: {counts['renamed']} file(s)")
    if skipped_ops:
         print(f"  Skipped invalid paths: {len(skipped_ops)} operation(s)")
    if counts['errors'] > 0:
        print(f"  Encountered errors: {counts['errors']} operation(s)")
        sys.exit(1)
    else:
        print("All operations completed successfully.")

if __name__ == "__main__":
    main()