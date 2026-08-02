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
from unittest import mock

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

    def test_excludes_review_subdir_and_brief(self):
        d = Path(tempfile.mkdtemp())
        (d / "ANA.md").write_text("# 要求分析メモ\nUR-001 を含む\n", encoding="utf-8")
        (d / "review").mkdir()
        (d / "review" / "ana-review.md").write_text(
            "# レビュー概要\nSR-999 総評\n", encoding="utf-8")
        (d / ".review-brief.md").write_text("# ブリーフ\nUR-888\n", encoding="utf-8")
        p = sf.extract_structural_properties(d)
        self.assertIn("要求分析メモ", p["headings"])
        self.assertNotIn("レビュー概要", p["headings"])   # review/ 除外
        self.assertIn("UR-001", p["ids"])
        self.assertNotIn("SR-999", p["ids"])             # review/ の ID は拾わない
        self.assertNotIn("UR-888", p["ids"])             # .review-brief.md も除外


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

    def test_reads_calibrate_budget(self):
        d = Path(tempfile.mkdtemp())
        cfg_path = d / "smoke_config.md"
        cfg_path.write_text("- `SMOKE_CALIBRATE_BUDGET`: 2.5\n", encoding="utf-8")
        cfg = sf.load_smoke_config(cfg_path)
        self.assertEqual(cfg["SMOKE_CALIBRATE_BUDGET"], 2.5)

    def test_strips_inline_comment(self):
        d = Path(tempfile.mkdtemp())
        cfg_path = d / "smoke_config.md"
        cfg_path.write_text(
            "- `SMOKE_TOKEN_BUDGET`: 0.0   # ← 校正ランで確定（USD）\n"
            "- `SMOKE_MAX_PHASES`: 13       # --all 暴走防止\n",
            encoding="utf-8")
        cfg = sf.load_smoke_config(cfg_path)
        self.assertEqual(cfg["SMOKE_TOKEN_BUDGET"], 0.0)
        self.assertEqual(cfg["SMOKE_MAX_PHASES"], 13)

    def test_calibrate_budget_defaults_absent(self):
        cfg = sf.load_smoke_config(Path("/nonexistent/smoke_config.md"))
        self.assertNotIn("SMOKE_CALIBRATE_BUDGET", cfg)

    def test_missing_file_returns_defaults(self):
        cfg = sf.load_smoke_config(Path("/nonexistent/smoke_config.md"))
        self.assertNotIn("SMOKE_TOKEN_BUDGET", cfg)


class TestEffectiveBudget(unittest.TestCase):
    def test_cli_budget_wins(self):
        cfg = {"SMOKE_TOKEN_BUDGET": 1.0, "SMOKE_CALIBRATE_BUDGET": 2.0}
        self.assertEqual(sf.resolve_effective_budget("assert", cfg, 5.0), 5.0)

    def test_assert_prefers_token_budget(self):
        cfg = {"SMOKE_TOKEN_BUDGET": 1.0, "SMOKE_CALIBRATE_BUDGET": 2.0}
        self.assertEqual(sf.resolve_effective_budget("assert", cfg, None), 1.0)

    def test_assert_falls_back_to_calibrate(self):
        cfg = {"SMOKE_TOKEN_BUDGET": 0.0, "SMOKE_CALIBRATE_BUDGET": 2.0}
        self.assertEqual(sf.resolve_effective_budget("assert", cfg, None), 2.0)

    def test_harvest_prefers_calibrate_budget(self):
        cfg = {"SMOKE_TOKEN_BUDGET": 1.0, "SMOKE_CALIBRATE_BUDGET": 2.0}
        self.assertEqual(sf.resolve_effective_budget("harvest", cfg, None), 2.0)

    def test_all_zero_returns_zero(self):
        self.assertEqual(sf.resolve_effective_budget("assert", {}, None), 0.0)


