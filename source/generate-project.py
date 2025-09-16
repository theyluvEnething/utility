#!/usr/bin/env python3
import os
import sys
import re
import shutil
import base64

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
DELETE_TAG_PATTERN = re.compile(r'<delete\s+path="([^"]+)"\s*/>')
RENAME_TAG_PATTERN = re.compile(r'<rename\s+from="([^"]+)"\s+to="([^"]+)"\s*/>')
PATCH_BLOCK_PATTERN = re.compile(
    r'<patch>\s*<!\[CDATA\[(.*?)]]>\s*</patch>',
    re.DOTALL
)
BINARY_BLOCK_PATTERN = re.compile(
    r'<binary\s+path="([^"]+)"\s+encoding="([^"]+)">\s*<!\[CDATA\[(.*?)]]>\s*</binary>',
    re.DOTALL
)

def parse_operations(text_content):
    operations = []
    parse_errors = []

    all_matches = []
    for pattern, op_type in [
        (FILE_BLOCK_PATTERN, 'create'),
        (DELETE_TAG_PATTERN, 'delete'),
        (RENAME_TAG_PATTERN, 'rename'),
        (PATCH_BLOCK_PATTERN, 'patch'),
        (BINARY_BLOCK_PATTERN, 'binary')
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

        elif op_type == 'patch':
            content = match.group(1)
            operations.append({'type': 'patch', 'content': content})

        elif op_type == 'binary':
            path = match.group(1).strip()
            encoding = match.group(2).strip()
            content = match.group(3).strip()
            if path and encoding:
                operations.append({'type': 'binary', 'path': path, 'encoding': encoding, 'content': content})
            else:
                parse_errors.append(f"Error: Found <binary> tag with missing attributes at position {match.start()}.")
        
        last_match_end = match.end()

    remaining_text = text_content[last_match_end:].strip()
    if remaining_text:
        # This can be noisy for developer notes, so we'll quiet it.
        pass

    if not operations and not text_content.strip():
        parse_errors.append("Error: No valid operation tags (<file>, <delete>, <rename>) found.")

    return operations, parse_errors

def is_safe_path(path_str):
    normalized_path = os.path.normpath(path_str).replace('\\', '/')
    return not (os.path.isabs(normalized_path) or normalized_path.startswith('../') or '..' in normalized_path.split('/'))

def parse_unified_diff(diff_content):
    import re
    operations, errors = [], []

    # Ignore any text/noise before the first '--- ' header
    lines = diff_content.splitlines()
    try:
        first = next(i for i, ln in enumerate(lines) if ln.startswith('--- '))
        lines = lines[first:]
    except StopIteration:
        return operations, ["No unified diff headers ('--- ') found."]

    # Split into file blocks whenever a new '--- ' line appears
    blocks, cur, started = [], [], False
    for ln in lines:
        if ln.startswith('--- '):
            if started and cur:
                blocks.append('\n'.join(cur))
                cur = [ln]
            else:
                cur = [ln]
                started = True
        else:
            cur.append(ln)
    if cur:
        blocks.append('\n'.join(cur))

    def _parse_header_path(header_line):
        # strip '--- ' / '+++ '
        rest = header_line[4:].strip()
        token = rest.split('\t')[0].split(' ')[0]
        # remove a/, b/, a\, b\  (git-style prefixes on any OS)
        token = re.sub(r'^[ab][\\/]', '', token)
        # normalize slashes for current OS
        normalized = token.replace('\\', '/').replace('/', os.sep)
        return token, normalized

    def _is_null_path(raw_token):
        return raw_token.lower() in ('/dev/null', 'nul')

    for block in blocks:
        blines = block.splitlines()
        if len(blines) < 2:
            errors.append(f"Invalid diff block (too short): {block[:200]}")
            continue

        from_header, to_header = blines[0], blines[1]
        if not from_header.startswith('--- ') or not to_header.startswith('+++ '):
            errors.append(f"Malformed diff header:\n{block[:200]}")
            continue

        from_raw, from_path = _parse_header_path(from_header)
        to_raw, to_path = _parse_header_path(to_header)
        diff_body = '\n'.join(blines[2:])

        if _is_null_path(to_raw):
            operations.append({'type': 'delete', 'path': from_path})
        elif _is_null_path(from_raw):
            operations.append({'type': 'patch', 'path': to_path, 'is_new': True, 'diff': diff_body})
        else:
            operations.append({'type': 'patch', 'path': to_path, 'is_new': False, 'diff': diff_body})

    return operations, errors

HUNK_HEADER_RE = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*')

def apply_patch(original_content, diff_text, *, debug=False, ignore_ws=False, ignore_eol=True):
    import re, difflib

    def file_eol(text):
        # Choose the dominant EOL of the original file, default to '\n'
        crlf = text.count('\r\n')
        lf   = text.count('\n') - crlf
        return '\r\n' if crlf > lf else '\n'

    def norm(line):
        # Normalize for comparison only (don’t mutate what we write)
        if ignore_eol:
            line = line.rstrip('\r\n')
        if ignore_ws:
            # collapse whitespace runs, ignore trailing spaces
            line = re.sub(r'\s+', ' ', line).rstrip()
        return line

    original_lines = original_content.splitlines(True)
    diff_lines     = diff_text.splitlines(True)
    patched_lines  = list(original_lines)
    target_eol     = file_eol(original_content)

    hunk_starts = [i for i, line in enumerate(diff_lines) if line.startswith('@@ ')]

    for i, start_index in enumerate(hunk_starts):
        hunk_header = diff_lines[start_index]
        match = HUNK_HEADER_RE.match(hunk_header)
        if not match:
            raise ValueError(f"Invalid hunk header: {hunk_header.strip()}")

        old_start = int(match.group(1))

        end_index  = hunk_starts[i+1] if i + 1 < len(hunk_starts) else len(diff_lines)
        hunk_lines = diff_lines[start_index + 1 : end_index]

        # Build blocks
        search_lines = [ln[1:] for ln in hunk_lines if ln.startswith(' ') or ln.startswith('-')]
        insert_lines = [ln[1:] for ln in hunk_lines if ln.startswith(' ') or ln.startswith('+')]

        # Normalize EOL of lines we will insert to match the file
        insert_lines = [ln.rstrip('\r\n') + target_eol for ln in insert_lines]

        if not search_lines:
            # Pure addition at a position (fallback to given old_start)
            insert_pos = old_start - 1 if old_start > 0 else 0
            if not patched_lines and insert_pos > 0:
                patched_lines.extend([target_eol] * insert_pos)
            patched_lines[insert_pos:insert_pos] = insert_lines
            continue

        # Exact-ish match with normalization
        found_at = -1
        max_j = len(patched_lines) - len(search_lines)
        for j in range(max_j + 1):
            ok = True
            for k, sline in enumerate(search_lines):
                if norm(patched_lines[j+k]) != norm(sline):
                    ok = False
                    break
            if ok:
                found_at = j
                break

        if found_at != -1:
            patched_lines[found_at:found_at+len(search_lines)] = insert_lines
        else:
            if debug:
                print("\n--- DEBUG: Hunk search failed ---", file=sys.stderr)
                print(hunk_header.strip(), file=sys.stderr)
                print("Expected (first 10 search lines):", file=sys.stderr)
                for ln in search_lines[:10]:
                    print(repr(ln.rstrip('\r\n')), file=sys.stderr)
                # Show best near-match window using difflib
                target = [norm(l) for l in search_lines]
                best_score, best_idx = 0.0, None
                for j in range(max_j + 1):
                    window = [norm(l) for l in patched_lines[j:j+len(search_lines)]]
                    score = difflib.SequenceMatcher(a=target, b=window).ratio()
                    if score > best_score:
                        best_score, best_idx = score, j
                if best_idx is not None:
                    print(f"\nClosest window starts at line {best_idx+1} (score {best_score:.3f})", file=sys.stderr)
                    for ln in patched_lines[best_idx:best_idx+min(len(search_lines),10)]:
                        print("FILE:", repr(ln.rstrip('\r\n')), file=sys.stderr)
                print("--- END DEBUG ---\n", file=sys.stderr)

            hunk_preview = "".join(hunk_lines[:5])
            raise ValueError(f"Hunk #{i+1} could not be applied. Content mismatch.\n-- Hunk Preview --\n{hunk_preview}[...]")

    return "".join(patched_lines)

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
    patches = []
    binaries = []
    skipped_ops = []

    # First pass: categorize all operations
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
        elif op['type'] == 'patch':
            patch_ops, patch_errors = parse_unified_diff(op['content'])
            if patch_errors:
                for err in patch_errors: print(f"Patch parsing error: {err}", file=sys.stderr)
            for patch_op in patch_ops:
                if patch_op['type'] == 'delete': # From a +++ NUL diff
                    deletions.append(patch_op)
                elif is_safe_path(patch_op['path']):
                    patches.append(patch_op)
                else:
                    skipped_ops.append(f"SKIPPING INVALID PATCH: {patch_op['path']}")
        elif op['type'] == 'binary':
            if is_safe_path(op['path']):
                binaries.append(op)
            else:
                skipped_ops.append(f"SKIPPING INVALID BINARY: {op['path']}")

    total_valid_ops = len(creations) + len(deletions) + len(renames) + len(patches) + len(binaries)
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
        print("Files/Dirs to be Deleted:")
        for op in deletions:
            print(f"  - {op['path']}")
    if creations:
        print("Files to be Created / Overwritten:")
        for op in creations:
            print(f"  - {op['path']}")
    if binaries:
        print("Binary files to be Created / Overwritten:")
        for op in binaries:
            print(f"  - {op['path']}")
    if patches:
        print("Files to be Patched:")
        for op in patches:
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
    counts = {'renamed': 0, 'deleted': 0, 'created': 0, 'patched': 0, 'binary': 0, 'errors': 0}

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
                if os.path.islink(path) or os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    print("Skipped (unknown file type).")
                    counts['deleted'] += 1
                    continue
                print("Done.")
            else:
                print("Skipped (not found).")
            counts['deleted'] += 1
        except (OSError, IOError, PermissionError) as e:
            print(f"\nError deleting file or directory: {e}")
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

    for op in binaries:
        try:
            path = os.path.join(target_directory, os.path.normpath(op['path']))
            dir_path = os.path.dirname(path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            
            content = op['content']
            decoded_content = base64.b64decode(content)
            
            print(f"  Writing binary file: {op['path']} ({len(decoded_content)} bytes) ... ", end="")
            with open(path, 'wb') as f:
                f.write(decoded_content)
            print("Done.")
            counts['binary'] += 1
        except (OSError, IOError, base64.binascii.Error) as e:
            print(f"\nError writing binary file: {e}")
            counts['errors'] += 1

    for op in patches:
        try:
            path = os.path.join(target_directory, os.path.normpath(op['path']))
            if op['is_new']:
                print(f"  Applying patch to create: {op['path']} ... ", end="")
                original_content = ""
            else:
                print(f"  Applying patch to modify: {op['path']} ... ", end="")
                if not os.path.exists(path):
                    print(f"Skipped (not found).")
                    counts['errors'] += 1
                    continue
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    original_content = f.read()
            
            new_content = apply_patch(original_content, op['diff'])
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(new_content)
            print("Done.")
            counts['patched'] += 1
        except (OSError, IOError, ValueError) as e:
            print(f"\nError applying patch to {op['path']}: {e}")
            counts['errors'] += 1

    print("-" * 40)
    print("Execution finished.")
    print(f"  Created/Written: {counts['created']} text, {counts['binary']} binary")
    print(f"  Patched: {counts['patched']} file(s)")
    print(f"  Deleted: {counts['deleted']} path(s)")
    print(f"  Renamed/Moved: {counts['renamed']} path(s)")
    if skipped_ops:
         print(f"  Skipped invalid paths: {len(skipped_ops)} operation(s)")
    if counts['errors'] > 0:
        print(f"  Encountered errors: {counts['errors']} operation(s)")
        sys.exit(1)
    else:
        print("All operations completed successfully.")

if __name__ == "__main__":
    main()