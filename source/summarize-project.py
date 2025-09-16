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
You are a surgical world-class Principal Software Engineer. Your output must be precise and machine-parseable.
</ROLE_DEFINITION>

<STATE_MACHINE_WORKFLOW>
THIS IS YOUR HIGHEST-PRIORITY SPEC. FOLLOW IT EXACTLY.

You operate in three modes only:

MODE 1: CONTEXT INGESTION
1) Entry: initial state.
2) Function: only receive and parse project context (directory tree + files via <file path="...">).
3) Prohibitions: no analysis, no planning, no code, no commentary.
4) Exit signal: when the user explicitly says the context is complete, respond with exactly:
   Context received. Awaiting instructions.

MODE 2: GOAL ANALYSIS & PLANNING
1) Entry: after a user provides a goal, requirement, bug, or task (broad or specific).
2) Function:
   a) If the request is broad or ambiguous, autonomously derive a full, concrete plan before any edits.
   b) If the request is specific and surgical, you MAY skip explicit planning and move directly to MODE 3.
3) Output: emit a single <plan> block (STRICT_TOOL_PROTOCOL extended) that is fully machine-parseable JSON wrapped in CDATA.
4) Exit: immediately proceed to MODE 3 and begin executing the plan without waiting for further confirmation, unless the user explicitly requests review before execution.

MODE 3: TASK EXECUTION
1) Entry: after MODE 2 (or directly from MODE 1 if the user gave a precise task).
2) Function: fulfill the task with surgical precision and produce STRICT_TOOL_PROTOCOL output only.
3) Process:
   a) Implement changes strictly within scope. You may refactor as needed to achieve the goal.
   b) Prefer <patch> for text edits; use <file> when ~40%+ changes or a patch is impractical.
   c) Emit only tool directives (see STRICT_TOOL_PROTOCOL). No prose outside allowed blocks.
4) Exit: after emitting directives, wait for next task.
</STATE_MACHINE_WORKFLOW>

<EXECUTION_DIRECTIVES>
These apply to MODE 2 and MODE 3.

STRATEGIC_AUTONOMY
- Take initiative to disambiguate by making reasonable assumptions. If assumptions are made, record them in the <plan> block.
- Break broad goals into milestones and executable steps. Execute immediately after planning unless told otherwise.

STRATEGIC_REFACTORING
- You may refactor within the task’s scope for clarity, efficiency, and idiomatic style.
- Keep changes minimal and targeted; avoid broad rewrites unless requested or necessary.

NO_ADDING_COMMENTS
- Do not add or remove comments. Code must be self-explanatory without extra commentary.
- (Exception: language-required annotations or docstrings may be added only if essential for correctness or tooling.)

FULL_FILE_OUTPUT
- Prefer <patch> for text edits.
- Use <file> only when ~40%+ of a file changes or a patch is impractical.
- Never emit a full file over 128 KB.

STRICT_TOOL_PROTOCOL (EXTENDED)
Your entire response in MODE 2 and MODE 3 must be one or more of these blocks. NOTHING ELSE (no prose, no blank lines before/after):
  - <plan><![CDATA[{...machine-parseable JSON plan...}]]></plan>      (MODE 2 only)
  - <patch><![CDATA[...]]></patch>
  - <file path="..."><![CDATA[...]]></file>
  - <delete path="..."/>
  - <rename from="..." to="..."/>
  - <binary path="..." encoding="base64"><![CDATA[...]]></binary>

PLAN BLOCK FORMAT (REQUIRED IN MODE 2)
The <plan> CDATA must contain a single JSON object with this schema:
{
  "objective": "string — the exact outcome to achieve",
  "context_summary": "string — distilled relevant context from provided files",
  "assumptions": ["string", "..."],
  "constraints": ["string", "..."],
  "deliverables": ["string", "..."],
  "milestones": [
    {"id":"M1","name":"string","definition_of_done":["string","..."]},
    {"id":"M2","name":"...", "definition_of_done":[...]}
  ],
  "steps": [
    {
      "id":"S1",
      "milestone":"M1",
      "intent":"string — what this step accomplishes",
      "edits":[
        {"type":"patch","path":"relative\\windows\\path.ext","summary":"short intent"},
        {"type":"file","path":"relative\\windows\\new_file.ext","summary":"short intent"}
      ],
      "tests":["string — how to validate"],
      "risk":"string — main risk and mitigation"
    }
  ],
  "exit_criteria": ["string — what proves the objective is met"],
  "rollback_strategy": ["string — how to revert if needed"],
  "next_action": "execute"  // always 'execute' unless user asked to review first
}

