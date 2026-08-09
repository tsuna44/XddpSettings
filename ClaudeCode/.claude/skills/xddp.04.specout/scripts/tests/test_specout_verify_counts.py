import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
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

WAVE0_WITH_SYMBOL_COLUMN = """# Discovery Log — CR-2026-999 / device-svc

## Wave 0

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W0-C1 | HIGH複合 | `\\b(processPayment)\\b` | 全域 | 2 |

**除外:** tests/

| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 1 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|---|
| W0-R1 | W0-C1 | `processPayment` | src/a.py | 10 | `processPayment(x)` | `handle` | 制御フロー | HIGH | `validate` | CRS |
| W0-R2 | W0-C1 | `processPayment` | src/b.py | 20 | `processPayment(y)` | `handle2` | 制御フロー | HIGH | `validate` | CRS |

→ Wave 1 frontier: `validate`[HIGH]

## 高ノイズシンボル（上限超過のため波及停止）
| シンボル | 発見波 | 発見ファイル数 | 備考 |
|---|---|---|---|
| （なし） | | | |
"""


WAVE_WITH_DROPS = """# Discovery Log — CR-2026-999 / device-svc

## Wave 5

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W5-C1 | HIGH複合 | `\\b(validate)\\b` | 全域 | 5 |

| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 6 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|---|
| W5-R1 | W5-C1 | `validate` | src/a.py | 5 | `validate(x)` | `f1` | 制御フロー | HIGH | - | - |
| W5-R2 | W5-C1 | `validate` | src/b.py | 6 | `validate(y)` | `f2` | 制御フロー | HIGH | - | - |
| W5-R3 | W5-C1 | `validate` | src/c.py | 7 | `validate(z)` | `f3` | 制御フロー | HIGH | - | - |

→ Wave 6 frontier: (なし)

### 件数一致検証
| コマンドID | ヒット行数（生） | dedup除外 | フィルタ除外 | 記録行数 | 一致 |
|---|---|---|---|---|---|
| W5-C1 | 5 | 1 | 1 | 3 | ✅（dedup 1/filter 1 除外） |

## 高ノイズシンボル（上限超過のため波及停止）
| シンボル | 発見波 | 発見ファイル数 | 備考 |
|---|---|---|---|
| （なし） | | | |
"""


# -- PLAN-20260808-specout-verify-counts-wiring: --wave all / --strict / 複数波 fixture --

MULTI_WAVE_ALL_MATCH = """# Discovery Log — CR-2026-999 / device-svc

## Wave 0

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W0-C1 | HIGH複合 | `\\b(a)\\b` | 全域 | 1 |

| 行ID | コマンドID | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 1 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|
| W0-R1 | W0-C1 | src/a.py | 1 | `a()` | `f` | 制御フロー | HIGH | - | CRS |

## Wave 1

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W1-C1 | HIGH複合 | `\\b(b)\\b` | 全域 | 1 |

| 行ID | コマンドID | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 2 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|
| W1-R1 | W1-C1 | src/b.py | 1 | `b()` | `f` | 制御フロー | HIGH | - | W0-R1 |

## Wave 2

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W2-C1 | HIGH複合 | `\\b(c)\\b` | 全域 | 1 |

| 行ID | コマンドID | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 3 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|
| W2-R1 | W2-C1 | src/c.py | 1 | `c()` | `f` | 制御フロー | HIGH | - | W1-R1 |

## 高ノイズシンボル（上限超過のため波及停止）
| シンボル | 発見波 | 発見ファイル数 | 備考 |
|---|---|---|---|
| （なし） | | | |
"""

