"""Command-line interface: `bale tree | bundle | flatten`."""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path
from typing import List, Optional, Sequence

from . import __version__
from .bundle import build_bundle
from .flatten import check_destination, plan_names, run_flatten
from .rules import OUTPUT_DIR
from .tree import render_tree
from .util import BaleError, abspath, copy_to_clipboard, write_text_file
from .walk import (
    SECRET,
    TOO_LARGE,
    ContentOptions,
    ScanOptions,
    Skipped,
    collect_files,
    scan,
)


def _err(message: str = "") -> None:
    print(message, file=sys.stderr)


def _force_utf8() -> None:
    """Make box-drawing characters and emoji safe on Windows consoles and pipes."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def _shown(path: Path) -> str:
    """A path as the user would want to read it: relative to where they are, if shorter."""
    try:
        rel = os.path.relpath(str(path))
    except ValueError:  # different drive on Windows
        return str(path)
    return rel if len(rel) < len(str(path)) else str(path)


# ----------------------------------------------------------------------------
# argument parsing
# ----------------------------------------------------------------------------

def _scan_parent() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("path", nargs="?", default=".", help="Project folder to process (default: current folder)")
    p.add_argument("--ignore", action="append", default=[], metavar="PATTERN",
                   help="Pattern to skip, in .gitignore syntax (repeatable), e.g. --ignore '*.sql'")
    p.add_argument("--no-gitignore", action="store_true", help="Do not read .gitignore files")
    p.add_argument("--no-defaults", action="store_true",
                   help="Do not skip node_modules, dist, caches and other built-in ignores")
    p.add_argument("-q", "--quiet", action="store_true", help="Suppress the summary on stderr")
    return p


def _content_parent() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--include", action="append", default=[], metavar="PATTERN",
                   help="Include only files matching this .gitignore-syntax pattern (repeatable)")
    p.add_argument("--max-size", type=int, default=1024, metavar="KB",
                   help="Skip files larger than this many KB (default: 1024)")
    p.add_argument("--include-secrets", action="store_true",
                   help="DANGEROUS: include .env files, private keys and other credential files")
    p.add_argument("--include-lockfiles", action="store_true",
                   help="Include lockfiles such as package-lock.json and pnpm-lock.yaml")
    return p


def _add_help(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-h", "--help", action="help", help="Show this help message and exit")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bale",
        add_help=False,
        description="Pack a project folder into an AI-ready prompt: tree, bundle and flatten. "
                    f"By default, output is written inside the project, in {OUTPUT_DIR}/.",
    )
    _add_help(parser)
    parser.add_argument("--version", action="version", version=f"bale {__version__}",
                        help="Show the version and exit")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    scan_p, content_p = _scan_parent(), _content_parent()

    tree = sub.add_parser("tree", add_help=False, parents=[scan_p], help="Print a visual directory tree",
                          description="Print a visual directory tree, respecting .gitignore. "
                                      "Prints to the terminal unless you pass -o or --copy.")
    tree.add_argument("-d", "--depth", type=int, metavar="N", help="Limit the tree depth")
    tree.add_argument("--dirs-only", action="store_true", help="Show directories only")
    tree.add_argument("--ascii", action="store_true", help="Use plain ASCII instead of box-drawing characters")
    tree.add_argument("--no-header", action="store_true", help="Omit the 'Project Structure' header line")
    tree.add_argument("-o", "--output", metavar="FILE", help="Write to FILE instead of the terminal")
    tree.add_argument("--copy", action="store_true", help="Copy the result to the clipboard")
    tree.set_defaults(func=cmd_tree)

    bundle = sub.add_parser("bundle", add_help=False, parents=[scan_p, content_p],
        help=f"Combine tree + all file contents into one Markdown file ({OUTPUT_DIR}/bundle.md)",
        description="Combine the directory tree and the contents of every text file into one "
                    f"Markdown document. Saved to PROJECT/{OUTPUT_DIR}/bundle.md by default.")
    bundle.add_argument("--no-tree", action="store_true", help="Omit the directory tree section")
    where = bundle.add_mutually_exclusive_group()
    where.add_argument("-o", "--output", metavar="FILE", help=f"Write to FILE instead of {OUTPUT_DIR}/bundle.md")
    where.add_argument("--stdout", action="store_true", help="Print to the terminal instead of saving a file")
    bundle.add_argument("--copy", action="store_true", help="Also copy the result to the clipboard")
    bundle.set_defaults(func=cmd_bundle)

    flat = sub.add_parser("flatten", add_help=False, parents=[scan_p, content_p],
        help=f"Copy all files into one flat folder ({OUTPUT_DIR}/flat/)",
        description="Copy every file into a single flat folder (handy for AI tools that only "
                    f"accept file uploads). Saved to PROJECT/{OUTPUT_DIR}/flat/ by default. "
                    "Your original files are never modified.")
    flat.add_argument("-o", "--output", metavar="DIR", help=f"Destination folder (default: PROJECT/{OUTPUT_DIR}/flat)")
    flat.add_argument("--names", choices=("path", "name"), default="path",
                      help="'path' (default) names files backend__src__app.ts; "
                           "'name' keeps app.ts and adds _1, _2 on clashes")
    flat.add_argument("--clean", action="store_true",
                      help="With -o: empty the destination first (only if a previous flatten created it)")
    flat.add_argument("--dry-run", action="store_true", help="Show what would be copied, change nothing")
    flat.add_argument("--include-binary", action="store_true", help="Also copy images and other binary files")
    flat.set_defaults(func=cmd_flatten)
    for sub_parser in (tree, bundle, flat):
        _add_help(sub_parser)
    return parser


# ----------------------------------------------------------------------------
# shared helpers
# ----------------------------------------------------------------------------

def _scan_options(args: argparse.Namespace, *, depth: Optional[int] = None,
                  exclude: Sequence[Path] = ()) -> ScanOptions:
    return ScanOptions(
        use_gitignore=not args.no_gitignore,
        use_defaults=not args.no_defaults,
        extra_ignore=tuple(args.ignore),
        max_depth=depth,
        exclude_paths=tuple(exclude),
    )


def _content_options(args: argparse.Namespace, *, include_binary: bool = False) -> ContentOptions:
    return ContentOptions(
        include=tuple(args.include),
        max_size=max(1, args.max_size) * 1024,
        include_secrets=args.include_secrets,
        include_lockfiles=args.include_lockfiles,
        include_binary=include_binary,
    )


def _project_dir(args: argparse.Namespace) -> Path:
    path = Path(args.path)
    if not path.exists():
        raise BaleError(f"no such folder: {path}")
    if not path.is_dir():
        raise BaleError(f"not a folder: {path}")
    return abspath(path)


def _report_skips(skipped: Sequence[Skipped]) -> None:
    """Summarise what was left out. Secrets are always named so nothing is silent."""
    if not skipped:
        return
    by_reason = Counter(s.reason for s in skipped)
    parts: List[str] = []
    for reason, count in by_reason.most_common():
        label = f"{count} {reason}" + ("s" if count > 1 and reason in (SECRET, "lockfile", "symlink") else "")
        if reason in (SECRET, TOO_LARGE):
            names = [s.node.rel for s in skipped if s.reason == reason]
            shown = ", ".join(names[:5]) + (f", +{len(names) - 5} more" if len(names) > 5 else "")
            label += f" ({shown})"
        parts.append(label)
    _err("Skipped: " + "; ".join(parts))
    if by_reason.get(SECRET):
        _err("  Secret files are excluded by default. Use --include-secrets to override.")


def _save(path: Path, text: str) -> None:
    """Write `text` to `path`. A new .bale/ folder git-ignores itself (no edits to your .gitignore)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.name == OUTPUT_DIR:
        marker = path.parent / ".gitignore"
        if not marker.exists():
            write_text_file(marker, "# Output written by bale. Safe to delete.\n*\n")
    write_text_file(path, text if text.endswith("\n") else text + "\n")