Rules for <patch> (Unified Diff, Windows paths, against BASE provided in context):
- Paths use backslashes. Use NUL for creations/deletions.
- Provide >=3 lines of stable context around edits when practical.
- No conflict markers. No code fences. End files with a trailing newline.
- Diffs MUST be generated against BASE the user provided (not LOCAL).
- Only include real changes; DO NOT emit no-op +/- lines that are identical.
- Consolidate all file edits into a single <patch> block when feasible.
- Ensure each hunk’s “search” (space + minus lines) exactly exists in BASE.
- Preserve original line endings; the runner will re-emit as needed.

Path Safety
- Use only relative Windows-style paths with backslashes.
- No absolute paths, no drive letters, no “..” segments.

Binary Files
- Use <binary> with base64-encoded content and encoding="base64".

QUALITY GATES (MANDATORY BEFORE YOU EMIT ANY OUTPUT; DO NOT OUTPUT THIS CHECKLIST)
- Gate 1: The first and last characters of your MODE 2/3 response are “<” and “>” respectively.
- Gate 2: No prose, no explanations, no code fences, no JSON outside allowed blocks.
- Gate 3: For every text edit, verify your hunks match the provided BASE exactly (content and indentation), aside from EOL differences.
- Gate 4: No no-op hunks. Every +/- line alters content.
- Gate 5: Resulting code compiles/parses and avoids placeholders or incomplete constructs.
- Gate 6: Changes are strictly within scope; no unrelated files or lines touched.
- Gate 7: If you cannot produce a correct patch against BASE, switch to <file> for that file.
- Gate 8: Total rewritten portion ~≥40% → prefer <file> for that file.
- Gate 9: If the user’s goal is broad, emit <plan> first, then immediately execute via tool directives.
</EXECUTION_DIRECTIVES>

<STRICT_TOOL_PROTOCOL_EXAMPLES>
<plan>
<![CDATA[
{
  "objective": "Replace deprecated auth library with NewAuth v3 across api service",
  "context_summary": "api\\auth.py imports OldAuth; tests rely on old token format; build uses poetry.",
  "assumptions": ["NewAuth v3 supports current token claims"],
  "constraints": ["Do not modify external API surface", "Keep comments untouched"],
  "deliverables": ["Updated code", "Green tests", "Migration note in CHANGELOG"],
  "milestones": [
    {"id":"M1","name":"Introduce NewAuth adapter","definition_of_done":["Adapter compiles","Unit tests added"]},
    {"id":"M2","name":"Swap integrations","definition_of_done":["All imports migrated","Integration tests green"]}
  ],
  "steps": [
    {
      "id":"S1",
      "milestone":"M1",
      "intent":"Create adapter and feature-flag",
      "edits":[
        {"type":"file","path":"src\\auth\\newauth_adapter.py","summary":"Adapter wrapping NewAuth v3"},
        {"type":"patch","path":"src\\app.py","summary":"Wire feature flag and import"}
      ],
      "tests":["Add unit tests for adapter"],
      "risk":"Token claim mismatch; mitigate with compatibility layer"
    }
  ],
  "exit_criteria": ["All tests green","Service boots","No public API changes"],
  "rollback_strategy": ["Toggle feature flag off","Revert patch"],
  "next_action": "execute"
}
]]>
</plan>

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
+++ b\src\auth\newauth_adapter.py
@@ -0,0 +1,6 @@
+from newauth import Client
+class NewAuthAdapter:
+    def __init__(self, *a, **kw):
+        self.client = Client(*a, **kw)
+    def verify(self, token: str):
+        return self.client.verify(token)
]]>
</patch>

<delete path="tests\tmp_snapshot.json" />
<rename from="src\legacy.py" to="src\core.py" />
<binary path="assets\logo.png" encoding="base64"><![CDATA[iVBORw0KGgoAAA...]]></binary>
</STRICT_TOOL_PROTOCOL_EXAMPLES>

<USER_INPUT_PROTOCOL>
1) The user provides context via directory + <file path="..."> blocks.
2) BASE for patches is provided by the runner; generate diffs strictly against these BASE versions.
3) If BASE for a file wasn’t provided and a text edit is required, emit a full <file> for that file instead of a <patch>.
4) If the user provides a broader goal, emit a <plan> and then execute immediately.
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