MULTI_WAVE_WAVE1_MISMATCH = """# Discovery Log — CR-2026-999 / device-svc

## Wave 0

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W0-C1 | HIGH複合 | `\\b(a)\\b` | 全域 | 1 |

| 行ID | コマンドID | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 1 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|
| W0-R1 | W0-C1 | src/a.py | 1 | `a()` | `f` | 制御フロー | HIGH | - | CRS |

## Wave 1

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W1-C1 | HIGH複合 | `\\b(b)\\b` | 全域 | 2 |

| 行ID | コマンドID | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 2 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|
| W1-R1 | W1-C1 | src/b.py | 1 | `b()` | `f` | 制御フロー | HIGH | - | W0-R1 |

## Wave 2

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W2-C1 | HIGH複合 | `\\b(c)\\b` | 全域 | 1 |

| 行ID | コマンドID | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 3 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|
| W2-R1 | W2-C1 | src/c.py | 1 | `c()` | `f` | 制御フロー | HIGH | - | W1-R1 |

## 高ノイズシンボル（上限超過のため波及停止）
| シンボル | 発見波 | 発見ファイル数 | 備考 |
|---|---|---|---|
| （なし） | | | |
"""

NO_WAVE_LOG = """# Discovery Log — CR-2026-999 / device-svc

## 高ノイズシンボル（上限超過のため波及停止）
| シンボル | 発見波 | 発見ファイル数 | 備考 |
|---|---|---|---|
| （なし） | | | |
"""

MULTI_WAVE_DISCARD = """# Discovery Log — CR-2026-999 / device-svc

## Wave 1

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W1-C1 | HIGH複合 | `\\b(paramA)\\b` | `src/base_a.cpp` | 2 |
| W1-C2 | MEDIUM | `\\b(paramA)\\b` | `src/derived_a.cpp` | 3 |

| 行ID | コマンドID | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 2 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|
| W1-R1 | W1-C1 | src/base_a.cpp | 1 | `paramA` | `f` | 制御フロー | HIGH | - | - |
| W1-R2 | W1-C1 | src/base_a.cpp | 2 | `paramA` | `g` | 制御フロー | HIGH | - | - |

## 同名 MEDIUM シンボル・異スコープ重複ログ（発生時のみ記録）

| Wave | シンボル | 検出スコープ一覧 | ケース | 処置 |
|---|---|---|---|---|
| Wave 1 | `paramA` | `src/base_a.cpp`, `src/derived_a.cpp` | A（HIGH昇格） | HIGH へ昇格（`src/base_a.cpp` で外部公開パターン検出）。`src/derived_a.cpp` の grep 結果を廃棄。次波で全域 grep |

## Wave 2

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W2-C1 | HIGH複合 | `\\b(mid)\\b` | 全域 | 1 |

| 行ID | コマンドID | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 3 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|
| W2-R1 | W2-C1 | src/mid.py | 1 | `mid()` | `f` | 制御フロー | HIGH | - | - |

## Wave 3

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W3-C1 | HIGH複合 | `\\b(paramB)\\b` | `src/base_b.cpp` | 2 |
| W3-C2 | MEDIUM | `\\b(paramB)\\b` | `src/derived_b.cpp` | 4 |

| 行ID | コマンドID | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 4 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|
| W3-R1 | W3-C1 | src/base_b.cpp | 1 | `paramB` | `f` | 制御フロー | HIGH | - | - |
| W3-R2 | W3-C1 | src/base_b.cpp | 2 | `paramB` | `g` | 制御フロー | HIGH | - | - |

## 同名 MEDIUM シンボル・異スコープ重複ログ（発生時のみ記録）

| Wave | シンボル | 検出スコープ一覧 | ケース | 処置 |
|---|---|---|---|---|
| Wave 3 | `paramB` | `src/base_b.cpp`, `src/derived_b.cpp` | A（HIGH昇格） | HIGH へ昇格（`src/base_b.cpp` で外部公開パターン検出）。`src/derived_b.cpp` の grep 結果を廃棄。次波で全域 grep |

## 高ノイズシンボル（上限超過のため波及停止）
| シンボル | 発見波 | 発見ファイル数 | 備考 |
|---|---|---|---|
| （なし） | | | |
"""

