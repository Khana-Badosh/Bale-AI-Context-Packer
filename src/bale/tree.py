"""Render a scanned folder as a visual tree."""

from __future__ import annotations

from typing import List

from .walk import Node


def render_tree(
    root: Node,
    *,
    ascii_only: bool = False,
    dirs_only: bool = False,
    header: bool = True,
) -> str:
    """Return the tree as text (no trailing newline).

    The header keeps the original script's look:  "📁 Project Structure: name".
    """
    tee, elbow, pipe, blank = (
        ("+-- ", "`-- ", "|   ", "    ") if ascii_only else ("├── ", "└── ", "│   ", "    ")
    )
    lines: List[str] = []
    if header:
        icon = "" if ascii_only else "📁 "
        lines.append(f"{icon}Project Structure: {root.name}")

    def walk(node: Node, prefix: str) -> None:
        if node.error:
            lines.append(f"{prefix}{elbow}[{node.error}]")
            return
        children = [c for c in node.children if c.is_dir or not dirs_only]
        for index, child in enumerate(children):
            last = index == len(children) - 1
            label = child.name
            if child.is_symlink:
                label += " (symlink)"
            lines.append(f"{prefix}{elbow if last else tee}{label}")
            if child.is_dir:
                walk(child, prefix + (blank if last else pipe))

    if root.error:
        lines.append(f"{elbow}[{root.error}]")
    else:
        walk(root, "")
    return "\n".join(lines)
