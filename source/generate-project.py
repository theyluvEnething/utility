#!/usr/bin/env python3
# Configuration (defaults; can be overridden by CLI flags)
DEBUG = False      # override with --debug
BACKUP = False     # override with --backup

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


# -----------------------------
# Bracket helpers (ported from JS)
# -----------------------------
def encodeBrackets(s: str) -> str:
    return s.replace('[', "|||LBR|||").replace(']', "|||RBR|||")

def decodeBrackets(s: str) -> str:
    return s.replace("|||LBR|||", "[").replace("|||RBR|||", "]")

# -----------------------------
# Patterns for directive blocks
# -----------------------------
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

# Hunk header pattern (unified diff)
HUNK_HEADER_RE = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*')


def parse_operations(text_content, *, debug=False):
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
    # Quiet remainder: often developer notes

    if not operations and not text_content.strip():
        parse_errors.append("Error: No valid operation tags (<file>, <delete>, <rename>) found.")

    if debug:
        print(f"[DEBUG] Parsed {len(operations)} operation(s) from clipboard", file=sys.stderr)
        if parse_errors:
            print(f"[DEBUG] parse_errors: {len(parse_errors)}", file=sys.stderr)

    return operations, parse_errors


def is_safe_path(path_str):
    normalized_path = os.path.normpath(path_str).replace('\\', '/')
    return not (os.path.isabs(normalized_path) or normalized_path.startswith('../') or '..' in normalized_path.split('/'))


def parse_unified_diff(diff_content, *, debug=False):
    import re
    operations, errors = [], []

    if debug:
        print(f"[DEBUG] parse_unified_diff: {len(diff_content)} chars of diff input", file=sys.stderr)

    # Ignore any text/noise before the first '--- ' header
    lines = diff_content.splitlines()
    try:
        first = next(i for i, ln in enumerate(lines) if ln.startswith('--- '))
        lines = lines[first:]
    except StopIteration:
        msg = "No unified diff headers ('--- ') found."
        if debug:
            print(f"[DEBUG] {msg}", file=sys.stderr)
        return operations, [msg]

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

    for idx, block in enumerate(blocks):
        blines = block.splitlines()
        if len(blines) < 2:
            errors.append(f"Invalid diff block (too short): {block[:200]}")
            if debug:
                print(f"[DEBUG] Block {idx}: too short\n{block}", file=sys.stderr)
            continue

        from_header, to_header = blines[0], blines[1]
        if not from_header.startswith('--- ') or not to_header.startswith('+++ '):
            errors.append(f"Malformed diff header:\n{block[:200]}")
            if debug:
                print(f"[DEBUG] Block {idx}: malformed headers\n{block}", file=sys.stderr)
            continue

        from_raw, from_path = _parse_header_path(from_header)
        to_raw, to_path = _parse_header_path(to_header)
        diff_body = '\n'.join(blines[2:])

        if _is_null_path(to_raw):
            operations.append({'type': 'delete', 'path': from_path})
            if debug:
                print(f"[DEBUG] Block {idx}: delete -> {from_path}", file=sys.stderr)
        elif _is_null_path(from_raw):
            operations.append({'type': 'patch', 'path': to_path, 'is_new': True, 'diff': diff_body})
            if debug:
                print(f"[DEBUG] Block {idx}: create via patch -> {to_path}", file=sys.stderr)
        else:
            operations.append({'type': 'patch', 'path': to_path, 'is_new': False, 'diff': diff_body})
            if debug:
                print(f"[DEBUG] Block {idx}: modify -> {to_path}", file=sys.stderr)

    if debug:
        print(f"[DEBUG] parse_unified_diff: produced {len(operations)} op(s), errors={len(errors)}", file=sys.stderr)

    return operations, errors