class TestResolveModel(unittest.TestCase):
    def test_override_wins(self):
        self.assertEqual(sf.resolve_model("04", {"models": {"04": "haiku"}}, "sonnet"),
                         "sonnet")

    def test_config_model(self):
        self.assertEqual(sf.resolve_model("04", {"models": {"04": "haiku"}}, None),
                         "haiku")

    def test_default_sonnet(self):
        self.assertEqual(sf.resolve_model("04", {"models": {}}, None), "sonnet")


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


class TestPhaseCommand(unittest.TestCase):
    """工程ラベル → 実スラッシュコマンド（引数込み）の正準化（plan §7 リスク是正）。"""

    def test_init_includes_cr_and_title(self):
        c = sf._phase_command("01", "CR-2026-970", "T")
        self.assertEqual(c, "/xddp.01.init CR-2026-970 T")

    def test_numbered_phase_full_name_and_cr(self):
        self.assertEqual(sf._phase_command("02", "CR-2026-970", "T"),
                         "/xddp.02.analysis CR-2026-970")
        self.assertEqual(sf._phase_command("04", "CR-2026-970", "T"),
                         "/xddp.04.specout CR-2026-970")

    def test_close_command(self):
        self.assertEqual(sf._phase_command("close", "CR-2026-970", "T"),
                         "/xddp.close CR-2026-970")

    def test_every_label_has_full_dotted_command(self):
        # 全工程で `/xddp.NN.xxx`（バレ名 `/xddp.NN` ではない）を渡すこと（空振り再発防止）。
        for label in ["01", *sf.PHASE_LABELS]:
            cmd = sf.PHASE_COMMANDS[label]
            self.assertTrue(cmd.startswith("/xddp."))
            if label != "close":
                # 数値工程は 3 セグメント（/xddp.NN.name）
                self.assertEqual(cmd.count("."), 2, f"{label}: {cmd}")


class TestInvokePhaseCommand(unittest.TestCase):
    """_invoke_phase が正しい argv（実コマンド名・権限バイパス・母体 add-dir）を組むこと。"""

    def _run_invoke(self, phase, *, with_multi):
        temp = Path(tempfile.mkdtemp())
        ws = temp / "ws"
        ws.mkdir()
        if with_multi:
            (temp / "multi").mkdir()
        home = Path(tempfile.mkdtemp())

        class _Proc:
            stdout = "{}"
            returncode = 0
        with mock.patch("smoke_full.subprocess.run", return_value=_Proc()) as run:
            sf._invoke_phase(phase, ws, "sonnet", home, {})
        return run.call_args

    def test_uses_full_command_and_skip_permissions(self):
        ca = self._run_invoke("04", with_multi=False)
        argv = ca.args[0]
        self.assertIn("--dangerously-skip-permissions", argv)
        self.assertEqual(argv[-1], f"/xddp.04.specout {sf.HARVEST_CR}")

    def test_adds_multi_dir_when_present(self):
        ca = self._run_invoke("04", with_multi=True)
        argv = ca.args[0]
        self.assertIn("--add-dir", argv)
        # 可変長 --add-dir がプロンプトを飲み込まないよう、値の直後は option であること。
        ai = argv.index("--add-dir")
        self.assertTrue(argv[ai + 2].startswith("--"))     # add-dir 値の次は別オプション
        self.assertEqual(argv[-1], f"/xddp.04.specout {sf.HARVEST_CR}")  # prompt は末尾に残る
        self.assertEqual(argv[-2], "--dangerously-skip-permissions")

    def test_no_multi_dir_when_absent(self):
        ca = self._run_invoke("04", with_multi=False)
        self.assertNotIn("--add-dir", ca.args[0])