def _emit(text: str, args: argparse.Namespace, what: str, default_path: Optional[Path] = None) -> None:
    """Deliver output: a file (-o, or the default inside the project), the clipboard, or stdout."""
    target = Path(args.output) if args.output else default_path
    to_stdout = getattr(args, "stdout", False)
    delivered = False

    def print_it() -> None:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")

    if target is not None and not to_stdout:
        _save(target, text)
        delivered = True
        if not args.quiet:
            _err(f"Saved {what} to {_shown(abspath(target))}")
    elif not args.copy or to_stdout:
        print_it()
        delivered = True

    if args.copy:
        ok, problem = copy_to_clipboard(text)
        if ok:
            if not args.quiet:
                _err(f"Copied {what} to the clipboard")
        else:
            _err(f"bale: could not copy to clipboard: {problem}")
            if not delivered:  # never lose the result because the clipboard failed
                print_it()


# ----------------------------------------------------------------------------
# commands
# ----------------------------------------------------------------------------

def cmd_tree(args: argparse.Namespace) -> int:
    project = _project_dir(args)
    exclude = [abspath(args.output)] if args.output else []
    root = scan(project, _scan_options(args, depth=args.depth, exclude=exclude))
    text = render_tree(root, ascii_only=args.ascii, dirs_only=args.dirs_only, header=not args.no_header)
    _emit(text, args, "tree")
    return 0