def apply_patch(original_content, diff_text, *, debug=False, ignore_eol=True, fuzzy_threshold=0.88, allow_already_applied=True):
    """
    Apply a unified diff to the given original content.

    - Matches tolerate EOL differences (\r\n vs \n) when ignore_eol=True.
    - When debug=True, prints helpful diagnostics on failed hunks.
    - Fuzzy mode: if an exact window isn't found, accept the best window when the
      similarity is >= fuzzy_threshold (0..1). Also treat an already-applied hunk
      as success to make patches idempotent.
    """
    import difflib

    def file_eol(text):
        # Choose the dominant EOL of the original file, default to '\n'
        crlf = text.count('\r\n')
        lf = text.count('\n') - crlf
        return '\r\n' if crlf > lf else '\n'

    def norm(line):
        # Normalize for comparison only (don’t mutate what we write)
        if ignore_eol:
            line = line.rstrip('\r\n')
        return line

    original_lines = original_content.splitlines(True)
    diff_lines = diff_text.splitlines(True)
    patched_lines = list(original_lines)
    target_eol = file_eol(original_content)

    if debug:
        print(f"[DEBUG] apply_patch: original lines={len(original_lines)}, diff lines={len(diff_lines)}, target_eol={'CRLF' if target_eol=='\r\n' else 'LF'}", file=sys.stderr)

    hunk_starts = [i for i, line in enumerate(diff_lines) if line.startswith('@@ ')]

    def _lines_equal(a_lines, b_lines):
        if len(a_lines) != len(b_lines):
            return False
        for x, y in zip(a_lines, b_lines):
            if norm(x) != norm(y):
                return False
        return True

    def _find_exact_window(haystack, needle):
        max_j = len(haystack) - len(needle)
        for j in range(max_j + 1):
            if _lines_equal(haystack[j:j + len(needle)], needle):
                return j
        return -1

    for i, start_index in enumerate(hunk_starts):
        hunk_header = diff_lines[start_index]
        match = HUNK_HEADER_RE.match(hunk_header)
        if not match:
            raise ValueError(f"Invalid hunk header: {hunk_header.strip()}")

        old_start = int(match.group(1))

        end_index = hunk_starts[i + 1] if i + 1 < len(hunk_starts) else len(diff_lines)
        hunk_lines = diff_lines[start_index + 1: end_index]

        # Build blocks
        search_lines = [ln[1:] for ln in hunk_lines if ln.startswith(' ') or ln.startswith('-')]
        insert_lines = [ln[1:] for ln in hunk_lines if ln.startswith(' ') or ln.startswith('+')]

        # Normalize EOL of lines we will insert to match the file
        insert_lines = [ln.rstrip('\r\n') + target_eol for ln in insert_lines]

        if debug:
            print(f"[DEBUG] Hunk {i+1}/{len(hunk_starts)}: header={hunk_header.strip()}, search={len(search_lines)} lines, insert={len(insert_lines)} lines", file=sys.stderr)

        if not search_lines:
            # Pure addition at a position (fallback to given old_start)
            insert_pos = old_start - 1 if old_start > 0 else 0
            if not patched_lines and insert_pos > 0:
                patched_lines.extend([target_eol] * insert_pos)
            patched_lines[insert_pos:insert_pos] = insert_lines
            if debug:
                print(f"[DEBUG] Hunk {i+1}: pure insertion at pos {insert_pos}", file=sys.stderr)
            continue

        # 1) Exact match first (with EOL normalization)
        found_at = _find_exact_window(patched_lines, [l if l.endswith(('\n', '\r\n')) else (l + target_eol) for l in [s.rstrip('\r\n') for s in search_lines]])
        if found_at != -1:
            if debug:
                print(f"[DEBUG] Hunk {i+1}: matched at line {found_at+1}", file=sys.stderr)
            patched_lines[found_at:found_at + len(search_lines)] = insert_lines
            continue

        # 2) Already-applied detection (idempotency): look for insert_lines as-is
        if allow_already_applied:
            already_pos = _find_exact_window(patched_lines, insert_lines)
            if already_pos != -1:
                if debug:
                    print(f"[DEBUG] Hunk {i+1}: appears already applied at line {already_pos+1}; skipping.", file=sys.stderr)
                continue

        # 3) Fuzzy fallback using difflib.SequenceMatcher
        if fuzzy_threshold is not None:
            target = [norm(l) for l in search_lines]
            best_score, best_idx = 0.0, None
            max_j = len(patched_lines) - len(search_lines)
            for j in range(max_j + 1):
                window = [norm(l) for l in patched_lines[j:j + len(search_lines)]]
                score = difflib.SequenceMatcher(a=target, b=window).ratio()
                if score > best_score:
                    best_score, best_idx = score, j
            if best_idx is not None and best_score >= fuzzy_threshold:
                if debug:
                    print(f"[DEBUG] Hunk {i+1}: [FUZZ] applying near-match at line {best_idx+1} (score {best_score:.3f})", file=sys.stderr)
                patched_lines[best_idx:best_idx + len(search_lines)] = insert_lines
                continue

        # 4) No match; emit detailed diagnostics and fail this hunk
        if debug:
            print("\n--- DEBUG: Hunk search failed ---", file=sys.stderr)
            print(hunk_header.strip(), file=sys.stderr)
            print("Expected (first 10 search lines):", file=sys.stderr)
            for ln in search_lines[:10]:
                print(repr(ln.rstrip('\r\n')), file=sys.stderr)
            # Show best near-match window using difflib
            target = [norm(l) for l in search_lines]
            best_score, best_idx = 0.0, None
            max_j = len(patched_lines) - len(search_lines)
            for j in range(max_j + 1):
                window = [norm(l) for l in patched_lines[j:j + len(search_lines)]]
                score = difflib.SequenceMatcher(a=target, b=window).ratio()
                if score > best_score:
                    best_score, best_idx = score, j
            if best_idx is not None:
                print(f"\nClosest window starts at line {best_idx + 1} (score {best_score:.3f})", file=sys.stderr)
                for ln in patched_lines[best_idx:best_idx + min(len(search_lines), 10)]:
                    print("FILE:", repr(ln.rstrip('\r\n')), file=sys.stderr)
            print("--- END DEBUG ---\n", file=sys.stderr)

        hunk_preview = "".join(hunk_lines[:5])
        raise ValueError(f"Hunk #{i + 1} could not be applied. Content mismatch.\n-- Hunk Preview --\n{hunk_preview}[...]")

    return "".join(patched_lines)

