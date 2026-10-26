"""Folder scanning: a .gitignore-aware walk plus content filtering."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple

from pathspec import GitIgnoreSpec

from . import rules
from .util import abspath

# Reasons a file can be left out of flatten/bundle output.
SECRET = "secret"
LOCKFILE = "lockfile"
BINARY = "binary"
TOO_LARGE = "too large"
EMPTY = "empty"
SYMLINK = "symlink"
NOT_INCLUDED = "not matched by --include"
UNREADABLE = "unreadable"

# (base directory, parsed .gitignore) pairs, ordered from the outermost directory in.
_SpecStack = List[Tuple[Path, GitIgnoreSpec]]


@dataclass
class ScanOptions:
    use_gitignore: bool = True
    use_defaults: bool = True
    extra_ignore: Sequence[str] = ()
    max_depth: Optional[int] = None
    # Absolute paths that must never be listed (e.g. the output file or folder).
    exclude_paths: Sequence[Path] = ()


@dataclass
class ContentOptions:
    include: Sequence[str] = ()
    max_size: int = 1024 * 1024
    include_secrets: bool = False
    include_lockfiles: bool = False
    include_binary: bool = False


@dataclass
class Node:
    path: Path
    name: str
    rel: str  # POSIX-style path relative to the scan root ("" for the root)
    is_dir: bool
    is_symlink: bool = False
    children: List["Node"] = field(default_factory=list)
    truncated: bool = False  # directory not expanded because of --depth
    error: Optional[str] = None  # e.g. "Permission Denied"


@dataclass
class Skipped:
    node: Node
    reason: str


def _load_spec(gitignore: Path) -> Optional[GitIgnoreSpec]:
    try:
        text = gitignore.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return GitIgnoreSpec.from_lines(text.splitlines())


def _ancestor_specs(root: Path) -> _SpecStack:
    """Load .gitignore files from the enclosing git repo (if any) above `root`.

    This makes `bale tree backend/src` honour the repo's top-level .gitignore.
    """
    lineage = [root, *root.parents]
    git_root = next((p for p in lineage if (p / ".git").exists()), None)
    if git_root is None or git_root == root:
        return []
    chain = [p for p in lineage[1:] if p == git_root or git_root in p.parents]
    stack: _SpecStack = []
    for directory in reversed(chain):  # outermost first
        gitignore = directory / ".gitignore"
        if gitignore.is_file():
            spec = _load_spec(gitignore)
            if spec is not None:
                stack.append((directory, spec))
    return stack


def _gitignored(path: Path, is_dir: bool, stack: _SpecStack) -> bool:
    """Apply every active .gitignore in order; the last matching pattern wins."""
    ignored = False
    for base, spec in stack:
        try:
            rel = path.relative_to(base).as_posix()
        except ValueError:
            continue
        if is_dir:
            rel += "/"
        result = spec.check_file(rel)
        if result.include is not None:
            ignored = bool(result.include)
    return ignored


@dataclass
class _Ctx:
    opts: ScanOptions
    extra: Optional[GitIgnoreSpec]
    excluded: frozenset


def scan(root: Path, opts: Optional[ScanOptions] = None) -> Node:
    """Scan `root` and return the tree of entries that survive the ignore rules."""
    opts = opts or ScanOptions()
    root = abspath(root)
    if not root.is_dir():
        raise NotADirectoryError(str(root))

    extra = GitIgnoreSpec.from_lines(list(opts.extra_ignore)) if opts.extra_ignore else None
    excluded = frozenset(os.path.abspath(p) for p in opts.exclude_paths)
    ctx = _Ctx(opts=opts, extra=extra, excluded=excluded)

    stack = _ancestor_specs(root) if opts.use_gitignore else []
    top = Node(path=root, name=root.name or str(root), rel="", is_dir=True)
    _fill(top, 1, stack, ctx)
    return top


def _fill(node: Node, depth: int, stack: _SpecStack, ctx: _Ctx) -> None:
    if ctx.opts.use_gitignore:
        gitignore = node.path / ".gitignore"
        if gitignore.is_file():
            spec = _load_spec(gitignore)
            if spec is not None:
                stack = stack + [(node.path, spec)]

    try:
        with os.scandir(node.path) as it:
            entries = list(it)
    except PermissionError:
        node.error = "Permission Denied"
        return
    except OSError as exc:
        node.error = exc.strerror or "unreadable"
        return

    # Directories first, then files, each alphabetical (case-insensitive).
    entries.sort(key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))

    for entry in entries:
        name = entry.name
        is_dir = entry.is_dir(follow_symlinks=False)

        if name in rules.ALWAYS_SKIP:
            continue
        if ctx.opts.use_defaults and rules.is_default_ignored(name, is_dir):
            continue
        if ctx.excluded and os.path.abspath(entry.path) in ctx.excluded:
            continue

        path = Path(entry.path)
        rel = f"{node.rel}/{name}" if node.rel else name

        if ctx.opts.use_gitignore and _gitignored(path, is_dir, stack):
            continue
        if ctx.extra is not None and ctx.extra.match_file(rel + "/" if is_dir else rel):
            continue

        child = Node(path=path, name=name, rel=rel, is_dir=is_dir, is_symlink=entry.is_symlink())
        node.children.append(child)
        if is_dir:
            if ctx.opts.max_depth is not None and depth >= ctx.opts.max_depth:
                child.truncated = True
            else:
                _fill(child, depth + 1, stack, ctx)


def iter_files(node: Node) -> Iterator[Node]:
    """Yield every non-directory node, depth first, in tree order."""
    for child in node.children:
        if child.is_dir:
            yield from iter_files(child)
        else:
            yield child


def collect_files(root: Node, opts: ContentOptions) -> Tuple[List[Node], List[Skipped]]:
    """Split the scanned files into (readable files, skipped files with reasons)."""
    include = GitIgnoreSpec.from_lines(list(opts.include)) if opts.include else None
    keep: List[Node] = []
    skipped: List[Skipped] = []

    for node in iter_files(root):
        reason = _content_skip_reason(node, opts, include)
        if reason is None:
            keep.append(node)
        else:
            skipped.append(Skipped(node, reason))
    return keep, skipped


def _content_skip_reason(
    node: Node, opts: ContentOptions, include: Optional[GitIgnoreSpec]
) -> Optional[str]:
    if node.is_symlink:
        return SYMLINK
    if not opts.include_secrets and rules.is_secret(node.name):
        return SECRET
    if not opts.include_lockfiles and rules.is_lockfile(node.name):
        return LOCKFILE
    if include is not None and not include.match_file(node.rel):
        return NOT_INCLUDED
    try:
        size = node.path.stat().st_size
    except OSError:
        return UNREADABLE
    if size == 0:
        return EMPTY
    if size > opts.max_size:
        return TOO_LARGE
    if not opts.include_binary and rules.is_binary(node.path):
        return BINARY
    return None