class TestStageWorkspace(unittest.TestCase):
    """隔離ステージング（plan 4.1）。実 setup.sh は subprocess をモック。"""

    def _make_seed(self, name):
        root = Path(tempfile.mkdtemp())
        seeds = root / "seeds"
        seed = seeds / name
        (seed / "xddp").mkdir(parents=True)
        (seed / "xddp.config.md").write_text("REPOS:\n  svc-a: ../multi/svc-a\n",
                                              encoding="utf-8")
        multi = root / "multi"
        (multi / "svc-a" / "src").mkdir(parents=True)
        (multi / "svc-a" / "src" / "mod_a.py").write_text("x=1\n", encoding="utf-8")
        (multi / "svc-b" / "src").mkdir(parents=True)
        return root, seed, multi

    def test_single_variant_stages_ws_home_and_motherbase(self):
        root, seed, multi = self._make_seed("phase02-single")
        temp = Path(tempfile.mkdtemp())
        with mock.patch("smoke_full.subprocess.run") as run:
            home, ws = sf.stage_workspace(seed, temp, repo_root=root, multi_src=multi)
        self.assertTrue((ws / "xddp.config.md").exists())          # seed 複製
        self.assertTrue((temp / "multi" / "svc-a" / "src" / "mod_a.py").exists())  # 母体同伴
        self.assertTrue((temp / "multi" / "svc-b").exists())
        self.assertTrue(home.is_dir())                              # home 生成
        self.assertEqual(ws, temp / "ws")
        run.assert_called_once()                                    # setup.sh 起動
        # setup.sh は隔離 HOME で起動される
        self.assertEqual(run.call_args.kwargs["env"]["HOME"], str(home))

    def test_multi_variant_skips_motherbase(self):
        root, seed, multi = self._make_seed("phase04-multi")
        temp = Path(tempfile.mkdtemp())
        with mock.patch("smoke_full.subprocess.run"):
            home, ws = sf.stage_workspace(seed, temp, repo_root=root, multi_src=multi)
        self.assertFalse((temp / "multi").exists())  # multi 版は母体内包 → 同伴なし

    def test_missing_seed_creates_empty_ws(self):
        root = Path(tempfile.mkdtemp())
        temp = Path(tempfile.mkdtemp())
        with mock.patch("smoke_full.subprocess.run"):
            home, ws = sf.stage_workspace(root / "seeds" / "phase01-single", temp,
                                          repo_root=root, multi_src=root / "nope")
        self.assertTrue(ws.is_dir())              # init は空 ws から起動
        self.assertEqual(list(ws.iterdir()), [])


class TestInjectAgentModels(unittest.TestCase):
    def _home_with_agent(self, body):
        home = Path(tempfile.mkdtemp())
        agents = home / ".claude" / "agents"
        agents.mkdir(parents=True)
        (agents / "foo.md").write_text(body, encoding="utf-8")
        return home, agents

    def test_injects_model_and_preserves_keys(self):
        home, agents = self._home_with_agent(
            "---\nname: foo\ndescription: bar\n---\n# Foo\n")
        changed = sf.inject_agent_models(home, {"*": "haiku"})
        self.assertEqual(changed, ["foo.md"])
        text = (agents / "foo.md").read_text(encoding="utf-8")
        self.assertIn("model: haiku", text)
        self.assertIn("name: foo", text)
        self.assertIn("description: bar", text)

    def test_replaces_existing_model(self):
        home, agents = self._home_with_agent(
            "---\nname: foo\nmodel: sonnet\n---\n")
        sf.inject_agent_models(home, {"foo": "haiku"})
        text = (agents / "foo.md").read_text(encoding="utf-8")
        self.assertIn("model: haiku", text)
        self.assertNotIn("model: sonnet", text)

    def test_empty_map_is_noop(self):
        home, agents = self._home_with_agent("---\nname: foo\n---\n")
        self.assertEqual(sf.inject_agent_models(home, {}), [])
        self.assertNotIn("model:", (agents / "foo.md").read_text(encoding="utf-8"))