def run_from_directives_text(directives_text, *, debug=False, fuzzy_threshold=0.88, backup=False):
    debug = bool(debug)
    if fuzzy_threshold is not None:
        try:
            fuzzy_threshold = float(fuzzy_threshold)
        except Exception:
            fuzzy_threshold = 0.88
    backup_patched = bool(backup)

    clipboard_content = decodeBrackets(directives_text)

    if (DEBUG): print(clipboard_content)

    operations, parse_errors = parse_operations(clipboard_content, debug=debug)

    if parse_errors:
        print("\n--- Parsing Issues Detected ---", file=sys.stderr)
        for error in parse_errors:
            print(error, file=sys.stderr)
        print("-------------------------------\n", file=sys.stderr)

    if not operations:
        print("Error: Could not parse any valid operations from the provided content.", file=sys.stderr)
        return 1

    target_directory = os.getcwd()
    print(f"\nOperations will be executed in: {target_directory}")
    print("-" * 40)

    creations = []
    deletions = []
    renames = []
    patches = []
    binaries = []
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
        elif op['type'] == 'patch':
            patch_ops, patch_errors = parse_unified_diff(op['content'], debug=debug)
            if patch_errors:
                for err in patch_errors:
                    print(f"Patch parsing error: {err}", file=sys.stderr)
            for patch_op in patch_ops:
                if patch_op['type'] == 'delete':
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
        return 0

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
            if debug:
                first_line = op['diff'].splitlines()[0] if op['diff'].splitlines() else ''
                if first_line.startswith('@@ '):
                    print(f"    [DEBUG] first hunk: {first_line}", file=sys.stderr)
    if skipped_ops:
        print("Skipped Invalid Operations:")
        for item in skipped_ops:
            print(f"  - {item}")
    print("-" * 40)

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
            if op.get('is_new'):
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

            new_content = apply_patch(
                original_content,
                op['diff'],
                debug=debug,
                fuzzy_threshold=fuzzy_threshold,
                allow_already_applied=True
            )

            os.makedirs(os.path.dirname(path), exist_ok=True)

            try:
                if backup_patched and os.path.exists(path):
                    backup_path = path + ".bak"
                    shutil.copyfile(path, backup_path)
            except Exception as be:
                print(f"\nWarning: could not create backup for {op['path']}: {be}", file=sys.stderr)

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
        return 1
    else:
        print("All operations completed successfully.")
        return 0

