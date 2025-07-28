#!/usr/bin/env python3
import os
import stat
import sys

def _get_default_colors():
    return {
        'di': '01;34', 'ln': '01;36', 'so': '01;35', 'pi': '40;33',
        'ex': '01;32', 'bd': '40;33;01', 'cd': '40;33;01',
        'or': '40;31;01', 'mi': '00', 'su': '37;41', 'sg': '30;43',
        'ca': '30;41', 'tw': '30;42', 'ow': '34;42', 'st': '37;44',
        'fi': '00',
    }

def parse_ls_colors(ls_colors_str):
    colors = _get_default_colors()
    if not ls_colors_str:
        return colors
    
    for entry in ls_colors_str.split(':'):
        if not entry:
            continue
        parts = entry.split('=', 1)
        if len(parts) == 2:
            key, value = parts
            if key and value:
                colors[key] = value
    return colors

def get_color_for_entry(entry, stat_info, colors):
    mode = stat_info.st_mode
    
    key = None
    if stat.S_ISDIR(mode):
        key = 'di'
    elif stat.S_ISLNK(mode):
        key = 'ln'
    elif stat.S_ISFIFO(mode):
        key = 'pi'
    elif stat.S_ISSOCK(mode):
        key = 'so'
    elif stat.S_ISBLK(mode):
        key = 'bd'
    elif stat.S_ISCHR(mode):
        key = 'cd'
    elif mode & stat.S_IXUSR or mode & stat.S_IXGRP or mode & stat.S_IXOTH:
        key = 'ex'
    else:
        key = 'fi'

    ext_match = f"*.{entry.name.split('.')[-1]}"
    if ext_match in colors:
        return colors[ext_match]

    return colors.get(key, '00')

def format_grid_output(path, use_colors):
    try:
        entries = sorted(os.scandir(path), key=lambda e: e.name.lower())
    except OSError as e:
        print(f"ls: cannot access '{path}': {e}", file=sys.stderr)
        return

    if not entries:
        return

    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        terminal_width = 80

    colors = parse_ls_colors(os.environ.get('LS_COLORS'))
    
    display_items = []
    for entry in entries:
        try:
            stat_info = entry.stat(follow_symlinks=False)
        except OSError:
            continue
            
        name = entry.name
        if use_colors:
            color_code = get_color_for_entry(entry, stat_info, colors)
            name = f"\033[{color_code}m{name}\033[0m"
        display_items.append({'raw': entry.name, 'display': name})

    if not display_items:
        return

    max_len = max(len(item['raw']) for item in display_items)
    col_width = max_len + 2
    
    num_cols = max(1, terminal_width // col_width)
    num_rows = (len(display_items) + num_cols - 1) // num_cols

    for r in range(num_rows):
        row_items = []
        for c in range(num_cols):
            index = r + c * num_rows
            if index < len(display_items):
                item = display_items[index]
                padding = col_width - len(item['raw'])
                row_items.append(item['display'] + ' ' * padding)
        print("".join(row_items))

def format_single_column_output(path):
    try:
        entries = sorted(os.listdir(path), key=str.lower)
    except OSError as e:
        print(f"ls: cannot access '{path}': {e}", file=sys.stderr)
        return
        
    for name in entries:
        print(name)

def main():
    target_path = '.'
    if len(sys.argv) > 1:
        target_path = sys.argv

    if not os.path.exists(target_path) or not os.path.isdir(target_path):
        print(f"ls: cannot access '{target_path}': No such file or directory", file=sys.stderr)
        sys.exit(1)

    if sys.stdout.isatty():
        format_grid_output(target_path, use_colors=True)
    else:
        format_single_column_output(target_path)

if __name__ == "__main__":
    main()