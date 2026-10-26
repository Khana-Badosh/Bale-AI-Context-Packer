"""Bundle a project into one Markdown document for pasting into an AI chat."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Dict, List, Sequence

from .tree import render_tree
from .util import estimate_tokens, fence_for, read_text
from .walk import UNREADABLE, Node, Skipped

# File extension -> Markdown code-fence language.
LANGUAGES: Dict[str, str] = {
    ".py": "python", ".ts": "ts", ".tsx": "tsx", ".js": "js", ".jsx": "jsx",
    ".mjs": "js", ".cjs": "js", ".json": "json", ".md": "markdown", ".sql": "sql",
    ".yml": "yaml", ".yaml": "yaml", ".toml": "toml", ".sh": "bash", ".bash": "bash",
    ".ps1": "powershell", ".css": "css", ".scss": "scss", ".html": "html",
    ".xml": "xml", ".go": "go", ".rs": "rust", ".java": "java", ".kt": "kotlin",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp", ".cs": "csharp",
    ".rb": "ruby", ".php": "php", ".swift": "swift", ".dockerfile": "dockerfile",
}


@dataclass
class BundleResult:
    text: str
    file_count: int
    token_estimate: int
    skipped: List[Skipped]  # files that failed to read while bundling


def _language(node: Node) -> str:
    if node.name.lower() == "dockerfile":
        return "dockerfile"
    return LANGUAGES.get(PurePosixPath(node.name).suffix.lower(), "")


def build_bundle(root: Node, files: Sequence[Node], *, include_tree: bool = True) -> BundleResult:
    parts: List[str] = [f"# {root.name}", ""]

    if include_tree:
        tree = render_tree(root, header=False)
        fence = fence_for(tree)
        parts += ["## Directory structure", "", f"{fence}text", tree, fence, ""]

    parts += ["## Files", ""]
    failed: List[Skipped] = []
    written = 0

    for node in files:
        try:
            content = read_text(node.path)
        except OSError:
            failed.append(Skipped(node, UNREADABLE))
            continue
        if not content.endswith("\n"):
            content += "\n"
        fence = fence_for(content)
        parts += [f"### {node.rel}", "", f"{fence}{_language(node)}", content.rstrip("\n"), fence, ""]
        written += 1

    text = "\n".join(parts).rstrip("\n") + "\n"
    return BundleResult(text, written, estimate_tokens(text), failed)