def main():
    # Baseline from top-level defaults; allow one-off overrides via CLI flags
    debug = DEBUG
    if '--debug' in sys.argv:
        debug = True

    # Fuzzy options
    fuzzy_threshold = 0.88  # default
    if '--no-fuzzy' in sys.argv:
        fuzzy_threshold = None
    else:
        if '--fuzzy' in sys.argv:
            try:
                idx = sys.argv.index('--fuzzy')
                fuzzy_threshold = float(sys.argv[idx + 1])
                if not (0.0 <= fuzzy_threshold <= 1.0):
                    raise ValueError
            except Exception:
                print("Warning: invalid --fuzzy value; using default 0.88", file=sys.stderr)
                fuzzy_threshold = 0.88

    # Backups are OFF by default; enable with --backup
    backup_patched = BACKUP
    if '--backup' in sys.argv:
        backup_patched = True

    if debug:
        print(f"[DEBUG] Platform: {sys.platform}", file=sys.stderr)
        print(f"[DEBUG] CWD: {os.getcwd()}", file=sys.stderr)
        if fuzzy_threshold is None:
            print("[DEBUG] Fuzzy patching: DISABLED", file=sys.stderr)
        else:
            print(f"[DEBUG] Fuzzy patching threshold: {fuzzy_threshold}", file=sys.stderr)
        print(f"[DEBUG] Backups before patch: {'ENABLED' if backup_patched else 'DISABLED'}", file=sys.stderr)

    print("Attempting to read operation directives from clipboard...")
    try:
        clipboard_content = pyperclip.paste()
        if not clipboard_content or clipboard_content.isspace():
            print("Error: Clipboard is empty or contains only whitespace.", file=sys.stderr)
            sys.exit(1)
    except pyperclip.PyperclipException as e:
        print(f"Error accessing clipboard: {e}", file=sys.stderr)
        sys.exit(1)

    if debug:
        print(f"[DEBUG] Clipboard content length: {len(clipboard_content)} chars", file=sys.stderr)

    clipboard_content = decodeBrackets(clipboard_content)

    operations, parse_errors = parse_operations(clipboard_content, debug=debug)

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
            patch_ops, patch_errors = parse_unified_diff(op['content'], debug=debug)
            if patch_errors:
                for err in patch_errors:
                    print(f"Patch parsing error: {err}", file=sys.stderr)
            for patch_op in patch_ops:
                if patch_op['type'] == 'delete':  # From a +++ NUL diff
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

    if debug:
        print(
            f"[DEBUG] Tally -> create:{len(creations)}, delete:{len(deletions)}, rename:{len(renames)}, "
            f"patch:{len(patches)}, binary:{len(binaries)}, skipped:{len(skipped_ops)}",
            file=sys.stderr
        )

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
            if debug:
                # Tiny visibility: show first hunk header if present
                first_line = op['diff'].splitlines()[0] if op['diff'].splitlines() else ''
                if first_line.startswith('@@ '):
                    print(f"    [DEBUG] first hunk: {first_line}", file=sys.stderr)
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
            if op.get('is_new'):
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

            if debug:
                # Show quick EOL summary for the file
                crlf = original_content.count('\r\n')
                lf = original_content.count('\n') - crlf
                eol_str = 'CRLF' if crlf > lf else 'LF'
                print(f"\n    [DEBUG] File EOL={eol_str}, original_lines={len(original_content.splitlines())}", file=sys.stderr)

            new_content = apply_patch(
                original_content,
                op['diff'],
                debug=debug,
                fuzzy_threshold=fuzzy_threshold,
                allow_already_applied=True
            )

            os.makedirs(os.path.dirname(path), exist_ok=True)

            # Optional backup before writing
            try:
                if backup_patched and os.path.exists(path):
                    backup_path = path + ".bak"
                    shutil.copyfile(path, backup_path)
                    if debug:
                        print(f"    [DEBUG] Backup saved to {backup_path}", file=sys.stderr)
            except Exception as be:
                print(f"\nWarning: could not create backup for {op['path']}: {be}", file=sys.stderr)

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
