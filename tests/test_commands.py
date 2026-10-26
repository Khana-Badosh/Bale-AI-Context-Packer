import os
import unittest
from unittest import mock

from bale.bundle import build_bundle
from bale.flatten import MARKER, plan_names
from bale.tree import render_tree
from bale.util import estimate_tokens, fence_for, read_text
from bale.walk import ContentOptions, collect_files, scan

from helpers import TempDirTest, make_tree, run_cli


class TreeTests(TempDirTest):
    SMALL = {"b.txt": "b", "a/x.ts": "x", "a/y.ts": "y", "c/d/z.ts": "z"}

    def test_exact_output(self):
        root = scan(self.project(self.SMALL))
        expected = "\n".join([
            "📁 Project Structure: proj",
            "├── a",
            "│   ├── x.ts",
            "│   └── y.ts",
            "├── c",
            "│   └── d",
            "│       └── z.ts",
            "└── b.txt",
        ])
        self.assertEqual(render_tree(root), expected)

    def test_ascii_and_no_header(self):
        root = scan(self.project(self.SMALL))
        text = render_tree(root, ascii_only=True, header=False)
        self.assertTrue(text.startswith("+-- a"))
        self.assertNotIn("├", text)
        self.assertNotIn("Project Structure", text)

    def test_dirs_only(self):
        root = scan(self.project(self.SMALL))
        text = render_tree(root, dirs_only=True)
        self.assertNotIn(".ts", text)
        self.assertIn("d", text)

    def test_tree_still_lists_secret_and_lock_names(self):
        text = render_tree(scan(self.project()))
        self.assertIn(".env", text)
        self.assertIn("pnpm-lock.yaml", text)
        self.assertNotIn("node_modules", text)


class BundleTests(TempDirTest):
    def bundle(self, files=None, **kw):
        root = scan(self.project(files))
        keep, _ = collect_files(root, ContentOptions())
        return build_bundle(root, keep, **kw)

    def test_contains_tree_and_files_but_no_secrets(self):
        result = self.bundle()
        self.assertIn("## Directory structure", result.text)
        self.assertIn("### backend/src/app.ts", result.text)
        self.assertIn("```ts\nexport const app = 1\n```", result.text)
        self.assertNotIn("super-secret", result.text)
        self.assertNotIn("PNG", result.text)

    def test_no_tree_option(self):
        self.assertNotIn("## Directory structure", self.bundle(include_tree=False).text)

    def test_fence_grows_around_backticks(self):
        content = "Example:\n```js\nx()\n```\n"
        result = self.bundle({"doc.md": content})
        self.assertIn("````markdown", result.text)
        self.assertEqual(fence_for("```"), "````")
        self.assertEqual(fence_for("none"), "```")

    def test_crlf_and_bom_normalised(self):
        proj = self.project({"w.txt": b"\xef\xbb\xbfline1\r\nline2"})
        self.assertEqual(read_text(proj / "w.txt"), "line1\nline2")

    def test_counts_and_token_estimate(self):
        result = self.bundle({"a.ts": "1", "b.ts": "2"})
        self.assertEqual(result.file_count, 2)
        self.assertEqual(result.token_estimate, estimate_tokens(result.text))
        self.assertGreater(result.token_estimate, 0)


class FlattenPlanTests(TempDirTest):
    def nodes(self, files):
        root = scan(self.project(files))
        return collect_files(root, ContentOptions())[0]

    def test_path_names(self):
        plan = plan_names(self.nodes({"a/index.ts": "1", "b/index.ts": "2"}), "path")
        self.assertEqual([p[1] for p in plan], ["a__index.ts", "b__index.ts"])
        self.assertFalse(any(p[2] for p in plan))

    def test_name_mode_resolves_collisions(self):
        plan = plan_names(self.nodes({"a/index.ts": "1", "b/index.ts": "2", "c/index.ts": "3"}), "name")
        self.assertEqual([p[1] for p in plan], ["index.ts", "index_1.ts", "index_2.ts"])
        self.assertEqual([p[2] for p in plan], [False, True, True])

    def test_case_insensitive_collisions(self):
        plan = plan_names(self.nodes({"a/Readme.md": "1", "b/README.md": "2"}), "name")
        self.assertEqual(len({p[1].lower() for p in plan}), 2)


