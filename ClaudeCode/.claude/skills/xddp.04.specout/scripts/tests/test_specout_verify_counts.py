import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import specout_verify_counts as mod  # noqa: E402

WAVE0_MATCHING = """# Discovery Log — CR-2026-999 / device-svc

## Wave 0

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W0-C1 | HIGH複合 | `\\b(processPayment)\\b` | 全域 | 2 |

**除外:** tests/

| 行ID | コマンドID | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 1 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|
| W0-R1 | W0-C1 | src/a.py | 10 | `processPayment(x)` | `handle` | 制御フロー | HIGH | `validate` | CRS |
| W0-R2 | W0-C1 | src/b.py | 20 | `processPayment(y)` | `handle2` | 制御フロー | HIGH | `validate` | CRS |

→ Wave 1 frontier: `validate`[HIGH]

## 高ノイズシンボル（上限超過のため波及停止）
| シンボル | 発見波 | 発見ファイル数 | 備考 |
|---|---|---|---|
| （なし） | | | |
"""

WAVE_MISMATCH = """# Discovery Log — CR-2026-999 / device-svc

## Wave 2

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W2-C1 | HIGH複合 | `\\b(validate)\\b` | 全域 | 3 |

| 行ID | コマンドID | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 3 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|
| W2-R1 | W2-C1 | src/a.py | 5 | `validate(x)` | `f1` | 制御フロー | HIGH | - | W0-R1 |
| W2-R2 | W2-C1 | src/b.py | 6 | `validate(y)` | `f2` | 制御フロー | HIGH | - | W0-R1 |

→ Wave 3 frontier: (なし)

## 高ノイズシンボル（上限超過のため波及停止）
| シンボル | 発見波 | 発見ファイル数 | 備考 |
|---|---|---|---|
| （なし） | | | |
"""

WAVE_WITH_DISCARD = """# Discovery Log — CR-2026-999 / device-svc

## Wave 3

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W3-C1 | HIGH複合 | `\\b(param)\\b` | `src/base.cpp` | 5 |
| W3-C2 | MEDIUM | `\\b(param)\\b` | `src/derived_a.cpp` | 4 |

| 行ID | コマンドID | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 4 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|
| W3-R1 | W3-C1 | src/base.cpp | 1 | `param` | `f` | 制御フロー | HIGH | - | - |
| W3-R2 | W3-C1 | src/base.cpp | 2 | `param` | `g` | 制御フロー | HIGH | - | - |
| W3-R3 | W3-C1 | src/base.cpp | 3 | `param` | `h` | 制御フロー | HIGH | - | - |
| W3-R4 | W3-C1 | src/base.cpp | 4 | `param` | `i` | 制御フロー | HIGH | - | - |
| W3-R5 | W3-C1 | src/base.cpp | 5 | `param` | `j` | 制御フロー | HIGH | - | - |

→ Wave 4 frontier: (なし)

## 同名 MEDIUM シンボル・異スコープ重複ログ（発生時のみ記録）

| Wave | シンボル | 検出スコープ一覧 | ケース | 処置 |
|---|---|---|---|---|
| Wave 3 | `param` | `src/base.cpp`, `src/derived_a.cpp` | A（HIGH昇格） | HIGH へ昇格（`src/base.cpp` で外部公開パターン検出）。`src/derived_a.cpp` の grep 結果を廃棄。次波で全域 grep |

## 高ノイズシンボル（上限超過のため波及停止）
| シンボル | 発見波 | 発見ファイル数 | 備考 |
|---|---|---|---|
| （なし） | | | |
"""


class SpecoutVerifyCountsTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, text: str, wave: int):
        log_path = Path(self.tmpdir.name) / "discovery-log.md"
        log_path.write_text(text, encoding="utf-8", newline="\n")
        parser = mod.build_parser()
        args = parser.parse_args(["--log", str(log_path), "--wave", str(wave)])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue()), log_path.read_text(encoding="utf-8")

    def test_matching_counts_produces_no_mismatches(self):
        result, text = self._run(WAVE0_MATCHING, 0)
        self.assertEqual(result["mismatches"], [])
        self.assertIn("| W0-C1 | 2 | 2 | ✅ |", text)
        self.assertIn("### 件数一致検証", text)

    def test_mismatch_is_flagged(self):
        result, text = self._run(WAVE_MISMATCH, 2)
        self.assertEqual(result["mismatches"], ["W2-C1"])
        self.assertIn("⚠️ W2-C1 件数不一致（ヒット3件/記録2件）", text)

    def test_case_a_discard_is_excluded_from_mismatches(self):
        result, text = self._run(WAVE_WITH_DISCARD, 3)
        self.assertEqual(result["mismatches"], [])
        self.assertEqual(result["excluded"], ["W3-C2"])
        self.assertIn("➖ 廃棄（ケースA, 次波でHIGH昇格済）", text)
        # W3-C1 (5件claimed, 5件recorded) は通常どおり一致判定
        self.assertIn("| W3-C1 | 5 | 5 | ✅ |", text)

    def test_rerun_replaces_previous_verification_table(self):
        _, text_first = self._run(WAVE0_MATCHING, 0)
        log_path = Path(self.tmpdir.name) / "discovery-log.md"
        parser = mod.build_parser()
        args = parser.parse_args(["--log", str(log_path), "--wave", "0"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        text_second = log_path.read_text(encoding="utf-8")
        self.assertEqual(text_second.count("### 件数一致検証"), 1)

    def test_missing_wave_errors(self):
        log_path = Path(self.tmpdir.name) / "discovery-log.md"
        log_path.write_text(WAVE0_MATCHING, encoding="utf-8", newline="\n")
        parser = mod.build_parser()
        args = parser.parse_args(["--log", str(log_path), "--wave", "99"])
        with self.assertRaises(SystemExit):
            args.func(args)

    def test_missing_file_errors(self):
        parser = mod.build_parser()
        args = parser.parse_args(["--log", str(Path(self.tmpdir.name) / "nope.md"), "--wave", "0"])
        with self.assertRaises(SystemExit):
            args.func(args)


if __name__ == "__main__":
    unittest.main()