def cmd_bundle(args: argparse.Namespace) -> int:
    project = _project_dir(args)
    exclude = [abspath(args.output)] if args.output else []
    root = scan(project, _scan_options(args, exclude=exclude))
    files, skipped = collect_files(root, _content_options(args))
    result = build_bundle(root, files, include_tree=not args.no_tree)
    _emit(result.text, args, "bundle", default_path=project / OUTPUT_DIR / "bundle.md")
    if not args.quiet:
        _err(f"Bundled {result.file_count} files · {len(result.text):,} chars · "
             f"≈{result.token_estimate:,} tokens (rough estimate)")
        _report_skips(skipped + result.skipped)
    return 0


def cmd_flatten(args: argparse.Namespace) -> int:
    source = _project_dir(args)
    default_dest = source / OUTPUT_DIR / "flat"
    dest = abspath(args.output) if args.output else default_dest
    # The default folder belongs to bale, so re-running replaces the previous result.
    # A folder you named yourself needs an explicit --clean.
    replace = args.clean or dest == default_dest

    check_destination(dest, source, replace)
    root = scan(source, _scan_options(args, exclude=[dest]))
    files, skipped = collect_files(root, _content_options(args, include_binary=args.include_binary))
    plan = plan_names(files, args.names)

    if args.dry_run:
        for node, target, _ in plan:
            print(f"{node.rel}  ->  {target}")
        if not args.quiet:
            _err(f"Dry run: {len(plan)} files would be copied to {_shown(dest)}")
            _report_skips(skipped)
        return 0

    result = run_flatten(plan, dest, source, replace=replace)
    if dest == default_dest:
        marker = dest.parent / ".gitignore"
        if not marker.exists():
            write_text_file(marker, "# Output written by bale. Safe to delete.\n*\n")
    if not args.quiet:
        _err(f"Copied {result.copied} files into {_shown(result.destination)}")
        if result.renamed:
            _err(f"Resolved {result.renamed} filename collisions with numeric suffixes")
        _report_skips(skipped)
    for problem in result.errors:
        _err(f"bale: could not copy {problem}")
    return 1 if result.errors else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    _force_utf8()
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except BaleError as exc:
        _err(f"bale: error: {exc}")
        return 1
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:  # e.g. `bale bundle --stdout | head`
        return 0


if __name__ == "__main__":
    sys.exit(main())
