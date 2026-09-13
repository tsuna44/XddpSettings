import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "xddp_verify_tools.py"


def _run(args: list) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
    )


class VerifyToolsTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmpdir.name) / "repo"
        self.repo.mkdir()
        self.output = Path(self.tmpdir.name) / "OUTPUT.md"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_all_configured_pass(self):
        result = _run([
            "run",
            "--repo-path", str(self.repo),
            "--output", str(self.output),
            "--lint", "exit 0",
            "--build", "exit 0",
            "--typecheck", "exit 0",
            "--timeout-sec", "10",
        ])
        self.assertEqual(result.returncode, 0)
        report = self.output.read_text(encoding="utf-8")
        self.assertEqual(report.count("✅ PASS"), 3)
        self.assertNotIn("❌ FAIL", report)

    def test_single_failure(self):
        result = _run([
            "run",
            "--repo-path", str(self.repo),
            "--output", str(self.output),
            "--lint", "exit 1",
            "--timeout-sec", "10",
        ])
        self.assertEqual(result.returncode, 1)
        report = self.output.read_text(encoding="utf-8")
        self.assertIn("❌ FAIL", report)
        self.assertEqual(report.count("➖ 未設定"), 2)

    def test_mixed_pass_fail(self):
        result = _run([
            "run",
            "--repo-path", str(self.repo),
            "--output", str(self.output),
            "--lint", "exit 0",
            "--build", "exit 1",
            "--timeout-sec", "10",
        ])
        self.assertEqual(result.returncode, 1)
        report = self.output.read_text(encoding="utf-8")
        self.assertIn("✅ PASS", report)
        self.assertIn("❌ FAIL", report)

    def test_timeout(self):
        result = _run([
            "run",
            "--repo-path", str(self.repo),
            "--output", str(self.output),
            "--build", "sleep 5",
            "--timeout-sec", "1",
        ])
        self.assertEqual(result.returncode, 1)
        report = self.output.read_text(encoding="utf-8")
        self.assertIn("⏱️ タイムアウト", report)

    def test_none_configured(self):
        result = _run([
            "run",
            "--repo-path", str(self.repo),
            "--output", str(self.output),
            "--timeout-sec", "10",
        ])
        self.assertEqual(result.returncode, 0)
        report = self.output.read_text(encoding="utf-8")
        self.assertEqual(report.count("➖ 未設定"), 3)

    def test_output_truncation(self):
        # 10行出力するコマンドを --max-output-lines 3 で切り詰める
        cmd = "for i in 1 2 3 4 5 6 7 8 9 10; do echo line$i; done"
        result = _run([
            "run",
            "--repo-path", str(self.repo),
            "--output", str(self.output),
            "--lint", cmd,
            "--timeout-sec", "10",
            "--max-output-lines", "3",
        ])
        self.assertEqual(result.returncode, 0)
        report = self.output.read_text(encoding="utf-8")
        self.assertIn("末尾 3 行のみ表示", report)
        self.assertIn("line8", report)
        self.assertIn("line9", report)
        self.assertIn("line10", report)
        self.assertNotIn("line7", report)

    def test_usage_error_no_output_file(self):
        # --repo-path を欠落させる（--output も他の必須引数として同種のケース）
        result = _run([
            "run",
            "--output", str(self.output),
            "--timeout-sec", "10",
        ])
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.output.exists())

    def test_internal_error_exit_code_2(self):
        missing_repo = Path(self.tmpdir.name) / "does-not-exist"
        result = _run([
            "run",
            "--repo-path", str(missing_repo),
            "--output", str(self.output),
            "--lint", "exit 0",
            "--timeout-sec", "10",
        ])
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
