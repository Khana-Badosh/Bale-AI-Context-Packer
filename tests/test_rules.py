import unittest

from bale import rules

from helpers import TempDirTest


class SecretTests(unittest.TestCase):
    def test_env_files_are_secret(self):
        for name in (".env", ".env.local", ".env.production", ".ENV"):
            self.assertTrue(rules.is_secret(name), name)

    def test_env_templates_are_not_secret(self):
        for name in (".env.example", ".env.sample", ".env.template"):
            self.assertFalse(rules.is_secret(name), name)

    def test_keys_and_credentials_are_secret(self):
        for name in ("server.pem", "id_rsa", "id_ed25519", "cert.p12", ".npmrc", "credentials.json"):
            self.assertTrue(rules.is_secret(name), name)

    def test_ordinary_files_are_not_secret(self):
        for name in ("app.ts", "environment.ts", "README.md", "env.py", "keys.ts"):
            self.assertFalse(rules.is_secret(name), name)


class DefaultIgnoreTests(unittest.TestCase):
    def test_default_dirs(self):
        for name in ("node_modules", "__pycache__", ".venv", "dist", "target", "foo.egg-info"):
            self.assertTrue(rules.is_default_ignored(name, True), name)
        self.assertFalse(rules.is_default_ignored("src", True))

    def test_junk_files_only_apply_to_files(self):
        self.assertTrue(rules.is_default_ignored(".DS_Store", False))
        self.assertFalse(rules.is_default_ignored("dist", False))

    def test_lockfiles(self):
        self.assertTrue(rules.is_lockfile("pnpm-lock.yaml"))
        self.assertFalse(rules.is_lockfile("package.json"))


class BinaryTests(TempDirTest):
    def test_extension_and_sniffing(self):
        png = self.tmp / "a.png"
        png.write_bytes(b"not really a png")
        sniffed = self.tmp / "blob.dat"
        sniffed.write_bytes(b"abc\x00def")
        text = self.tmp / "notes.dat"
        text.write_text("plain text")
        self.assertTrue(rules.is_binary(png))
        self.assertTrue(rules.is_binary(sniffed))
        self.assertFalse(rules.is_binary(text))


if __name__ == "__main__":
    unittest.main()
