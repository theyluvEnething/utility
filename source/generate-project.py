#!/usr/bin/env python3
import os
import sys
import re
import io # io is imported but not explicitly used, which is fine.

try:
    import pyperclip
except ImportError:
    print("Error: 'pyperclip' library not found.")
    print("It's needed to read text from the clipboard.")
    print("Please install it by opening Command Prompt or PowerShell and running:")
    print("pip install pyperclip")
    sys.exit(1)

# --- MODIFIED REGEX ---
# Changed format to --- <filename> --- and --- </filename> ---
# Made the separator line optional
FILE_BLOCK_PATTERN = re.compile(
    r"^--- <(.+?)> ---\r?\n"     # Start marker: --- <filename> ---, capture filename (Group 1)
    r"(.*?)"                    # Capture content (Group 2), non-greedy, matches newlines
    r"^--- </\1> ---\r?\n?"     # End marker: --- </filename> --- (matches Group 1), optional final newline
    # Make the separator line and surrounding whitespace optional
    # Use a non-capturing group (?:...) as we don't need to capture the separator itself
    # Match optional whitespace, then >=5 '=', then optional non-greedy whitespace,
    # then optional newline(s), anchored to the end of a line (due to MULTILINE)
    r"(?:\s*={5,}\s*?\r?\n?)?$", # Optional Separator part
    re.MULTILINE | re.DOTALL
)
# --- END MODIFICATION ---

def parse_project_structure(text_content):
    """Parses the project structure from text using file markers."""
    project_data = []
    parse_errors = []
    last_match_end = 0

    for match in FILE_BLOCK_PATTERN.finditer(text_content):
        filename = match.group(1).strip()
        # Content is captured exactly as it appears between the markers
        content = match.group(2)
        start, end = match.span()

        # Check for text *before* this match that wasn't part of a previous match
        # Use match.start() which is the beginning of the entire matched block
        unmatched_start = last_match_end
        unmatched_end = match.start()

        if unmatched_end > unmatched_start:
            unmatched_text = text_content[unmatched_start:unmatched_end].strip()
            if unmatched_text:
                # Be more specific about where the ignored text is
                location = "start of input" if unmatched_start == 0 else "between file blocks"
                # Refine the warning message
                warning_msg = (
                    f"Warning: Ignoring unrecognized text {location} "
                    f"(between position {unmatched_start} and {unmatched_end}):\n---\n"
                    f"{unmatched_text[:200]}{'...' if len(unmatched_text) > 200 else ''}\n---"
                )
                # Avoid adding duplicate warnings if the only difference is minor whitespace
                if not parse_errors or warning_msg.split('\n---')[1] != parse_errors[-1].split('\n---')[1]:
                     parse_errors.append(warning_msg)


        if not filename:
            # This case is unlikely with the regex `(.+?)`, but good to keep
            parse_errors.append(f"Error: Found file block with empty filename near position {start}.")
            continue

        project_data.append({"filename": filename, "content": content})
        # Update last_match_end to the end of the current complete match
        last_match_end = end

    # Check for remaining text *after* the last match
    remaining_text = text_content[last_match_end:].strip()
    if remaining_text:
        parse_errors.append(
            f"Warning: Ignoring unrecognized text at the end of input "
            f"(near position {last_match_end}):\n---\n"
            f"{remaining_text[:200]}{'...' if len(remaining_text) > 200 else ''}\n---"
        )

    # Check if *any* blocks were found, even if there were other errors
    if not project_data and not parse_errors:
         # If there are already errors, don't add this potentially redundant one.
         # Only add it if the input was completely unparseable by the core pattern.
         if not FILE_BLOCK_PATTERN.search(text_content): # Double check if regex finds *anything*
            parse_errors.append("Error: No valid file blocks found in the input. Check the format: --- <filename> --- ... --- </filename> ---")

    return project_data, parse_errors


