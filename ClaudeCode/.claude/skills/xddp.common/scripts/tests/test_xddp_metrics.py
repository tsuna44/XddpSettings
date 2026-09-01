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

    def test_reviewer_call_event_accepted(self):
        self._run(["record", "--cr-path", str(self.cr_path), "--step", "4a", "--event", "reviewer_call"])
        entries = self._read_metrics()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["event"], "reviewer_call")

    def test_reference_file_omitted_leaves_existing_behavior_unchanged(self):
        self._run(["record", "--cr-path", str(self.cr_path), "--step", "5", "--event", "review_loop"])
        entries = self._read_metrics()
        self.assertEqual(len(entries), 1)
        self.assertNotIn("reference_bytes", entries[0])
        self.assertNotIn("reference_file_count", entries[0])
        self.assertNotIn("reference_unmeasured_count", entries[0])

    def test_reference_file_sums_multiple_plain_files(self):
        f1 = self.cr_path / "a.md"
        f1.write_text("12345", encoding="utf-8")
        f2 = self.cr_path / "b.md"
        f2.write_text("1234567890", encoding="utf-8")
        self._run([
            "record", "--cr-path", str(self.cr_path), "--step", "4a", "--event", "reviewer_call",
            "--reference-file", str(f1), "--reference-file", str(f2),
        ])
        entries = self._read_metrics()
        self.assertEqual(entries[0]["reference_bytes"], 15)
        self.assertEqual(entries[0]["reference_file_count"], 2)
        self.assertEqual(entries[0]["reference_unmeasured_count"], 0)

    def test_reference_file_trailing_description_recognized_as_directory(self):
        subdir = self.cr_path / "modules"
        subdir.mkdir()
        (subdir / "m1.md").write_text("hello", encoding="utf-8")
        (subdir / "m2.md").write_text("world!", encoding="utf-8")
        self._run([
            "record", "--cr-path", str(self.cr_path), "--step", "4a", "--event", "reviewer_call",
            "--reference-file", f"{subdir} (all .md)",
        ])
        entries = self._read_metrics()
        self.assertEqual(entries[0]["reference_file_count"], 2)
        self.assertEqual(entries[0]["reference_bytes"], 11)
        self.assertEqual(entries[0]["reference_unmeasured_count"], 0)

    def test_reference_file_leading_fullwidth_condition_recognized_as_path(self):
        f1 = self.cr_path / "SPO-001.md"
        f1.write_text("abcde", encoding="utf-8")
        self._run([
            "record", "--cr-path", str(self.cr_path), "--step", "4a", "--event", "reviewer_call",
            "--reference-file", f"（repo が \"cross\" 以外の場合のみ追加）{f1}",
        ])
        entries = self._read_metrics()
        self.assertEqual(entries[0]["reference_file_count"], 1)
        self.assertEqual(entries[0]["reference_bytes"], 5)
        self.assertEqual(entries[0]["reference_unmeasured_count"], 0)

    def test_reference_file_halfwidth_parens_also_stripped(self):
        f1 = self.cr_path / "CRS-001.md"
        f1.write_text("xyz", encoding="utf-8")
        self._run([
            "record", "--cr-path", str(self.cr_path), "--step", "4a", "--event", "reviewer_call",
            "--reference-file", f"(only if present) {f1}",
        ])
        entries = self._read_metrics()
        self.assertEqual(entries[0]["reference_file_count"], 1)
        self.assertEqual(entries[0]["reference_bytes"], 3)

    def test_reference_file_description_with_comma_not_split(self):
        subdir = self.cr_path / "modules"
        subdir.mkdir()
        (subdir / "m1.md").write_text("hi", encoding="utf-8")
        self._run([
            "record", "--cr-path", str(self.cr_path), "--step", "4a", "--event", "reviewer_call",
            "--reference-file", f"{subdir} (all .md, including subdirectories)",
        ])
        entries = self._read_metrics()
        self.assertEqual(entries[0]["reference_file_count"], 1)
        self.assertEqual(entries[0]["reference_bytes"], 2)

    def test_reference_file_directory_recursive_sum(self):
        subdir = self.cr_path / "modules"
        (subdir / "nested").mkdir(parents=True)
        (subdir / "top.md").write_text("ab", encoding="utf-8")
        (subdir / "nested" / "deep.md").write_text("cde", encoding="utf-8")
        self._run([
            "record", "--cr-path", str(self.cr_path), "--step", "4a", "--event", "reviewer_call",
            "--reference-file", str(subdir),
        ])
        entries = self._read_metrics()
        self.assertEqual(entries[0]["reference_file_count"], 2)
        self.assertEqual(entries[0]["reference_bytes"], 5)

    def test_reference_file_nonexistent_path_counts_unmeasured(self):
        self._run([
            "record", "--cr-path", str(self.cr_path), "--step", "4a", "--event", "reviewer_call",
            "--reference-file", str(self.cr_path / "does-not-exist.md"),
        ])
        entries = self._read_metrics()
        self.assertEqual(entries[0]["reference_file_count"], 0)
        self.assertEqual(entries[0]["reference_bytes"], 0)
        self.assertEqual(entries[0]["reference_unmeasured_count"], 1)


if __name__ == "__main__":
    unittest.main()
