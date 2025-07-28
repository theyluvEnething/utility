#!/usr/bin/env python3
import os
import stat
import sys
from datetime import datetime

IS_POSIX = os.name == 'posix'
if IS_POSIX:
    import pwd
    import grp

def get_file_type_char(mode):
    if stat.S_ISDIR(mode):
        return 'd'
    if stat.S_ISLNK(mode):
        return 'l'
    if stat.S_ISCHR(mode):
        return 'c'
    if stat.S_ISBLK(mode):
        return 'b'
    if stat.S_ISFIFO(mode):
        return 'p'
    if stat.S_ISSOCK(mode):
        return 's'
    return '-'

def get_permission_string(mode):
    permissions = [
        (stat.S_IRUSR, 'r'), (stat.S_IWUSR, 'w'), (stat.S_IXUSR, 'x'),
        (stat.S_IRGRP, 'r'), (stat.S_IWGRP, 'w'), (stat.S_IXGRP, 'x'),
        (stat.S_IROTH, 'r'), (stat.S_IWOTH, 'w'), (stat.S_IXOTH, 'x'),
    ]
    perm_str = ''.join(p if mode & p else '-' for p in permissions)

    if mode & stat.S_ISUID:
        perm_str = perm_str[:2] + ('s' if perm_str == 'x' else 'S') + perm_str[3:]
    if mode & stat.S_ISGID:
        perm_str = perm_str[:5] + ('s' if perm_str == 'x' else 'S') + perm_str[6:]
    if mode & stat.S_ISVTX:
        perm_str = perm_str[:8] + ('t' if perm_str == 'x' else 'T')
    return perm_str

def format_time(mtime_epoch):
    mtime = datetime.fromtimestamp(mtime_epoch)
    six_months_ago = datetime.now() - datetime.timedelta(days=180)
    if mtime < six_months_ago:
        return mtime.strftime('%b %d  %Y')
    return mtime.strftime('%b %d %H:%M')

def get_owner_and_group(stat_info):
    if IS_POSIX:
        try:
            owner = pwd.getpwuid(stat_info.st_uid).pw_name
        except KeyError:
            owner = str(stat_info.st_uid)
        try:
            group = grp.getgrgid(stat_info.st_gid).gr_name
        except KeyError:
            group = str(stat_info.st_gid)
    else:
        owner = str(stat_info.st_uid)
        group = str(stat_info.st_gid)
    return owner, group

def format_ls_output(path):
    try:
        with os.scandir(path) as it:
            entries = list(it)
    except OSError as e:
        print(f"ls: cannot access '{path}': {e}", file=sys.stderr)
        return

    file_details = []
    total_blocks = 0

    for entry in entries:
        try:
            stat_info = entry.stat(follow_symlinks=False)
        except OSError:
            continue
        
        mode = stat_info.st_mode
        file_type = get_file_type_char(mode)
        permissions = get_permission_string(mode)
        permission_str = file_type + permissions

        owner, group = get_owner_and_group(stat_info)
        
        name = entry.name
        if file_type == 'l':
            try:
                target = os.readlink(entry.path)
                name = f"{entry.name} -> {target}"
            except OSError:
                name = f"{entry.name} -> [broken link]"

        file_details.append({
            'permissions': permission_str,
            'links': stat_info.st_nlink,
            'owner': owner,
            'group': group,
            'size': stat_info.st_size,
            'mtime': format_time(stat_info.st_mtime),
            'name': name
        })
        
        if hasattr(stat_info, 'st_blocks'):
            total_blocks += stat_info.st_blocks

    if not file_details:
        return
        
    link_width = len(str(max(d['links'] for d in file_details)))
    owner_width = len(max((d['owner'] for d in file_details), key=len))
    group_width = len(max((d['group'] for d in file_details), key=len))
    size_width = len(str(max(d['size'] for d in file_details)))

    if IS_POSIX:
        print(f"total {total_blocks // 2}")

    for detail in sorted(file_details, key=lambda x: x['name'].lower()):
        print(
            f"{detail['permissions']} "
            f"{str(detail['links']).rjust(link_width)} "
            f"{detail['owner'].ljust(owner_width)} "
            f"{detail['group'].ljust(group_width)} "
            f"{str(detail['size']).rjust(size_width)} "
            f"{detail['mtime']} "
            f"{detail['name']}"
        )

def main():
    if len(sys.argv) > 1:
        target_path = sys.argv
    else:
        target_path = '.'
    
    if not os.path.exists(target_path):
        print(f"ls: cannot access '{target_path}': No such file or directory", file=sys.stderr)
        sys.exit(1)
        
    format_ls_output(target_path)

if __name__ == "__main__":
    main()