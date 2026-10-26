"""Copy every file in a project into one flat folder."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence, Set, Tuple

from .util import BaleError, abspath, write_text_file
from .walk import Node

MARKER = ".bale-flatten"


@dataclass
class FlattenResult:
    destination: Path
    copied: int = 0
    renamed: int = 0  # files that needed a numeric suffix to avoid a name clash
    errors: List[str] = field(default_factory=list)


def plan_names(files: Sequence[Node], names: str) -> List[Tuple[Node, str, bool]]:
    """Choose a destination file name for every file.

    names="path": backend/src/app.ts -> backend__src__app.ts (self-describing, rarely clashes)
    names="name": app.ts, with _1, _2, ... appended on clashes
    Returns (node, target_name, was_renamed_for_collision).
    """
    used: Set[str] = set()  # lowercase, because Windows/macOS file systems are case-insensitive
    plan: List[Tuple[Node, str, bool]] = []
    for node in files:
        base = node.rel.replace("/", "__") if names == "path" else node.name
        candidate, renamed, counter = base, False, 0
        stem, ext = os.path.splitext(base)
        while candidate.lower() in used:
            counter += 1
            candidate, renamed = f"{stem}_{counter}{ext}", True
        used.add(candidate.lower())
        plan.append((node, candidate, renamed))
    return plan


def check_destination(dest: Path, source: Path, replace: bool) -> None:
    """Raise BaleError if `dest` is unsafe to write to. Never modifies anything.

    `replace` means "an earlier flatten output here may be wiped and rewritten". It is
    only ever honoured for folders that carry bale's marker file, so a typo in -o
    can never delete an unrelated folder.
    """
    dest, source = abspath(dest), abspath(source)
    if dest == source or dest in source.parents:
        raise BaleError(f"destination {dest} contains the source folder; choose another -o")
    if dest.exists() and not dest.is_dir():
        raise BaleError(f"destination {dest} exists and is not a folder")
    if dest.is_dir() and any(dest.iterdir()):
        ours = (dest / MARKER).exists()
        if replace and ours:
            return
        if replace:
            raise BaleError(
                f"refusing to replace {dest}: it was not created by 'bale flatten' "
                f"(no {MARKER} marker inside). Delete it yourself or choose another -o."
            )
        raise BaleError(
            f"destination {dest} is not empty. Use --clean to replace the output of a "
            "previous flatten, or choose another -o."
        )


def run_flatten(
    plan: Sequence[Tuple[Node, str, bool]],
    dest: Path,
    source: Path,
    *,
    replace: bool = False,
) -> FlattenResult:
    check_destination(dest, source, replace)
    dest = abspath(dest)

    if dest.is_dir() and replace:
        for child in dest.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(str(child))
            else:
                child.unlink()
    dest.mkdir(parents=True, exist_ok=True)
    write_text_file(
        dest / MARKER,
        f"Created by bale flatten from {abspath(source)}\n"
        "Safe to replace with: bale flatten --clean\n",
    )

    result = FlattenResult(destination=dest)
    for node, target_name, renamed in plan:
        try:
            shutil.copy2(str(node.path), str(dest / target_name))
        except OSError as exc:
            result.errors.append(f"{node.rel}: {exc}")
            continue
        result.copied += 1
        result.renamed += int(renamed)
    return result