class CliTests(TempDirTest):
    def test_tree_to_stdout(self):
        code, out, _ = run_cli("tree", str(self.project()))
        self.assertEqual(code, 0)
        self.assertIn("Project Structure: proj", out)
        self.assertIn("app.ts", out)

    def test_tree_output_file_not_listed(self):
        proj = self.project()
        target = proj / "TREE.txt"
        code, _, _ = run_cli("tree", str(proj), "-o", str(target), "-q")
        self.assertEqual(code, 0)
        self.assertNotIn("TREE.txt", target.read_text(encoding="utf-8"))

    def test_bundle_reports_skipped_secret(self):
        code, out, err = run_cli("bundle", str(self.project()), "--stdout")
        self.assertEqual(code, 0)
        self.assertNotIn("super-secret", out)
        self.assertIn("1 secret (.env)", err)
        self.assertIn("--include-secrets", err)
        self.assertIn("tokens", err)

    def test_bundle_include_secrets_flag(self):
        _, out, _ = run_cli("bundle", str(self.project()), "--include-secrets", "--stdout")
        self.assertIn("super-secret", out)

    def test_bundle_output_file_excluded_from_itself(self):
        proj = self.project()
        target = proj / "context.md"
        run_cli("bundle", str(proj), "-o", str(target), "-q")
        run_cli("bundle", str(proj), "-o", str(target), "-q")  # second run must not ingest the first
        self.assertEqual(target.read_text(encoding="utf-8").count("### context.md"), 0)

    def test_missing_folder_is_a_clean_error(self):
        code, _, err = run_cli("tree", str(self.tmp / "nope"))
        self.assertEqual(code, 1)
        self.assertIn("no such folder", err)

    def test_flatten_end_to_end(self):
        proj, dest = self.project(), self.tmp / "out"
        code, _, err = run_cli("flatten", str(proj), "-o", str(dest))
        self.assertEqual(code, 0, err)
        names = sorted(p.name for p in dest.iterdir())
        self.assertIn("backend__src__app.ts", names)
        self.assertIn("backend__src__index.ts", names)
        self.assertIn("shared__src__index.ts", names)
        self.assertIn(MARKER, names)
        self.assertNotIn(".env", names)
        self.assertNotIn("pnpm-lock.yaml", names)
        self.assertNotIn("logo.png", names)
        self.assertEqual((dest / "backend__src__app.ts").read_text(), "export const app = 1\n")

    def test_flatten_dry_run_writes_nothing(self):
        proj, dest = self.project(), self.tmp / "out"
        code, out, _ = run_cli("flatten", str(proj), "-o", str(dest), "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("backend/src/app.ts  ->  backend__src__app.ts", out)
        self.assertFalse(dest.exists())

    def test_flatten_refuses_non_empty_destination(self):
        proj, dest = self.project(), self.tmp / "out"
        make_tree(dest, {"precious.txt": "do not delete"})
        code, _, err = run_cli("flatten", str(proj), "-o", str(dest))
        self.assertEqual(code, 1)
        self.assertIn("not empty", err)
        code, _, err = run_cli("flatten", str(proj), "-o", str(dest), "--clean")
        self.assertEqual(code, 1)
        self.assertIn("refusing to replace", err)
        self.assertTrue((dest / "precious.txt").exists())

    def test_flatten_clean_replaces_previous_run(self):
        proj, dest = self.project(), self.tmp / "out"
        run_cli("flatten", str(proj), "-o", str(dest), "-q")
        (dest / "stale.txt").write_text("old")
        code, _, err = run_cli("flatten", str(proj), "-o", str(dest), "--clean", "-q")
        self.assertEqual(code, 0, err)
        self.assertFalse((dest / "stale.txt").exists())
        self.assertTrue((dest / "backend__src__app.ts").exists())

    def test_flatten_destination_inside_source_is_not_rescanned(self):
        proj = self.project()
        dest = proj / "flat"
        run_cli("flatten", str(proj), "-o", str(dest), "-q")
        code, _, err = run_cli("flatten", str(proj), "-o", str(dest), "--clean", "-q")
        self.assertEqual(code, 0, err)
        self.assertFalse(any("flat__" in p.name for p in dest.iterdir()))

    def test_flatten_destination_cannot_contain_source(self):
        proj = self.project()
        code, _, err = run_cli("flatten", str(proj), "-o", str(self.tmp))
        self.assertEqual(code, 1)
        self.assertIn("contains the source folder", err)

    def test_flatten_name_mode(self):
        proj, dest = self.project(), self.tmp / "out"
        run_cli("flatten", str(proj), "-o", str(dest), "--names", "name", "-q")
        names = {p.name for p in dest.iterdir()}
        self.assertIn("app.ts", names)
        self.assertIn("index.ts", names)
        self.assertIn("index_1.ts", names)

    # ---- output stays inside the project ------------------------------------

    def test_bundle_defaults_to_file_inside_project(self):
        proj = self.project()
        code, out, err = run_cli("bundle", str(proj))
        self.assertEqual(code, 0)
        self.assertEqual(out, "")  # nothing printed to stdout
        saved = proj / ".bale" / "bundle.md"
        self.assertTrue(saved.is_file())
        self.assertIn("### backend/src/app.ts", saved.read_text(encoding="utf-8"))
        self.assertIn("Saved bundle to", err)

    def test_bale_folder_ignores_itself_and_is_never_rescanned(self):
        proj = self.project()
        run_cli("bundle", str(proj), "-q")
        run_cli("bundle", str(proj), "-q")  # second run must not ingest the first
        text = (proj / ".bale" / "bundle.md").read_text(encoding="utf-8")
        self.assertNotIn(".bale", text)
        self.assertNotIn("bundle.md", text)
        self.assertEqual((proj / ".bale" / ".gitignore").read_text(encoding="utf-8").strip().splitlines()[-1], "*")
        _, tree_out, _ = run_cli("tree", str(proj))
        self.assertNotIn(".bale", tree_out)

    def test_bundle_stdout_writes_no_file(self):
        proj = self.project()
        code, out, _ = run_cli("bundle", str(proj), "--stdout", "-q")
        self.assertEqual(code, 0)
        self.assertIn("## Files", out)
        self.assertFalse((proj / ".bale").exists())

    def test_bundle_custom_output_path(self):
        proj = self.project()
        target = self.tmp / "elsewhere" / "ctx.md"
        run_cli("bundle", str(proj), "-o", str(target), "-q")
        self.assertTrue(target.is_file())
        self.assertFalse((proj / ".bale").exists())

    def test_flatten_defaults_to_folder_inside_project(self):
        proj = self.project()
        code, _, err = run_cli("flatten", str(proj))
        self.assertEqual(code, 0, err)
        flat = proj / ".bale" / "flat"
        self.assertTrue((flat / "backend__src__app.ts").is_file())
        self.assertNotIn(".bale", "".join(p.name for p in flat.iterdir() if p.name != ".bale-flatten"))

    def test_flatten_default_folder_is_replaced_on_rerun(self):
        proj = self.project()
        run_cli("flatten", str(proj), "-q")
        stale = proj / ".bale" / "flat" / "stale.txt"
        stale.write_text("old")
        code, _, err = run_cli("flatten", str(proj), "-q")  # no --clean needed for the default folder
        self.assertEqual(code, 0, err)
        self.assertFalse(stale.exists())

    def test_flatten_default_folder_not_ours_is_protected(self):
        proj = self.project()
        make_tree(proj, {".bale/flat/precious.txt": "keep"})
        code, _, err = run_cli("flatten", str(proj), "-q")
        self.assertEqual(code, 1)
        self.assertIn("refusing to replace", err)
        self.assertTrue((proj / ".bale" / "flat" / "precious.txt").exists())

    def test_nothing_is_written_to_downloads_or_home(self):
        proj = self.project()
        fake_home = self.tmp / "home"
        fake_home.mkdir()
        saved = {k: os.environ.get(k) for k in ("HOME", "USERPROFILE")}
        os.environ["HOME"] = os.environ["USERPROFILE"] = str(fake_home)
        try:
            run_cli("flatten", str(proj), "-q")
            run_cli("bundle", str(proj), "-q")
            run_cli("tree", str(proj), "-q")
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertEqual(list(fake_home.iterdir()), [])

    def test_tree_copy_failure_falls_back_to_printing(self):
        with mock.patch("bale.cli.copy_to_clipboard", return_value=(False, "no clipboard")):
            code, out, err = run_cli("tree", str(self.project()), "--copy")
        self.assertEqual(code, 0)
        self.assertIn("could not copy to clipboard", err)
        self.assertIn("Project Structure", out)  # result is not lost

    def test_tree_copy_success_does_not_print(self):
        with mock.patch("bale.cli.copy_to_clipboard", return_value=(True, None)) as copy:
            code, out, _ = run_cli("tree", str(self.project()), "--copy")
        self.assertEqual((code, out), (0, ""))
        self.assertIn("Project Structure", copy.call_args[0][0])

    def test_bundle_copy_saves_file_and_copies(self):
        proj = self.project()
        with mock.patch("bale.cli.copy_to_clipboard", return_value=(True, None)) as copy:
            run_cli("bundle", str(proj), "--copy", "-q")
        self.assertTrue((proj / ".bale" / "bundle.md").is_file())
        self.assertIn("### backend/src/app.ts", copy.call_args[0][0])

    def test_no_subcommand_exits_with_usage_error(self):
        with self.assertRaises(SystemExit) as ctx:
            run_cli()
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
