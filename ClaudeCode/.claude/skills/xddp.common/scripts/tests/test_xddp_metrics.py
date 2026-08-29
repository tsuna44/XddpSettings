import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import xddp_metrics as mod  # noqa: E402


class MetricsTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cr_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, argv):
        parser = mod.build_parser()
        args = parser.parse_args(argv)
        args.func(args)

    def _read_metrics(self):
        path = self.cr_path / "metrics.jsonl"
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def test_phase_start_writes_marker(self):
        self._run(["phase-start", "--cr-path", str(self.cr_path), "--step", "2"])
        marker = self.cr_path / ".phase-metrics-2.json"
        self.assertTrue(marker.exists())
        data = json.loads(marker.read_text(encoding="utf-8"))
        self.assertEqual(data["step"], "2")
        self.assertIn("started_at", data)

    def test_phase_complete_computes_duration_and_removes_marker(self):
        self._run(["phase-start", "--cr-path", str(self.cr_path), "--step", "2"])
        marker = self.cr_path / ".phase-metrics-2.json"
        self.assertTrue(marker.exists())
        self._run(["record", "--cr-path", str(self.cr_path), "--step", "2", "--event", "phase_complete"])
        self.assertFalse(marker.exists())
        entries = self._read_metrics()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["event"], "phase_complete")
        self.assertIn("duration_ms", entries[0])
        self.assertGreaterEqual(entries[0]["duration_ms"], 0)

    def test_phase_complete_without_marker_omits_duration(self):
        self._run(["record", "--cr-path", str(self.cr_path), "--step", "7", "--event", "phase_complete"])
        entries = self._read_metrics()
        self.assertEqual(len(entries), 1)
        self.assertNotIn("duration_ms", entries[0])

    def test_phase_complete_with_corrupt_marker_omits_duration(self):
        marker = self.cr_path / ".phase-metrics-2.json"
        marker.write_text("not valid json", encoding="utf-8")
        self._run(["record", "--cr-path", str(self.cr_path), "--step", "2", "--event", "phase_complete"])
        entries = self._read_metrics()
        self.assertEqual(len(entries), 1)
        self.assertNotIn("duration_ms", entries[0])

    def test_phase_complete_with_missing_started_at_omits_duration(self):
        marker = self.cr_path / ".phase-metrics-2.json"
        marker.write_text(json.dumps({"step": "2"}), encoding="utf-8")
        self._run(["record", "--cr-path", str(self.cr_path), "--step", "2", "--event", "phase_complete"])
        entries = self._read_metrics()
        self.assertEqual(len(entries), 1)
        self.assertNotIn("duration_ms", entries[0])

    def test_review_loop_records_numeric_rounds(self):
        self._run([
            "record", "--cr-path", str(self.cr_path), "--step", "5", "--event", "review_loop",
            "--document-type", "DSN", "--review-rounds", "2", "--review-max-rounds", "3",
            "--review-outcome", "converged",
        ])
        entries = self._read_metrics()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["review_rounds"], 2)
        self.assertEqual(entries[0]["review_max_rounds"], 3)
        self.assertIsInstance(entries[0]["review_rounds"], int)
        self.assertIsInstance(entries[0]["review_max_rounds"], int)
        self.assertEqual(entries[0]["review_outcome"], "converged")

    def test_target_included_only_when_specified(self):
        self._run([
            "record", "--cr-path", str(self.cr_path), "--step", "5", "--event", "review_loop",
            "--review-rounds", "1", "--review-max-rounds", "1", "--review-outcome", "converged",
            "--target", "repo-a",
        ])
        self._run([
            "record", "--cr-path", str(self.cr_path), "--step", "5", "--event", "review_loop",
            "--review-rounds", "1", "--review-max-rounds", "1", "--review-outcome", "converged",
        ])
        entries = self._read_metrics()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["target"], "repo-a")
        self.assertNotIn("target", entries[1])

    def test_append_only_preserves_existing_lines(self):
        self._run(["record", "--cr-path", str(self.cr_path), "--step", "2", "--event", "phase_complete"])
        self._run(["record", "--cr-path", str(self.cr_path), "--step", "3", "--event", "phase_complete"])
        entries = self._read_metrics()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["step"], "2")
        self.assertEqual(entries[1]["step"], "3")


if __name__ == "__main__":
    unittest.main()
