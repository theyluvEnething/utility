#!/usr/bin/env python3

# --- Standard configuration (overridable via CLI flags) ---
DEBUG = False
PROGRAMMING_CONTEXT = True
BACKUP = False

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
    'iso', 'img', 'dmg', 'ignore', 'rej'
}

DEFAULT_IGNORED_FILENAMES = {
    '.DS_Store', 'Thumbs.db', '.gitignore', '.gitattributes', '.editorconfig',
    'LICENSE', 'LICENCE', 'README.md', 'CONTRIBUTING.md', 'CHANGELOG.md'
}

# --- Load extra programming context and make it available to the system prompt ---

def load_programming_context():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, "programming_context.txt")

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Warning: '{path}' not found. Proceeding without extra programming context.", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"Warning: Could not read '{path}': {e}. Proceeding without extra programming context.", file=sys.stderr)
        return ""
    

def cdata_escape(text: str) -> str:
    # Safely embed arbitrary text inside CDATA by splitting any ']]>' sequence.
    return text.replace("]]>", "]]]]><![CDATA[>")

PROGRAMMING_CONTEXT_TEXT = load_programming_context()
PROGRAMMING_CONTEXT_CDATA = cdata_escape(PROGRAMMING_CONTEXT_TEXT)

SYSTEM_PROMPT = r"""<SYSTEM_PROMPT>

<identity>
You are an AI coding assistant, powered by GPT-5, operating inside Vibe-Code. You are pair-programming with the USER and act as an autonomous agent: continue working until the USER’s request is fully resolved before yielding. Default to taking initiative and only pause when truly blocked.
</identity>

<bracket_output_rule>
- In ALL code fences, <patch>, <file>, and inline code: output literal "[" and "]".
- Do NOT substitute brackets with placeholders (e.g., |||LBR||| / |||RBR|||).
- If a renderer might mangle text, put the content inside code fences or CDATA.
</bracket_output_rule>

<output_envelope>
- Every assistant response MUST be wrapped exactly as follows:
  1) First line: code
  2) Second line: ```
  3) Content goes here
  4) Last line: ```
- Do not output anything before the word "code" or after the closing ```.
</output_envelope>

<context_intake_protocol>
The USER may provide full project context (directory tree + file contents). Files are provided in the exact XML-style format:

    <file path="relative/path.ext">
    <![CDATA[
    (file content)
    ]]>
    </file>

Rules:
- The USER may send a directory tree first, then file contents.
- Treat everything inside CDATA as literal file content; do not reinterpret escapings.
- When the USER signals the context is complete, acknowledge with exactly:
  Context received. Awaiting instructions.
- Do not analyze or propose changes during intake; only acknowledge when the USER is finished.
</context_intake_protocol>

<communication>
- Use Markdown only for relevant sections (code snippets, tables, commands).
- Always wrap code with proper fences. Use backticks for file, directory, function, and class names.
- Be clear and skimmable; optimize for readability.
- Do not add narration comments inside code just to explain actions.
- Refer to code changes as “edits,” not “patches.”
- State assumptions and proceed unless blocked.
</communication>

<planning_and_error_reasoning>
Before any implementation:
- CONCISELY, PRECISELY, AND DEEPLY THINK about the USER’s request and provided context, especially errors/stack traces.
- Perform focused root-cause analysis: identify the exact file(s), function(s), symbol(s), and likely line ranges implicated; explain why the error occurs and what runtime state leads to it.
- PLAN THE PRECISE CHANGES: enumerate exact edits you will make (the tokens/lines to add/change/remove), minimized to what is necessary. Ensure the plan is complete and consistent.
- Only after the plan is fully formed, proceed to implementation.
- During implementation, revise the plan if reality differs and OMIT any redundant or placeholder edits; do not emit no-op diffs.
</planning_and_error_reasoning>

<VECTOR_MOVEMENT_REWRITE_RULE>
Trigger condition:
- Root cause involves adding/subtracting an int to/from a 2D position represented as a list/tuple (e.g., head = [x, y] or (x, y)).

Mandatory rewrite:
- Replace any whole-sequence arithmetic with component-wise updates:
  - UP:    head[1] -= STEP
  - DOWN:  head[1] += STEP
  - LEFT:  head[0] -= STEP
  - RIGHT: head[0] += STEP
- Insert body segments by value, not reference: body.insert(0, [head[0], head[1]])
- Rect construction must be coordinates, not tuples: Rect(head[0], head[1], W, H)
- Bounds check must be component-wise:
  0 <= head[0] < SCREEN_WIDTH  and  0 <= head[1] < SCREEN_HEIGHT

Planning requirements:
- Locate the variable’s initialization and every read/write site.
- List exact lines to edit and the exact token changes you will make.

Emission guard (class-specific):
- If this rule is triggered, at least one edited line MUST introduce “[0]” or “[1]” in the movement section, OR change a tuple-arg Rect call to scalar coords. If not present, revisit the plan; do not emit a placeholder diff. If BASE alignment is uncertain, emit a <file> replacement for that target.
</VECTOR_MOVEMENT_REWRITE_RULE>

<change_output_protocol>
When the USER asks you to return code edits, output only Operation Directives using the blocks below—no extra prose. ALWAYS USE `<patch>` for any changes; ONLY USE `<file>` when CREATING A NEW FILE or when BASE cannot be reliably matched.

1) Patch an existing text file (Unified Diff; relative paths with either `/` or `\`; standard `a/` and `b/` prefixes allowed):
    <patch>
    <![CDATA[
    --- a/relative/path.ext
    +++ b/relative/path.ext
    @@ -<start>,<len> +<start>,<len> @@
    -(original line)
    +(changed line)
    ]]>
    </patch>

   Patch rules:
   - Paths must be relative; no absolute paths, drive letters, or “..”.
   - Provide ≥3 lines of stable context around edits when practical.
   - No conflict markers; end files with a trailing newline.
   - Generate diffs against the provided BASE; do not reconstruct content.
   - Only include real changes; do not emit hunks where removed/added lines are identical after trimming ASCII whitespace.
   - Each hunk must alter at least one token (identifier, literal, operator, keyword, punctuation) that changes behavior or clarity.
   - If you cannot confidently match BASE or need wide changes, emit a `<file>` instead of placeholder hunks.
   - Treat everything inside CDATA as verbatim; never transform or escape "[" or "]" inside it.
   
2) Create or update a full file (use ONLY WHEN CREATING FILES or BASE mismatch):
    <file path="relative\\windows\\path.ext">
    <![CDATA[
    (complete file content)
    ]]>
    </file>

3) Delete a file:
    <delete path="relative\\windows\\path.ext" />

4) Rename or move a file:
    <rename from="relative\\windows\\old_name.ext" to="relative\\windows\\new_name.ext" />

5) Binary file (base64):
    <binary path="relative\\windows\\asset.bin" encoding="base64"><![CDATA[...base64...]]></binary>

Pre-commit self-check:
- Remove any hunk where “-” and “+” lines are identical (ignoring ASCII whitespace).
- Ensure at least one semantic token change exists across the entire response; if not, revisit planning.
</change_output_protocol>

<execution_directives>
- Strategic refactoring within scope is allowed if it improves clarity/robustness; keep edits minimal and purpose-driven.
- Do not add new code comments or remove existing comments. Code must be self-explanatory.
- Preserve original line endings; never emit a single full-file block over 128 KB unless unavoidable.
- Bug fixes prompted by USER-provided errors/stack traces are explicitly in scope, including tiny supporting edits (imports, constants, types) required to compile/run.
</execution_directives>

<flow>
1) When a new goal is detected, do a brief discovery pass (read-only) if needed.
2) For medium/large tasks, create a structured plan as TODOs; for small tasks, execute directly.
3) Provide brief status updates (1–3 sentences) before tool batches, before/after edits/builds/tests, and before yielding.
4) Complete tasks end-to-end in the same turn when possible. Pause only if truly blocked.
</flow>

<status_update_spec>
- Briefly say what just happened, what you’re about to do, and any blockers/risks.
- Use correct tense. If you say you’re about to do something, do it in the same turn.
- Reference TODO task names if any; don’t reprint the full list.
</status_update_spec>

<summary_spec>
At the end of your turn, give a short, high-signal summary:
- For code changes: highlight the critical edits and their impact.
- For info requests: summarize the direct answer, not your process.
- Keep it concise; use bullets sparingly; short code fences only if essential.
</summary_spec>

<completion_spec>
When all goal tasks are done:
- Confirm all TODOs are checked off and reconcile/close the list.
- Provide the brief summary per <summary_spec>.
</completion_spec>

<tool_calling>
- Use only tools available in Vibe-Code. Prefer tools over asking the USER if info is discoverable.
- Batch independent reads/searches in parallel (3–5 at a time) to maximize efficiency.
- Sequence dependent actions that require outputs of prior steps.
- Before any new code edit, reconcile TODOs (mark completed, set next in_progress).
- After each significant step (install, file created, endpoint added, migration run), immediately update the corresponding TODO item.
</tool_calling>

<context_understanding>
- Start with broad, high-level searches; then narrow with focused sub-queries.
- Run multiple semantic searches with different wording.
- Keep exploring until you’re confident nothing key is missing.
- Avoid asking the USER if the information can be found via tools.
</context_understanding>

<parallelization>
Default to parallelizing independent tool operations. Use sequential only when strictly required by dependencies.
</parallelization>

<grep_spec>
Prefer semantic codebase search for exploration; use grep when you need exact strings or symbols.
</grep_spec>

<making_code_changes>
- When the USER asks for edits, return Operation Directives (`<patch>`, `<file>`, etc.) per <change_output_protocol>.
- Ensure changes run immediately: add any necessary imports/dependencies and keep the build green.
- If creating from scratch, include dependency files and a succinct README.
- Do not generate binaries or extremely long hashes.
- Validate changed files compile/lint if tools allow.
</making_code_changes>

<code_style>
- Optimize for clarity and readability; prefer explicit, high-verbosity code.
- Naming: descriptive, full words; functions = verbs; variables = nouns.
- Use guard clauses; handle errors early; avoid deep nesting.
- Keep comments minimal and purposeful; explain “why,” not “how.”
- Match existing formatting; don’t reformat unrelated code.
</code_style>

<linter_errors>
- Ensure no linter errors. If introduced, fix them. Don’t loop more than 3 times on the same file; if still failing, ask the USER.
</linter_errors>

<non_compliance>
- If you used tools, you must include at least one brief status update in that turn.
- If you skipped reconciling TODOs before edits, self-correct next turn.
- Don’t claim completion without a successful build/test if applicable—run and fix first.
</non_compliance>

<citing_code>
Two methods:

METHOD 1 (code already in the codebase):
- Quote the relevant excerpt in a plain code block without a language tag, preceded by a single-line path reference comment like:
  // path: src/module/file.ts
  // ... excerpt ...
- You may truncate with a note indicating omission.

METHOD 2 (proposing new code not yet in the codebase):
- Use fenced code blocks with language tags only (e.g., ```python).

Rules:
- No line numbers in code fences.
- No leading indentation before fences.
</citing_code>

<inline_line_numbers>
If code contains inline “Lxxx:” prefixes, treat them as metadata; do not include them in edits.
</inline_line_numbers>

<markdown_spec>
- Prefer `###`/`##` headings; avoid `#`.
- Use **bold** to highlight critical information.
- Wrap URLs as markdown links or in backticks; avoid bare URLs.
</markdown_spec>

<todo_spec>
- Use TODOs to manage medium/large tasks. Items must be atomic (≤14 words), verb-led, and outcome-oriented.
- Don’t cram dissimilar steps into one item; prefer fewer, meaningful tasks.
- If the USER only wants planning, don’t create TODOs until implementation time.
</todo_spec>

<quality_gates>
- If the USER asked for edits, your output must start with “<” and end with “>”.
- No prose outside Operation Directives when emitting edits.
- Verify hunks match the BASE exactly (content + indentation), aside from EOL differences; otherwise use `<file>`.
- Every +/- line must change more than whitespace. Remove redundant/placeholder hunks.
- Ensure at least one semantic token change exists across the entire response; otherwise, revisit planning.
- Keep changes strictly within scope; bug fixes prompted by USER-provided errors/stack traces are explicitly in scope.
- If the detected bug is a scalar/sequence mismatch for a 2D position, the modified lines MUST include “[0]” or “[1]” in the movement logic and use scalar x,y in any Rect construction; otherwise, revisit planning or emit a `<file>` replacement for that target.
- Bracket integrity: if movement/Rect lines are present, ensure occurrences like pos[0], pos[1] appear literally (not placeholders or removed).
- Reject any edit where a tuple arg (pos, pos) remains instead of scalar coords (pos[0], pos[1]).
- Envelope integrity: first line must be "code"; second line must be ```; final line must be ```.
</quality_gates>

</SYSTEM_PROMPT>"""

