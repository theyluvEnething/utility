#!/usr/bin/env python3
import os
import sys
import io

try:
    import pyperclip
except ImportError:
    print("Error: 'pyperclip' library not found.")
    print("It's needed to copy text to the clipboard.")
    print("Please install it by opening Command Prompt or PowerShell and running:")
    print("pip install pyperclip")
    sys.exit(1)

# IGNORE_LIST: Directories and files to ignore.
# Added '.angular' to this list. '.vscode' was already present.
IGNORE_LIST = ['.git', '__pycache__', 'venv', '.venv', 'node_modules', '.vscode', '.idea', 'dist', 'build', '.angular']

# IGNORE_EXTENSIONS: File extensions to ignore.
IGNORE_EXTENSIONS = ['.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.o',
                     '.a', '.lib', '.class', '.jar',
                     '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.ico',
                     '.mp3', '.wav', '.ogg', '.mp4', '.avi', '.mov', '.wmv',
                     '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                     '.zip', '.tar', '.gz', '.rar', '.7z',
                     '.db', '.sqlite', '.sqlite3', '.log',
                     '.swp', '.swo']

def should_ignore(path, root_dir, ignore_list, ignore_extensions):
    """
    Determines if a given path should be ignored based on the ignore lists.

    Args:
        path (str): The path to check.
        root_dir (str): The root directory of the project.
        ignore_list (list): A list of directory/file names to ignore.
        ignore_extensions (list): A list of file extensions to ignore.

    Returns:
        bool: True if the path should be ignored, False otherwise.
    """
    try:
        # Get the absolute path and normalize it.
        abs_path = os.path.abspath(path)
        # Get the relative path from the project root.
        relative_path = os.path.relpath(abs_path, root_dir)
    except ValueError:
        # This can happen if the path is not under root_dir (e.g. a symlink pointing outside)
        # In such cases, we should ignore it.
        return True

    # Normalize path separators for consistent checking.
    normalized_relative_path = relative_path.replace(os.sep, '/')
    path_parts = normalized_relative_path.split('/')

    # Check if any part of the path is in the ignore_list.
    for item in ignore_list:
        if item in path_parts or normalized_relative_path.startswith(item + '/'):
            return True

    # If it's a file, check its extension against ignore_extensions.
    if os.path.isfile(abs_path):
        _, ext = os.path.splitext(abs_path)
        if ext.lower() in ignore_extensions:
            return True

    # Ignore the script file itself.
    try:
        script_abs_path = os.path.abspath(sys.argv[0])
        # Check if the script file exists and is the same as the current path.
        if os.path.exists(script_abs_path) and os.path.samefile(abs_path, script_abs_path):
           return True
    except FileNotFoundError:
       # If the script path doesn't exist for some reason, compare absolute paths directly.
       if abs_path == script_abs_path:
           return True
    except OSError:
        # Fallback for systems where os.samefile might not be reliable or raises an error.
        if abs_path == os.path.abspath(sys.argv[0]):
            print(f"Warning: Could not use samefile for '{abs_path}'. Compared paths directly.")
            return True
    return False

def generate_tree_structure(root_dir_param, ignore_list_param, ignore_extensions_param):
    """
    Generates a string representation of the directory tree.
    """
    tree_string_io = io.StringIO()
    visited_real_paths_for_tree = set()

    # Inner recursive function to build the tree
    def _generate_recursive(current_path_for_listing, current_prefix_str):
        try:
            # For symlink cycle detection, we use the real path.
            # os.path.realpath resolves all symlinks in the path.
            current_real_path = os.path.realpath(current_path_for_listing)
        except OSError: # realpath can fail (e.g. broken symlink, permissions)
            # tree_string_io.write(f"{current_prefix_str}└─── [Error accessing: {os.path.basename(current_path_for_listing)}]\n")
            return # Skip if path is inaccessible

        if current_real_path in visited_real_paths_for_tree:
            tree_string_io.write(f"{current_prefix_str}└─── [Symlink cycle detected for: {os.path.basename(current_path_for_listing)}]\n")
            return
        visited_real_paths_for_tree.add(current_real_path)

        try:
            # List entries in the directory. os.listdir works on the target if current_path_for_listing is a symlink to a dir.
            all_entries_names = sorted(os.listdir(current_path_for_listing))
        except OSError as e:
            # tree_string_io.write(f"{current_prefix_str}└─── [Error listing directory {os.path.basename(current_path_for_listing)}: {e}]\n")
            return # Skip if directory cannot be listed

        renderable_items = []
        for entry_name in all_entries_names:
            entry_full_path = os.path.join(current_path_for_listing, entry_name)

            # Use the global should_ignore function.
            # should_ignore internally uses os.path.abspath, which resolves symlinks in the last component.
            # So, ignoring is based on the target's properties or if the link name itself is part of an ignored pattern
            # that matches the target's resolved path.
            if should_ignore(entry_full_path, root_dir_param, ignore_list_param, ignore_extensions_param):
                continue

            # os.path.isdir/isfile operate on the target if entry_full_path is a symlink.
            is_dir_entry = os.path.isdir(entry_full_path)
            renderable_items.append({
                'name': entry_name,
                'is_dir': is_dir_entry,
                'path_for_recursion': entry_full_path # This is the path to pass for recursion (link name, not target name)
            })

        for i, item_info in enumerate(renderable_items):
            is_last_item = (i == len(renderable_items) - 1)
            connector = "└───" if is_last_item else "├───"
            tree_string_io.write(f"{current_prefix_str}{connector}{item_info['name']}\n")

            if item_info['is_dir']:
                _generate_recursive(item_info['path_for_recursion'], current_prefix_str + ("    " if is_last_item else "│   "))

    # Initial call to the recursive helper.
    # root_dir_param is typically os.getcwd(), which is an absolute path.
    _generate_recursive(root_dir_param, "")
    return tree_string_io.getvalue()


