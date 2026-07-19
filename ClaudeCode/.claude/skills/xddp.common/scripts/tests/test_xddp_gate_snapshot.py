import io
import json
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import xddp_gate_snapshot as mod  # noqa: E402


class GateSnapshotTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name) / "CR-2026-999"
        self.root.mkdir()
        (self.root / "a.md").write_text("hello", encoding="utf-8")
        sub = self.root / "03_change-requirements"
        sub.mkdir()
        (sub / "CRS-CR-2026-999.md").write_text("crs content", encoding="utf-8")
        self.snap_path = self.root / ".gate-snapshot.json"

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, argv):
        parser = mod.build_parser()
        args = parser.parse_args(argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def test_snapshot_excludes_itself(self):
        result = self._run(["snapshot", "--root", str(self.root), "--out", str(self.snap_path)])
        self.assertTrue(result["ok"])
        self.assertEqual(result["file_count"], 2)
        data = json.loads(self.snap_path.read_text(encoding="utf-8"))
        self.assertNotIn(".gate-snapshot.json", data["files"])

    def test_diff_unchanged_is_false(self):
        self._run(["snapshot", "--root", str(self.root), "--out", str(self.snap_path)])
        result = self._run(["diff", "--snapshot", str(self.snap_path)])
        self.assertFalse(result["changed"])
        self.assertEqual(result["changed_files"], [])

    def test_diff_detects_content_change(self):
        self._run(["snapshot", "--root", str(self.root), "--out", str(self.snap_path)])
        time.sleep(0.01)
        (self.root / "a.md").write_text("hello world", encoding="utf-8")
        result = self._run(["diff", "--snapshot", str(self.snap_path)])
        self.assertTrue(result["changed"])
        self.assertIn("a.md", result["changed_files"])

    def test_diff_ignores_touch_without_content_change(self):
        self._run(["snapshot", "--root", str(self.root), "--out", str(self.snap_path)])
        time.sleep(0.01)
        (self.root / "a.md").touch()
        result = self._run(["diff", "--snapshot", str(self.snap_path)])
        self.assertFalse(result["changed"])

    def test_diff_detects_new_file(self):
        self._run(["snapshot", "--root", str(self.root), "--out", str(self.snap_path)])
        (self.root / "new.md").write_text("new", encoding="utf-8")
        result = self._run(["diff", "--snapshot", str(self.snap_path)])
        self.assertTrue(result["changed"])
        self.assertIn("new.md", result["changed_files"])

    def test_diff_detects_deleted_file(self):
        self._run(["snapshot", "--root", str(self.root), "--out", str(self.snap_path)])
        (self.root / "a.md").unlink()
        result = self._run(["diff", "--snapshot", str(self.snap_path)])
        self.assertTrue(result["changed"])
        self.assertIn("a.md", result["changed_files"])

    def test_missing_snapshot_errors(self):
        parser = mod.build_parser()
        args = parser.parse_args(["diff", "--snapshot", str(self.root / "nope.json")])
        with self.assertRaises(SystemExit):
            args.func(args)


if __name__ == "__main__":
    unittest.main()