# 検証表直後の空行が明示的に2行（§3.3 冪等化の正規化対象を作る）。
WAVE_IDEMPOTENT = """# Discovery Log — CR-2026-999 / device-svc

## Wave 0

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W0-C1 | HIGH複合 | `\\b(a)\\b` | 全域 | 1 |

| 行ID | コマンドID | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 1 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|
| W0-R1 | W0-C1 | src/a.py | 1 | `a()` | `f` | 制御フロー | HIGH | - | CRS |

### 件数一致検証
| コマンドID | ヒット行数（生） | dedup除外 | フィルタ除外 | noise-collapse除外 | 記録行数 | 一致 |
|---|---|---|---|---|---|---|
| W0-C1 | 1 | 0 | 0 | 0 | 1 | ✅ |


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
        self.assertEqual(result["waves"][0]["mismatches"], [])
        self.assertIn("| W0-C1 | 2 | 0 | 0 | 0 | 2 | ✅ |", text)
        self.assertIn("### 件数一致検証", text)
        self.assertIn("noise-collapse除外", text)

    def test_matching_counts_with_search_symbol_column_produces_no_mismatches(self):
        # 「検索シンボル」列（specout_bfs.py が追加）が挿入されても、列名ベースの解決
        # （header.index）により件数一致検証は引き続き正しく動作する。
        result, text = self._run(WAVE0_WITH_SYMBOL_COLUMN, 0)
        self.assertEqual(result["waves"][0]["mismatches"], [])
        self.assertIn("| W0-C1 | 2 | 0 | 0 | 0 | 2 | ✅ |", text)
        self.assertIn("### 件数一致検証", text)

    def test_mismatch_is_flagged(self):
        result, text = self._run(WAVE_MISMATCH, 2)
        self.assertEqual(result["waves"][0]["mismatches"], ["W2-C1"])
        self.assertIn("⚠️ W2-C1 件数不一致（生3件/記録2+除外0件）", text)

    def test_case_a_discard_is_excluded_from_mismatches(self):
        result, text = self._run(WAVE_WITH_DISCARD, 3)
        self.assertEqual(result["waves"][0]["mismatches"], [])
        self.assertEqual(result["waves"][0]["excluded"], ["W3-C2"])
        self.assertIn("➖ 廃棄（ケースA, 次波でHIGH昇格済）", text)
        # W3-C1 (5件claimed, 5件recorded) は通常どおり一致判定
        self.assertIn("| W3-C1 | 5 | 0 | 0 | 0 | 5 | ✅ |", text)

    def test_dedup_filter_drops_reconciled(self):
        # PLAN-20260804 Phase 1: commit-wave が書いた dedup除外/フィルタ除外 を入力に、
        # 生 == 記録 + dedup + filter + noise-collapse で照合し不一致にしない（生5 = 記録3 + dedup1 + filter1）。
        # WAVE_WITH_DROPS の既存テーブルは noise-collapse除外 列が無い旧形式のため 0 とみなす（後方互換）。
        result, text = self._run(WAVE_WITH_DROPS, 5)
        self.assertEqual(result["waves"][0]["mismatches"], [])
        self.assertIn("| W5-C1 | 5 | 1 | 1 | 0 | 3 | ✅（dedup 1/filter 1/noise-collapse 0 除外） |", text)

    def test_noise_collapse_drops_reconciled(self):
        # PLAN-20260806 Phase 2A: noise-collapse除外 列を持つ既存テーブルからも正しく再照合する
        # （生6 = 記録3 + dedup1 + filter1 + noise-collapse1）。
        text = """# Discovery Log — CR-2026-999 / device-svc

## Wave 6

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W6-C1 | HIGH複合 | `\\b(validate)\\b` | 全域 | 6 |

| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 7 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|---|
| W6-R1 | W6-C1 | `validate` | src/a.py | 5 | `validate(x)` | `f1` | 制御フロー | HIGH | - | - |
| W6-R2 | W6-C1 | `validate` | src/b.py | 6 | `validate(y)` | `f2` | 制御フロー | HIGH | - | - |
| W6-R3 | W6-C1 | `validate` | src/c.py | 7 | `validate(z)` | `f3` | 制御フロー | HIGH | - | - |