class TestRunPhase(unittest.TestCase):
    """工程ランナー（plan 4.3）。stage_workspace の subprocess と _invoke_phase をモック。"""

    def _fixture(self, *, with_golden=False, golden_props=None):
        root = Path(tempfile.mkdtemp())
        seeds = root / "seeds"
        seed = seeds / "phase02-single"
        art = seed / "xddp" / "CR-2026-001" / "02_analysis"
        art.mkdir(parents=True)
        (art / "ANA.md").write_text(
            "---\nversion: 1\n---\n# タイトル\n## 4. 分析\nUR-001 を含む。\n",
            encoding="utf-8")
        golden = root / "golden"
        if with_golden:
            golden.mkdir(parents=True)
            import json as _json
            (golden / "phase02-single.json").write_text(
                _json.dumps(golden_props or {}), encoding="utf-8")
        return root, seeds, golden

    def _stub_invoke(self, cost=0.01):
        calls = []

        def _invoke(phase, ws, model, home, auth_env):
            calls.append(phase)
            return {"usage": {"input_tokens": 10, "output_tokens": 5},
                    "total_cost_usd": cost, "_phase": phase}
        return _invoke, calls

    def test_harvest_generates_only_no_golden(self):
        root, seeds, golden = self._fixture()
        invoke, calls = self._stub_invoke()
        b = sf.BudgetTracker(1.0)
        with mock.patch("smoke_full.subprocess.run"):
            r = sf.run_phase("02", budget=b, mode="harvest", seeds_root=seeds,
                             golden_dir=golden, multi_src=root / "none", invoke=invoke)
        self.assertEqual(r["status"], "harvested")
        self.assertIn("properties", r)
        self.assertFalse((golden / "phase02-single.json").exists())  # 書き込まない
        self.assertEqual(calls, ["02"])

    def test_assert_golden_missing_stops_without_invoking(self):
        root, seeds, golden = self._fixture()
        invoke, calls = self._stub_invoke()
        b = sf.BudgetTracker(1.0)
        with mock.patch("smoke_full.subprocess.run"), \
             mock.patch("smoke_full.compare_to_golden") as cmp:
            r = sf.run_phase("02", budget=b, mode="assert", seeds_root=seeds,
                             golden_dir=golden, multi_src=root / "none", invoke=invoke)
        self.assertEqual(r["status"], "golden_missing")
        self.assertEqual(calls, [])          # 未起動＝無駄な消費なし
        cmp.assert_not_called()              # 偽赤を作らない

    def test_assert_passes_when_golden_matches(self):
        root, seeds, golden = self._fixture(
            with_golden=True, golden_props={"required_headings": ["4. 分析"],
                                            "ids": ["UR-001"]})
        invoke, _ = self._stub_invoke()
        b = sf.BudgetTracker(1.0)
        with mock.patch("smoke_full.subprocess.run"):
            r = sf.run_phase("02", budget=b, mode="assert", seeds_root=seeds,
                             golden_dir=golden, multi_src=root / "none", invoke=invoke)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["violations"], [])

    def test_assert_flags_violations(self):
        root, seeds, golden = self._fixture(
            with_golden=True, golden_props={"required_headings": ["存在しない見出し"]})
        invoke, _ = self._stub_invoke()
        b = sf.BudgetTracker(1.0)
        with mock.patch("smoke_full.subprocess.run"):
            r = sf.run_phase("02", budget=b, mode="assert", seeds_root=seeds,
                             golden_dir=golden, multi_src=root / "none", invoke=invoke)
        self.assertEqual(r["status"], "violations")
        self.assertTrue(r["violations"])

    def test_invoke_error_skips_golden(self):
        # is_error 応答（セッション上限等）ではゴールデンを書かず invoke_error を返す。
        root, seeds, golden = self._fixture()

        def _invoke(phase, ws, model, home, auth_env):
            return {"is_error": True, "_returncode": 1,
                    "result": "You've hit your session limit", "total_cost_usd": 0.0}
        b = sf.BudgetTracker(1.0)
        with mock.patch("smoke_full.subprocess.run"):
            r = sf.run_phase("02", budget=b, mode="update-golden", seeds_root=seeds,
                             golden_dir=golden, multi_src=root / "none", invoke=_invoke)
        self.assertEqual(r["status"], "invoke_error")
        self.assertFalse((golden / "phase02-single.json").exists())  # 偽ゴールデンを書かない

    def test_update_golden_writes_file(self):
        root, seeds, golden = self._fixture()
        invoke, _ = self._stub_invoke()
        b = sf.BudgetTracker(1.0)
        with mock.patch("smoke_full.subprocess.run"):
            r = sf.run_phase("02", budget=b, mode="update-golden", seeds_root=seeds,
                             golden_dir=golden, multi_src=root / "none", invoke=invoke)
        self.assertEqual(r["status"], "golden_written")
        self.assertTrue((golden / "phase02-single.json").exists())

    def test_update_golden_preserves_handwritten_keys(self):
        """update-golden は抽出対象外の手書きキー（required_headings）を引き継ぎ、
        抽出対象キー（ids 等）は新しい値で上書きする。"""
        root, seeds, golden = self._fixture(
            with_golden=True, golden_props={"required_headings": ["4. 分析"],
                                            "ids": ["OLD-999"]})
        invoke, _ = self._stub_invoke()
        b = sf.BudgetTracker(1.0)
        with mock.patch("smoke_full.subprocess.run"):
            r = sf.run_phase("02", budget=b, mode="update-golden", seeds_root=seeds,
                             golden_dir=golden, multi_src=root / "none", invoke=invoke)
        self.assertEqual(r["status"], "golden_written")
        import json as _json
        written = _json.loads((golden / "phase02-single.json").read_text(encoding="utf-8"))
        self.assertEqual(written["required_headings"], ["4. 分析"])  # 手書きキーは保持
        self.assertEqual(written["ids"], ["UR-001"])  # 抽出対象キーは新しい値で上書き

    def test_update_golden_recovers_from_corrupt_json(self):
        """壊れた golden（不正 JSON）に対しても update-golden は例外送出せず、
        警告を出したうえで props のみ（全置換相当）で書き出す（#32 の回帰防止）。"""
        root, seeds, golden = self._fixture()
        golden.mkdir(parents=True, exist_ok=True)
        (golden / "phase02-single.json").write_text("{not valid json", encoding="utf-8")
        invoke, _ = self._stub_invoke()
        b = sf.BudgetTracker(1.0)
        with mock.patch("smoke_full.subprocess.run"):
            r = sf.run_phase("02", budget=b, mode="update-golden", seeds_root=seeds,
                             golden_dir=golden, multi_src=root / "none", invoke=invoke)
        self.assertEqual(r["status"], "golden_written")
        import json as _json
        written = _json.loads((golden / "phase02-single.json").read_text(encoding="utf-8"))
        self.assertNotIn("required_headings", written)  # 壊れた旧golden由来のキーは引き継がれない

    def test_calibrate_counts_false_failure(self):
        root, seeds, golden = self._fixture(
            with_golden=True, golden_props={"required_headings": ["存在しない見出し"]})
        invoke, _ = self._stub_invoke()
        b = sf.BudgetTracker(1.0)
        with mock.patch("smoke_full.subprocess.run"):
            r = sf.run_phase("02", budget=b, mode="calibrate", seeds_root=seeds,
                             golden_dir=golden, multi_src=root / "none", invoke=invoke)
        self.assertEqual(r["status"], "calibrated")
        self.assertTrue(r["false_failure"])

    def test_budget_exceeded_raises(self):
        root, seeds, golden = self._fixture()
        invoke, _ = self._stub_invoke(cost=2.0)
        b = sf.BudgetTracker(0.5)
        with mock.patch("smoke_full.subprocess.run"):
            with self.assertRaises(sf.BudgetExceeded):
                sf.run_phase("02", budget=b, mode="harvest", seeds_root=seeds,
                             golden_dir=golden, multi_src=root / "none", invoke=invoke)

    def test_budget_skip_when_cannot_start(self):
        root, seeds, golden = self._fixture()
        invoke, calls = self._stub_invoke()
        b = sf.BudgetTracker(0.01)  # 残 0.01 < est 0.10
        with mock.patch("smoke_full.subprocess.run"):
            r = sf.run_phase("02", budget=b, mode="harvest", seeds_root=seeds,
                             golden_dir=golden, multi_src=root / "none", invoke=invoke)
        self.assertEqual(r["status"], "budget_skip")
        self.assertEqual(calls, [])

    def test_multi_variant_resolves_multi_seed(self):
        root = Path(tempfile.mkdtemp())
        seeds = root / "seeds"
        art = seeds / "phase04-multi" / "xddp" / "CR-2026-001" / "04_specout"
        art.mkdir(parents=True)
        (art / "SPO.md").write_text("# SPO\n", encoding="utf-8")
        golden = root / "golden"
        invoke, _ = self._stub_invoke()
        b = sf.BudgetTracker(1.0)
        with mock.patch("smoke_full.subprocess.run"):
            r = sf.run_phase("04", variant="multi", budget=b, mode="harvest",
                             seeds_root=seeds, golden_dir=golden,
                             multi_src=root / "none", invoke=invoke)
        self.assertEqual(r["seed"], "phase04-multi")
        self.assertEqual(r["status"], "harvested")


