"""Unit tests for utilkit pure logic. Run: python -m pytest tests/ (or unittest)."""
import contextlib
import io
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "source"))

from utilkit import collate, fileops, sessions, ui, walk  # noqa: E402


class TestWalk(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "node_modules"))
        os.makedirs(os.path.join(self.root, "src"))
        open(os.path.join(self.root, "src", "a.py"), "w").close()
        open(os.path.join(self.root, "image.png"), "w").close()
        open(os.path.join(self.root, "node_modules", "junk.js"), "w").close()

    def test_ignores_directory(self):
        path = os.path.join(self.root, "node_modules", "junk.js")
        self.assertTrue(walk.should_ignore(path, self.root))

    def test_ignores_extension(self):
        self.assertTrue(walk.should_ignore(os.path.join(self.root, "image.png"), self.root))

    def test_keeps_source(self):
        self.assertFalse(walk.should_ignore(os.path.join(self.root, "src", "a.py"), self.root))

    def test_only_filter(self):
        py = os.path.join(self.root, "src", "a.py")
        self.assertFalse(walk.should_ignore(py, self.root, only_exts={"py"}))
        self.assertTrue(walk.should_ignore(py, self.root, only_exts={"js"}))

    def test_iter_text_files_excludes_ignored(self):
        found = {rel for rel, _ in walk.iter_text_files(self.root)}
        self.assertIn("src/a.py", found)
        self.assertNotIn("image.png", found)
        self.assertFalse(any("node_modules" in f for f in found))


class TestExtensionParsing(unittest.TestCase):
    def test_bracket_list(self):
        self.assertEqual(collate.parse_extension_list("[py,js,css]"), {"py", "js", "css"})

    def test_single(self):
        self.assertEqual(collate.parse_extension_list(".py"), {"py"})

    def test_empty(self):
        self.assertEqual(collate.parse_extension_list(None), set())


class TestFileOps(unittest.TestCase):
    def test_parse_all_kinds(self):
        text = (
            '<file path="a.py">\n<![CDATA[\nx = 1\n]]>\n</file>\n'
            '<delete path="b.txt" />\n'
            '<rename from="c" to="d" />'
        )
        ops, warnings = fileops.parse(text)
        kinds = sorted(o["type"] for o in ops)
        self.assertEqual(kinds, ["create", "delete", "rename"])

    def test_safe_path_rejects_traversal(self):
        self.assertFalse(fileops.is_safe("../escape.py"))
        self.assertFalse(fileops.is_safe("/etc/passwd"))
        self.assertTrue(fileops.is_safe("src/app.py"))

    def test_apply_creates_file(self):
        root = tempfile.mkdtemp()
        ops = [{"type": "create", "path": "sub/x.txt", "content": "hi"}]
        counts = fileops.apply(ops, root)
        self.assertEqual(counts["created"], 1)
        with open(os.path.join(root, "sub", "x.txt")) as f:
            self.assertEqual(f.read(), "hi")


class TestSessions(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["UTILKIT_CONFIG_DIR"] = self.dir

    def tearDown(self):
        os.environ.pop("UTILKIT_CONFIG_DIR", None)

    def test_record_and_list(self):
        sessions.record("host1", "user1", 22)
        sessions.record("host2", "user2", 2222, label="staging")
        ordered = sessions.most_recent_first()
        self.assertEqual(len(ordered), 2)
        self.assertEqual(ordered[0]["host"], "host2")

    def test_record_dedupes(self):
        sessions.record("h", "u", 22)
        sessions.record("h", "u", 22)
        self.assertEqual(len(sessions.load()), 1)

    def test_remove(self):
        sessions.record("h1", "u", 22)
        sessions.record("h2", "u", 22)
        removed = sessions.remove(1)
        self.assertIsNotNone(removed)
        self.assertEqual(len(sessions.load()), 1)


class TestUI(unittest.TestCase):
    def test_truncate_no_reset_when_plain(self):
        self.assertEqual(ui.truncate("abcdefghij", 5), "abcd…")
        self.assertNotIn("\x1b", ui.truncate("abcdefghij", 5))

    def test_truncate_closes_color(self):
        out = ui.truncate("\x1b[31mabcdefghij\x1b[0m", 5)
        self.assertTrue(out.endswith("\x1b[0m"))

    def test_truncate_keeps_short_text(self):
        self.assertEqual(ui.truncate("abc", 10), "abc")

    def test_card_lines_are_aligned(self):
        os.environ["COLUMNS"] = "100"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ui.card("title here", [
                ("PID", "1234"),
                ("Location", "C:/a/very/long/path/to/some/executable/program.exe"),
                (None, None),
                ("Memory", "20 MB"),
            ])
        widths = {ui.visible_len(line) for line in buf.getvalue().splitlines()}
        self.assertEqual(len(widths), 1, f"card lines misaligned: {widths}")


class TestExtractTraversal(unittest.TestCase):
    def test_zip_members_detected(self):
        # The extract tool's _check_members must flag traversal entries.
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "source"))
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "extract_tool",
            os.path.join(os.path.dirname(__file__), "..", "source", "extract.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        tmp = tempfile.mkdtemp()
        archive = os.path.join(tmp, "evil.zip")
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("../escape.txt", "x")
        dest = os.path.join(tmp, "evil")
        with self.assertRaises(mod.ExtractError):
            mod._prevalidate(archive, dest)


if __name__ == "__main__":
    unittest.main()