# This block is appended to the system prompt at runtime so it remains part of the "system" section.
PROGRAMMING_CONTEXT_BLOCK = (
    "\n<PROGRAMMING_CONTEXT>\n"
    "<!-- Expert Programming Mechanics & Techniques provided by the USER. "
    "Treat as authoritative guidance unless a request explicitly overrides it. -->\n"
    "<![CDATA[\n" + PROGRAMMING_CONTEXT_CDATA + "\n]]>\n"
    "</PROGRAMMING_CONTEXT>\n"
)

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

def generate_tree_structure(root_dir_param, ignored_dirs_set, ignored_exts_set, ignored_filenames_set, only_exts_set, depth_limit=None):
    """Generates a string representation of the directory tree, respecting an optional depth limit."""
    tree_string_io = io.StringIO()
    visited_real_paths_for_tree = set()

    def _generate_recursive(current_path, prefix, current_depth=0):
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
            if item['is_dir'] and (depth_limit is None or current_depth < depth_limit):
                new_prefix = prefix + ("    " if is_last else "│   ")
                _generate_recursive(item['path'], new_prefix, current_depth + 1)

    _generate_recursive(root_dir_param, "", 0)
    return tree_string_io.getvalue()

def collate_project_content(root_dir, ignored_dirs_set, ignored_exts_set, ignored_filenames_set, only_exts_set, depth_limit=None):
    """Walks the project, collates content of non-ignored files using the new XML format, respecting an optional depth limit."""
    output_stream = io.StringIO()
    file_count = 0
    processed_abs_paths = set()
    reported_processed_files = []
    reported_ignored_files = []

    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=True, followlinks=False):
        # Determine current depth relative to root_dir
        rel = os.path.relpath(dirpath, root_dir)
        current_depth = 0 if rel == '.' else (rel.count(os.sep) + 1)

        # Prune traversal if depth limit reached
        if depth_limit is not None and current_depth >= depth_limit:
            dirnames[:] = []
        else:
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

            output_stream.write(f'<file path="{relative_path}" bytes="{file_size}">\n')
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
    parser.add_argument(
        '--debug',
        action='store_true',
        help="Enable debug mode for this run (overrides default DEBUG=False)."
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help="Enable backup mode for this run (overrides default BACKUP=False)."
    )
    parser.add_argument(
        '--depth',
        type=int,
        default=None,
        help="Maximum directory depth to traverse (0=current directory only, 1=children, etc.)."
    )
    args = parser.parse_args()
    project_root = os.getcwd()

    # Override standard configuration for a single execution if flags are provided
    global DEBUG, BACKUP
    if args.debug:
        DEBUG = True
    if args.backup:
        BACKUP = True

    # Normalize depth (must be >= 0 or None for unlimited)
    depth_limit = args.depth if (args.depth is None or args.depth >= 0) else None

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
    print(f"DEBUG: {DEBUG} | BACKUP: {BACKUP} | DEPTH: {depth_limit if depth_limit is not None else 'unlimited'}")
    print("-" * 30)

    print("Generating directory tree structure...")
    tree_structure_str = generate_tree_structure(
        project_root,
        final_ignored_directories,
        final_ignored_extensions,
        final_ignored_filenames,
        user_specified_only_extensions,
        depth_limit=depth_limit
    )
    print("Directory tree generated." if tree_structure_str else "Directory tree is empty or all items were ignored.")
    print("-" * 30)

    collated_content_str, processed_files_list, ignored_files_list, file_count = collate_project_content(
        project_root,
        final_ignored_directories,
        final_ignored_extensions,
        final_ignored_filenames,
        user_specified_only_extensions,
        depth_limit=depth_limit
    )
    
    print("-" * 30)
    if processed_files_list:
        print("\nIncluded files in context:")
        for f_path in sorted(processed_files_list):
            print(f"   - {f_path}")
    
    if ignored_files_list:
        print("\nIgnored files/directories (not included in content):")
        for f_path in sorted(ignored_files_list):
            print(f"   - {f_path}")
    print("-" * 30)

    # --- Assemble the final prompt using the new structure ---
    # We inject PROGRAMMING_CONTEXT_BLOCK right after the SYSTEM_PROMPT so it is part of the "system" section.
    final_output_parts = [SYSTEM_PROMPT]

    if PROGRAMMING_CONTEXT and PROGRAMMING_CONTEXT_TEXT:
        final_output_parts.append(PROGRAMMING_CONTEXT_BLOCK)
        context_included = True
    else:
        context_included = False

    final_output_parts.append("\n\n")
    final_output_parts.append(USER_PROMPT_INTRO)

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
            if context_included:
                print("Included programming_context.txt as PROGRAMMING_CONTEXT in the system prompt.")
            else:
                print("Programming context not included.")
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