class TestRunHarvestChain(unittest.TestCase):
    """連鎖ハーベスト（plan 5.1）。setup.sh(subprocess) と _invoke_phase をモック。"""

    def _base_config(self):
        d = Path(tempfile.mkdtemp())
        cfg = d / "xddp.config.md"
        cfg.write_text("REPOS:\n  svc-a: ../multi/svc-a\n", encoding="utf-8")
        return cfg

    def _stub_invoke(self, cost=0.01, write=False):
        calls = []

        def _invoke(phase, ws, model, home, auth_env):
            calls.append((phase, str(ws)))
            if write:
                (Path(ws) / f"out-{phase}.txt").write_text("x", encoding="utf-8")
            return {"usage": {"input_tokens": 10, "output_tokens": 5},
                    "total_cost_usd": cost, "_phase": phase}
        return _invoke, calls

    def test_chain_invokes_all_phases_in_one_ws(self):
        out = Path(tempfile.mkdtemp()) / "seeds"
        invoke, calls = self._stub_invoke()
        b = sf.BudgetTracker(100.0)
        with mock.patch("smoke_full.subprocess.run"):
            results = sf.run_harvest_chain(
                budget=b, model_resolver=lambda p: "sonnet",
                seeds_out=out, base_config=self._base_config(),
                multi_src=Path("/none"), invoke=invoke)
        self.assertEqual([p for p, _ in calls], sf.HARVEST_SINGLE_CHAIN)
        ws_paths = {ws for _, ws in calls}
        self.assertEqual(len(ws_paths), 1)  # 全工程が同一 ws を使い回す
        self.assertTrue(all(r["status"] == "harvested" for r in results))

    def test_snapshots_skip_init_and_capture_entry_state(self):
        out = Path(tempfile.mkdtemp()) / "seeds"
        invoke, _ = self._stub_invoke(write=True)
        b = sf.BudgetTracker(100.0)
        with mock.patch("smoke_full.subprocess.run"):
            sf.run_harvest_chain(
                budget=b, model_resolver=lambda p: "sonnet",
                seeds_out=out, base_config=self._base_config(),
                multi_src=Path("/none"), invoke=invoke)
        self.assertFalse((out / "phase01-single").exists())   # init は seed 無し
        # phase02 の入口＝01 完了後（out-01 あり・out-02 なし＝起動前スナップショット）
        self.assertTrue((out / "phase02-single" / "out-01.txt").exists())
        self.assertFalse((out / "phase02-single" / "out-02.txt").exists())
        # phase03 の入口＝02 まで完了
        self.assertTrue((out / "phase03-single" / "out-02.txt").exists())
        # close の入口＝11 まで完了
        self.assertTrue((out / "phaseClose-single" / "out-11.txt").exists())

    def test_snapshot_contains_config_not_multi_or_home(self):
        out = Path(tempfile.mkdtemp()) / "seeds"
        invoke, _ = self._stub_invoke()
        b = sf.BudgetTracker(100.0)
        with mock.patch("smoke_full.subprocess.run"):
            sf.run_harvest_chain(
                budget=b, model_resolver=lambda p: "sonnet",
                seeds_out=out, base_config=self._base_config(),
                multi_src=Path("/none"), invoke=invoke)
        seed = out / "phase02-single"
        self.assertTrue((seed / "xddp.config.md").exists())   # 起点 config を継承
        self.assertFalse((seed / "multi").exists())           # 母体は含めない
        self.assertFalse((seed / "home").exists())            # home は含めない

    def test_budget_exceeded_raises(self):
        out = Path(tempfile.mkdtemp()) / "seeds"
        invoke, _ = self._stub_invoke(cost=2.0)
        b = sf.BudgetTracker(0.5)
        with mock.patch("smoke_full.subprocess.run"):
            with self.assertRaises(sf.BudgetExceeded):
                sf.run_harvest_chain(
                    budget=b, model_resolver=lambda p: "sonnet",
                    seeds_out=out, base_config=self._base_config(),
                    multi_src=Path("/none"), invoke=invoke)

    def test_budget_skip_stops_chain(self):
        out = Path(tempfile.mkdtemp()) / "seeds"
        invoke, calls = self._stub_invoke()
        b = sf.BudgetTracker(0.05)  # 残 0.05 < est 0.10 → 先頭で起動不可
        with mock.patch("smoke_full.subprocess.run"):
            results = sf.run_harvest_chain(
                budget=b, model_resolver=lambda p: "sonnet",
                seeds_out=out, base_config=self._base_config(),
                multi_src=Path("/none"), invoke=invoke)
        self.assertEqual(calls, [])                       # 一切起動しない
        self.assertEqual(results[-1]["status"], "budget_skip")


