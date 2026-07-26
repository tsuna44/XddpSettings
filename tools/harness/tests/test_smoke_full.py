#!/usr/bin/env python3
"""test_smoke_full.py — smoke_full の純ロジック unittest（LLM 非起動・トークン0）。

構造性質抽出・予算積算・上限判定・ゴールデン照合・--phase 解決・config ロードを検証する。
実 LLM 起動経路（_invoke_phase）はモックせず対象外（3.5 step 0 スパイクで別途確認）。
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import smoke_full as sf  # noqa: E402


class TestBudgetTracker(unittest.TestCase):
    def test_accumulates_cost_and_tokens(self):
        b = sf.BudgetTracker(budget_usd=1.0)
        b.add_response({"usage": {"input_tokens": 100, "output_tokens": 50},
                        "total_cost_usd": 0.2, "_phase": "02"})
        b.add_response({"usage": {"input_tokens": 10, "output_tokens": 5},
                        "total_cost_usd": 0.1, "_phase": "03"})
        snap = b.snapshot()
        self.assertAlmostEqual(snap["total_cost_usd"], 0.3)
        self.assertEqual(snap["input_tokens"], 110)
        self.assertEqual(snap["output_tokens"], 55)
        self.assertEqual(snap["phases_run"], 2)

    def test_raises_when_over_budget(self):
        b = sf.BudgetTracker(budget_usd=0.25)
        b.add_response({"usage": {}, "total_cost_usd": 0.2, "_phase": "02"})
        with self.assertRaises(sf.BudgetExceeded):
            b.add_response({"usage": {}, "total_cost_usd": 0.1, "_phase": "03"})

    def test_can_start_respects_remaining_budget(self):
        b = sf.BudgetTracker(budget_usd=1.0)
        b.add_response({"usage": {}, "total_cost_usd": 0.8, "_phase": "02"})
        self.assertTrue(b.can_start(0.1))
        self.assertFalse(b.can_start(0.5))  # 残0.2 < 0.5

    def test_can_start_respects_max_phases(self):
        b = sf.BudgetTracker(budget_usd=100.0, max_phases=1)
        self.assertTrue(b.can_start(0.1))
        b.add_response({"usage": {}, "total_cost_usd": 0.1, "_phase": "02"})
        self.assertFalse(b.can_start(0.1))  # 工程数上限に到達


class TestStructuralProperties(unittest.TestCase):
    def _write(self, text):
        d = Path(tempfile.mkdtemp())
        f = d / "artifact.md"
        f.write_text(text, encoding="utf-8")
        return f

    def test_extracts_headings_ids_frontmatter(self):
        f = self._write(
            "---\nversion: 1\nsource: x\n---\n"
            "# Title\n## 4. トレーサビリティ\n"
            "SP-001 と UR-003 を含む。\n"
            "| a | b |\n| - | - |\n")
        p = sf.extract_structural_properties(f)
        self.assertIn("4. トレーサビリティ", p["headings"])
        self.assertIn("SP-001", p["ids"])
        self.assertIn("UR-003", p["ids"])
        self.assertIn("version", p["frontmatter_keys"])
        self.assertIn("source", p["frontmatter_keys"])
        self.assertEqual(p["unreplaced_tokens"], [])

    def test_detects_unreplaced_tokens(self):
        f = self._write("# T\n未置換 {CR_PATH} と {SP_ID} が残る\n")
        p = sf.extract_structural_properties(f)
        self.assertEqual(p["unreplaced_tokens"], ["{CR_PATH}", "{SP_ID}"])


class TestCompareToGolden(unittest.TestCase):
    def test_pass_when_matches(self):
        actual = {"headings": ["A", "B"], "ids": ["SP-001"],
                  "unreplaced_tokens": [], "frontmatter_keys": ["version"]}
        golden = {"required_headings": ["A"], "ids": ["SP-001"],
                  "frontmatter_keys": ["version"]}
        self.assertEqual(sf.compare_to_golden(actual, golden), [])

    def test_flags_missing_heading(self):
        actual = {"headings": ["A"], "unreplaced_tokens": []}
        golden = {"required_headings": ["A", "B"]}
        vs = sf.compare_to_golden(actual, golden)
        self.assertTrue(any("必須見出し" in v for v in vs))

    def test_flags_unreplaced_tokens(self):
        actual = {"headings": [], "unreplaced_tokens": ["{CR}"]}
        vs = sf.compare_to_golden(actual, {})
        self.assertTrue(any("未置換トークン" in v for v in vs))

    def test_flags_missing_ids(self):
        actual = {"headings": [], "ids": [], "unreplaced_tokens": []}
        golden = {"ids": ["SP-001"]}
        vs = sf.compare_to_golden(actual, golden)
        self.assertTrue(any("期待 ID" in v for v in vs))


class TestPhaseResolution(unittest.TestCase):
    def test_single_phase(self):
        self.assertEqual(sf.resolve_phase("02", multi=False), "phase02-single")

    def test_multi_phase(self):
        self.assertEqual(sf.resolve_phase("04", multi=True), "phase04-multi")

    def test_close_label(self):
        self.assertEqual(sf.resolve_phase("close", multi=False), "phaseClose-single")

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            sf.resolve_phase("01", multi=False)  # init は --all 専用

    def test_multi_on_non_cross_phase_raises(self):
        with self.assertRaises(ValueError):
            sf.resolve_phase("02", multi=True)


class TestConfigLoader(unittest.TestCase):
    def test_reads_budget(self):
        d = Path(tempfile.mkdtemp())
        cfg_path = d / "smoke_config.md"
        cfg_path.write_text(
            "- `SMOKE_TOKEN_BUDGET`: 3.5\n- `SMOKE_MAX_PHASES`: 12\n",
            encoding="utf-8")
        cfg = sf.load_smoke_config(cfg_path)
        self.assertEqual(cfg["SMOKE_TOKEN_BUDGET"], 3.5)
        self.assertEqual(cfg["SMOKE_MAX_PHASES"], 12)

    def test_missing_file_returns_defaults(self):
        cfg = sf.load_smoke_config(Path("/nonexistent/smoke_config.md"))
        self.assertNotIn("SMOKE_TOKEN_BUDGET", cfg)


class TestResolveAuthEnv(unittest.TestCase):
    def setUp(self):
        self._orig_oauth = os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
        self._orig_key = os.environ.pop("ANTHROPIC_API_KEY", None)

    def tearDown(self):
        if self._orig_oauth is not None:
            os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = self._orig_oauth
        else:
            os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
        if self._orig_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = self._orig_key
        else:
            os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_both_unset_returns_none(self):
        self.assertIsNone(sf._resolve_auth_env())

    def test_oauth_token_only(self):
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = "tok"
        self.assertEqual(sf._resolve_auth_env(), {"CLAUDE_CODE_OAUTH_TOKEN": "tok"})

    def test_api_key_only(self):
        os.environ["ANTHROPIC_API_KEY"] = "key"
        self.assertEqual(sf._resolve_auth_env(), {"ANTHROPIC_API_KEY": "key"})

    def test_both_set_prefers_oauth_token(self):
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = "tok"
        os.environ["ANTHROPIC_API_KEY"] = "key"
        self.assertEqual(sf._resolve_auth_env(), {"CLAUDE_CODE_OAUTH_TOKEN": "tok"})


if __name__ == "__main__":
    unittest.main()
