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

def get_file_extension_filter():
    """Prompts the user for a file extension filter."""
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
    """Checks if a file should be included based on the filter."""
    if not extension_filter:
        return True
    return filename.lower().endswith(extension_filter)

def format_file_block(relative_path, content):
    """Formats a single file's path and content into the angle-bracket format."""
    return (
        f"--- <{relative_path}> ---\n"
        f"{content}"
        f"--- </{relative_path}> ---\n"
        f"=====\n"
    )

def main():
    """
    Prompts for a file extension filter, traverses the current directory,
    formats matching files into angle-bracket blocks, and copies to clipboard.
    """
    extension_filter = get_file_extension_filter()
    print(f"Filtering for extension: '{extension_filter}' (leave blank for all files)")

    current_directory = os.getcwd()
    print(f"Scanning directory: {current_directory}")

    output_blocks = []
    processed_count = 0
    skipped_count = 0
    error_count = 0

    for root, _, files in os.walk(current_directory):
        for filename in files:
            full_path = os.path.join(root, filename)
            relative_path = os.path.relpath(full_path, current_directory).replace('\\', '/')

            if should_include_file(filename, extension_filter):
                try:
                    # Use 'io.open' for more robust encoding handling
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

    # Join all blocks
    full_output = "".join(output_blocks)

    try:
        pyperclip.copy(full_output)
        print("-" * 30)
        print(f"Successfully processed {processed_count} file(s).")
        print(f"Skipped {skipped_count} file(s) (due to filter or directory type).")
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
