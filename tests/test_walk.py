import os
import unittest

from bale import walk
from bale.walk import ContentOptions, ScanOptions, collect_files, iter_files, scan

from helpers import TempDirTest, make_tree


def rels(root):
    return [n.rel for n in iter_files(root)]


class ScanTests(TempDirTest):
    def test_defaults_and_gitignore(self):
        files = rels(scan(self.project()))
        # skipped: node_modules, dist (defaults); app.log, scratch/ (gitignore); backend/generated (nested)
        self.assertNotIn("node_modules/pkg/index.js", files)
        self.assertNotIn("dist/bundle.js", files)
        self.assertNotIn("app.log", files)
        self.assertNotIn("scratch/notes.txt", files)
        self.assertNotIn("backend/generated/out.ts", files)

    def test_negation_and_anchoring(self):
        files = rels(scan(self.project()))
        self.assertIn("keep.log", files)  # !keep.log re-includes it
        self.assertIn("docs/scratch/kept.txt", files)  # /scratch/ only matches at the root

    def test_normal_files_present(self):
        files = rels(scan(self.project()))
        for expected in ("README.md", "backend/src/app.ts", "shared/src/index.ts", ".env", "pnpm-lock.yaml"):
            self.assertIn(expected, files)

    def test_git_dir_always_skipped(self):
        root = self.project()
        make_tree(root, {".git/config": "x", ".git/HEAD": "ref"})
        self.assertFalse(any(r.startswith(".git/") for r in rels(scan(root))))
        self.assertFalse(any(r.startswith(".git/") for r in rels(scan(root, ScanOptions(use_defaults=False, use_gitignore=False)))))

    def test_bale_output_folder_always_skipped(self):
        root = self.project()
        make_tree(root, {".bale/bundle.md": "old output", ".bale/flat/a.ts": "x"})
        opts = ScanOptions(use_defaults=False, use_gitignore=False)
        self.assertFalse(any(r.startswith(".bale") for r in rels(scan(root, opts))))

    def test_no_gitignore_flag(self):
        files = rels(scan(self.project(), ScanOptions(use_gitignore=False)))
        self.assertIn("app.log", files)
        self.assertIn("scratch/notes.txt", files)
        self.assertNotIn("node_modules/pkg/index.js", files)  # defaults still on

    def test_no_defaults_flag(self):
        files = rels(scan(self.project(), ScanOptions(use_defaults=False)))
        self.assertIn("node_modules/pkg/index.js", files)
        self.assertIn("dist/bundle.js", files)
        self.assertNotIn("app.log", files)  # gitignore still on

    def test_extra_ignore_patterns(self):
        files = rels(scan(self.project(), ScanOptions(extra_ignore=["*.md", "shared/"])))
        self.assertNotIn("README.md", files)
        self.assertNotIn("shared/src/index.ts", files)
        self.assertIn("backend/src/app.ts", files)

    def test_max_depth_truncates(self):
        root = scan(self.project(), ScanOptions(max_depth=1))
        backend = next(c for c in root.children if c.name == "backend")
        self.assertTrue(backend.truncated)
        self.assertEqual(backend.children, [])

    def test_excluded_paths_are_hidden(self):
        proj = self.project()
        out = proj / "out.md"
        out.write_text("generated")
        files = rels(scan(proj, ScanOptions(exclude_paths=[out])))
        self.assertNotIn("out.md", files)

    def test_dirs_sort_before_files(self):
        root = scan(self.project())
        kinds = [c.is_dir for c in root.children]
        self.assertEqual(kinds, sorted(kinds, reverse=True))

    def test_parent_repo_gitignore_applies_to_subfolder(self):
        repo = self.tmp / "repo"
        make_tree(repo, {".git/HEAD": "ref", ".gitignore": "*.tmp\n", "sub/a.ts": "a", "sub/b.tmp": "b"})
        files = rels(scan(repo / "sub"))
        self.assertEqual(files, ["a.ts"])

    def test_not_a_directory(self):
        f = self.tmp / "file.txt"
        f.write_text("x")
        with self.assertRaises(NotADirectoryError):
            scan(f)

    @unittest.skipIf(os.name == "nt", "symlinks need privileges on Windows")
    def test_symlinks_are_not_followed(self):
        proj = self.project()
        (proj / "link").symlink_to(proj / "backend", target_is_directory=True)
        root = scan(proj)
        link = next(c for c in root.children if c.name == "link")
        self.assertTrue(link.is_symlink)
        self.assertEqual(link.children, [])


class CollectTests(TempDirTest):
    def reasons(self, **kw):
        root = scan(self.project())
        _, skipped = collect_files(root, ContentOptions(**kw))
        return {s.node.rel: s.reason for s in skipped}

    def test_default_skips(self):
        reasons = self.reasons()
        self.assertEqual(reasons[".env"], walk.SECRET)
        self.assertEqual(reasons["pnpm-lock.yaml"], walk.LOCKFILE)
        self.assertEqual(reasons["logo.png"], walk.BINARY)
        self.assertEqual(reasons["empty.txt"], walk.EMPTY)
        self.assertNotIn(".env.example", reasons)

    def test_secrets_never_collected_by_default(self):
        files, _ = collect_files(scan(self.project()), ContentOptions())
        self.assertNotIn(".env", [f.rel for f in files])

    def test_include_secrets_opt_in(self):
        files, _ = collect_files(scan(self.project()), ContentOptions(include_secrets=True))
        self.assertIn(".env", [f.rel for f in files])

    def test_include_lockfiles_opt_in(self):
        files, _ = collect_files(scan(self.project()), ContentOptions(include_lockfiles=True))
        self.assertIn("pnpm-lock.yaml", [f.rel for f in files])

    def test_include_binary_opt_in(self):
        files, _ = collect_files(scan(self.project()), ContentOptions(include_binary=True))
        self.assertIn("logo.png", [f.rel for f in files])

    def test_max_size(self):
        proj = self.project({"big.txt": "x" * 5000, "small.txt": "x"})
        files, skipped = collect_files(scan(proj), ContentOptions(max_size=1000))
        self.assertEqual([f.rel for f in files], ["small.txt"])
        self.assertEqual(skipped[0].reason, walk.TOO_LARGE)

    def test_include_patterns_restrict_files(self):
        files, skipped = collect_files(scan(self.project()), ContentOptions(include=["*.ts"]))
        self.assertEqual(sorted(f.rel for f in files),
                         ["backend/src/app.ts", "backend/src/index.ts", "shared/src/index.ts"])
        self.assertTrue(any(s.reason == walk.NOT_INCLUDED for s in skipped))

    def test_include_cannot_override_secrets(self):
        files, _ = collect_files(scan(self.project()), ContentOptions(include=[".env"]))
        self.assertEqual(files, [])


if __name__ == "__main__":
    unittest.main()