→ Wave 7 frontier: (なし)

### 件数一致検証
| コマンドID | ヒット行数（生） | dedup除外 | フィルタ除外 | noise-collapse除外 | 記録行数 | 一致 |
|---|---|---|---|---|---|---|
| W6-C1 | 6 | 1 | 1 | 1 | 3 | ✅（dedup 1/filter 1/noise-collapse 1 除外） |

## 高ノイズシンボル（上限超過のため波及停止）
| シンボル | 発見波 | 発見ファイル数 | 備考 |
|---|---|---|---|
| （なし） | | | |
"""
        result, out_text = self._run(text, 6)
        self.assertEqual(result["waves"][0]["mismatches"], [])
        self.assertIn("| W6-C1 | 6 | 1 | 1 | 1 | 3 | ✅（dedup 1/filter 1/noise-collapse 1 除外） |", out_text)

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

    # -- PLAN-20260808 不具合1（エスケープ規約の読み書き対称化・列数 fail-loud）--

    def _run_expect_err(self, text: str, wave: int) -> str:
        """verify が exit 非0 で停止することを確認し、stderr の内容を返す。"""
        log_path = Path(self.tmpdir.name) / "discovery-log.md"
        log_path.write_text(text, encoding="utf-8", newline="\n")
        parser = mod.build_parser()
        args = parser.parse_args(["--log", str(log_path), "--wave", str(wave)])
        buf = io.StringIO()
        with redirect_stderr(buf), self.assertRaises(SystemExit) as cm:
            args.func(args)
        self.assertNotEqual(cm.exception.code, 0)
        return buf.getvalue()

    def test_split_row_unescapes_pipe(self):
        cells = mod._split_row(r"| W0-C1 | `\b(A\|B\|C)\b` | 全域 |")
        self.assertEqual(cells, ["W0-C1", r"`\b(A|B|C)\b`", "全域"])

    def test_join_row_reescapes_pipe(self):
        # 正準形（区切りは ` | ` で空白パディング・セル前後に余分な空白なし）でのみ往復一致する。
        line = r"| W0-C1 | `\b(A\|B\|C)\b` | 全域 |"
        self.assertEqual(mod._join_row(mod._split_row(line)), line)

    def test_verify_reads_escaped_composite_pattern(self):
        """`\\b(A\\|B)\\b` 形式のエスケープ済み複合パターンから正しい生ヒット数を読む。"""
        text = """# Discovery Log — CR-2026-999 / device-svc

## Wave 0

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W0-C1 | HIGH複合 | `\\b(alpha\\|beta\\|gamma)\\b` | 全域 | 2 |

| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 1 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|---|
| W0-R1 | W0-C1 | `alpha` | src/a.c | 10 | `alpha \\|= FLAG;` | `f1` | データフロー | HIGH | - | CRS |
| W0-R2 | W0-C1 | `beta` | src/b.c | 20 | `beta \\|= FLAG;` | `f2` | データフロー | HIGH | - | CRS |
"""
        result, out_text = self._run(text, 0)
        self.assertEqual(result["waves"][0]["mismatches"], [])
        self.assertIn("| W0-C1 | 2 | 0 | 0 | 0 | 2 | ✅ |", out_text)

    def test_verify_fails_loud_on_unescaped_pipe_in_exec_table(self):
        """未エスケープ `|` を含む（旧形式の）実行コマンド一覧で停止し、行番号を示す。"""
        text = """# Discovery Log — CR-2026-999 / device-svc

## Wave 0

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W0-C1 | HIGH複合 | `\\b(alpha|beta)\\b` | 全域 | 1 |

| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 1 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|---|
| W0-R1 | W0-C1 | `alpha` | src/a.c | 10 | `alpha()` | `f1` | データフロー | HIGH | - | CRS |
"""
        err = self._run_expect_err(text, 0)
        self.assertIn("### 実行コマンド一覧", err)
        self.assertIn("行 8", err)

    def test_verify_fails_loud_on_unescaped_pipe_in_hits_table(self):
        """未エスケープ `|` を含むヒット行テーブルで停止する（従来は記録数が無音で過少になった）。"""
        text = """# Discovery Log — CR-2026-999 / device-svc

## Wave 0

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W0-C1 | HIGH複合 | `\\b(alpha)\\b` | 全域 | 1 |

| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 1 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|---|
| W0-R1 | W0-C1 | `alpha` | src/a.c | 10 | `alpha |= FLAG;` | `f1` | データフロー | HIGH | - | CRS |
"""
        err = self._run_expect_err(text, 0)
        self.assertIn("ヒット行テーブル", err)

    def test_verify_fails_loud_on_short_row(self):
        """列数が不足する行も無音スキップせず停止する（旧 continue の回帰防止）。"""
        text = """# Discovery Log — CR-2026-999 / device-svc

## Wave 0

### 実行コマンド一覧
| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |
|---|---|---|---|---|
| W0-C1 | HIGH複合 | 全域 | 1 |

| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | Wave 1 追加シンボル | 派生元 |
|---|---|---|---|---|---|---|---|---|---|---|
| W0-R1 | W0-C1 | `alpha` | src/a.c | 10 | `alpha()` | `f1` | データフロー | HIGH | - | CRS |
"""
        err = self._run_expect_err(text, 0)
        self.assertIn("ヘッダ 5 列 / データ 4 列", err)

    # -- PLAN-20260808-specout-verify-counts-wiring: --wave all / --strict / 全セクション走査 / 冪等化 --

    def test_wave_all_verifies_every_wave(self):
        log_path = Path(self.tmpdir.name) / "discovery-log.md"
        log_path.write_text(MULTI_WAVE_ALL_MATCH, encoding="utf-8", newline="\n")
        parser = mod.build_parser()
        args = parser.parse_args(["--log", str(log_path), "--wave", "all"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        result = json.loads(buf.getvalue())
        self.assertEqual([w["wave"] for w in result["waves"]], [0, 1, 2])
        text = log_path.read_text(encoding="utf-8")
        self.assertEqual(text.count("### 件数一致検証"), 3)

    def test_single_wave_returns_waves_list_of_one(self):
        result, _ = self._run(WAVE0_MATCHING, 0)
        self.assertEqual(set(result.keys()), {"ok", "waves", "mismatch_waves"})
        self.assertEqual(len(result["waves"]), 1)
        self.assertEqual(result["waves"][0]["wave"], 0)

    def test_wave_all_returns_mismatch_waves(self):
        log_path = Path(self.tmpdir.name) / "discovery-log.md"
        log_path.write_text(MULTI_WAVE_WAVE1_MISMATCH, encoding="utf-8", newline="\n")
        parser = mod.build_parser()
        args = parser.parse_args(["--log", str(log_path), "--wave", "all"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        result = json.loads(buf.getvalue())
        self.assertEqual(result["mismatch_waves"], [1])

    def test_wave_all_on_log_without_waves_is_noop(self):
        log_path = Path(self.tmpdir.name) / "discovery-log.md"
        log_path.write_text(NO_WAVE_LOG, encoding="utf-8", newline="\n")
        parser = mod.build_parser()
        args = parser.parse_args(["--log", str(log_path), "--wave", "all"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        result = json.loads(buf.getvalue())
        self.assertEqual(result, {"ok": True, "waves": [], "mismatch_waves": []})

    def test_wave_all_rejects_invalid_wave_arg(self):
        log_path = Path(self.tmpdir.name) / "discovery-log.md"
        log_path.write_text(WAVE0_MATCHING, encoding="utf-8", newline="\n")
        parser = mod.build_parser()
        args = parser.parse_args(["--log", str(log_path), "--wave", "abc"])
        buf = io.StringIO()
        with redirect_stderr(buf), self.assertRaises(SystemExit) as cm:
            args.func(args)
        self.assertEqual(cm.exception.code, 1)

    def test_strict_exits_3_on_mismatch(self):
        log_path = Path(self.tmpdir.name) / "discovery-log.md"
        log_path.write_text(WAVE_MISMATCH, encoding="utf-8", newline="\n")
        parser = mod.build_parser()
        args = parser.parse_args(["--log", str(log_path), "--wave", "all", "--strict"])
        buf = io.StringIO()
        with redirect_stdout(buf), self.assertRaises(SystemExit) as cm:
            args.func(args)
        self.assertEqual(cm.exception.code, mod.EXIT_MISMATCH)

    def test_strict_exits_0_when_all_match(self):
        log_path = Path(self.tmpdir.name) / "discovery-log.md"
        log_path.write_text(WAVE0_MATCHING, encoding="utf-8", newline="\n")
        parser = mod.build_parser()
        args = parser.parse_args(["--log", str(log_path), "--wave", "all", "--strict"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)  # SystemExit が発生しなければ成功

    def test_without_strict_exits_0_on_mismatch(self):
        log_path = Path(self.tmpdir.name) / "discovery-log.md"
        log_path.write_text(WAVE_MISMATCH, encoding="utf-8", newline="\n")
        parser = mod.build_parser()
        args = parser.parse_args(["--log", str(log_path), "--wave", "all"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)  # --strict 無指定なので SystemExit は発生しない
        result = json.loads(buf.getvalue())
        self.assertEqual(result["mismatch_waves"], [2])

    def test_strict_still_writes_verification_table(self):
        log_path = Path(self.tmpdir.name) / "discovery-log.md"
        log_path.write_text(WAVE_MISMATCH, encoding="utf-8", newline="\n")
        parser = mod.build_parser()
        args = parser.parse_args(["--log", str(log_path), "--wave", "all", "--strict"])
        buf = io.StringIO()
        with redirect_stdout(buf), self.assertRaises(SystemExit):
            args.func(args)
        text = log_path.read_text(encoding="utf-8")
        self.assertIn("### 件数一致検証", text)
        self.assertIn("⚠️ W2-C1 件数不一致", text)

    def test_ok_stays_true_on_mismatch(self):
        result, _ = self._run(WAVE_MISMATCH, 2)
        self.assertTrue(result["ok"])

    def test_discarded_scopes_detected_in_later_waves(self):
        log_path = Path(self.tmpdir.name) / "discovery-log.md"
        log_path.write_text(MULTI_WAVE_DISCARD, encoding="utf-8", newline="\n")
        parser = mod.build_parser()
        args = parser.parse_args(["--log", str(log_path), "--wave", "all"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        result = json.loads(buf.getvalue())
        wave1 = next(w for w in result["waves"] if w["wave"] == 1)
        wave3 = next(w for w in result["waves"] if w["wave"] == 3)
        self.assertEqual(wave1["mismatches"], [])
        self.assertEqual(wave1["excluded"], ["W1-C2"])
        # 修正前は最初の1セクション（Wave 1分）しか読まないため、Wave 3の廃棄スコープが
        # 取りこぼされ W3-C2 が偽の不一致になっていた。
        self.assertEqual(wave3["mismatches"], [])
        self.assertEqual(wave3["excluded"], ["W3-C2"])

    def test_verify_is_idempotent(self):
        log_path = Path(self.tmpdir.name) / "discovery-log.md"
        log_path.write_text(WAVE_IDEMPOTENT, encoding="utf-8", newline="\n")
        parser = mod.build_parser()

        def run_once():
            args = parser.parse_args(["--log", str(log_path), "--wave", "all"])
            buf = io.StringIO()
            with redirect_stdout(buf):
                args.func(args)
            return log_path.read_text(encoding="utf-8")

        run_once()  # 1回目: 既存の複数空行を1行へ正規化しうるため比較対象外
        text_second = run_once()
        text_third = run_once()
        self.assertEqual(text_second, text_third)


if __name__ == "__main__":
    unittest.main()