class TestBuildTasks(unittest.TestCase):
    def _ns(self, **kw):
        import argparse
        d = {"all": False, "phase": None, "multi": False}
        d.update(kw)
        return argparse.Namespace(**d)

    def test_all_includes_init_and_multi(self):
        tasks = sf._build_tasks(self._ns(all=True))
        self.assertIn(("01", "single"), tasks)
        self.assertIn(("04", "multi"), tasks)
        self.assertIn(("11", "multi"), tasks)
        self.assertIn(("close", "single"), tasks)
        # 04/11 は single と multi の両方
        self.assertIn(("04", "single"), tasks)

    def test_phase_single(self):
        self.assertEqual(sf._build_tasks(self._ns(phase="02")), [("02", "single")])

    def test_phase_multi(self):
        self.assertEqual(sf._build_tasks(self._ns(phase="04", multi=True)),
                         [("04", "multi")])


class TestMainExitCodes(unittest.TestCase):
    """main の分岐・exit コード表を固定する（plan 4.5。実 LLM 起動なし）。"""

    def _run(self, argv, *, cfg=None, claude=True, auth=True, run_phase_ret=None,
             run_phase_side=None, harvest_chain_ret=None):
        cfg = cfg if cfg is not None else {}
        patches = [
            mock.patch("smoke_full.claude_available", return_value=claude),
            mock.patch("smoke_full._resolve_auth_env",
                       return_value=({"CLAUDE_CODE_OAUTH_TOKEN": "t"} if auth else None)),
            mock.patch("smoke_full.load_smoke_config", return_value=cfg),
        ]
        if run_phase_side is not None:
            patches.append(mock.patch("smoke_full.run_phase", side_effect=run_phase_side))
        elif run_phase_ret is not None:
            patches.append(mock.patch("smoke_full.run_phase", return_value=run_phase_ret))
        if harvest_chain_ret is not None:
            patches.append(mock.patch("smoke_full.run_harvest_chain",
                                      return_value=harvest_chain_ret))
        import contextlib
        import io
        with contextlib.ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            return sf.main(argv)

    def test_no_target_returns_2(self):
        self.assertEqual(self._run([]), 2)

    def test_bad_phase_returns_2(self):
        self.assertEqual(self._run(["--phase", "01"]), 2)  # init は --all 専用

    def test_claude_missing_returns_3(self):
        self.assertEqual(self._run(["--all"], claude=False), 3)

    def test_auth_missing_returns_5(self):
        self.assertEqual(self._run(["--all"], auth=False), 5)

    def test_no_budget_returns_6(self):
        self.assertEqual(self._run(["--all"], cfg={}), 6)

    def test_calibrate_budget_passes_gate_for_harvest(self):
        # --phase NN --harvest（単一工程ハーベスト）は run_phase 経路（seed 既存前提）。
        rc = self._run(["--phase", "04", "--harvest"],
                       cfg={"SMOKE_CALIBRATE_BUDGET": 2.0},
                       run_phase_ret={"seed": "s", "mode": "harvest", "model": "m",
                                      "status": "harvested", "cost_usd": 0.0})
        self.assertEqual(rc, 0)

    def test_all_harvest_routes_to_chain(self):
        # --all --harvest は連鎖ハーベスト（run_harvest_chain）へ結線される。
        rc = self._run(["--all", "--harvest"], cfg={"SMOKE_CALIBRATE_BUDGET": 2.0},
                       harvest_chain_ret=[{"seed": "phase02-single", "mode": "harvest",
                                           "model": "m", "status": "harvested",
                                           "cost_usd": 0.0}])
        self.assertEqual(rc, 0)

    def test_cli_budget_passes_gate(self):
        rc = self._run(["--phase", "02", "--budget", "1.0"], cfg={},
                       run_phase_ret={"seed": "s", "mode": "assert", "model": "m",
                                      "status": "ok", "cost_usd": 0.0})
        self.assertEqual(rc, 0)

    def test_violations_return_1(self):
        rc = self._run(["--phase", "02", "--budget", "1.0"],
                       run_phase_ret={"seed": "s", "mode": "assert", "model": "m",
                                      "status": "violations", "violations": ["x"],
                                      "cost_usd": 0.0})
        self.assertEqual(rc, 1)

    def test_golden_missing_returns_8(self):
        rc = self._run(["--phase", "02", "--budget", "1.0"],
                       run_phase_ret={"seed": "s", "mode": "assert", "model": "m",
                                      "status": "golden_missing",
                                      "golden_path": "/x.json"})
        self.assertEqual(rc, 8)

    def test_budget_exceeded_returns_7(self):
        def _boom(*a, **k):
            raise sf.BudgetExceeded("over")
        rc = self._run(["--phase", "02", "--budget", "1.0"], run_phase_side=_boom)
        self.assertEqual(rc, 7)

    def test_invoke_error_returns_9(self):
        rc = self._run(["--phase", "02", "--budget", "1.0"],
                       run_phase_ret={"seed": "s", "mode": "update-golden",
                                      "model": "m", "status": "invoke_error",
                                      "error": "session limit", "cost_usd": 0.0})
        self.assertEqual(rc, 9)

    def test_no_exit_4_anymore(self):
        # 旧 exit 4（校正完了後に有効化）は撤去済み。予算供給で通常経路に入る。
        rc = self._run(["--phase", "02", "--budget", "1.0"],
                       run_phase_ret={"seed": "s", "mode": "assert", "model": "m",
                                      "status": "ok", "cost_usd": 0.0})
        self.assertNotEqual(rc, 4)


if __name__ == "__main__":
    unittest.main()