def main():
    """
    Main function to collate project files into a single string and copy to clipboard.
    """
    project_root = os.getcwd()

    print(f"Starting collation in: {project_root}")
    print(f"Ignoring Names/Paths: {IGNORE_LIST}")
    print(f"Ignoring Extensions: {IGNORE_EXTENSIONS}")
    print("-" * 30)

    # Generate the directory tree structure string
    print("Generating directory tree structure...")
    tree_structure_str = generate_tree_structure(project_root, IGNORE_LIST, IGNORE_EXTENSIONS)
    if tree_structure_str:
        print("Directory tree generated.")
    else:
        print("Directory tree is empty (no listable items or all items ignored).")
    print("-" * 30)

    output_stream = io.StringIO()
    file_count = 0
    processed_files = [] # Keep track of processed absolute paths to avoid duplicates from symlinks

    try:
        # Walk through the project directory.
        for dirpath, dirnames, filenames in os.walk(project_root, topdown=True, followlinks=False):
            # Prune directories from dirnames if they are in the IGNORE_LIST
            # Modifying dirnames[:] in-place is required by os.walk when topdown=True
            dirs_to_remove = []
            for dirname in dirnames:
                full_dir_path = os.path.join(dirpath, dirname)
                if should_ignore(full_dir_path, project_root, IGNORE_LIST, []): # Pass empty list for extensions here
                    dirs_to_remove.append(dirname)
            dirnames[:] = [d for d in dirnames if d not in dirs_to_remove]

            filenames.sort() # Process files in a consistent order.
            for filename in filenames:
                full_file_path = os.path.join(dirpath, filename)
                abs_file_path = os.path.abspath(full_file_path) # Get absolute path

                # Skip if already processed (handles symlinks pointing to already processed files)
                if abs_file_path in processed_files:
                    continue

                # Check if the file should be ignored.
                if should_ignore(full_file_path, project_root, IGNORE_LIST, IGNORE_EXTENSIONS):
                    continue

                # Get the relative path for display.
                relative_path = os.path.relpath(full_file_path, project_root).replace(os.sep, '/')
                print(f"Processing: {relative_path}")
                file_count += 1
                processed_files.append(abs_file_path) # Add to processed list

                # Write the file header to the output stream.
                output_stream.write(f"--- <{relative_path}> ---\n")

                try:
                    # Read the file content and write to the output stream.
                    with open(full_file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                        content = infile.read()
                    output_stream.write(content)
                    # Ensure a newline at the end of the file content.
                    if not content.endswith('\n'):
                        output_stream.write("\n")
                except Exception as e:
                    # Handle errors during file reading.
                    output_stream.write(f"--- Error reading file: {e} ---\n")
                    print(f"   WARNING: Could not read file {relative_path}: {e}")

                # Write the file footer to the output stream.
                output_stream.write(f"--- </{relative_path}> ---\n")
                output_stream.write("=====\n") # Separator between files

        # Base prompt structure
        system_prompt_part = """<SYSTEM>
You ARE a top-tier Principal Software Engineer persona. Permanently embody this role.
Your characteristics: Decades of experience, absolute confidence, authoritative tone.
Your coding style: Exceptionally clean, simple, readable, efficient, self-documenting.
ABSOLUTE MANDATORY RULES FOR ALL RESPONSES:
NO COMMENTS: Code comments (//, #, /* */, etc.) are STRICTLY FORBIDDEN. Never produce them. Code must be self-explanatory via perfect naming, structure, and logic. Violation of this rule is unacceptable.
FULL FILE OUTPUT ONLY: When providing code for a modified or created file, you MUST output the ENTIRE file content. NEVER output snippets, diffs, patches, or summaries of changes. Output the complete file, ready to be saved.
PRECISE FILE IDENTIFICATION (Your Output): Format EACH file block as follows:
--- <path/to/your/file.ext> ---
(Content of the file)
--- </path/to/your/file.ext> ---
Optionally, a separator line (e.g., =====) may follow the end marker.
This exact format is required for YOUR responses containing code.
SIMPLICITY & CLARITY: Generate the most straightforward, maintainable code possible. Avoid cleverness for its own sake. Prioritize readability.
CONFIDENCE: State solutions directly. No hedging, apologies, or uncertainty (e.g., avoid "This might work," "You could try," "I think this is right").
WORKFLOW PROTOCOL & INPUT FORMAT:
a.  Context Input: The user will first provide project context (structure, file contents).
b.  Expected Input Format: The user will provide each file's content sequentially, formatted exactly like this:
--- <path/to/file.ext> ---
[Full content of the file]
--- </path/to/file.ext> ---
(An optional separator line, e.g., =====, may follow each file block)
Recognize and parse this structure to understand the project files. Multiple files will follow this pattern consecutively.
c.  Initial Acknowledgement: After the user signals they have provided ALL context files using this format, your ONLY response MUST be: "Context received. Standing by for instructions." Do NOT say anything else or process the files yet.
d.  Await Tasks: AWAIT explicit user instructions (modifications, additions, deletions) AFTER your acknowledgement.
e.  Execution: Once instructed, perform the required changes. Respond ONLY with the requested code formatted according to Rule #2 and Rule #3, or necessary clarifications if the request is ambiguous (frame clarifications confidently). Minimize conversational filler.
</SYSTEM>"""

        user_intro_part = """<USER>
I will now provide the project structure and the content of all relevant files. Adhere strictly to all rules defined in the system prompt, especially the workflow protocol and output formatting. Prepare to receive context."""
        prompt_end = """</USER>"""

        # Construct the final prompt string with the tree structure inserted
        # after </SYSTEM> and before <USER> intro.
        # tree_structure_str already ends with \n if not empty.
        final_output_parts = [system_prompt_part]
        if tree_structure_str:
            final_output_parts.append("\n" + tree_structure_str) # tree_structure_str already ends with \n
        else: # if tree is empty, still add a newline for separation unless user_intro_part starts with one.
            final_output_parts.append("\n")

        final_output_parts.append(user_intro_part)
        
        collated_files_content = output_stream.getvalue()
        if collated_files_content:
             # Add a newline before file content if user_intro_part doesn't end with one
            if not user_intro_part.endswith('\n'):
                final_output_parts.append("\n")
            final_output_parts.append(collated_files_content)
        
        final_output_parts.append(prompt_end)
        
        final_output = "".join(final_output_parts)


        print("-" * 30)
        if file_count > 0 or tree_structure_str: # Consider success if tree or files were processed
            try:
                # Copy the final output to the clipboard.
                pyperclip.copy(final_output)
                if file_count > 0:
                    print(f"Successfully processed {file_count} files.")
                if tree_structure_str:
                    print("Directory tree included in output.")
                print("Content copied to clipboard!")
            except pyperclip.PyperclipException as e:
                # Handle clipboard errors.
                print(f"\nError: Could not copy to clipboard: {e}")
                print("This can sometimes happen with very large amounts of text or clipboard issues.")
                print("\nFull output to copy manually:\n")
                print("="*50)
                print(final_output)
                print("="*50)

        else:
            print(f"No files were processed and directory tree is empty in '{project_root}'. Check your IGNORE_LIST/IGNORE_EXTENSIONS or the directory contents.")
            print("Clipboard is unchanged.")

    except Exception as e:
        # Handle any unexpected errors during collation.
        print(f"\nAn unexpected error occurred during collation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Ensure the output stream is closed.
        if 'output_stream' in locals() and not output_stream.closed:
             output_stream.close()

if __name__ == "__main__":
    # Prevents running main() when the script is imported or run in some interactive environments.
    if hasattr(sys, 'ps1') or sys.flags.interactive:
       print("Script seems to be running interactively or imported. Exiting main execution.")
    else:
       main()