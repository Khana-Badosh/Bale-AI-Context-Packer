"""Small helpers shared by the commands."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


class BaleError(Exception):
    """A user-facing error. The CLI prints the message and exits with status 1."""


def abspath(path) -> Path:
    """Absolute, symlink-resolved path that also works for paths that don't exist yet.

    Path.resolve() on Windows before Python 3.10 returns a relative path unchanged
    when it does not exist, which breaks "is the output inside the project?" checks.
    os.path.realpath does not have that problem.
    """
    return Path(os.path.realpath(str(path)))


def write_text_file(path: Path, text: str) -> None:
    """Write UTF-8 text with LF newlines (Path.write_text(newline=...) needs Python 3.10)."""
    with open(str(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def estimate_tokens(text: str) -> int:
    """Very rough token estimate (about 4 characters per token for code and prose)."""
    return max(1, round(len(text) / 4)) if text else 0


def read_text(path: Path) -> str:
    """Read a text file as UTF-8 (BOM stripped, bad bytes replaced, CRLF -> LF)."""
    data = path.read_bytes()
    return data.decode("utf-8-sig", errors="replace").replace("\r\n", "\n")


def fence_for(text: str) -> str:
    """Return a backtick fence long enough that `text` cannot close it early."""
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def _clipboard_commands() -> List[List[str]]:
    if sys.platform == "darwin":
        return [["pbcopy"]]
    if sys.platform.startswith("win"):
        return [
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "[Console]::InputEncoding=[Text.Encoding]::UTF8;"
                "Set-Clipboard -Value ([Console]::In.ReadToEnd())",
            ],
            ["clip"],
        ]
    commands: List[List[str]] = []
    if os.environ.get("WAYLAND_DISPLAY"):
        commands.append(["wl-copy"])
    commands += [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]
    commands.append(["wl-copy"])
    return commands


def copy_to_clipboard(text: str) -> Tuple[bool, Optional[str]]:
    """Copy text to the system clipboard. Returns (ok, error_message)."""
    for cmd in _clipboard_commands():
        if shutil.which(cmd[0]) is None:
            continue
        try:
            subprocess.run(cmd, input=text.encode("utf-8"), check=True, timeout=15,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, None
        except (subprocess.SubprocessError, OSError):
            continue
    return False, "no working clipboard tool found (tried pbcopy/clip/wl-copy/xclip/xsel)"
