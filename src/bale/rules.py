"""Built-in ignore rules and file classification.

These are the defaults applied on top of .gitignore. The design goal is that the
tool is safe to point at any project without leaking secrets or flooding a prompt
with build output.
"""

from __future__ import annotations

from fnmatch import fnmatchcase
from pathlib import Path

# Version-control metadata is never useful, and .bale/ is where bale writes its own
# output (so it must never be read back in). Skipped even with --no-defaults.
# Name of the folder bale writes its output to, inside the project.
OUTPUT_DIR = ".bale"

ALWAYS_SKIP = frozenset({".git", ".hg", ".svn", OUTPUT_DIR})

# Directories that are almost never worth sending to an AI (dependencies, caches,
# build output, editor state). Skipped by name, anywhere in the tree.
DEFAULT_IGNORE_DIRS = frozenset(
    {
        # dependencies / virtual environments
        "node_modules", ".venv", "venv", "__pypackages__", ".pnpm-store", ".yarn",
        # caches
        "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
        ".cache", ".parcel-cache", ".turbo", ".eslintcache", ".gradle",
        # build output
        "dist", "build", "target", ".next", ".nuxt", ".svelte-kit", "out",
        "coverage", ".nyc_output",
        # editor / OS state
        ".idea", ".vscode", ".vs",
    }
)

# Noise files that are skipped everywhere (tree, flatten and bundle).
JUNK_FILES = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})

# Lockfiles: huge, machine-generated, rarely useful to a model. Hidden from
# content output by default, but still shown in the tree.
LOCKFILES = frozenset(
    {
        "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock",
        "poetry.lock", "uv.lock", "Pipfile.lock", "Cargo.lock", "composer.lock",
        "Gemfile.lock", "go.sum", "gradle.lockfile", "pubspec.lock", "flake.lock",
    }
)

# File names that commonly hold credentials. Their contents are never emitted
# unless the user passes --include-secrets.
SECRET_PATTERNS = (
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "*.keystore", "*.jks",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", ".npmrc", ".pypirc", ".netrc",
    "credentials.json", "secrets.json", "*.tfstate", "*.tfvars",
)

# Templates that look like secrets by name but are meant to be committed.
SECRET_SAFE = frozenset({".env.example", ".env.sample", ".env.template", ".env.dist"})

BINARY_EXTENSIONS = frozenset(
    {
        # images / media
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".tiff", ".psd",
        ".mp3", ".wav", ".flac", ".ogg", ".mp4", ".mov", ".avi", ".mkv", ".webm",
        # archives
        ".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar",
        # compiled / executables
        ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a", ".class", ".jar",
        ".pyc", ".pyo", ".wasm",
        # documents / fonts / data
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".ttf", ".otf", ".woff", ".woff2", ".eot",
        ".db", ".sqlite", ".sqlite3", ".parquet",
    }
)


def is_default_ignored(name: str, is_dir: bool) -> bool:
    """True if a directory/file name is skipped by the built-in defaults."""
    if is_dir:
        return name in DEFAULT_IGNORE_DIRS or name.endswith(".egg-info")
    return name in JUNK_FILES


def is_secret(name: str) -> bool:
    lowered = name.lower()
    if lowered in SECRET_SAFE:
        return False
    return any(fnmatchcase(lowered, pattern) for pattern in SECRET_PATTERNS)


def is_lockfile(name: str) -> bool:
    return name in LOCKFILES


def is_binary(path: Path) -> bool:
    """Binary by extension, otherwise by sniffing for NUL bytes in the first 8 KB."""
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(path, "rb") as handle:
            return b"\0" in handle.read(8192)
    except OSError:
        return True
