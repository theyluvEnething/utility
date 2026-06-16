"""Single source of truth for ignore rules and toolkit settings.

Previously every context tool carried its own copy of these sets. Now they all
import from here. Users can extend (not replace) the ignore lists without
touching source by dropping a ``config.toml`` next to the sessions file.
"""
import os
from pathlib import Path

IGNORED_DIRECTORIES = {
    ".git", ".hg", ".svn", ".claude", ".planning", ".history",
    "__pycache__", "pycache", "venv", ".venv", "env", ".env",
    "node_modules", ".vscode", ".idea", "dist", "build", "builds",
    ".angular", "temp", "tmp", "libraries", "target", "gen", "icons",
    ".next", ".nuxt", ".cache", ".pytest_cache", ".mypy_cache",
    ".gradle", "coverage", ".tox", ".eggs",
}

IGNORED_EXTENSIONS = {
    "pyc", "pyo", "pyd", "so", "dll", "egg", "manifest", "spec", "mo", "pot",
    "log", "sqlite", "sqlite3", "sqlite3-journal", "db", "bak", "tmp", "swp", "swo",
    "png", "jpg", "jpeg", "gif", "bmp", "ico", "svg", "tif", "tiff", "webp",
    "zip", "tar", "gz", "tgz", "rar", "7z", "bz2", "xz",
    "exe", "bin", "o", "a", "lib", "class", "jar", "wasm",
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp",
    "mp3", "wav", "ogg", "flac", "mp4", "mkv", "avi", "mov", "wmv",
    "ttf", "otf", "woff", "woff2", "eot",
    "iso", "img", "dmg", "ignore",
    "mtl", "obj", "fbx", "stl", "gltf", "glb", "3ds", "blend", "dae", "ply",
    "usd", "usdz", "usda", "usdc", "max", "ma", "mb", "c4d", "wrl", "abc",
}

IGNORED_FILENAMES = {
    ".DS_Store", "Thumbs.db", ".gitignore", ".gitattributes", ".editorconfig",
    "LICENSE", "LICENCE", "README.md", "CONTRIBUTING.md", "CHANGELOG.md",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "Cargo.lock", "composer.lock",
}


def config_dir():
    """Per-user config directory, portable across Windows/macOS/Linux."""
    override = os.environ.get("UTILKIT_CONFIG_DIR")
    if override:
        return Path(override)
    return Path.home() / ".config" / "utilkit"


def sessions_file():
    return config_dir() / "servers.json"


def _load_user_overrides():
    """Merge extra ignore entries from ``config.toml`` if it exists.

    Keys (all optional): ``ignore_directories``, ``ignore_extensions``,
    ``ignore_filenames`` — each a list of strings that is *added* to the
    defaults. Missing file or tomllib is silently ignored.
    """
    path = config_dir() / "config.toml"
    if not path.exists():
        return
    try:
        import tomllib
    except ModuleNotFoundError:
        return
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return
    IGNORED_DIRECTORIES.update(data.get("ignore_directories", []))
    IGNORED_EXTENSIONS.update(e.lstrip(".") for e in data.get("ignore_extensions", []))
    IGNORED_FILENAMES.update(data.get("ignore_filenames", []))


_load_user_overrides()
