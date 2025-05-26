#!/usr/bin/env python3
import os
import sys

try:
    import pyperclip
except ImportError:
    print("Error: 'pyperclip' library not found.")
    print("It is required to copy the path to the clipboard.")
    print("Please install it by running: pip install pyperclip")
    sys.exit(1)

def get_current_directory_as_linux_path():
    current_path = os.getcwd()
    return current_path.replace('\\', '/')

def main():
    linux_style_path = get_current_directory_as_linux_path()
    print(linux_style_path)

    try:
        pyperclip.copy(linux_style_path)
        print("Current directory path copied to clipboard.")
    except pyperclip.PyperclipException as e:
        print(f"Error: Could not copy to clipboard: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during clipboard operation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
