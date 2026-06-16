#!/usr/bin/env python3
"""extract <archive> — unpack an archive into ./<archive-name>/.

Handles .zip, .tar(.gz/.bz2/.xz), .tgz, and standalone .gz with the standard
library. .7z and .rar are delegated to the 7z / unrar binaries if present.
Archive members with absolute or parent-traversal paths are rejected (zip-slip).
"""
import gzip
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile

from utilkit import ui

_TAR_SUFFIXES = (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")


class ExtractError(Exception):
    pass


def _dest_dir(archive):
    base = os.path.basename(archive)
    for suffix in (".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz2", ".txz",
                   ".tar", ".zip", ".7z", ".rar", ".gz"):
        if base.lower().endswith(suffix):
            base = base[: -len(suffix)]
            break
    return os.path.join(os.getcwd(), base)


def _is_within(directory, target):
    directory = os.path.abspath(directory)
    target = os.path.abspath(target)
    return os.path.commonpath([directory, target]) == directory


def _check_members(names, dest):
    for name in names:
        if os.path.isabs(name) or not _is_within(dest, os.path.join(dest, name)):
            raise ExtractError(f"refusing unsafe path in archive: {name}")


def _zip(archive, dest):
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        _check_members(names, dest)
        zf.extractall(dest)
        return len(names)


def _tar(archive, dest):
    with tarfile.open(archive) as tf:
        members = tf.getmembers()
        _check_members([m.name for m in members], dest)
        tf.extractall(dest)
        return len(members)


def _gz_single(archive, dest):
    os.makedirs(dest, exist_ok=True)
    out_name = os.path.basename(archive)[:-3] or "output"
    with gzip.open(archive, "rb") as src, open(os.path.join(dest, out_name), "wb") as dst:
        shutil.copyfileobj(src, dst)
    return 1


def _external(tool, archive, dest, build_cmd):
    if not shutil.which(tool):
        raise ExtractError(
            f"'{tool}' is required to extract this archive but was not found on PATH."
        )
    os.makedirs(dest, exist_ok=True)
    code = subprocess.call(build_cmd(archive, dest))
    if code != 0:
        raise ExtractError(f"{tool} failed with exit code {code}.")
    return None


def _prevalidate(archive, dest):
    """Reject unsafe member paths before any output or extraction begins."""
    lower = archive.lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            _check_members(zf.namelist(), dest)
    elif lower.endswith(_TAR_SUFFIXES):
        with tarfile.open(archive) as tf:
            _check_members([m.name for m in tf.getmembers()], dest)


def _handler_for(lower):
    if lower.endswith(".zip"):
        return _zip
    if lower.endswith(_TAR_SUFFIXES):
        return _tar
    if lower.endswith(".7z"):
        return lambda a, d: _external("7z", a, d, lambda a, d: ["7z", "x", "-y", f"-o{d}", a])
    if lower.endswith(".rar"):
        return lambda a, d: _external("unrar", a, d, lambda a, d: ["unrar", "x", "-y", a, d])
    if lower.endswith(".gz"):
        return _gz_single
    return None


def main():
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: extract <archive>")
        sys.exit(0 if len(sys.argv) == 2 else 1)

    archive = sys.argv[1]
    if not os.path.isfile(archive):
        ui.error(f"no such file: {archive}")
        sys.exit(1)

    handler = _handler_for(archive.lower())
    if handler is None:
        ui.error(f"unsupported archive type: {os.path.basename(archive)}")
        sys.exit(1)

    dest = _dest_dir(archive)

    try:
        _prevalidate(archive, dest)
    except ExtractError as exc:
        ui.error(str(exc))
        sys.exit(1)
    except (zipfile.BadZipFile, tarfile.TarError, OSError) as exc:
        ui.error(f"could not read archive: {exc}")
        sys.exit(1)

    ui.header(f"Extracting {os.path.basename(archive)}")
    ui.kv("Into", dest)
    print()

    try:
        count = handler(archive, dest)
    except ExtractError as exc:
        ui.error(str(exc))
        sys.exit(1)
    except (zipfile.BadZipFile, tarfile.TarError, OSError) as exc:
        ui.error(f"could not extract: {exc}")
        sys.exit(1)

    if count is None:
        ui.ok(f"extracted to {ui.style(dest, 'bold')}")
    else:
        ui.ok(f"extracted {ui.style(count, 'bold')} item(s) to {ui.style(dest, 'bold')}")


if __name__ == "__main__":
    main()
