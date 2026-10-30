"""Tests for the filestats CLI. Run with: python -m unittest discover -s tests"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

# Make the package importable when tests are run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from my_cli_tool.cli import human_size, main, scan_directory  # noqa: E402


def _make_file(root: Path, rel: str, size: int) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"x" * size)


class HumanSizeTests(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(human_size(0), "0 B")
        self.assertEqual(human_size(512), "512 B")

    def test_kilobytes(self):
        self.assertEqual(human_size(2048), "2.0 KB")

    def test_megabytes(self):
        self.assertEqual(human_size(5 * 1024 * 1024), "5.0 MB")

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            human_size(-1)


class ScanDirectoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_groups_by_extension_and_sums_size(self):
        _make_file(self.root, "a.py", 100)
        _make_file(self.root, "b.py", 300)
        _make_file(self.root, "c.txt", 200)
        _make_file(self.root, "README", 50)  # no extension

        result = scan_directory(self.root)

        self.assertEqual(result.total_files, 4)
        self.assertEqual(result.extensions["py"].count, 2)
        self.assertEqual(result.extensions["py"].bytes_total, 400)
        self.assertEqual(result.extensions["txt"].count, 1)
        self.assertEqual(result.extensions["[no ext]"].count, 1)
        self.assertEqual(result.total_bytes, 650)

    def test_recursive_flag(self):
        _make_file(self.root, "top.py", 10)
        _make_file(self.root, "sub/deep.py", 20)

        recursive = scan_directory(self.root, recursive=True)
        self.assertEqual(recursive.total_files, 2)

        flat = scan_directory(self.root, recursive=False)
        self.assertEqual(flat.total_files, 1)

    def test_max_depth(self):
        _make_file(self.root, "a.py", 10)
        _make_file(self.root, "sub/b.py", 20)
        _make_file(self.root, "sub/deep/c.py", 30)

        result = scan_directory(self.root, max_depth=1)
        self.assertEqual(result.total_files, 2)

    def test_skip_hidden(self):
        _make_file(self.root, "visible.py", 10)
        _make_file(self.root, ".hidden.py", 20)
        _make_file(self.root, ".cache/data.txt", 30)

        kept = scan_directory(self.root, skip_hidden=True)
        self.assertEqual(kept.total_files, 1)

        all_files = scan_directory(self.root, skip_hidden=False)
        self.assertEqual(all_files.total_files, 3)

    def test_missing_directory_returns_error_code(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main([str(self.root / "does-not-exist")])
        self.assertEqual(code, 1)


class CliJsonOutputTests(unittest.TestCase):
    def test_json_output_is_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_file(root, "x.js", 1024)
            _make_file(root, "y.js", 2048)
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main([str(root), "--json"])
            self.assertEqual(code, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["total_files"], 2)
            self.assertEqual(payload["extensions"]["js"]["bytes"], 3072)
            self.assertEqual(len(payload["largest_files"]), 2)


if __name__ == "__main__":
    unittest.main()
