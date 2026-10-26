"""Shared test fixtures. Tests use unittest so they run with `python -m unittest` or pytest."""

import contextlib
import os
import io
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Tuple

from bale.cli import main


def make_tree(root: Path, files: Dict[str, object]) -> None:
    """Create files under root. Values may be str (text) or bytes."""
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:  # open() rather than Path.write_text(newline=...), which needs Python 3.10
            with open(str(path), "w", encoding="utf-8", newline="") as handle:
                handle.write(content)


def run_cli(*argv: str) -> Tuple[int, str, str]:
    """Run the CLI in-process. Returns (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


# A small project shaped like a real monorepo, used by several test modules.
PROJECT = {
    ".gitignore": "*.log\n!keep.log\n/scratch/\ncoverage-report/\n",
    ".env": "JWT_SECRET=super-secret\n",
    ".env.example": "JWT_SECRET=\n",
    "README.md": "# Demo\n",
    "pnpm-lock.yaml": "lockfileVersion: 9\n",
    "app.log": "noise\n",
    "keep.log": "keep me\n",
    "scratch/notes.txt": "ignored by /scratch/\n",
    "docs/scratch/kept.txt": "/scratch/ is anchored, so this stays\n",
    "node_modules/pkg/index.js": "module.exports = 1\n",
    "dist/bundle.js": "built\n",
    "backend/.gitignore": "generated/\n",
    "backend/generated/out.ts": "ignored by nested gitignore\n",
    "backend/src/app.ts": "export const app = 1\n",
    "backend/src/index.ts": "export * from './app'\n",
    "shared/src/index.ts": "export const shared = 1\n",
    "logo.png": b"\x89PNG\r\n\x1a\n\x00\x00\x00",
    "empty.txt": "",
}


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(os.path.realpath(self._tmp.name))

    def project(self, files=None) -> Path:
        root = self.tmp / "proj"
        root.mkdir()
        make_tree(root, PROJECT if files is None else files)
        return root