def main():
    """Reads project structure from clipboard, parses it, and generates files."""
    print("Attempting to read project structure from clipboard...")

    try:
        clipboard_content = pyperclip.paste()
        if not clipboard_content or clipboard_content.isspace():
            print("Error: Clipboard is empty or contains only whitespace.")
            sys.exit(1)
    except pyperclip.PyperclipException as e:
        print(f"Error accessing clipboard: {e}")
        sys.exit(1)
    except Exception as e:
        # Catch potential errors during paste() like out of memory
        print(f"An unexpected error occurred reading from clipboard: {e}")
        sys.exit(1)

    print(f"Read {len(clipboard_content)} characters from clipboard.")
    print("Parsing project structure using file markers...")
    project_data, parse_errors = parse_project_structure(clipboard_content)

    if parse_errors:
        print("\n--- Parsing Issues Detected ---")
        for error in parse_errors:
            print(error)
        print("-------------------------------\n")
        # Decide if parsing errors should halt execution even if some files were found
        # For now, we allow proceeding if at least one file was parsed.

    if not project_data:
        print("Error: Could not parse any valid file data from the clipboard content.")
        # --- MODIFIED EXAMPLE FORMAT ---
        print("Ensure the clipboard contains text formatted like:")
        print("--- <path/to/your/file.txt> ---")
        print("File content goes here.")
        print("Multiple lines are fine.")
        print("--- </path/to/your/file.txt> ---")
        # print("======================================") # Separator no longer required
        print("(Optional: Separator line with at least 5 '=' signs between files)")
        # --- END MODIFICATION ---
        sys.exit(1)

    target_directory = os.getcwd()
    print(f"\nProject will be generated in the current directory: {target_directory}")
    print("-" * 30)
    print("Files to be created/overwritten:")
    files_to_create = []
    for item in project_data:
        # Normalize path separators for display and consistency
        relative_path = os.path.normpath(item['filename'].strip()).replace('\\', '/')
        # Prevent absolute paths or path traversal for security
        if os.path.isabs(relative_path) or ".." in relative_path.split('/'):
             print(f"  - SKIPPING INVALID PATH: {item['filename']} (Absolute paths or '..' not allowed)")
             continue # Skip adding to files_to_create
        files_to_create.append(relative_path)
        print(f"  - {relative_path}")
    print("-" * 30)

    # Re-filter project_data based on valid paths identified above
    valid_project_data = [item for item in project_data
                         if os.path.normpath(item['filename'].strip()).replace('\\', '/') in files_to_create]

    if not valid_project_data:
        print("No valid file paths found after filtering. Nothing to generate.")
        sys.exit(0) # Not an error, just nothing to do

    try:
        # Make prompt clearer
        confirm = input(f"Proceed with generating {len(valid_project_data)} file(s) in '{target_directory}'? (y/n): ").strip().lower()
    except EOFError:
        print("\nNon-interactive mode detected or input aborted. Aborting generation (requires confirmation).")
        sys.exit(1)

    if confirm != 'y':
        print("Operation cancelled by user.")
        sys.exit(0)

    print("\nStarting file generation...")
    created_count = 0
    error_count = 0
    skipped_count = len(project_data) - len(valid_project_data) # Count skipped due to invalid paths

    for item in valid_project_data:
        original_filename = item['filename'].strip() # Keep original for error messages if needed
        # Normalize path for os operations, ensure relative
        relative_path = os.path.normpath(original_filename).replace('\\', '/')
        # Double check for safety (already filtered, but belt-and-suspenders)
        if os.path.isabs(relative_path) or ".." in relative_path.split('/'):
             print(f"  Skipping invalid path again: {original_filename}")
             skipped_count +=1 # Should not happen if filtering above worked
             continue

        content = item['content']

        # --- START: MODIFICATION TO REMOVE LINES STARTING WITH ``` ---
        lines = content.splitlines(True)  # Keep newlines
        filtered_lines = [line for line in lines if not line.lstrip().startswith("```")]
        content = "".join(filtered_lines)
        # --- END: MODIFICATION ---

        try:
            # Create full path safely relative to the target directory
            full_path = os.path.join(target_directory, relative_path)

            # --- Enhanced Path Safety Check ---
            # Resolve both paths fully to prevent tricks like symlinks pointing outside
            real_target_dir = os.path.realpath(target_directory)
            # Get the directory part of the intended full path for checking
            # If full_path is just a filename (e.g. "file.txt"), os.path.dirname(full_path) will be empty.
            # In this case, the real_full_path_dir should be real_target_dir.
            intended_dir_part = os.path.dirname(full_path)
            if not intended_dir_part: # File is in the root of target_directory
                real_full_path_dir = real_target_dir
            else:
                real_full_path_dir = os.path.realpath(intended_dir_part)


            # Ensure the directory we intend to write into is within or is the target directory
            if not real_full_path_dir.startswith(real_target_dir):
                 raise OSError(f"Attempted path traversal detected: '{relative_path}' resolves its directory outside target directory '{target_directory}'.")
            # --- End Enhanced Path Safety Check ---


            dir_path = os.path.dirname(full_path)

            # Create directories only if needed
            if dir_path and not os.path.exists(dir_path):
                 print(f"  Creating directory: {os.path.dirname(relative_path)} ... ", end="")
                 # Use realpath for safety again before creating
                 os.makedirs(os.path.realpath(dir_path), exist_ok=True)
                 print("Done.")
            elif dir_path and not os.path.isdir(dir_path):
                 raise OSError(f"Cannot create directory '{os.path.dirname(relative_path)}': a file with the same name exists.")


            print(f"  Writing file: {relative_path} ({len(content)} bytes) ... ", end="")
            # Use newline='' to prevent universal newline translation on write
            # Use realpath on the full path just before opening for final safety
            with open(os.path.realpath(full_path), 'w', encoding='utf-8', newline='') as f:
                f.write(content)
            print("Done.")
            created_count += 1
        except OSError as e:
            print(f"\nError creating directory/file '{relative_path}': {e}")
            error_count += 1
        except IOError as e:
            print(f"\nError writing file '{relative_path}': {e}")
            error_count += 1
        except Exception as e:
             print(f"\nAn unexpected error occurred processing '{relative_path}': {e}")
             error_count += 1

    print("-" * 30)
    if error_count == 0 and skipped_count == 0:
        print(f"Successfully generated {created_count} file(s).")
    else:
        print(f"Generation finished.")
        print(f"  Successfully created: {created_count} file(s)")
        if skipped_count > 0:
             print(f"  Skipped invalid paths: {skipped_count} file(s)")
        if error_count > 0:
            print(f"  Encountered errors: {error_count} file(s)")
        # Provide exit code indicating partial success or failure
        if error_count > 0:
            sys.exit(1) # Indicate failure

if __name__ == "__main__":
    main()