"""
specout_bfs.py — Discovery BFS 帳簿エンジン（段階3）

`xddp-specout-agent.md` の Step 2（BFS ループ）が担っていた帳簿処理（visited/frontier 管理・
複合 grep コマンド組み立てと実行・コマンドID採番・件数記録・SYMBOL_ORIGIN_MAP・HIGH/MEDIUM
交差ルール・同名 MEDIUM 異スコープのケースA/B/C分岐・高ノイズシンボル判定・
discovery-log.md/BFS 状態ファイルの書き出し）を機械化する。

真実は `--path` で渡す bfs-state.json（工程4では `{OUTPUT_DIR}/work/bfs-state.json`。
checkpoint.json は段階1で廃止・本ファイルに統合）。
同じディレクトリの `bfs-state.md` は本スクリプトが状態から再生成する人可読ビュー（表示フォーマットは
段階1 `specout_checkpoint.py` と互換）。discovery-log.md はテンプレート
（`04_specout-discovery-log-template.md`）と同一の見出し・テーブル列構成で生成する。

波ループのプロトコル（波ループの実行主体は SKILL 側オーケストレータ）:
  0. Step A-Seed で `seed-preview` が候補表（work/seed-candidates.md）の採用シンボルのヒット数を試算し、
     人が採否を確定する
  1. `init --seed-candidates` で BFS を開始（Wave 0 の初期シンボル・ENTRY_POINTS・由来テーブルは
     候補表の採用行から決定的に作る。`--symbols` による直接指定も可）。判定エンジン（slice / rule）・
     予算・波数上限は init の値を state に保存し、再開を含むその CR の判定の単一情報源にする
  2. オーケストレータ（SKILL）が `search` で現波の frontier を検索する（既定は識別子索引 `index`）。
     dedup・保守的フィルタ・1波の予算（hit-budget / llm-budget）を適用し、`wave-{N}-hits.json` と、
     判定先ごとのチャンク（スライス用 `wave-{N}-hits-chunk-S.json`〔常に1件〕と、関数の範囲を決定的に
     取れない言語の LLM 用 `wave-{N}-hits-chunk-{K}.json`〔0件可〕）を出力する。state の
     `seed_summary_pending` が空でなければ検索せずに終了コード 6 で止まる。探索の起点の波から数えた波数が
     上限に達したら、残りを打ち切り記録に残して complete にする
  3. スライス用チャンクを `specout_slice.py classify` が判定し、LLM 用チャンクを classifier サブエージェント
     （チャンク単位・並列起動）が意味判定する（`wave-{N}-chunk-{S|K}-class.json`）
  4. `merge_classification.py` がチャンク結果を検証・結合して `wave-{N}-class.json`（および
     grep未対応パターン `wave-{N}-unsupported.json`）を作る
  5. `commit-wave` が classification を検証し、帳簿（打ち切り記録・要約・関数か値か・再訪を含む）を
     更新して discovery-log.md に書き出す
  6. frontier が尽きるか波数上限に達するまで 2〜5 を繰り返す。`status --brief` で再開判定を確認する
  7. 波ループ終了時に `prelim-metrics` が件数系計測（prelim_summary）を metrics.jsonl へ記録する。
     SPO の仕上げでは、`doc-targets --auto-assign` が、どのモジュールにも属さない確定ファイルを親ディレクトリへ割り当て、
     `ripple-summary` が波紋調査の結果を機能（モジュール）単位に要約する（人向けの全量と assemble-spo の入力の JSON）。
     シードの直接参照のうち台帳に無いファイルがあれば、`doc-targets --only seed-direct` と
     `assemble-spo --layout-only --only seed-direct` が追加下調べの対象と書き先を決める（下調べのエージェントが資料を書く）。
     `verify-sweep` が検証スイープを行い、`assemble-spo` が SPO のスクリプトが書く欄・モジュール資料の「波紋調査の結果」・
     版の確定を書いて、document agent に渡す ENTRY_POINTS と入力の指紋を返す。document agent の成功の後に
     `commit-assemble-inputs` が指紋を保存する。波紋調査を行わなかった repo は `assemble-spo --no-ripple` だけを使う

Usage:
  python3 specout_bfs.py write-seed-candidates --input SEED_INPUT_JSON --out CANDIDATES_MD
      --unsupported-out UNSUPPORTED_JSON
      (--append | [--template TEMPLATE_MD --cr CR --repo REPO [--stale-ref FILE]])
  python3 specout_bfs.py seed-preview --seed-candidates CANDIDATES_MD --repo-path REPO_PATH
      [--exclude PATTERNS] [--include-ext EXTS] [--backend NAME] [--hit-filter MODE]
      [--max-files-per-module N] [--ledger LEDGER_MD] [--wave-hit-budget N] [--slice-engine slice|rule]
  python3 specout_bfs.py init --path STATE_JSON --repo-path REPO_PATH --discovery-log LOG_MD
      (--seed-candidates CANDIDATES_MD | --symbols SYMS [--entry-point-symbols SYMS])
      --today TODAY --cr CR --repo REPO [--exclude PATTERNS] [--include-ext EXTS]
      [--max-wave N] [--max-files-per-module N] [--module-catalog FILE]
      [--unsupported-patterns JSON] [--wave-hit-budget N] [--llm-hit-budget N]
      [--slice-engine slice|rule] [--probe-file PROBE_JSON] [--use-probe-warning]
      [--slice-ignore-calls-file TXT] [--slice-h-as auto|c|cpp]
  python3 specout_bfs.py search --path STATE_JSON (--hits-out HITS_JSON | --hits-dir DIR)
      [--chunk-size N]
  python3 specout_bfs.py commit-wave --path STATE_JSON --hits HITS_JSON --classification CLASS_JSON --today TODAY
      [--chunk-count N] [--batch-count N] [--parallelism N] [--chunk-mtime-min EPOCH]
      [--unsupported-patterns FILE]
  python3 specout_bfs.py status --path STATE_JSON [--brief]
  python3 specout_bfs.py extend --path STATE_JSON --max-wave N --today TODAY
  python3 specout_bfs.py switch-engine --path STATE_JSON --to rule --today TODAY
  python3 specout_bfs.py merge-frontier --path STATE_JSON --symbols SYMS [--entry-point-symbols SYMS]
      [--summaries-file SUMMARIES_JSON] [--as-seed-globals] [--reset-wave-origin]
  python3 specout_bfs.py re-discover --path STATE_JSON --symbols SYMS [--entry-point-symbols SYMS] --today TODAY
  python3 specout_bfs.py set-state --path STATE_JSON --state STATE
  python3 specout_bfs.py import --path STATE_JSON --from CHECKPOINT_MD
  python3 specout_bfs.py doc-targets --path STATE_JSON [--ledger LEDGER_MD] [--memo MEMO_MD]
      [--module-assignments JSON] [--auto-assign] [--gap-reviewed GAP_MD] [--only seed-direct --max-files N]
  python3 specout_bfs.py ripple-summary --path STATE_JSON --discovery-log LOG_MD [--ledger LEDGER_MD]
      [--module-assignments JSON] [--gap-reviewed GAP_MD] [--max-files N] --out SUMMARY_MD --json SUMMARY_JSON
      [--waves-dir DIR]
  python3 specout_bfs.py verify-sweep --path STATE_JSON --discovery-log LOG_MD
      [--exclude-patterns P] [--include-extensions E]
  python3 specout_bfs.py assemble-spo --path STATE_JSON --output-dir OUTPUT_DIR
      --summary-template TEMPLATE --module-template TEMPLATE --max-files-per-module N
      [--detail-level standard|brief] --cr CR --today TODAY
      (--layout-only --only seed-direct --max-files N
       | --summary-json SUMMARY_JSON [--sweep-json SWEEP_JSON] --crs-file CRS_MD --entry-points EPS
         [--propagation-log LOG_JSON] [--metrics METRICS_JSONL])
  python3 specout_bfs.py assemble-spo --no-ripple --repo-path REPO_PATH --repo REPO --output-dir OUTPUT_DIR
      --summary-template TEMPLATE --module-template TEMPLATE --max-files-per-module N
      [--detail-level standard|brief] --cr CR --today TODAY --crs-file CRS_MD --entry-points EPS
      [--propagation-log LOG_JSON] [--metrics METRICS_JSONL]
  python3 specout_bfs.py commit-assemble-inputs --output-dir OUTPUT_DIR --fingerprint SHA256
  python3 specout_bfs.py prelim-metrics --path STATE_JSON --seed-candidates CANDIDATES_MD
      [--ledger LEDGER_MD] --seed-gate true|false

Output: 成功時は stdout に JSON 1オブジェクト（{"ok": true, ...}）。
        失敗時は exit code 非0 + stderr にメッセージ。
        search は投入シンボルが0件（1波もコミットしていない状態で frontier が空）のときは終了コード 4
        （EXIT_EMPTY_SEED）、シード要約の取り込みが済んでいない（seed_summary_pending が空でない）ときは
        終了コード 6（EXIT_SEED_SUMMARY_PENDING）で終了する。
        init は --seed-candidates と --symbols / --entry-point-symbols の併用で終了コード 2（EXIT_USAGE）。
        seed-preview・init・doc-targets・prelim-metrics は候補表・台帳・観察メモの書式不正と台帳の整合違反で
        終了コード 1（stderr に原因ファイルのパスを含める）。doc-targets は --module-assignments の組の不正で
        終了コード 5（EXIT_ASSIGNMENTS_INVALID）。doc-targets --auto-assign は自動で付けたモジュール名が
        異なるディレクトリで衝突したとき終了コード 1。verify-sweep は未記録ヒットがあるとき終了コード 7
        （EXIT_UNRECORDED_SWEEP。specout_verify_counts.py の件数不一致〔3〕とは別の値）。
        ripple-summary はどのモジュールにも属さない確定ファイルがあるとき、doc-targets・ripple-summary・assemble-spo は
        追加下調べの判断の記録（prelim-gap-reviewed.md）の書式不正で終了コード 1。assemble-spo・doc-targets は
        引数の組み合わせの誤りで終了コード 2（EXIT_USAGE）。
"""

import argparse
import collections
import datetime
import fnmatch
import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import time
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specout_log_values as LV  # noqa: E402
import specout_macros as MAC  # noqa: E402

VALID_STATES = {"in-progress", "complete"}
MEDIUM_RE = re.compile(r"^(?P<symbol>.+)\[MEDIUM:(?P<scope>.+)\]$")
# そのファイルの中でしか参照できない名前（static 等）。MEDIUM（LLM 分類の「引数として伝播」）とは別のエントリ。
FILE_RE = re.compile(r"^(?P<symbol>.+)\[FILE:(?P<scope>.+)\]$")
# C++ のメソッド・メンバー変数（クラス ClassName のもの）。C++ として解析するファイルを素の名前で検索し、判定でクラスを絞る。
CLASS_RE = re.compile(r"^(?P<symbol>[^\[\]]+)\[CLASS:(?P<scope>[A-Za-z_][A-Za-z0-9_]*)\]$")
SCOPE_MEDIUM = "MEDIUM"
SCOPE_FILE = "FILE"
SCOPE_CLASS = "CLASS"
# symbol_kinds の値のうち値シンボル（関数でないもの）。variable は §ヒット側の除外（member-name 等）の対象。
VALUE_KINDS = {"value", "variable", "macro"}
# 同じ素名に複数の種類が付いたときの優先順位（左ほど優先。variable 以外が混ざれば変数向けの除外を適用しない）。
KIND_PRIORITY = ("function", "value", "macro", "variable")
CLASS_VALUES = {
    "false-positive",
    "propagation-direct",
    "propagation-argument",
    "propagation-return",
    "out-of-scope-discard",
}
CONFIDENCE_FOR_CLASS = {
    "false-positive": "—",
    "propagation-direct": "HIGH",
    "propagation-argument": "MEDIUM",
    "propagation-return": "HIGH",
    "out-of-scope-discard": "—",
}
NO_PROPAGATION_CLASSES = {"false-positive", "out-of-scope-discard"}
CONFIDENCE_RANK = {"HIGH": 2, "MEDIUM": 1}

# PLAN-20260806 Phase 3 Stage 1 §4.5(d): classify_wall_ms は「search → commit-wave 間の壁時計」であり
# LLM の実行時間そのものではなくその上界（規定外の手動操作では人の待ち時間が丸ごと混入する）。
# 閾値超過は汚染の疑いとして metrics に併記し、ゲート判定の集計から除外できるようにする。
# 暫定値であり実測分布が得られた時点で見直す（固定閾値ではなく中央値の N 倍という相対基準も選択肢）。
CLASSIFY_WALL_MS_SUSPECT_THRESHOLD_MS = 1800000  # 30分

# PLAN-20260806 Phase 3 Stage 2 §4.5(e): discovery-log ヘッダ部の見出し文字列。
# `_discovery_log_header` の生成側と `_append_unsupported_patterns` の挿入側で同一定数を参照し、
# 見出し文言のドリフトによる「セクション不在（no-op）」の再発を防ぐ。
GREP_UNSUPPORTED_HEADING = "## grep未対応パターン（手動確認必要）"

# Wave 0 ブロックの境界検出（`_wave0_block_span`）と `_upsert_confirmed_files_section` が共有する見出し。
CONFIRMED_FILES_HEADING = "## 確定した波及ファイル一覧（Documentation チェックリスト）"
# ヒットがすべて false-positive だったファイルの節。確定ファイルの節の後ろに置く（`_wave0_block_span` の境界より後）。
FALSE_POSITIVE_FILES_HEADING = "## 判定で関係なしとしたファイル（false-positive のみ）"
WAVE_HEADING_RE = re.compile(r"^## Wave \d+", re.MULTILINE)

# ⚠️ この見出しは絶対に `## Wave ` で始めてはならない。
# `WAVE_HEADING_RE`（`^## Wave \d+`・行末アンカーなし）と `_wave0_block_span()` の
# `"## Wave 0"` 文字列検索はいずれも前方一致であり、`## Wave 0 未ヒット…` のような
# 見出しを Wave セクションとして誤検出して Wave 0 ブロックの境界を壊す
# （`_wave0_block_span` は `cmd_funcmap_counts` が使う）。
# 本書式は `## ` の直後が `未` であるため、`"## Wave 0"` を部分文字列として含まない。
ZERO_HIT_HEADING_FMT = "## 未ヒット投入シンボル（Wave {n}）"
ZERO_HIT_HEADING_PREFIX = "## 未ヒット投入シンボル（Wave "

# この見出しは `## Wave ` で始めてはならない（WAVE_HEADING_RE と _wave0_block_span の前方一致に誤検出されるため）。
NOISY_SEED_HEADING_FMT = "## ヒット過多の投入シンボル（Wave {n}）"

# search が「投入シンボルが0件」を呼び出し元へ区別して伝えるための終了コード。
EXIT_EMPTY_SEED = 4
# search が「シード要約の取り込みが済んでいない（seed_summary_pending が空でない）」を伝える終了コード。
EXIT_SEED_SUMMARY_PENDING = 6

# この見出しは `## Wave ` で始めてはならない（WAVE_HEADING_RE と _wave0_block_span の前方一致に誤検出されるため）。
BUDGET_SEED_HEADING_FMT = "## 予算で打ち切った投入シンボル（Wave {n}）"
REVISIT_HEADING_FMT = "## 要約の拡大による再訪（Wave {n}）"
TRUNCATION_HEADING = "## 打ち切り記録"
LEGEND_HEADING = "## 凡例"
ENGINE_SWITCH_HEADING_FMT = "## 判定エンジンの切り替え（Wave {n} から rule）"
EXTEND_HEADING_FMT = "## 探索の延長（上限 {old} → {new}）"
SEARCH_SETTINGS_HEADING = "## 探索設定"

# 判定エンジン（specout_slice.py）。slice は tree-sitter、rule は標準ライブラリのみ。
SLICE_ENGINES = ("slice", "rule")
# .h を C++ として解析する手がかりになる拡張子（SPECOUT_SLICE_H_AS: auto）。言語が cpp の拡張子（specout_macros）。
CPP_SOURCE_EXTS = MAC.CPP_EXTS
# 識別子索引で引けるシンボル（識別子・識別子2つを `.` でつないだ root.field）。
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ROOT_FIELD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")

# 投入シンボルの由来テーブル。全9行は init --seed-candidates が候補表から書き、ENTRY_POINTS 行は
# merge-frontier / re-discover が和集合で追記する（PLAN-20260927-specout-prelim-phase）。セル書式をここで固定する:
# 各シンボルをバッククォートで囲み `, ` で連結する。値が無い場合は空セル記号を置く。
ORIGIN_HEADING = "## 投入シンボルの由来"
ORIGIN_ROW_ENTRY_POINTS = "ENTRY_POINTS（人が明示指定）"
ORIGIN_ROW_CRS = "CRS SP項目"
ORIGIN_ROW_PRELIM = "下調べ（Step A-Prelim）"
ORIGIN_ROW_CODE = "母体コードから補完"
ORIGIN_ROW_INHERIT = "継承展開"
ORIGIN_ROW_HUMAN_ADDED = "確認時に人が追加"
ORIGIN_ROW_HUMAN_REMOVED = "確認時に人が除外"
ORIGIN_ROW_UNRESOLVED_EP = "解決できなかった ENTRY_POINT"
ORIGIN_ROW_UNKNOWN = "シンボル不明"
ORIGIN_EMPTY_CELL = "（指定なし）"   # ENTRY_POINTS 行専用（人が指定しなかった）
ORIGIN_NONE_CELL = "（なし）"        # ENTRY_POINTS 行以外の8行
ORIGIN_UNKNOWN_CELL = "（特定できず）"  # シンボル不明行（識別子を特定できなかった振る舞いがある）
# 表の行順は ENTRY_POINTS 行 → ORIGIN_OTHER_ROWS の順（テンプレートの由来テーブルと一致させる）。
ORIGIN_OTHER_ROWS = (ORIGIN_ROW_CRS, ORIGIN_ROW_PRELIM, ORIGIN_ROW_CODE, ORIGIN_ROW_INHERIT,
                     ORIGIN_ROW_HUMAN_ADDED, ORIGIN_ROW_HUMAN_REMOVED, ORIGIN_ROW_UNRESOLVED_EP,
                     ORIGIN_ROW_UNKNOWN)

# シード候補表（work/seed-candidates.md）の書式。seed-preview・init・prelim-metrics が共有する。
SEED_SECTION_CANDIDATES = "## 候補"
SEED_SECTION_UNRESOLVED_EP = "## 解決できなかった ENTRY_POINT"
SEED_SECTION_UNKNOWN = "## 識別子を特定できなかった振る舞い"
SEED_CANDIDATE_COLUMNS = ("採否", "シンボル", "由来", "根拠", "ヒット（ファイル数）", "警告", "除外理由")
SEED_UNRESOLVED_EP_COLUMNS = ("指定値", "理由")
SEED_UNKNOWN_COLUMNS = ("振る舞い（CRS）", "調べた範囲")
SEED_ADOPTED = "☑"
SEED_REJECTED = "☐"
SEED_ORIGIN_ENTRY_POINTS = "ENTRY_POINTS"
SEED_ORIGIN_CRS = "CRS SP項目"
SEED_ORIGIN_PRELIM = "下調べ"
SEED_ORIGIN_CODE = "母体コードから補完"
SEED_ORIGIN_INHERIT = "継承展開"
SEED_ORIGIN_HUMAN_ADDED = "人が追加"
SEED_ORIGINS = (SEED_ORIGIN_ENTRY_POINTS, SEED_ORIGIN_CRS, SEED_ORIGIN_PRELIM, SEED_ORIGIN_CODE,
                SEED_ORIGIN_INHERIT, SEED_ORIGIN_HUMAN_ADDED)
SEED_WARN_ZERO_HIT = "未ヒット"
SEED_WARN_ZERO_AFTER_FILTER = "フィルタ後0件"
SEED_WARN_NOISY = "ヒット過多"
SEED_WARN_OVER_BUDGET = "予算超過"
SEED_WARN_SEP = "・"
# seed-preview が候補表の「## 候補」の表の直前に書く注記行の先頭（再試算で置き換える）。
SEED_TOTAL_NOTE_PREFIXES = ("> 採用シンボルの合計ヒット数:", "> ⚠️ 採用シンボルの合計ヒット数:")

# 文書化済みファイル台帳（work/documented-files.md）と累積観察メモ（work/observation-memo.md）の書式。
# seed-preview・doc-targets・prelim-metrics が同じ解析関数を共有する。
LEDGER_COLUMNS = ("ファイルパス", "モジュール", "モジュールディレクトリ", "工程", "関係する振る舞い（CRS）")
LEDGER_PHASE_PRELIM = "下調べ"
LEDGER_PHASE_ADDITIONAL = "追加下調べ"
OBS_MEMO_SECTIONS = ("## 外部副作用", "## テスト可能性", "## 非機能特性", "## 入力源", "## 制約照合")
OBS_MEMO_FILE_COLUMN = "ファイルパス"
MODULE_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")

# doc-targets が module-assignments.json の組の不正を、台帳・観察メモ由来の exit 1 と区別して返す終了コード。
EXIT_ASSIGNMENTS_INVALID = 5
# init の --seed-candidates と --symbols / --entry-point-symbols の併用（argparse の使用法エラーと同じ値）。
EXIT_USAGE = 2


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def _file_mtime(path: Path):
    """ファイルの mtime（エポック秒）。取得できない場合は None を返す。

    PLAN-20260806 Phase 3 Stage 1 §4.5(d) の「再利用波の判定」専用。計測専用の値であり
    correctness に関与しないため、取得失敗を例外として伝播させず判定不能（None）に落とす。
    """
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _drop_classify_timer(data: dict) -> None:
    """PLAN-20260806 Phase 3 Stage 1 §4.5(c): 分類区間の開始時刻2キーを state から取り除く。

    用途は2つ。(1) commit-wave の消費後破棄、(2) search を経ない状態遷移
    （re-discover / extend / set-state / 波数上限の早期 return）の後に古い開始時刻が
    残らないようにする二次防御。一次防御は commit-wave 側の波一致検証（classify_started_wave == wave）。
    """
    data.pop("classify_started_at", None)
    data.pop("classify_started_wave", None)


def _md_cell(value) -> str:
    r"""Markdown テーブルのセル値をエスケープする。

    セル内の生の `|` は列区切りと解釈され、テーブルの列数を壊す。
    ソースコード（C のビット OR `a |= b`）や正規表現の選択（`(A|B|C)`）は
    discovery-log.md のセルへ日常的に入るため、書き出し側で必ずエスケープする。
    改行も同様にセルを壊すため空白へ畳む。

    前提（読み側 _split_row との契約）: 呼び出し側は列区切りを必ず ` | ` と
    空白でパディングする。セル値の末尾が `\` の場合でも、区切りの `|` の直前は
    空白になるため、読み側の「直前が `\` でない `|` を区切りとみなす」判定が
    誤らない。この前提を崩す（パディング無しで連結する）書き出しを追加しないこと。
    """
    s = "" if value is None else str(value)
    return s.replace("|", r"\|").replace("\n", " ").replace("\r", " ")


def _split_row(line: str) -> list:
    r"""Markdown テーブル行をセルへ分割する（`_md_cell` の逆変換）。

    `specout_verify_counts.py` の同名関数と同一規約：直前が `\` でない `|` のみを区切りとみなし、
    分割後にエスケープを戻す。PLAN-20260913 で `funcmap-counts`（discovery-log.md の Wave 0
    ヒットテーブルの読み取り）用に導入。
    """
    if "|" not in line:
        return []
    cells = re.split(r"(?<!\\)\|", line)[1:-1]
    return [c.strip().replace(r"\|", "|") for c in cells]


def _split_csv(raw: str) -> list:
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


def _parse_entry(entry: str):
    """エントリ文字列を (素名, スコープ) にする。スコープは MEDIUM・FILE ではファイル、CLASS ではクラス名。"""
    m = MEDIUM_RE.match(entry) or FILE_RE.match(entry) or CLASS_RE.match(entry)
    if m:
        return m.group("symbol"), m.group("scope")
    return entry, None


def _entry_scope_kind(entry: str):
    """エントリのスコープの種別（`SCOPE_MEDIUM` / `SCOPE_FILE` / `SCOPE_CLASS` / None＝修飾なし）。"""
    if MEDIUM_RE.match(entry):
        return SCOPE_MEDIUM
    if FILE_RE.match(entry):
        return SCOPE_FILE
    if CLASS_RE.match(entry):
        return SCOPE_CLASS
    return None


def _is_qualified_entry(entry: str) -> bool:
    return bool(MEDIUM_RE.match(entry) or FILE_RE.match(entry) or CLASS_RE.match(entry))


def summary_key(entry: str) -> str:
    """要約（symbol_summaries・next_symbol_summaries 等）と種類（symbol_kinds）の表の鍵。`[CLASS:…]` のエントリは
    エントリ文字列、それ以外（修飾なし・`[FILE:…]`・`[MEDIUM:…]`）は素名。specout_slice.py もこの関数を使う。"""
    if CLASS_RE.match(entry):
        return entry
    return _parse_entry(entry)[0]


def resolve_h_as(value: str, repo_path: str, exclude_patterns: list) -> str:
    """SPECOUT_SLICE_H_AS（`.h` の解析言語）の解決。`auto` は C++ のソースがあれば `cpp`、無ければ `c`。"""
    value = (value or "auto").strip()
    if value != "auto":
        return value
    return "cpp" if any(f.endswith(CPP_SOURCE_EXTS) for f in list_repo_files(repo_path, exclude_patterns)) else "c"


def is_cpp_file(rel: str, h_as: str) -> bool:
    """`[CLASS:…]` のエントリを検索するファイル（C++ として解析するファイル）か。"""
    return MAC.c_cxx_lang(rel, h_as) == "cpp"


def _format_entry(symbol: str, scope, kind: str = SCOPE_MEDIUM) -> str:
    return f"{symbol}[{kind}:{scope}]" if scope else symbol


def _validate_frontier_format(symbols: list) -> None:
    for s in symbols:
        if "[" in s or "]" in s:
            if not _is_qualified_entry(s):
                _err(f"Frontier のシンボル形式が不正です: {s!r}"
                     "（MEDIUM形式は symbol[MEDIUM:filepath]、FILE形式は symbol[FILE:filepath]、"
                     "CLASS形式は symbol[CLASS:ClassName]）")


def _kind_rank(kind) -> int:
    return KIND_PRIORITY.index(kind) if kind in KIND_PRIORITY else len(KIND_PRIORITY)


def _raise_identity(identity: dict, entry: str, value: str) -> None:
    """entry_identity を更新する。resolved は下げない。"""
    if value == LV.IDENTITY_RESOLVED:
        identity[entry] = LV.IDENTITY_RESOLVED
    else:
        identity.setdefault(entry, LV.IDENTITY_NAME_ONLY)


def _set_input_identity(data: dict, symbols: list, resolved: set, name_only: set = frozenset()) -> None:
    """外から入るエントリの同一性: `resolved` に入るものは resolved（`name_only` に入るものを除く）、
    それ以外は既存の値を保ち、無ければ name-only（由来が分からないものを resolved にしない）。"""
    identity = data.setdefault("entry_identity", {})
    for e in symbols:
        _raise_identity(identity, e, LV.IDENTITY_RESOLVED if (e in resolved and e not in name_only)
                        else LV.IDENTITY_NAME_ONLY)


def escape_symbol(sym: str) -> str:
    """Phase 0「シンボル名の正規表現エスケープ」規則。既にエスケープ済みの `\\.` は二重エスケープしない。"""
    specials = set(".+*?[](){}|^$\\")
    out = []
    i = 0
    while i < len(sym):
        c = sym[i]
        if c == "\\" and i + 1 < len(sym) and sym[i + 1] in specials:
            out.append(sym[i : i + 2])
            i += 2
            continue
        if c in specials:
            out.append("\\" + c)
        else:
            out.append(c)
        i += 1
    return "".join(out)


# 保守的事前フィルタ（PLAN-20260804 Phase 1b）用の行コメントマーカー表。
# コメントマーカーは「共通集合」ではなく拡張子から言語別に解決する（PLAN §3.2・指摘#10）。
# 理由: `#` は Python/Ruby/Shell では行コメントだが C/C++ では前処理指令（#define/#include/#ifdef）で
# 真の参照。共通集合に入れると silent に漏らす。曖昧さのない拡張子のみ登録し、未登録・曖昧拡張子
# （.m＝Objective-C(//)/Matlab(%) 等）は除外しない（安全側）。C/C++ 系は `//` のみで `#` を登録しない。
LINE_COMMENT_BY_EXT = {
    ".py": ("#",), ".rb": ("#",), ".sh": ("#",), ".bash": ("#",),
    ".yaml": ("#",), ".yml": ("#",), ".toml": ("#",),
    ".c": ("//",), ".h": ("//",), ".cpp": ("//",), ".hpp": ("//",), ".cc": ("//",),
    ".java": ("//",), ".js": ("//",), ".ts": ("//",), ".go": ("//",),
    ".rs": ("//",), ".swift": ("//",), ".kt": ("//",), ".scala": ("//",),
    ".sql": ("--",), ".lua": ("--",), ".hs": ("--",),
    ".lisp": (";",), ".el": (";",), ".clj": (";",),
    ".tex": ("%",),
}


def _is_pure_line_comment(content: str, symbol: str, ext: str) -> bool:
    """`content`（grep/rg の単一行）が「行全体が行コメントで、シンボルがコメント本文中にのみ現れる」
    かを判定する（PLAN-20260804 Phase 1b）。コメントマーカーは拡張子から言語別に解決し、未登録・
    曖昧拡張子は常に False（除外しない＝安全側）。ブロックコメント/文字列リテラルは単一行からは
    確実に判定できないため対象外（初期スコープ外）。"""
    markers = LINE_COMMENT_BY_EXT.get(ext)
    if not markers:
        return False
    stripped = content.lstrip()
    if not stripped.startswith(markers):
        return False
    marker_pos = min((content.find(m) for m in markers if m in content), default=-1)
    code_part = content[:marker_pos] if marker_pos >= 0 else ""
    # マーカー以前（コード部）にシンボルが現れないこと＝コメント本文中のみ
    return not _symbol_regex(symbol).search(code_part)


def _is_word_char(ch: str) -> bool:
    """単語文字（[A-Za-z0-9_]）なら True。`\\b` の有無を決めるために使う。"""
    return ch.isalnum() or ch == "_"


def _word_boundary(sym: str) -> str:
    """語境界付き単一シンボル正規表現（rg patternfile の1行に対応）。
    先頭・末尾が非単語文字の場合はその側の `\\b` を省略し、無音 0 ヒットを防ぐ。
    """
    esc = escape_symbol(sym)
    prefix = r"\b" if _is_word_char(sym[0]) else ""
    suffix = r"\b" if _is_word_char(sym[-1]) else ""
    return prefix + esc + suffix


def _grep_symbol_pattern(sym: str) -> str:
    """grep -E / rg に渡す1シンボル分のパターン。

    `root.field` 形式は `root.field` / `root->field`（間の空白を許す）に一致する
    `\\broot[[:space:]]*(\\.|->)[[:space:]]*field\\b` にする（索引の `_FIELD_PAIR_RE` と同じ行に一致する）。
    それ以外は `_word_boundary` と同じ。
    戻り値は POSIX の文字クラスを含むため、Python の `re` には渡さない（Python 内の判定は `_symbol_regex`）。
    """
    if ROOT_FIELD_RE.match(sym):
        root, field = sym.split(".", 1)
        return (r"\b" + escape_symbol(root) + r"[[:space:]]*(\.|->)[[:space:]]*" + escape_symbol(field) + r"\b")
    return _word_boundary(sym)


def _grep_compound(syms: list) -> str:
    """複数シンボルを1本にまとめた grep 形式の複合パターン `(A|B|C)`。
    各シンボルのパターンは `_grep_symbol_pattern` で個別に解決する。
    """
    return "(" + "|".join(_grep_symbol_pattern(s) for s in syms) + ")"


def _grep_compound_repr(syms: list) -> str:
    """複合パターンの人間可読な表示形式（ログ・pattern_repr 用）。

    全シンボルが単語文字（[A-Za-z0-9_]）で囲まれている場合は旧形式
    `\\b(alpha|beta)\\b` を返し、過去の discovery-log 表記との一貫性を保つ。
    非単語文字端シンボルや `root.field` 形式のシンボルが含まれる場合は、各シンボルのパターンを個別に表現した
    `(A|B|C)` を返し、実際の一致の範囲を表す。
    単一シンボルの場合はグループ化しない。
    """
    if not syms:
        return "()"
    if len(syms) == 1:
        return _grep_symbol_pattern(syms[0])
    # 全シンボルが両端単語文字で root.field を含まないなら旧形式を維持
    if all(_is_word_char(s[0]) and _is_word_char(s[-1]) and not ROOT_FIELD_RE.match(s) for s in syms):
        return r"\b(" + "|".join(escape_symbol(s) for s in syms) + r")\b"
    # それ以外は個別表示
    return "(" + "|".join(_grep_symbol_pattern(s) for s in syms) + ")"


# ---------------------------------------------------------------------------
# State load/save
# ---------------------------------------------------------------------------

def _default_state() -> dict:
    return {
        "state": "in-progress",
        "repo_path": "",
        "discovery_log": "",
        "cr": "",
        "repo": "",
        "backend": "auto",
        "backend_effective": "",
        "backend_fallback_logged": False,
        "current_wave": 0,
        "last_completed_wave": -1,
        "wave_write_complete": True,
        "visited": [],
        "frontier": [],
        "low_priority_frontier": [],
        "confirmed_file_count": 0,
        "exclude_patterns": [],
        "include_extensions": [],
        # 起点の波（wave_origin）から数えて調べる波の数。current_wave - wave_origin が上限に達した search で
        # 残りを打ち切り記録に残して complete にする。
        "max_wave_depth": 6,
        "wave_origin": 0,
        "max_files_per_module": 10,
        "module_catalog_file": "",
        "module_priority_map": {},
        "module_priority_computed": False,
        "module_priority_mode": "",  # "catalog" / "simple"（PLAN-20260806 Phase 2B）
        "symbol_module": {},
        "symbol_origin_map": {},
        "high_noise_symbols": [],
        "confirmed_files": {},
        # PLAN-20260804 Phase 1a: 分類済みロケーション（cross-wave dedup 用）。
        # キー形式は "{symbol}\x00{file}\x00{line_no}\x00{scope_class}"（scope_class は HIGH または MEDIUM スコープ文字列）。
        # JSON にはソート済みリストで永続化し、in-memory では set として扱う。
        "classified_locations": [],
        # PLAN-20260804 Phase 1b: 保守的事前フィルタのモード（conservative / off）。
        "hit_filter": "conservative",
        # PLAN-20260829: classifier の out-of-scope-discard 判定用スコープ要約（CRS 全文の代替）。
        # init 時に --scope-summary-file の内容を1回だけ保存し、search が毎波・毎チャンクへ複製配布する
        # （known_symbols と同一の配布パターン）。
        "scope_summary": "",
        # 人が明示指定した投入シンボル（init / merge-frontier / re-discover の --entry-point-symbols）。
        # search の未ヒット投入シンボル検出で、wave 1 以降の検出対象を伝播由来の frontier から区別する。
        "entry_point_symbols": [],
        # 1波の予算（dedup・フィルタの後のヒット数。0 は無制限）と、LLM 分類に回すヒットの上限。
        "wave_hit_budget": 10000,
        "llm_hit_budget": 160,
        # 判定エンジン（slice / rule）と、その判定に使う設定。init の値で固定する（switch-engine を除く）。
        "slice_engine": "rule",
        "engine_exts": [],
        "slice_ignore_calls": "",
        "slice_h_as": "c",
        # 打ち切り記録 [{wave, reason, symbol, hits, from?}]（「## 打ち切り記録」の単一情報源）。
        "truncated": [],
        # 関数シンボルの要約 {symbol: {returns, out, globals, side, closure}} と、シンボルが関数か値か。
        "symbol_summaries": {},
        "symbol_kinds": {},
        # シード関数が書くグローバル（シードの診断に混ぜない）と、要約の取り込みが済んでいないシード。
        "seed_globals": [],
        "seed_summary_pending": [],
        # シードが偽陽性・out-of-scope-discard 以外でヒットしたファイル（CR の規模の判定に使う）と、
        # そのファイルごとのヒット行数（追加下調べの対象を上限で絞るときの順序に使う）。
        "seed_direct_files": [],
        "seed_direct_hits": {},
        # ヒットがすべて false-positive だったため確定ファイルにしなかったファイル（{ファイル: 最初に現れた波}）。
        "false_positive_files": {},
        # エントリの同一性 {エントリ: resolved | name-only}（値の無いエントリは name-only とみなす）。
        "entry_identity": {},
    }


def _md_path_for(json_path: Path) -> Path:
    return json_path.with_suffix(".md") if json_path.suffix == ".json" else json_path.parent / "checkpoint.md"


def _render_md(data: dict) -> str:
    lines = [
        "# BFS Checkpoint",
        "",
        "> このファイルは `specout_bfs.py` が `bfs-state.json` から生成する人可読ビューです。",
        "> 直接編集せず `merge-frontier`/`re-discover`/`extend`/`switch-engine` 等の専用サブコマンドを使用してください。",
        "",
        f"**状態：** {data['state']}",
        f"**現在 Wave 番号：** {data['current_wave']}",
        f"**最終完了 Wave：** {data['last_completed_wave']}",
        f"**Wave 書き込み完了：** {'true' if data['wave_write_complete'] else 'false'}",
        f"**確定ファイル数：** {data['confirmed_file_count']}",
        f"**除外パターン：** {','.join(data['exclude_patterns'])}",
        f"**投入シンボル（ENTRY_POINTS）：** {','.join(data.get('entry_point_symbols') or [])}",
        f"**最大波数：** {data.get('max_wave_depth', 6)}",
        f"**探索の起点の波：** {data.get('wave_origin', 0)}",
        f"**1波の予算：** {data.get('wave_hit_budget', 0)}",
        f"**LLM 分類の上限：** {data.get('llm_hit_budget', 0)}",
        f"**判定エンジン：** {data.get('slice_engine') or 'rule'}",
        f"**判定エンジンの対象拡張子：** {','.join(data.get('engine_exts') or [])}",
        f"**影響なしとみなす呼び出し（参考表示。import は slice-ignore-calls.txt から復元）：** "
        f"{data.get('slice_ignore_calls') or ''}",
        f"**.h の解析言語：** {data.get('slice_h_as') or 'c'}",
        f"**シードのグローバル：** {','.join(data.get('seed_globals') or [])}",
        f"**シード要約の取り込み待ち：** {','.join(data.get('seed_summary_pending') or [])}",
        f"**打ち切り記録の件数：** {len(data.get('truncated') or [])}",
        f"**シードの直接参照ファイル数：** {len(data.get('seed_direct_files') or [])}",
        f"**判定で関係なしとしたファイル数：** {len(data.get('false_positive_files') or {})}",
        f"**名前の一致のみの確定ファイル数：** {_name_only_file_count(data)}",
        "",
        "## Visited",
        "",
    ]
    lines.extend(data["visited"] if data["visited"] else ["(なし)"])
    lines.append("")
    lines.append("## Frontier")
    lines.append("")
    lines.extend(data["frontier"] if data["frontier"] else ["(なし)"])
    lines.append("")
    if data.get("low_priority_frontier"):
        lines.append("## Low Priority Frontier（MODULE_PRIORITY_LOW 退避分）")
        lines.append("")
        lines.extend(data["low_priority_frontier"])
        lines.append("")
    return "\n".join(lines)


def _name_only_file_count(data: dict) -> int:
    return sum(1 for info in (data.get("confirmed_files") or {}).values()
               if info.get("identity") != LV.IDENTITY_RESOLVED)


def _write_state(json_path: Path, data: dict) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    md_path = _md_path_for(json_path)
    with open(md_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(_render_md(data))


def _load_state(json_path: Path) -> dict:
    if not json_path.exists():
        _err(f"bfs-state.json が見つかりません: {json_path}（init を実行してください）")
    return json.loads(json_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# discovery-log.md rendering
# ---------------------------------------------------------------------------

def _format_origin_cell(symbols: list, empty: str) -> str:
    return ", ".join(f"`{_md_cell(s)}`" for s in symbols) if symbols else empty


def _origin_section_skeleton(entry_point_symbols: list, filled: dict = None) -> str:
    """`ORIGIN_HEADING` セクション（9行）。ENTRY_POINTS 行は `entry_point_symbols` で埋め、他の行は
    `ORIGIN_NONE_CELL` とする。`filled`（{行名: (シンボル欄, 備考欄)}。`_origin_rows_from_seeds` の戻り値）を
    渡すと、その行を上書きする（init --seed-candidates）。"""
    cells = {ORIGIN_ROW_ENTRY_POINTS: (_format_origin_cell(entry_point_symbols, ORIGIN_EMPTY_CELL), "—")}
    cells.update({name: (ORIGIN_NONE_CELL, "—") for name in ORIGIN_OTHER_ROWS})
    cells.update(filled or {})
    rows = [f"| {name} | {cells[name][0]} | {cells[name][1]} |"
            for name in (ORIGIN_ROW_ENTRY_POINTS,) + ORIGIN_OTHER_ROWS]
    return (f"{ORIGIN_HEADING}\n\n| 由来 | シンボル | 備考 |\n|---|---|---|\n"
            + "\n".join(rows) + "\n\n")


LEGEND_BODY = """> 本ログの表のセルに書く種別・派生元・判定の値の意味。

| 箇所 | 値 | 意味 |
|---|---|---|
| ヒット表「伝播種別」 | `false-positive` | 偽陽性（コメント・文字列の中・goto のラベル名・プロトタイプ宣言の引数名等）。伝播しない。この判定だけのファイルは確定ファイルにせず、「## 判定で関係なしとしたファイル（false-positive のみ）」に記録する。スライス判定の偽陽性のうち、名前が同じだけの別の名前と構文・言語の規則で決まったものは判定の注記（classification の note）に理由を書く: `member-name`＝構造体のメンバー名・属性名（C と Python。変数のシンボル）／`shadowed-local`＝同じ名前のローカル変数・引数のある関数の中（変数のシンボル）／`param-name`＝引数の宣言子の名前（変数のシンボル）／`other-static`＝ヒットしたファイル自身の static 等（内部リンケージ）の同じ名前（修飾なしのエントリ。シードを除く）／`other-class`＝C++ の `name[CLASS:X]` のエントリで、受け手のクラスが X と関係の無いクラス（兄弟・無関係のクラス・リポジトリの外の型）と決まった出現、またはメソッドのエントリで変数・引数の名前（宣言子・同じ名前のローカル変数・呼ばずに参照するデータメンバー）の出現 |
| ヒット表「伝播種別」 | `propagation-direct` | LLM 分類: 制御フロー・データフロー（含む関数・代入先等を次の波で追う） |
| ヒット表「伝播種別」 | `propagation-argument` | LLM 分類: 呼ばれる側の引数として伝播（スコープ限定で追う） |
| ヒット表「伝播種別」 | `propagation-return` | LLM 分類: 戻り値・外部公開として伝播 |
| ヒット表「伝播種別」 | `out-of-scope-discard` | LLM 分類: CR のスコープ外として廃棄 |
| ヒット表「伝播種別」 | `slice(escape=…)` | スライス判定: 影響が関数の外へ出る経路。`return`・`exception`・`out`（出力引数・this/self）・`heap`・`state`（static ローカル）・`unknown`（解析不能）・`closure` は呼び出し元（含む関数）を、`global` は書き込んだグローバル変数（`root.field`）の読み手を次の波で追う |
| ヒット表「伝播種別」 | `slice(file-scope=…)` | スライス判定: 関数の外のヒットから値を伝播させる。`macro-def`＝マクロ定義の本体（マクロ名を追う）／`global-init`＝グローバル変数の初期化子（変数名を追う）／`module/class-assign`＝Python のモジュール・クラス本体の代入（代入先を追う） |
| ヒット表「伝播種別」 | `slice(none=…)` | スライス判定: 伝播しない。`no-escape`＝影響が関数内で閉じる／`write-only`＝上書きされて読まれない／`self-def`＝関数の定義そのもの（宣言部）／`file-scope`＝関数の外の宣言／`neutralized-macro`＝構文解析の前に置き換えたマクロ（宣言を飾るマクロ・名前空間マクロ・空にした組のマクロ）自体の使用箇所（ファイルを確定し、次の波へは送らない） |
| ヒット表「伝播種別」 | `rule(enclosing)` | 規則判定: ヒット行を含む関数を次の波で追う |
| ヒット表「伝播種別」 | `rule(none=…)` | 規則判定: 伝播しない（`self-def`＝関数の宣言部／`file-scope`＝関数の外） |
| ヒット表「同一性」 | `resolved` | シードから名前の解決（static・`extern`・定義が1件。C++ の `name[CLASS:X]` は受け手のクラスが X・その派生クラス・virtual の基底クラスと決まった）で区別できた経路でたどり着いたヒット |
| ヒット表「同一性」 | `name-only` | 名前の一致のみ（同名の定義が複数・規則判定・LLM 分類・`extern` の見えない定義・受け手のクラスを決められない出現を経由した）。別物の可能性がある。到達は削除しない |
| ヒット表「同一性」 | `—` | 偽陽性 |
| ヒット表「派生元」 | `seed(X)` | その波でシードとして投入したシンボル X のヒット（第0波のシード・`--re-discover` で人が入れたシンボル） |
| ヒット表「派生元」 | `seed-global(X)` | シード関数が書くグローバル X のヒット（スライス判定の要約から求めた） |
| ヒット表「派生元」 | `W{n}-R{m}` | このシンボルを次の波へ送った前の波の行ID |
| ヒット表「派生元」 | `unknown-origin` | 派生元を特定できない（人が直接 frontier に加えた等） |
| 実行コマンド一覧「種別」 | `HIGH-compound` | 全域を検索する複合コマンド（スコープ〔ファイル〕を限定した検索の種別は確信度の値をそのまま書く） |
| 実行コマンド一覧「種別」 | `FILE` | `symbol[FILE:filepath]`（そのファイルの中でしか参照できない static 等の名前）を、そのファイルの中だけで検索するコマンド。確定ファイルの確信度は HIGH |
| 実行コマンド一覧「種別」 | `CLASS` | `symbol[CLASS:ClassName]`（C++ のメソッド・メンバー変数）を、C++ として解析するファイルで素の名前で検索するコマンド（同じ素の名前のエントリは1回の検索の結果をエントリごとに複製する）。判定でクラスを絞る。確定ファイルの確信度は HIGH |
| 件数一致検証「一致」 | `✅` / `✅ excluded(…)` | 生ヒット＝記録＋dedup除外＋フィルタ除外＋noise-collapse除外（括弧内は除外の内訳） |
| 件数一致検証「一致」 | `⚠️ mismatch(raw=…,recorded=…,excluded=…)` | 件数が一致しない（記録の欠落の疑い） |
| 件数一致検証「一致」 | `➖ discarded(case-a)` | 同名シンボル・異スコープのケースA で廃棄したコマンド（照合の対象外） |
| 件数一致検証「フィルタ除外」列 | 件数 | 保守的フィルタ（行コメント）と、1波の予算（`hit-budget` / `llm-budget`）で除いた件数の合計。予算で除いた行は「## フィルタ除外一覧」ではなく「## 打ち切り記録」にシンボル単位で記録する |
| 同名シンボル・異スコープ重複ログ「ケース」 | `case-a` / `case-b` / `case-c` | HIGH へ昇格／どのスコープにもヒットなし／スコープ内の参照のみ |
| 同名シンボル・異スコープ重複ログ「処置」 | `promote-high; discard=…` / `manual-check` / `keep-visited` | HIGH へ昇格して列挙したスコープの検索結果を廃棄／手動確認を推奨／両エントリを visited に保持（伝播なし） |
| 打ち切り記録「理由」 | `hit-budget` | 1波の予算（`SPECOUT_WAVE_HIT_BUDGET`）を超えたため、優先順位の低いシンボルの判定を打ち切った |
| 打ち切り記録「理由」 | `llm-budget` | LLM 分類の上限（`SPECOUT_LLM_HIT_BUDGET`）を超えたため、LLM 分類に回るヒットを打ち切った |
| 打ち切り記録「理由」 | `wave-limit` | 波数上限（`SPECOUT_MAX_WAVE_DEPTH`）に達したため、残りのシンボルを検索しなかった |
| grep未対応パターン「パターン種別」 | `parse-artifact` | スライス判定・規則判定: 構文解析の誤りで言語の予約語（`namespace`・`class` 等）が含む関数・次の波のシンボルになった箇所。予約語は次の波へ送らない（含む関数の本当の呼び出し元を追えていない可能性がある）。ファイルと予約語の組ごとに1行、注記に件数 |
"""


def _backend_desc(effective: str) -> str:
    if effective == "index":
        delegate = "rg" if shutil.which("rg") else "grep"
        return f"index（識別子索引。索引で引けないシンボルは {delegate}）"
    if effective == "grep":
        return "grep -rn -E"
    return effective or "(未解決)"


def _engine_desc(engine: str, engine_exts: list) -> str:
    exts = ",".join(engine_exts) if engine_exts else "(なし)"
    label = "slice（スライス判定・tree-sitter）" if engine == "slice" else "rule（規則判定・標準ライブラリ）"
    return f"{label}: {exts}／LLM 分類: 上記以外の拡張子"


def _preprocess_line(engine: str, preprocess) -> str:
    """「## 探索設定」の置き換えたマクロの行（判定エンジンが slice のときは state の preprocess の件数）。"""
    if engine != "slice" or not preprocess:
        return "- 置き換えたマクロ: —（規則判定では置き換えない）"
    return (f"- 置き換えたマクロ: {preprocess.get('neutralized_macros', 0)} 件"
            f"（名前空間 {preprocess.get('namespace', 0)}・宣言を飾る {preprocess.get('decorator', 0)}"
            f"・空にした組 {preprocess.get('empty_pair', 0)}）")


def _discovery_log_header(cr: str, repo: str, today: str, exclude_patterns: list,
                           include_extensions: list, max_wave_depth: int, initial_symbols: list,
                           entry_point_symbols: list = None, origin_rows: dict = None,
                           backend_effective: str = "", slice_engine: str = "rule",
                           engine_exts: list = None, warnings: list = None, preprocess: dict = None) -> str:
    excl = ",".join(exclude_patterns) if exclude_patterns else "(なし)"
    incl = ",".join(include_extensions) if include_extensions else "(全ファイル対象)"
    # 由来は独立セクション `## 投入シンボルの由来` に記録する（--seed-candidates 指定時は候補表から全行、
    # 未指定時は ENTRY_POINTS 行のみ）。初期シンボルの一覧には由来を併記しない。
    symbol_lines = "\n".join(f"  - `{s}`" for s in initial_symbols) or "  - （未設定）"
    warning_lines = "".join(f"> ⚠️ {w}\n" for w in (warnings or []))
    return (
        f"# Discovery Log — {cr} / {repo}\n\n"
        f"{SEARCH_SETTINGS_HEADING}\n"
        f"- 開始日時: {today}\n"
        f"- 検索ツール: {_backend_desc(backend_effective)}\n"
        "- 検索対象: プロダクションコードのみ\n"
        f"- 除外パターン: {excl}\n"
        f"- 検索拡張子: {incl}（空の場合は全ファイル対象）\n"
        f"- 最大波数: {max_wave_depth}（探索の起点の波から数えて {max_wave_depth} 波。"
        "上限到達時は打ち切り記録を残して自動完了）\n"
        f"- 判定先: {_engine_desc(slice_engine, engine_exts or [])}\n"
        f"{_preprocess_line(slice_engine, preprocess)}\n"
        "- ⚠️ MEDIUM スコープ限定の既知制約: `param[MEDIUM:src/process.py]` は指定ファイル内のみ検索する。\n"
        "  同スコープ外でインポート・再利用されている同名シンボルは検出されない。\n"
        "  MEDIUM ヒットファイルが他ファイルへ公開 API としてエクスポートしている場合は手動確認すること。\n"
        "- `name[FILE:src/a.c]` はそのファイルの中でしか参照できない名前（static・無名名前空間・そのファイルで定義した\n"
        "  マクロ、extern の宣言が見えない定義）であり、指定ファイルの中だけを検索する。\n"
        "- `name[CLASS:X]` は C++ のクラス X のメソッド・メンバー変数であり、C++ として解析するファイルを素の名前で検索し、\n"
        "  判定で受け手のクラスが X と関係するものだけを残す。\n"
        "- 初期シンボル（Wave 0）:\n"
        f"{symbol_lines}\n\n"
        f"{warning_lines + chr(10) if warning_lines else ''}"
        r"> **セル記法:** 本ログのテーブルのセル値に含まれる `|` は、Markdown の列区切りと" "\n"
        r"> 衝突するため `\|` にエスケープして記録されている（`specout_bfs.py` の `_md_cell()`）。" "\n"
        r"> セル値を他の成果物へ転記する際は `\|` を `|` に戻すこと。" "\n"
        r"> `\|` は元のソースコード／正規表現では単なる `|` である。" "\n\n"
        f"{LEGEND_HEADING}\n\n{LEGEND_BODY}\n"
        f"{_origin_section_skeleton(entry_point_symbols or [], origin_rows)}"
        f"{GREP_UNSUPPORTED_HEADING}\n"
        "| パターン種別 | 根拠（CRS/コードより） | 確認状況 |\n"
        "|---|---|---|\n"
    )


def _append_to_file(path: Path, text: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(existing + text)


def _truncate_wave_section(log_path: Path, wave: int) -> None:
    """再開時、書きかけの Wave セクション以降を切り捨てる（クラッシュ再開の重複防止）。"""
    if not log_path.exists():
        return
    text = log_path.read_text(encoding="utf-8")
    heading = f"## Wave {wave}"
    idx = text.find(heading)
    if idx == -1:
        return
    with open(log_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text[:idx].rstrip("\n") + "\n")


def _split_hits_into_chunks(hits: list, chunk_size: int) -> list:
    """PLAN-20260806 Phase 3 Stage 2 §4.5(b): ファイル単位グルーピング＋貪欲詰めでチャンク分割する。
    同一ファイルのヒットは同一チャンクに入れる（1ファイルのヒット数が chunk_size を超える場合は
    当該ファイル単独でチャンク化する）。全 line_id はちょうど1チャンクに属する（重複・欠落なし）。
    分割条件を満たさない場合（chunk_size <= 0 または len(hits) <= chunk_size）も
    必ず1件（空でも1件）返す＝呼び出し側に分岐を作らない統一契約。"""
    if chunk_size <= 0 or len(hits) <= chunk_size:
        return [hits]
    file_order = []
    group_by_file = {}
    for h in hits:
        key = h["file"]
        if key not in group_by_file:
            group_by_file[key] = []
            file_order.append(key)
        group_by_file[key].append(h)
    chunks = []
    current = []
    for key in file_order:
        group = group_by_file[key]
        if current and len(current) + len(group) > chunk_size:
            chunks.append(current)
            current = []
        current.extend(group)
    if current:
        chunks.append(current)
    return chunks or [[]]


def _append_unsupported_patterns(log_path: Path, entries: list) -> None:
    """PLAN-20260806 Phase 3 Stage 2 §4.5(e): `GREP_UNSUPPORTED_HEADING` 直下のテーブル末尾
    （次の `## ` 見出しまたは `---` の手前）へ、classifier が報告した grep未対応パターンを
    重複なく挿入する。書き手を commit-wave（単一）に集約するための「セクション内挿入」ヘルパであり、
    `_upsert_confirmed_files_section`（末尾へ再構築する方式）とは異なりヘッダ部の位置を保つ。
    `entries`: [{"pattern", "location", "note"(optional)}, ...]。重複判定キーは (pattern, location)。"""
    if not entries:
        return
    text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    idx = text.find(GREP_UNSUPPORTED_HEADING)
    if idx == -1:
        return  # 旧形式ログ等でセクション自体が無ければ no-op（安全側）
    search_from = idx + len(GREP_UNSUPPORTED_HEADING)
    next_heading = text.find("\n## ", search_from)
    next_dash = text.find("\n---", search_from)
    boundaries = [b for b in (next_heading, next_dash) if b != -1]
    end = min(boundaries) if boundaries else len(text)
    section_text = text[idx:end]
    existing_keys = set()
    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("|---"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) == 3 and cells[0] != "パターン種別":
            # 根拠列は "{location}（{note}）" 形式で note が連結されているため、
            # location のみを dedup キーへ用いる。location は "（" を含まない想定:
            # init 経由（seed-unsupported.json）は write-seed-candidates が正規化した値で、形式は種別により
            # 識別子・ファイルパス・要求 ID。commit-wave 経由は classifier またはスライス判定（specout_slice.py）が
            # 報告する {file}:{line}（正規化しない）。
            existing_keys.add((cells[0], cells[1].split("（")[0]))
    new_lines = []
    seen = set()
    for e in entries:
        pattern = e["pattern"]
        location = e["location"]
        note = e.get("note") or ""
        key = (_md_cell(pattern), location)
        if key in existing_keys or key in seen:
            continue
        seen.add(key)
        evidence = f"{location}（{note}）" if note else location
        new_lines.append(f"| {_md_cell(pattern)} | {_md_cell(evidence)} | ⬜ 未確認 |")
    if not new_lines:
        return
    text = text[:end] + "\n" + "\n".join(new_lines) + text[end:]
    with open(log_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _section_end(text: str, start: int) -> int:
    """`start` 以降で次の `\\n## ` または `\\n---` の位置（無ければ末尾）。
    `_append_unsupported_patterns` と同じ境界規則。"""
    boundaries = [b for b in (text.find("\n## ", start), text.find("\n---", start)) if b != -1]
    return min(boundaries) if boundaries else len(text)


def _upsert_section(log_path_str: str, heading: str, body: str) -> None:
    """discovery-log.md の `heading` セクションを `body` で置換する（冪等な upsert）。

    - `log_path_str` が空文字列、またはファイルが存在しない場合は no-op。
      引数を `Path` で受けないのは、`Path("")` が `Path(".")` へ正規化されて `.exists()` が
      True になり、`read_text()` が `IsADirectoryError` になるため。
    - セクションが既にある場合: `heading` 行から次の `\\n## ` または `\\n---` の手前までを置換する。
    - セクションが無い場合: `GREP_UNSUPPORTED_HEADING` の直前に挿入する。同見出しが無い旧形式ログでは no-op。
    - `body` が空文字列の場合: 当該セクションを削除する。

    EOF へ追記しないのは、`cmd_search` が同一波で EOF へ書くバックエンド警告・パース不能ヒット警告を
    次回の置換で巻き込んで消さないため。append ではなく upsert とするのは、再 search を冪等に保つため。
    """
    if not log_path_str:
        return
    log_path = Path(log_path_str)
    if not log_path.is_file():
        return
    text = log_path.read_text(encoding="utf-8")
    section = heading + "\n\n" + body.strip("\n") + "\n" if body else ""
    idx = text.find(heading + "\n")
    if idx == -1 and text.endswith(heading):
        idx = len(text) - len(heading)
    if idx != -1:
        end = _section_end(text, idx + len(heading))
        if section:
            new_text = text[:idx] + section + text[end:]
        else:
            rest = text[end:].lstrip("\n")
            new_text = text[:idx] + rest if rest else text[:idx].rstrip("\n") + "\n"
    else:
        if not section:
            return
        anchor = text.find(GREP_UNSUPPORTED_HEADING)
        if anchor == -1:
            return
        new_text = text[:anchor] + section + "\n" + text[anchor:]
    if new_text != text:
        with open(log_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_text)


def _zero_hit_heading(wave: int) -> str:
    """波ごとに独立した見出しを返す。

    `cmd_search` は state に対して読み取り専用であり検出結果を state へ持ち越せないため、
    単一見出しにすると後続波の upsert が前の波の記録を消してしまう。見出しを分ければ
    各波の upsert は互いに独立で、同一波の再 search に対してのみ冪等に上書きされる。
    """
    return ZERO_HIT_HEADING_FMT.format(n=wave)


def _zero_hit_section_body(zero_raw: list, zero_after_filter: list, entry_syms: set) -> str:
    """未ヒットが1件もない場合は空文字列を返す（＝ _upsert_section がセクションを削除する）。

    データ行・注記のいずれにも `MEDIUM` の語を書かない（`xddp_review_brief.py` の
    `_extract_markers` が全行の `MEDIUM` を確信度マーカーとして計上するため）。"""
    if not zero_raw and not zero_after_filter:
        return ""

    def _origin(sym: str) -> str:
        return "ENTRY_POINTS" if sym in entry_syms else "CRS等"

    lines = [
        "> この波で投入されたシンボルのうち、母体コードにヒットしなかったものの一覧。",
        "> CRS の識別子の誤字・旧名称、マクロ／リフレクション経由の参照、または本当に不要な",
        "> シンボルのいずれかである。工程は停止しない。",
        "> 同一行に複数の投入シンボルが現れる場合、ヒットの帰属は行内で最初にマッチした",
        "> 1シンボルに寄るため（`_matching_symbol`）、稀に誤って未ヒットと報告されることがある。",
        "> 「フィルタ後0件」には、同名シンボルがスコープ限定エントリとしても投入されていた場合に",
        "> その除外分が混入することがある。",
        "",
        "| 投入シンボル | 由来 | 区分 | 想定される原因 |",
        "|---|---|---|---|",
    ]
    for sym in zero_raw:
        cause = "母体に当該名称が存在しない（誤字・旧名称）／マクロ・リフレクション経由"
        if sym in entry_syms:
            cause += "。由来が ENTRY_POINTS かつマルチリポジトリの場合は他リポジトリ向けの指定である可能性がある"
        lines.append(f"| `{_md_cell(sym)}` | {_origin(sym)} | 生ヒット0件 | {cause}（要確認） |")
    for sym in zero_after_filter:
        lines.append(
            f"| `{_md_cell(sym)}` | {_origin(sym)} | フィルタ後0件 | 生ヒットはあったが全件が行コメント除外・"
            f"過去波 dedup で除外された（`## フィルタ除外一覧` を参照）（要確認） |"
        )
    return "\n".join(lines) + "\n"


def _noisy_seed_heading(wave: int) -> str:
    """波ごとに独立した見出しを返す（未ヒット投入シンボルと同じく、後続波の upsert が前の波の記録を消さないため）。"""
    return NOISY_SEED_HEADING_FMT.format(n=wave)


def _noisy_seed_section_body(noisy: list, all_noisy: bool, entry_syms: set, limit: int) -> str:
    """ヒット過多が1件もない場合は空文字列を返す（＝ _upsert_section がセクションを削除する）。

    見出し行は _upsert_section が付けるため含めない。データ行・注記のいずれにも `MEDIUM` の語を書かない
    （`xddp_review_brief.py` の `_extract_markers` が全行の `MEDIUM` を確信度マーカーとして計上するため）。"""
    if not noisy:
        return ""
    lines = [
        f"> この波で投入されたシンボルのうち、ヒットしたファイル数が上限（{limit}）を超えたもの（多数のファイルに",
        "> ヒットした）の一覧。一般語（識別子ではない語）がシードに混入している可能性がある。",
        "> LLM 分類に回るヒット（関数の範囲を決定的に取れない言語）は代表行に縮退され、代表行以外の行を起点とする",
        "> 次の波への伝播は起きない（ヒットしたファイル自体は確定ファイル一覧に記録される）。工程は停止しない。",
        "> 「由来」列の「CRS等」は ENTRY_POINTS 以外（CRS・母体からの補完・継承展開）を指す。"
        "内訳は `## 投入シンボルの由来` を参照。",
        "",
    ]
    if all_noisy:
        lines += ["> ⚠️ 投入シンボルの全件がヒット過多です。この探索は変更対象を特定できていない可能性が高い（要確認）。", ""]
    lines += ["| 投入シンボル | 由来 | ヒットファイル数 | 想定される原因 |", "|---|---|---|---|"]
    for n in noisy:
        origin = "ENTRY_POINTS" if n["symbol"] in entry_syms else "CRS等"
        lines.append(f"| `{_md_cell(n['symbol'])}` | {origin} | {n['file_count']} | "
                     "一般語・汎用名のためシードとして機能していない／本当に広く使われる識別子（要確認） |")
    return "\n".join(lines) + "\n"


def _update_origin_entry_points(log_path_str: str, symbols: list) -> list:
    """`ORIGIN_HEADING` テーブルの `ORIGIN_ROW_ENTRY_POINTS` 行のシンボル欄（2セル目）を
    既存セルとの**和集合**で更新し、捨てたトークンのリストを返す（無ければ `[]`）。

    この行は「人がこれまでに明示指定したシンボル」の記録であり、`merge-frontier` /
    `re-discover` のどちらから呼ばれても過去の指定を消さない（置換モードを持たない）。
    state の `entry_point_symbols`（今回の波の検出スコープ）とは別管理である。

    - 既存セルはバッククォートで囲まれたトークンのみを識別子として採る。空セル記号
      （`ORIGIN_EMPTY_CELL`・`ORIGIN_NONE_CELL`）はバッククォートの有無によらず識別子としない。
    - バッククォート外に残った、空セル記号でないトークンは識別子として採らずに捨て、戻り値で返す。
      捨てた場合はテーブル最終行の直後へ `（要確認）` 付きの警告行を1行挿入する
      （書き換え後のセルはそのトークンを含まないため、次回呼び出しで警告は重複しない）。
    - 1セル目・3セル目と他の行は保持する（行単位の書き換え。`_upsert_section` を流用すると他の行を消す）。
    - no-op（戻り値 `[]`）: `log_path_str` が空文字列・ファイル不在・セクション不在・行不在。
      引数を `str` で受ける理由は `_upsert_section` と同じ。
    """
    if not log_path_str:
        return []
    log_path = Path(log_path_str)
    if not log_path.is_file():
        return []
    text = log_path.read_text(encoding="utf-8")
    idx = text.find(ORIGIN_HEADING)
    if idx == -1:
        return []
    end = _section_end(text, idx + len(ORIGIN_HEADING))
    lines = text[idx:end].split("\n")
    row_i = None
    for i, line in enumerate(lines):
        cells = _split_row(line)
        if len(cells) >= 3 and cells[0] == ORIGIN_ROW_ENTRY_POINTS:
            row_i = i
            break
    if row_i is None:
        return []
    empty_marks = {ORIGIN_EMPTY_CELL, ORIGIN_NONE_CELL}
    parts = re.split(r"(?<!\\)\|", lines[row_i])
    cell = parts[2].strip().replace(r"\|", "|")
    existing = [t for t in re.findall(r"`([^`]+)`", cell) if t.strip() not in empty_marks]
    residual = re.sub(r"`[^`]*`", "", cell)
    unparsed = [t.strip() for t in residual.split(",")
                if t.strip() and t.strip() not in empty_marks]
    merged = list(dict.fromkeys(existing + [s for s in symbols if s]))
    parts[2] = f" {_format_origin_cell(merged, ORIGIN_EMPTY_CELL)} "
    lines[row_i] = "|".join(parts)
    if unparsed:
        last = row_i
        while last + 1 < len(lines) and lines[last + 1].strip().startswith("|"):
            last += 1
        warn = ("> ⚠️ 由来テーブルの ENTRY_POINTS 行からバッククォートなしトークンを破棄しました: "
                + ", ".join(f"`{t}`" for t in unparsed) + "（要確認）")
        lines[last + 1:last + 1] = ["", warn]
    new_text = text[:idx] + "\n".join(lines) + text[end:]
    if new_text != text:
        with open(log_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_text)
    return unparsed


def _confidence_label(kind: str) -> str:
    return "HIGH" if kind in (LV.KIND_HIGH, LV.KIND_FILE, LV.KIND_CLASS) else "MEDIUM"


def _upsert_truncation_section(log_path_str: str, data: dict) -> None:
    """「## 打ち切り記録」を state の truncated から作り直す（state が単一情報源。0件ならセクションを消す）。"""
    entries = data.get("truncated") or []
    if not entries:
        _upsert_section(log_path_str, TRUNCATION_HEADING, "")
        return
    lines = [
        "> 波数上限・1波の予算・検索ツールの制約で、判定・検索を打ち切ったシンボルの一覧（理由は「## 凡例」）。",
        "> `wave-limit` は `SPECOUT_MAX_WAVE_DEPTH` を上げて `/xddp-04-specout {CR}` を再実行すると続きから探索する。",
        "> `hit-budget` / `llm-budget` のシンボルを追う場合は `/xddp-04-specout {CR} --re-discover {シンボル}` を実行する。",
        "",
    ]
    lines += ["| 波 | 理由 | シンボル | ヒット数 |", "|---|---|---|---|"]
    for t in entries:
        hits = "-" if t.get("hits") is None else str(t["hits"])
        lines.append(f"| Wave {t.get('wave')} | {_md_cell(t.get('reason'))} | `{_md_cell(t.get('symbol'))}` | {hits} |")
    _upsert_section(log_path_str, TRUNCATION_HEADING, "\n".join(lines) + "\n")


def _budget_seed_section_body(items: list, all_truncated: bool, entry_syms: set, budget: int) -> str:
    """予算で丸ごと打ち切った投入シンボルの一覧。無ければ空文字列（＝セクションを消す）。"""
    if not items:
        return ""
    lines = [
        f"> この波で投入されたシンボルのうち、1波の予算（{budget}）に収まらず判定を丸ごと打ち切ったものの一覧。",
        "> CR の変更対象そのものが一度も追われないまま探索が進んでいる可能性がある。工程は停止しない。",
        "> 追う場合は `SPECOUT_WAVE_HIT_BUDGET` を上げて状態ファイルから作り直すか、より具体的なシンボルを",
        "> `/xddp-04-specout {CR} --re-discover {シンボル}` で投入する。",
        "",
    ]
    if all_truncated:
        lines += ["> ⚠️ 投入シンボルの全件が打ち切られました。この探索は変更対象を追えていない可能性が高い（要確認）。", ""]
    lines += ["| 投入シンボル | 由来 | ヒット数 |", "|---|---|---|"]
    for it in items:
        origin = "ENTRY_POINTS" if it["symbol"] in entry_syms else "CRS等"
        lines.append(f"| `{_md_cell(it['symbol'])}` | {origin} | {it['hits']} |")
    return "\n".join(lines) + "\n"


def _rebuild_tail_section(log_path: Path, heading: str, section: list) -> None:
    """見出し `heading` の節を（あれば）取り除き、ファイルの末尾へ作り直す。見出しは行頭の行全体で探す
    （凡例などの文中に同じ見出しの文字列が現れるため）。"""
    text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    m = re.search(r"(?m)^" + re.escape(heading) + r"[ \t]*$", text)
    if m:
        idx = m.start()
        end = text.find("\n## ", m.end())
        end_dash = text.find("\n---", m.end())
        boundaries = [b for b in (end, end_dash) if b != -1]
        end = min(boundaries) if boundaries else len(text)
        text = text[:idx] + text[end:].lstrip("\n")
    with open(log_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.rstrip("\n") + "\n\n" + "\n".join(section) + "\n")


def _upsert_confirmed_files_section(log_path: Path, data: dict) -> None:
    """Step 3「確定ファイル一覧の書き出し」相当。commit-wave のたびに全体を末尾へ再構築する。"""
    section = [CONFIRMED_FILES_HEADING, "",
               f"> ヒットがすべて `false-positive` のファイルは含めない（「{FALSE_POSITIVE_FILES_HEADING}」に記録する）。",
               "",
               r"> **セル記法:** 本ログのテーブルのセル値に含まれる `|` は、Markdown の列区切りと",
               r"> 衝突するため `\|` にエスケープして記録されている（`specout_bfs.py` の `_md_cell()`）。",
               r"> セル値を他の成果物へ転記する際は `\|` を `|` に戻すこと。",
               r"> `\|` は元のソースコード／正規表現では単なる `|` である。",
               "",
               "> 「同一性」が `name-only` のファイルは名前の一致のみでたどり着いた（別物の可能性がある）。",
               "",
               "| ファイル | 発見波 | 最高確信度 | 同一性 | ドキュメント化 |", "|---|---|---|---|---|"]
    for path_, info in sorted(data["confirmed_files"].items()):
        section.append(f"| {_md_cell(path_)} | Wave {info['wave']} | {info['confidence']} | "
                       f"{info.get('identity') or LV.IDENTITY_NAME_ONLY} | ⬜ 未 |")
    section.append("")
    _rebuild_tail_section(log_path, CONFIRMED_FILES_HEADING, section)


def _upsert_false_positive_files_section(log_path: Path, data: dict) -> None:
    """ヒットがすべて false-positive だったファイルの節。確定ファイルの節の後に呼び、その後ろへ再構築する。"""
    section = [FALSE_POSITIVE_FILES_HEADING, "",
               "> ヒットがすべて `false-positive`（コメント・文字列の中等）だったため、確定ファイルにしなかったファイル。",
               "> 後の波で `false-positive` 以外の判定でヒットしたファイルは、確定した波及ファイル一覧へ移る。",
               ""]
    fp_files = data.get("false_positive_files") or {}
    if fp_files:
        section += ["| ファイル | 波 |", "|---|---|"]
        section += [f"| {_md_cell(path_)} | Wave {w} |" for path_, w in sorted(fp_files.items())]
    else:
        section.append("なし")
    section.append("")
    _rebuild_tail_section(log_path, FALSE_POSITIVE_FILES_HEADING, section)


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

def cmd_init(args) -> None:
    seed_mode = getattr(args, "seed_candidates", None) is not None
    if seed_mode and (args.symbols is not None or getattr(args, "entry_point_symbols", None) is not None):
        print("--seed-candidates は --symbols・--entry-point-symbols と併用できません"
              "（初期シンボルと ENTRY_POINTS は候補表から導出します）", file=sys.stderr)
        sys.exit(EXIT_USAGE)
    json_path = Path(args.path)
    if json_path.exists():
        _err(f"bfs-state.json が既に存在します: {json_path}（re-discover か import を使用してください）")
    origin_rows = None
    if seed_mode:
        # 状態ファイル・discovery-log を書く前に候補表・未対応パターンをすべて検証する（途中で失敗して
        # 片方だけが残ると、次回の init が「既に存在」で止まるため）。
        if Path(args.discovery_log).exists():
            _err(f"discovery-log.md が既に存在します: {args.discovery_log}"
                 "（--seed-candidates は新規の discovery-log にのみ由来テーブルを書けます。"
                 "前回の残骸を削除してから init を実行してください）")
        seeds = _parse_seed_candidates(Path(args.seed_candidates))
        symbols = _seed_adopted_symbols(seeds)
        if not symbols:
            _err(f"シード候補表で採用（{SEED_ADOPTED}）された候補が0件です: {args.seed_candidates}")
        entry_point_symbols = _seed_adopted_symbols(seeds, (SEED_ORIGIN_ENTRY_POINTS, SEED_ORIGIN_HUMAN_ADDED))
        origin_rows = _origin_rows_from_seeds(seeds)
    else:
        symbols = _split_csv(args.symbols or "")
        _validate_frontier_format(symbols)
        entry_point_symbols = _split_csv(getattr(args, "entry_point_symbols", None) or "")
    unsupported_entries = _load_unsupported_patterns(getattr(args, "unsupported_patterns", None))
    # 判定エンジンの設定（自由文はファイルで受け取る。シェルの引用規則に依存しないため）。
    slice_engine = getattr(args, "slice_engine", None) or "rule"
    probe = {}
    if getattr(args, "probe_file", None):
        pp = Path(args.probe_file)
        if not pp.is_file():
            _err(f"--probe-file が見つかりません: {pp}")
        try:
            probe = json.loads(pp.read_text(encoding="utf-8"))
        except ValueError as e:
            _err(f"--probe-file を JSON として読めません: {pp}（{e}）")
    ignore_calls = ""
    if getattr(args, "slice_ignore_calls_file", None):
        ip = Path(args.slice_ignore_calls_file)
        if not ip.is_file():
            _err(f"--slice-ignore-calls-file が見つかりません: {ip}")
        ignore_calls = _read_ignore_calls(ip)
        if ignore_calls:
            try:
                re.compile(ignore_calls)
            except re.error as e:
                _err(f"影響なしとみなす呼び出しの正規表現が不正です（{e}）: {ignore_calls}")
    exclude_patterns = _split_csv(args.exclude)
    include_extensions = _split_csv(args.include_ext)
    h_as = resolve_h_as(getattr(args, "slice_h_as", None), args.repo_path, exclude_patterns)
    header_warnings = []
    if getattr(args, "use_probe_warning", False) and probe.get("warning"):
        header_warnings.append(f"スライス判定エンジン警告: {probe['warning']}（規則判定で実行）")
    if exclude_patterns:
        all_files = list_repo_files(args.repo_path, [])
        for pat in exclude_patterns:
            if not any(_is_excluded(f, [pat]) for f in all_files):
                header_warnings.append(f"除外パターン警告: {pat} に一致するファイルがありません")
    data = _default_state()
    scope_summary = ""
    scope_summary_missing = False
    if args.scope_summary_file:
        p = Path(args.scope_summary_file)
        if p.exists():
            scope_summary = p.read_text(encoding="utf-8").strip()
        if not scope_summary:
            scope_summary_missing = True
    data.update({
        "repo_path": args.repo_path,
        "discovery_log": args.discovery_log,
        "cr": args.cr,
        "repo": args.repo,
        "backend": (args.backend or "auto").strip() or "auto",
        "frontier": symbols,
        "exclude_patterns": exclude_patterns,
        "include_extensions": include_extensions,
        "max_wave_depth": args.max_wave,
        "wave_origin": 0,
        "wave_hit_budget": args.wave_hit_budget,
        "llm_hit_budget": args.llm_hit_budget,
        "slice_engine": slice_engine,
        "engine_exts": list(probe.get("engine_exts") or []),
        "slice_ignore_calls": ignore_calls,
        "slice_h_as": h_as,
        "max_files_per_module": args.max_files_per_module,
        "module_catalog_file": args.module_catalog or "",
        "hit_filter": (getattr(args, "hit_filter", None) or "conservative").strip() or "conservative",
        "scope_summary": scope_summary,
        "entry_point_symbols": entry_point_symbols,
    })
    if slice_engine == "slice":
        # スライス判定の前処理で置き換えるマクロの数（specout_slice.py は同じ関数で同じ表を作る）
        data["preprocess"] = MAC.table_counts(MAC.neutralize_table(args.repo_path))
    _set_input_identity(data, symbols, set(symbols))   # 第0波のシードは resolved
    _mark_seed_summary_pending(data, symbols)
    data["backend_effective"] = resolve_backend(data)[1]
    _write_state(json_path, data)

    log_path = Path(args.discovery_log)
    if not log_path.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(_discovery_log_header(
                args.cr, args.repo, args.today, data["exclude_patterns"],
                data["include_extensions"], data["max_wave_depth"], symbols,
                data["entry_point_symbols"], origin_rows,
                backend_effective=data["backend_effective"], slice_engine=slice_engine,
                engine_exts=data["engine_exts"], warnings=header_warnings,
                preprocess=data.get("preprocess"),
            ))
    # discovery-setup が見つけた grep 未対応パターン（ファイル不在・空配列は no-op）。
    _append_unsupported_patterns(log_path, unsupported_entries)
    result = {"ok": True, "current_wave": 0, "frontier_count": len(symbols), "slice_engine": slice_engine,
              "slice_h_as": h_as, "seed_summary_pending_count": len(data["seed_summary_pending"])}
    if header_warnings:
        result["header_warnings"] = header_warnings
    if scope_summary_missing:
        # PLAN-20260829 レビュー指摘#4: scope_summary の生成漏れが誰にも気づかれず
        # out-of-scope-discard が機能しない状態が継続するのを防ぐ（cmd_import の warnings パターンを踏襲）。
        warning = ("scope_summary が空です（--scope-summary-file 未指定またはファイル不在/空）。"
                   "out-of-scope-discard 判定は機能せず、保守的フォールバックにより全ヒットが通常の"
                   "伝播種別判定へ回ります。")
        result["warnings"] = [warning]
        _append_to_file(log_path, "\n> ⚠️ " + warning + "\n")
    print(json.dumps(result, ensure_ascii=False))


# ---------------------------------------------------------------------------
# module priority
# ---------------------------------------------------------------------------

def _parse_module_catalog(text: str):
    """module-catalog-template.md の構造を読む。
    戻り値: (dir_of[module_name], deps[module_dir], rdeps[module_dir], symbol_to_module[symbol])
    """
    lines = text.split("\n")
    dir_of = {}
    deps = {}
    rdeps = {}
    symbol_to_module = {}

    # ## 2. モジュール一覧: "### {name}/ — ..." に続くブレット
    i = 0
    n = len(lines)
    while i < n and lines[i].strip() != "## 2. モジュール一覧":
        i += 1
    if i < n:
        i += 1
        current_name = None
        while i < n and not lines[i].strip().startswith("## "):
            line = lines[i].strip()
            m = re.match(r"^###\s+([^\s/]+)/", line)
            if m:
                current_name = m.group(1)
            elif current_name:
                dm = re.match(r"^-\s*\*\*ディレクトリ：?\*\*\s*`([^`]+)`", line)
                if dm:
                    dir_of[current_name] = dm.group(1)
                depm = re.match(r"^-\s*\*\*依存先モジュール：?\*\*\s*(.*)$", line)
                if depm:
                    deps[current_name] = [
                        d.strip("` ") for d in depm.group(1).split(",")
                        if d.strip("` ") and d.strip("` ") != "なし"
                    ]
                rdepm = re.match(r"^-\s*\*\*被依存元モジュール：?\*\*\s*(.*)$", line)
                if rdepm:
                    rdeps[current_name] = [
                        d.strip("` ") for d in rdepm.group(1).split(",")
                        if d.strip("` ") and d.strip("` ") != "なし"
                    ]
            i += 1

    # ## 3. シンボル索引: table "| シンボル名 | モジュールディレクトリ |"
    i = 0
    while i < n and lines[i].strip() != "## 3. シンボル索引":
        i += 1
    if i < n:
        i += 1
        while i < n and not lines[i].strip().startswith("## "):
            line = lines[i].strip()
            if line.startswith("|") and "シンボル名" not in line and "---" not in line:
                # GFM ではセル内の `|` を `\|` でエスケープできる（本ファイルの `_md_cell()` と同一規約）。
                # エスケープを区切りとして数えると以降の列がずれるため、否定後読みで分割し値を戻す。
                cells = [c.strip().replace(r"\|", "|") for c in re.split(r"(?<!\\)\|", line)[1:-1]]
                if len(cells) >= 2:
                    sym = cells[0].strip("` ")
                    mod = cells[1].strip("` ")
                    if sym:
                        symbol_to_module[sym] = mod
            i += 1

    # 名前 → ディレクトリの解決（deps/rdeps は名前ベースなので、ディレクトリキーへ変換する）
    deps_by_dir = {dir_of.get(name, name): [dir_of.get(d, d) for d in dlist] for name, dlist in deps.items()}
    rdeps_by_dir = {dir_of.get(name, name): [dir_of.get(d, d) for d in dlist] for name, dlist in rdeps.items()}
    all_dirs = set(dir_of.values())
    return all_dirs, deps_by_dir, rdeps_by_dir, symbol_to_module


def _compute_module_priority(catalog_text: str, entry_modules: set) -> dict:
    all_dirs, deps, rdeps, _ = _parse_module_catalog(catalog_text)
    high = set(entry_modules)
    for e in entry_modules:
        high.update(deps.get(e, []))
        high.update(rdeps.get(e, []))
    medium = set()
    for h in high:
        medium.update(deps.get(h, []))
        medium.update(rdeps.get(h, []))
    medium -= high
    priority = {}
    for d in all_dirs:
        if d in high:
            priority[d] = "HIGH"
        elif d in medium:
            priority[d] = "MEDIUM"
        else:
            priority[d] = "LOW"
    return priority


def _module_dir_for_file(repo_path: str, file_path: str) -> str:
    # confirmed_files/hits の file はいずれもリポジトリ相対パス（_rel_file 出力）で既に格納されている
    # ため、絶対パスの場合のみ relpath 変換する（_dir_for_file と同一の防御。相対パスへ再度 relpath を
    # 適用すると cwd 起点で誤って解決される）。
    if os.path.isabs(file_path):
        try:
            rel = os.path.relpath(file_path, repo_path)
        except ValueError:
            rel = file_path
    else:
        rel = file_path
    parts = Path(rel).parts
    if len(parts) <= 1:
        return "_root"
    return parts[0]


# ---------------------------------------------------------------------------
# 2B: module-catalog 不在時の簡易近傍優先（PLAN-20260806-specout-phase2-noise-priority.md §3.2）
# ---------------------------------------------------------------------------

def _dir_for_file(repo_path: str, file_path: str) -> str:
    """ファイルの直接の親ディレクトリ（リポジトリ相対）を返す。`_module_dir_for_file`（トップ階層のみ）とは
    異なり、簡易近傍優先（`_simple_neighbor_priority`）の module granularity として使う。
    `confirmed_files`/hits の `file` はいずれもリポジトリ相対パス（`_rel_file` 出力）で既に格納されている
    ため、絶対パスの場合のみ relpath 変換する（相対パスへ再度 relpath を適用すると cwd 起点で誤って
    解決される）。"""
    rel = os.path.relpath(file_path, repo_path) if os.path.isabs(file_path) else file_path
    parent = str(Path(rel).parent)
    return "_root" if parent in (".", "") else parent


def _parent_dir(d: str) -> str:
    if d == "_root":
        return "_root"
    parent = str(Path(d).parent)
    return "_root" if parent in (".", "") else parent


def _simple_neighbor_priority(repo_path: str, base_dirs: set) -> dict:
    """module-catalog 不在時、entryシンボルのファイルのディレクトリ近傍（同一・親・子、深度1固定）を
    HIGH とする簡易 module_priority_map を構築する。キーの粒度は `_dir_for_file` と同一（ファイルの
    直接の親ディレクトリ）。マップに無いディレクトリは LOW 扱い（cmd_search 側で mode="simple" 時の
    既定値を LOW とする。§3.2 参照。捨てるわけではなく low_priority_frontier へ退避され後続波で処理される）。"""
    high = set()
    for d in base_dirs:
        high.add(d)
        high.add(_parent_dir(d))
        child_base = Path(repo_path) if d == "_root" else Path(repo_path) / d
        if child_base.is_dir():
            for entry in os.scandir(child_base):
                if entry.is_dir():
                    child_rel = entry.name if d == "_root" else os.path.join(d, entry.name)
                    high.add(child_rel)
    return {d: "HIGH" for d in high}


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def _is_excluded(rel_path: str, patterns: list) -> bool:
    """`SPECOUT_EXCLUDE_PATTERNS` の判定（バックエンドによらず同じ意味）。`rel_path` はリポジトリ相対。
    - `/` で終わり途中に `/` を含まない（`tests/`）: パスのどの階層でも、その名前のディレクトリの配下を除く
    - `/` で終わり途中に `/` を含む（`lib/legacy/`）: ルートからのパスがそのディレクトリの配下なら除く
    - `/` で終わらない（`*.pb.c`・`gen/*.c`）: `/` を含まなければファイル名、含めばルートからのパスに対する glob"""
    rel = rel_path.replace("\\", "/")
    while rel.startswith("./"):
        rel = rel[2:]
    parts = rel.split("/")
    for raw in patterns:
        p = (raw or "").strip().replace("\\", "/")
        if not p:
            continue
        if p.endswith("/"):
            d = p.rstrip("/")
            while d.startswith("./"):
                d = d[2:]
            if not d:
                continue
            if "/" not in d:
                if d in parts[:-1]:
                    return True
            elif rel.startswith(d + "/"):
                return True
        elif "/" in p:
            if fnmatch.fnmatchcase(rel, p.lstrip("./") if p.startswith("./") else p):
                return True
        elif fnmatch.fnmatchcase(parts[-1], p):
            return True
    return False


def _git_listed_files(repo_path: str):
    """git 管理下なら追跡ファイルと未追跡（.gitignore 対象外）のファイルを返す。git でなければ None。"""
    try:
        proc = subprocess.run(["git", "-C", repo_path, "ls-files", "-co", "--exclude-standard", "-z"],
                              capture_output=True)
    except OSError:
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None
    return [p for p in proc.stdout.decode("utf-8", "surrogateescape").split("\0") if p]


def list_repo_files(repo_path: str, exclude_patterns: list, include_extensions: list = None) -> list:
    """リポジトリ相対パス（`/` 区切り）の昇順。git 管理下なら `git ls-files`（.gitignore を尊重）、
    そうでなければ隠しディレクトリを除いて走査する。除外パターンは `_is_excluded`、拡張子は `include_extensions`。
    識別子索引（index バックエンド）・判定エンジン（specout_slice.py）・init の除外パターン警告が共有する。"""
    root = Path(repo_path)
    listed = _git_listed_files(repo_path)
    if listed is None:
        listed = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            for fn in filenames:
                listed.append(os.path.relpath(os.path.join(dirpath, fn), root).replace(os.sep, "/"))
    out = []
    for rel in listed:
        if include_extensions and not any(rel.endswith(ext) for ext in include_extensions):
            continue
        if _is_excluded(rel, exclude_patterns):
            continue
        if not (root / rel).is_file():
            continue
        out.append(rel)
    return sorted(set(out))


def _build_exclude_include_grep(exclude_patterns: list, include_extensions: list) -> list:
    # 速度のための前段。パスで書いたエントリ（途中に `/` を含む）は grep の --exclude-dir / --exclude が
    # 名前でしか比べないため出さず、結果を `_is_excluded` で後段フィルタする。
    opts = []
    for p in exclude_patterns:
        if "/" in p.rstrip("/"):
            continue
        if p.endswith("/"):
            opts.append(f"--exclude-dir={p.rstrip('/')}")
        else:
            opts.append(f"--exclude={p}")
    for ext in include_extensions:
        opts.append(f"--include=*{ext}")
    return opts


def _build_exclude_include_rg(exclude_patterns: list, include_extensions: list) -> list:
    opts = []
    for p in exclude_patterns:
        name = p.rstrip("/")
        opts.append("-g")
        opts.append(f"!{name}")
    for ext in include_extensions:
        opts.append("-g")
        opts.append(f"*{ext}")
    return opts


_HIT_LINE_RE = re.compile(r"^(?P<file>.+?):(?P<line>\d+):(?P<content>.*)$")


def _rel_file(file_path: str, repo_path: str) -> str:
    try:
        return os.path.relpath(file_path, repo_path)
    except ValueError:
        return file_path


def _resolve_scope_target(scope, repo_path: str) -> str:
    """MEDIUM スコープの scope（hits.json の `file` と同じリポジトリ相対パス、または絶対パス）を
    grep/rg に渡せる実パスへ解決する。"""
    if not scope:
        return repo_path
    return scope if os.path.isabs(scope) else os.path.join(repo_path, scope)


def _run_grep_batch(pattern: str, scope, exclude_opts_grep, repo_path: str) -> tuple:
    """`grep -rn -H -E pattern [scope|repo_path]` を実行し (rows, unparsed_count) を返す。
    unparsed_count は `_HIT_LINE_RE` にマッチしなかった非空行数（無言破棄の可視化用）。"""
    target = _resolve_scope_target(scope, repo_path)
    cmd = ["grep", "-rn", "-H", "-E"] + (exclude_opts_grep if not scope else []) + [pattern, target]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode not in (0, 1):
        _err(f"grep 実行に失敗しました: {' '.join(cmd)}\n{proc.stderr}")
    rows = []
    unparsed_count = 0
    for line in proc.stdout.split("\n"):
        if not line:
            continue
        m = _HIT_LINE_RE.match(line)
        if m:
            rows.append((m.group("file"), int(m.group("line")), m.group("content")))
        else:
            unparsed_count += 1
    return rows, unparsed_count


def _run_rg_patternfile(patterns: list, scope, exclude_opts_rg, repo_path: str) -> tuple:
    """`rg -n --no-heading --with-filename -f patternfile [scope|repo_path]` を実行し
    (rows, unparsed_count) を返す。unparsed_count は `_HIT_LINE_RE` にマッチしなかった非空行数。"""
    with tempfile.NamedTemporaryFile("w", suffix=".patterns", delete=False, encoding="utf-8") as tf:
        tf.write("\n".join(patterns) + "\n")
        patternfile = tf.name
    try:
        target = _resolve_scope_target(scope, repo_path)
        cmd = ["rg", "-n", "--no-heading", "--with-filename"] + (exclude_opts_rg if not scope else []) + ["-f", patternfile, target]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode not in (0, 1):
            _err(f"rg 実行に失敗しました: {' '.join(cmd)}\n{proc.stderr}")
        rows = []
        unparsed_count = 0
        for line in proc.stdout.split("\n"):
            if not line:
                continue
            m = _HIT_LINE_RE.match(line)
            if m:
                rows.append((m.group("file"), int(m.group("line")), m.group("content")))
            else:
                unparsed_count += 1
        return rows, unparsed_count
    finally:
        os.unlink(patternfile)


def _batch_symbols(symbols: list) -> list:
    """grep フォールバック時の ARG_MAX 対処（50件ずつ、平均長 > 50 文字なら20件ずつ）。"""
    if not symbols:
        return []
    avg_len = sum(len(s) for s in symbols) / len(symbols)
    batch_size = 20 if avg_len > 50 else 50
    return [symbols[i : i + batch_size] for i in range(0, len(symbols), batch_size)]


# ---------------------------------------------------------------------------
# 参照解決バックエンド（Backend 抽象）
# ---------------------------------------------------------------------------
#
# 参照解決（「シンボル群が scope 内で参照されている箇所の列挙」）を差し替え可能な Backend として
# 抽象化する。cmd_search は command_id/line_id 採番・シンボル帰属・帳簿構築を担い、バックエンドは
# 「参照箇所を下位ツールの1回実行に対応するコマンド単位で列挙する」ことだけに責務を絞る。
#
# SearchCommand は「1回の下位ツール実行（grep 1バッチ / rg 1 patternfile / 将来のタグDB1問い合わせ）」を表す:
#   - pattern_repr: discovery-log のコマンド表に出すパターン表現
#   - rows: [(file, line_no, content)]
#   - candidates: そのコマンドが探索した候補シンボルの部分集合（_matching_symbol の帰属範囲）
# grep 経路は _batch_symbols で HIGH を複数コマンドに割るため、返却単位をフラットな Hit ではなく
# SearchCommand とすることで「複数コマンド」構造と跨バッチのシンボル帰属を現行どおり保つ。

SearchCommand = collections.namedtuple("SearchCommand", ["pattern_repr", "rows", "candidates"])

# 段階2以降で実装予定の静的解析バックエンド名（現時点では未実装 → grep フォールバック）。
STATIC_BACKENDS = {"ctags", "global", "lsp"}


def _drop_excluded_rows(rows: list, repo_path: str, exclude_patterns: list) -> list:
    """grep / rg の結果のうち `_is_excluded` に当たる行を捨てる（除外した行は生ヒットに数えない）。"""
    if not exclude_patterns:
        return rows
    return [r for r in rows if not _is_excluded(_rel_file(r[0], repo_path).replace(os.sep, "/"), exclude_patterns)]


class GrepBackend:
    """`grep -rn -E` による参照探索。HIGH は _batch_symbols で複数コマンドへ分割（現行 grep 経路の再現）。"""

    name = "grep"

    def __init__(self, exclude_patterns: list, include_extensions: list, repo_path: str):
        self.exclude_opts = _build_exclude_include_grep(exclude_patterns, include_extensions)
        self.exclude_patterns = list(exclude_patterns)
        self.repo_path = repo_path
        self.unparsed_count = 0

    def _rows(self, pattern: str, scope) -> list:
        rows, unparsed = _run_grep_batch(pattern, scope, self.exclude_opts, self.repo_path)
        self.unparsed_count += unparsed
        return rows if scope else _drop_excluded_rows(rows, self.repo_path, self.exclude_patterns)

    def search(self, symbols: list, scope) -> list:
        if scope is None:
            commands = []
            for batch in _batch_symbols(symbols):
                rows = self._rows(_grep_compound(batch), None)
                commands.append(SearchCommand(_grep_compound_repr(batch), rows, list(batch)))
            return commands
        rows = self._rows(_grep_compound(symbols), scope)
        return [SearchCommand(_grep_compound_repr(symbols), rows, list(symbols))]


class RgBackend:
    """ripgrep patternfile による参照探索。HIGH/MEDIUM とも単一コマンドへ集約（現行 rg 経路の再現）。"""

    name = "rg"

    def __init__(self, exclude_patterns: list, include_extensions: list, repo_path: str):
        self.exclude_opts = _build_exclude_include_rg(exclude_patterns, include_extensions)
        self.exclude_patterns = list(exclude_patterns)
        self.repo_path = repo_path
        self.unparsed_count = 0

    def search(self, symbols: list, scope) -> list:
        patterns = [_grep_symbol_pattern(s) for s in symbols]
        rows, unparsed = _run_rg_patternfile(patterns, scope, self.exclude_opts, self.repo_path)
        self.unparsed_count += unparsed
        if not scope:
            rows = _drop_excluded_rows(rows, self.repo_path, self.exclude_patterns)
        pattern_repr = _grep_compound_repr(symbols)
        return [SearchCommand(pattern_repr, rows, list(symbols))]


# 識別子（直前が単語文字でないもの。grep の \b と同じ境界）と root.field の組。索引と帰属判定が共有する。
_TOKEN_RE = re.compile(rb"(?<![A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_]*")
_FIELD_PAIR_RE = re.compile(rb"(?=(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)\s*(?:\.|->)\s*([A-Za-z_][A-Za-z0-9_]*))")
_TOKEN_STR_RE = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_]*")
_FIELD_PAIR_STR_RE = re.compile(r"(?=(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)\s*(?:\.|->)\s*([A-Za-z_][A-Za-z0-9_]*))")


def _is_indexable(symbol: str) -> bool:
    return bool(IDENT_RE.match(symbol) or ROOT_FIELD_RE.match(symbol))


class IndexBackend:
    """識別子索引（識別子と `root.field` の転置インデックス）による参照探索。起動のたびに作る（キャッシュしない）。
    索引で引けないシンボル（識別子・root.field 以外）は `delegate`（rg があれば rg・無ければ grep）に委譲し、
    別のコマンドとして返す。HIGH は索引で引くシンボルを複合1コマンド、MEDIUM はスコープ（ファイル）ごと。"""

    name = "index"

    def __init__(self, exclude_patterns: list, include_extensions: list, repo_path: str, delegate):
        self.repo_path = repo_path
        self.exclude_patterns = list(exclude_patterns)
        self.include_extensions = list(include_extensions)
        self.delegate = delegate
        self.unparsed_count = 0
        self.build_ms = 0
        self._files = None
        self._idx = None
        self._lines = {}

    def _build(self) -> None:
        if self._idx is not None:
            return
        t0 = time.monotonic()
        self._files = list_repo_files(self.repo_path, self.exclude_patterns, self.include_extensions)
        idx = {}
        for fid, rel in enumerate(self._files):
            try:
                data = (Path(self.repo_path) / rel).read_bytes()
            except OSError:
                continue
            if b"\0" in data[:8192]:
                continue
            for ln, line in enumerate(data.split(b"\n"), 1):
                seen = set(_TOKEN_RE.findall(line))
                if b"." in line or b"->" in line:
                    for m in _FIELD_PAIR_RE.finditer(line):
                        seen.add(m.group(1) + b"." + m.group(2))
                key = (fid << 24) | ln
                for t in seen:
                    a = idx.get(t)
                    if a is None:
                        idx[t] = a = array("Q")
                    a.append(key)
        self._idx = idx
        self.build_ms = int((time.monotonic() - t0) * 1000)

    def _line_text(self, fid: int, ln: int) -> str:
        rel = self._files[fid]
        lines = self._lines.get(rel)
        if lines is None:
            text = (Path(self.repo_path) / rel).read_bytes().decode("utf-8", "replace")
            lines = text.split("\n")
            self._lines[rel] = lines
        return lines[ln - 1].rstrip("\r") if 0 < ln <= len(lines) else ""

    def _scope_rows(self, symbols: list, scope) -> list:
        path = Path(_resolve_scope_target(scope, self.repo_path))
        if not path.is_file():
            return []
        text = path.read_bytes().decode("utf-8", "replace")
        rx = [_symbol_regex(s) for s in symbols]
        rows = []
        for ln, line in enumerate(text.split("\n"), 1):
            line = line.rstrip("\r")
            if any(r.search(line) for r in rx):
                rows.append((str(path), ln, line))
        return rows

    def search(self, symbols: list, scope) -> list:
        indexable = [s for s in symbols if _is_indexable(s)]
        others = [s for s in symbols if not _is_indexable(s)]
        commands = []
        if indexable:
            if scope is not None:
                rows = self._scope_rows(indexable, scope)
            else:
                self._build()
                keys = set()
                for sym in indexable:
                    keys.update(self._idx.get(sym.encode("utf-8"), ()))
                rows = [(os.path.join(self.repo_path, self._files[k >> 24]), k & ((1 << 24) - 1),
                         self._line_text(k >> 24, k & ((1 << 24) - 1)))
                        for k in sorted(keys, key=lambda k: (self._files[k >> 24], k & ((1 << 24) - 1)))]
            commands.append(SearchCommand(_grep_compound_repr(indexable), rows, list(indexable)))
        if others:
            commands.extend(self.delegate.search(others, scope))
            self.unparsed_count = self.delegate.unparsed_count
        return commands


def resolve_backend(data: dict):
    """`data["backend"]` から Backend 実装を解決する。既定 `auto` は `index`（識別子索引。索引で引けない
    シンボルは rg があれば rg・無ければ grep に委譲）。`grep` / `rg` を明示すると索引を使わない。

    戻り値: (backend, effective_name, warning)。warning は grep への非明示フォールバックが
    起きた場合の説明文字列（無音縮退の禁止＝警告を discovery-log/bfs-state.json に記録するため）。
    """
    repo_path = data["repo_path"]
    excl = data.get("exclude_patterns") or []
    incl = data.get("include_extensions") or []
    name = (data.get("backend") or "auto").strip().lower() or "auto"
    have_rg = shutil.which("rg") is not None

    def _grep():
        return GrepBackend(excl, incl, repo_path)

    def _rg():
        return RgBackend(excl, incl, repo_path)

    if name == "grep":
        return _grep(), "grep", None
    if name == "rg":
        if have_rg:
            return _rg(), "rg", None
        return _grep(), "grep", (
            "SPECOUT_BACKEND=rg が指定されましたが rg（ripgrep）が見つかりません。grep にフォールバックしました。")
    if name in ("auto", "index"):
        return IndexBackend(excl, incl, repo_path, _rg() if have_rg else _grep()), "index", None
    if name in STATIC_BACKENDS:
        return _grep(), "grep", (
            f"SPECOUT_BACKEND={name} は段階2以降で実装予定の静的解析バックエンドです（未実装）。"
            "grep にフォールバックしました。")
    return _grep(), "grep", (
        f"SPECOUT_BACKEND={name} は未知のバックエンド値です。grep にフォールバックしました。")


def _symbol_regex(sym: str):
    """行内の出現判定の正規表現。`root.field` は `root.field` / `root->field` に一致させる。"""
    if ROOT_FIELD_RE.match(sym):
        root, fld = sym.split(".", 1)
        return re.compile(r"\b%s\s*(?:\.|->)\s*%s\b" % (re.escape(root), re.escape(fld)))
    # 検索パターンと同じ境界（両端が単語文字でない側は \b を付けない。`$var`・`Foo::bar` 等）
    return re.compile(_word_boundary(sym))


def _matching_symbol(content: str, candidates: list) -> str:
    """ヒット行の帰属シンボル（候補の順で最初に行に現れるもの）。search と seed-preview が共有する。"""
    return _attributor(candidates)(content)


def _attributor(candidates: list):
    """`_matching_symbol` と同じ帰属を、1コマンドの全行に対して速く求める関数を返す。識別子・root.field の候補は
    行の識別子の集合との照合で、それ以外の候補（`$var`・`Foo::bar` 等）は正規表現で判定する。"""
    pos = {}
    for i, sym in enumerate(candidates):
        pos.setdefault(sym, i)
    plain = [(pos[sym], _symbol_regex(sym)) for sym in pos if not _is_indexable(sym)]
    has_pairs = any(ROOT_FIELD_RE.match(sym) for sym in pos)
    fallback = candidates[0] if candidates else ""

    def match(content: str) -> str:
        best = None
        for tok in _TOKEN_STR_RE.findall(content):
            i = pos.get(tok)
            if i is not None and (best is None or i < best):
                best = i
        if has_pairs and ("." in content or "->" in content):
            for m in _FIELD_PAIR_STR_RE.finditer(content):
                i = pos.get(m.group(1) + "." + m.group(2))
                if i is not None and (best is None or i < best):
                    best = i
        for i, rx in plain:
            if (best is None or i < best) and rx.search(content):
                best = i
        return candidates[best] if best is not None else fallback
    return match


def _summary_norm(summ: dict) -> str:
    """要約の正規形（`_summary_growth` が比べる returns・side・ソートした out）。dedup の鍵に使う。"""
    out = ",".join(sorted(str(o) for o in (summ.get("out") or ())))
    return f"returns={int(bool(summ.get('returns')))};side={int(bool(summ.get('side')))};out={out}"


def _summary_growth(old: dict, new: dict) -> list:
    """new が old より広がった項目（`returns`・`side`・`out+=[…]`）。広がらなければ空。"""
    grown = []
    if new.get("returns") and not old.get("returns"):
        grown.append("returns")
    if new.get("side") and not old.get("side"):
        grown.append("side")
    added = sorted({str(o) for o in (new.get("out") or ())} - {str(o) for o in (old.get("out") or ())})
    if added:
        grown.append(f"out+=[{','.join(added)}]")
    return grown


def _merge_summary(old: dict, new: dict) -> dict:
    def _union(key):
        merged = {}
        for v in list(old.get(key) or ()) + list(new.get(key) or ()):
            merged.setdefault(str(v), v)
        return [merged[k] for k in sorted(merged)]
    return {"returns": bool(old.get("returns") or new.get("returns")), "out": _union("out"),
            "globals": _union("globals"), "side": bool(old.get("side") or new.get("side")),
            "closure": _union("closure"), "name_only": _union("name_only")}


def _complete_at_wave_limit(data: dict, state_path: Path) -> dict:
    """波数上限に達した search: 残りのエントリを打ち切り記録に残し、frontier を空にして complete にする。"""
    wave = data["current_wave"]
    truncated = data.setdefault("truncated", [])
    count = 0
    for src, key in (("frontier", "frontier"), ("low", "low_priority_frontier")):
        for entry in data.get(key) or []:
            truncated.append({"wave": wave, "reason": LV.TRUNC_WAVE_LIMIT, "symbol": entry, "hits": None,
                              "from": src})
            count += 1
        data[key] = []
    data["state"] = "complete"
    _drop_classify_timer(data)
    _write_state(state_path, data)
    _upsert_truncation_section(data.get("discovery_log") or "", data)
    return {"ok": True, "complete": True, "truncated": True, "truncated_count": count, "wave": wave}


def _budget_order(entries: dict, kinds: dict) -> list:
    """予算で採る順: 関数シンボル → 値シンボル、各群の中ではヒットの少ない順、同数ならシンボル名の順。"""
    return sorted(entries, key=lambda e: (kinds.get(summary_key(e)) in VALUE_KINDS, entries[e], e))


def _seed_entries(entries, wave: int, seed_globals: set, entry_syms: set) -> set:
    """その波でシードとみなすエントリ（エントリ文字列）。第0波は全エントリ、第1波以降は人が入れたもの
    （`entry_point_symbols` の要素が修飾なしなら素名で、修飾つきならエントリ文字列で照合する）。シードのグローバルは
    エントリ文字列で除く。"""
    plain = {s for s in entry_syms if not _is_qualified_entry(s)}
    out = set()
    for e in entries:
        if e in seed_globals:
            continue
        if wave == 0 or e in entry_syms or _parse_entry(e)[0] in plain:
            out.add(e)
    return out


def cmd_search(args) -> None:
    # --hits-out / --hits-dir は相互排他。両方未指定・両方指定はいずれも明示エラーとし、暗黙の優先順位を作らない。
    if (args.hits_out is None) == (args.hits_dir is None):
        _err("--hits-out と --hits-dir はどちらか一方のみを指定してください（同時未指定・同時指定はエラー）")
    state_path = Path(args.path)
    data = _load_state(state_path)
    if data["state"] == "complete":
        _err("BFS は既に complete 状態です（search 不要）")
    if data["state"] not in VALID_STATES:
        _err(f"不正な状態です: {data['state']}（状態ファイルを退避・削除して最初から探索してください）")
    if data["current_wave"] <= data.get("last_completed_wave", -1):
        # 完了済みの波へ state だけを戻した状態（set-state in-progress / 不整合 checkpoint の import）。
        # このまま search すると commit-wave が条件3 で fail-loud するため、search と
        # 分類のトークンが丸ごと無駄になる。判定は整数2つの比較で決定的に行えるため
        # スクリプト側で前倒しに止める（CLAUDE.md「決定的処理はスクリプト」）。
        _err(
            f"current_wave={data['current_wave']} は last_completed_wave={data['last_completed_wave']} 以下です"
            f"（完了済みの波へ戻った状態）。search は実行できません。"
            f"追加探索する場合は次の3手順で再開してください: "
            f"(1) status --path {args.path} で frontier の残存シンボルを控える "
            f"(2) set-state --path {args.path} --state complete "
            f"(3) re-discover --path {args.path} --symbols '<(1)の残存＋追加シンボル>' "
            f"--entry-point-symbols '<追加シンボルのみ>' --today <YYYY-MM-DD>"
            f"（re-discover は frontier を置換するため、(1) の残存分を --symbols に含めないと黙って失われる。"
            f"--entry-point-symbols には人が追加したシンボルだけを渡す。省略すると由来テーブルと"
            f"未ヒット検出の対象が前回のままになる）"
        )

    # シード要約の取り込みが済んでいなければ検索しない（波数上限の判定より前。取り込み前のシードを打ち切らない）。
    pending = data.get("seed_summary_pending") or []
    if pending:
        print(f"シード要約の取り込みが済んでいません（{len(pending)} 件）", file=sys.stderr)
        sys.exit(EXIT_SEED_SUMMARY_PENDING)

    if data["current_wave"] - data.get("wave_origin", 0) >= data["max_wave_depth"]:
        print(json.dumps(_complete_at_wave_limit(data, state_path), ensure_ascii=False))
        return

    module_map = data.get("module_priority_map") or {}
    symbol_module = data.get("symbol_module") or {}
    frontier = list(data["frontier"])
    low = list(data.get("low_priority_frontier") or [])

    if data.get("module_priority_computed") and module_map:
        # catalog モードは未知モジュールを HIGH（既存挙動不変）、simple モード（module-catalog 不在）は
        # 未知ディレクトリを LOW とする（捨てず低優先で退避）。
        default_unlisted = "LOW" if data.get("module_priority_mode") == "simple" else "HIGH"
        this_wave, new_low = [], []
        for entry in frontier:
            module = symbol_module.get(entry)
            prio = module_map.get(module, default_unlisted) if module else "HIGH"
            (new_low if prio == "LOW" else this_wave).append(entry)
        low.extend(new_low)
        if not this_wave and low:
            this_wave, low = low, []
    else:
        this_wave = frontier

    if not this_wave:
        if data.get("last_completed_wave", -1) < 0:
            # まだ1波もコミットしていない状態で frontier が空＝discovery-setup がシードを1件も得られなかった。
            # 呼び出し元がこの場合だけを区別して人へ案内できるよう、専用の終了コードで返す。
            print("frontier が空です（投入シンボルが0件のため Wave 0 を開始できません）", file=sys.stderr)
            sys.exit(EXIT_EMPTY_SEED)
        _err("frontier が空です（search 対象がありません）")

    wave = data["current_wave"]
    repo_path = data["repo_path"]
    log_path_str = data.get("discovery_log") or ""
    backend, effective_backend, backend_warning = resolve_backend(data)
    data["backend_effective"] = effective_backend
    if backend_warning and not data.get("backend_fallback_logged"):
        _append_to_file(Path(data["discovery_log"]), f"\n> ⚠️ バックエンド警告: {backend_warning}\n")
        data["backend_fallback_logged"] = True

    high_symbols = [e for e in this_wave if _parse_entry(e)[1] is None]
    scoped_entries = [_parse_entry(e) + (_entry_scope_kind(e),) for e in this_wave
                      if _parse_entry(e)[1] is not None and _entry_scope_kind(e) != SCOPE_CLASS]
    medium_entries = [(sym, scope) for sym, scope, kind in scoped_entries if kind == SCOPE_MEDIUM]
    # `[CLASS:…]` のエントリは同じ素の名前ごとに1回だけ検索し、ヒット行をエントリごとに複製する。
    class_entries_by_base = {}
    for e in this_wave:
        if _entry_scope_kind(e) == SCOPE_CLASS:
            class_entries_by_base.setdefault(_parse_entry(e)[0], []).append(e)
    h_as = data.get("slice_h_as") or "c"

    budget_truncated = []
    # スコープを限定する検索は (種別, ファイル) ごとに1コマンド（同じファイルでも MEDIUM と FILE は別のコマンド）。
    scoped_by_key = {}
    for symbol, scope, kind in scoped_entries:
        scoped_by_key.setdefault((kind, scope), []).append(symbol)

    engine_exts = set(data.get("engine_exts") or [])
    summaries = data.get("symbol_summaries") or {}
    kinds = data.get("symbol_kinds") or {}
    classified_set = set(data.get("classified_locations") or [])  # cross-wave dedup（scope_class 込み）
    hit_filter = data.get("hit_filter", "conservative")
    metrics = {"wave": wave, "search_ms": 0, "raw_hits": 0, "dedup_removed": 0, "filter_removed": 0,
               "noise_collapse_removed": 0, "hit_budget_removed": 0, "llm_budget_removed": 0,
               "index_build_ms": 0, "slice_hits": 0, "llm_hits": 0}
    filtered_out = []  # discovery-log 記録用: {file, line_no, symbol, reason}
    commands = []
    cmd_meta = {}
    candidates = []    # フィルタを通ったヒット（line_id は予算の適用後に振る）
    cmd_n = 0

    def _next_cmd_id():
        nonlocal cmd_n
        cmd_n += 1
        return f"W{wave}-C{cmd_n}"

    def _route(rel: str) -> str:
        return "slice" if os.path.splitext(rel)[1] in engine_exts else "llm"

    def _summary_suffix(key: str) -> str:
        # 要約のある関数シンボルは要約の正規形を鍵に含める（要約が広がった再訪で呼び出し元を判定し直すため）。
        # key は summary_key（`[CLASS:…]` はエントリ文字列、それ以外は素名）。
        if key in summaries and kinds.get(key) not in VALUE_KINDS:
            return "#" + _summary_norm(summaries[key])
        return ""

    def _scope_class(sym: str, scope, scope_kind) -> str:
        # HIGH（要約付きは HIGH#{正規形}）／MEDIUM はスコープ文字列／FILE は FILE:{スコープ}・CLASS は CLASS:{クラス名}
        # （要約付きは #{正規形}）。
        if scope is None:
            return "HIGH" + _summary_suffix(sym)
        if scope_kind == SCOPE_FILE:
            return f"FILE:{scope}" + _summary_suffix(sym)
        if scope_kind == SCOPE_CLASS:
            return f"CLASS:{scope}" + _summary_suffix(_format_entry(sym, scope, SCOPE_CLASS))
        return scope

    def _loc_key(sym: str, rel_file: str, line_no, scope_class: str) -> str:
        return "\x00".join([sym, rel_file, str(line_no), scope_class])

    def _consume(sc, kind: str, scope, scope_kind=None) -> None:
        cmd_id = _next_cmd_id()
        attribute = _attributor(sc.candidates)
        # CLASS のスコープはクラス名（検索はファイルを限定しない。ヒットの scope_file は None）。
        display_scope = "全域" if scope is None else (f"CLASS:{scope}" if scope_kind == SCOPE_CLASS else scope)
        meta = {"command_id": cmd_id, "kind": kind, "pattern": sc.pattern_repr,
                "scope": display_scope, "hit_count": len(sc.rows),
                "dedup_removed": 0, "filter_removed": 0, "noise_collapse_removed": 0, "budget_removed": 0}
        cmd_meta[cmd_id] = meta
        commands.append(meta)
        for file_, line_no, content in sc.rows:
            metrics["raw_hits"] += 1
            sym = attribute(content)
            rel = _rel_file(file_, repo_path)
            scls = _scope_class(sym, scope, scope_kind)
            entry = _format_entry(sym, scope, scope_kind or SCOPE_MEDIUM)
            if _loc_key(sym, rel, line_no, scls) in classified_set:  # 過去波で同一スコープ種別で分類済み
                metrics["dedup_removed"] += 1
                meta["dedup_removed"] += 1
                filtered_out.append({"file": rel, "line_no": line_no, "symbol": sym, "entry": entry, "reason": "dedup"})
                continue
            ext = os.path.splitext(file_)[1].lower()
            if hit_filter == "conservative" and _is_pure_line_comment(content, sym, ext):
                metrics["filter_removed"] += 1
                meta["filter_removed"] += 1
                filtered_out.append({"file": rel, "line_no": line_no, "symbol": sym, "entry": entry,
                                     "reason": "line-comment"})
                continue
            candidates.append({"command_id": cmd_id, "symbol": sym,
                               "scope_file": None if scope_kind == SCOPE_CLASS else scope, "file": rel,
                               "line_no": line_no, "matched_text": content, "loc_scope_class": scls,
                               "route": _route(rel), "entry": entry})

    if high_symbols:
        t0 = time.monotonic()
        for sc in backend.search(high_symbols, None):
            _consume(sc, LV.KIND_HIGH, None)
        metrics["search_ms"] += int((time.monotonic() - t0) * 1000)
    for scope_kind, scope in sorted(scoped_by_key.keys(), key=lambda k: (k[1], k[0])):
        t0 = time.monotonic()
        for sc in backend.search(scoped_by_key[(scope_kind, scope)], scope):
            _consume(sc, LV.KIND_FILE if scope_kind == SCOPE_FILE else LV.KIND_MEDIUM, scope, scope_kind)
        metrics["search_ms"] += int((time.monotonic() - t0) * 1000)
    for base in sorted(class_entries_by_base):
        # 素の名前ごとに1回（違う素の名前を1回の呼び出しにまとめない＝行の帰属が素の名前に閉じる）。C++ 以外の行は捨てる
        # （生ヒットにもどの除外にも数えない）。行はエントリごとに複製し、エントリごとに1コマンドとして記録する。
        t0 = time.monotonic()
        cmds = backend.search([base], None)
        metrics["search_ms"] += int((time.monotonic() - t0) * 1000)
        for e in sorted(class_entries_by_base[base]):
            for sc in cmds:
                rows = [r for r in sc.rows if is_cpp_file(_rel_file(r[0], repo_path), h_as)]
                _consume(sc._replace(rows=rows), LV.KIND_CLASS, _parse_entry(e)[1], SCOPE_CLASS)
    metrics["index_build_ms"] = getattr(backend, "build_ms", 0)

    # 投入シンボルごとのフィルタの後のファイル数（判定先によらない。ヒット過多の投入シンボルの判定に使う）。
    seed_files = {}
    for c in candidates:
        if _entry_scope_kind(c["entry"]) != SCOPE_MEDIUM:
            seed_files.setdefault(c["entry"], set()).add(c["file"])

    # 前倒し縮退: LLM 分類に回る HIGH のヒットだけ、ファイル数が上限を超えるシンボルを代表行に縮退する。
    pre_noisy = set()
    module_files = {}   # {symbol: [file, ...]}（縮退したシンボルの全ファイル。confirmed_files 網羅維持用）
    by_symbol = {}
    for i, c in enumerate(candidates):
        if c["scope_file"] is None and c["route"] == "llm" and _entry_scope_kind(c["entry"]) is None:
            by_symbol.setdefault(c["symbol"], []).append(i)
    removed = set()
    for sym, idxs in by_symbol.items():
        files = sorted({candidates[i]["file"] for i in idxs})
        if len(files) <= data["max_files_per_module"]:
            continue
        pre_noisy.add(sym)
        module_files[sym] = files
        # 代表サブセット: ファイルパス昇順で先頭 max_files_per_module 件・各ファイル最大1行（ファイル内最小行番号）。
        first_index_by_file = {}
        for i in idxs:
            first_index_by_file.setdefault(candidates[i]["file"], i)
        rep_indices = {first_index_by_file[f] for f in files[: data["max_files_per_module"]]}
        for i in idxs:
            if i in rep_indices:
                continue
            removed.add(i)
            c = candidates[i]
            filtered_out.append({"file": c["file"], "line_no": c["line_no"], "symbol": c["symbol"],
                                 "reason": "noise-collapse"})
            cmd_meta[c["command_id"]]["noise_collapse_removed"] += 1
    metrics["noise_collapse_removed"] = len(removed)
    candidates = [c for i, c in enumerate(candidates) if i not in removed]

    # 1波の予算（dedup・フィルタ・縮退の後の件数）。エントリ単位で、関数 → 値、ヒットの少ない順に採る。
    def _apply_budget(limit: int, reason: str, route=None) -> None:
        nonlocal candidates
        counts = collections.Counter(c["entry"] for c in candidates if route is None or c["route"] == route)
        if limit <= 0 or sum(counts.values()) <= limit:
            return
        used = 0
        dropped = set()
        for e in _budget_order(counts, kinds):
            if used + counts[e] <= limit:
                used += counts[e]
            else:
                dropped.add(e)
                budget_truncated.append({"wave": wave, "reason": reason, "symbol": e, "hits": counts[e]})
        kept = []
        for c in candidates:
            if c["entry"] in dropped and (route is None or c["route"] == route):
                cmd_meta[c["command_id"]]["budget_removed"] += 1
                metrics["hit_budget_removed" if reason == LV.TRUNC_HIT_BUDGET else "llm_budget_removed"] += 1
                continue
            kept.append(c)
        candidates = kept

    _apply_budget(int(data.get("wave_hit_budget") or 0), LV.TRUNC_HIT_BUDGET)
    _apply_budget(int(data.get("llm_hit_budget") or 0), LV.TRUNC_LLM_BUDGET, route="llm")

    hits = []
    for n, c in enumerate(candidates, 1):
        hits.append({"line_id": f"W{wave}-R{n}", "command_id": c["command_id"], "symbol": c["symbol"],
                     "scope_file": c["scope_file"], "entry": c["entry"], "file": c["file"], "line_no": c["line_no"],
                     "matched_text": c["matched_text"], "route": c["route"],
                     "loc_scope_class": c["loc_scope_class"]})
    slice_hits = [h for h in hits if h["route"] == "slice"]
    llm_hits = [h for h in hits if h["route"] == "llm"]
    metrics["slice_hits"] = len(slice_hits)
    metrics["llm_hits"] = len(llm_hits)

    if backend.unparsed_count > 0:
        _append_to_file(Path(data["discovery_log"]),
                        f"\n> ⚠️ パース不能なヒット行が {backend.unparsed_count} 件検出されました"
                        "（_HIT_LINE_RE 不一致により無言破棄。grep/rg 出力形式が想定外の可能性があります）。\n")

    frontier_medium_scopes = {}
    for symbol, scope in medium_entries:
        frontier_medium_scopes.setdefault(symbol, []).append(scope)

    # シードとみなすエントリ: 第0波はその波で検索するエントリ（シードのグローバルを除く）、第1波以降は人が入れたもの。
    # シードのグローバル・人が入れたシンボルとの照合は _seed_entries（エントリ文字列で引く）。
    seed_globals = set(data.get("seed_globals") or [])
    entry_syms = set(data.get("entry_point_symbols") or [])
    searched_bases = {_parse_entry(e)[0] for e in this_wave}
    searched_keys = {summary_key(e) for e in this_wave}
    seed_entries = _seed_entries(this_wave, wave, seed_globals, entry_syms)
    seed_symbols = sorted(seed_entries)
    seed_keys = sorted({summary_key(e) for e in seed_entries})
    # 投入シンボルの検出の対象（MEDIUM はケースB が扱うため除く）。照合と報告はエントリ文字列。
    seed_high = {e for e in seed_entries if _entry_scope_kind(e) != SCOPE_MEDIUM}

    function_summaries = {key: summaries[key] for key in sorted(searched_keys)
                          if key in summaries and kinds.get(key) not in VALUE_KINDS}
    hits_payload = {
        "wave": wave,
        "commands": commands,
        "hits": hits,
        "frontier_medium_scopes": frontier_medium_scopes,
        "searched_frontier": this_wave,
        "metrics": metrics,            # commit-wave で classified 数を足して確定
        "filtered_out": filtered_out,  # discovery-log 監査記録用
        "pre_noisy": sorted(pre_noisy),   # commit-wave の noisy_keys 拡張入力（LLM 分類に回るヒットのみ）
        "module_files": module_files,     # confirmed_files 網羅維持用
        # LOW 退避の結果は search が state へ書き戻さず commit-wave（フロンティア状態の単一書き手）へ渡す。
        "deferred_low": low,
        # 予算・検索ツールの制約で打ち切ったエントリ（commit-wave が state の truncated に追記する）。
        "budget_truncated": budget_truncated,
        # その波でシードとみなすシンボル（派生元 seed(X) とシードの直接参照ファイル数に使う）。
        "seed_symbols": sorted(seed_symbols),
        # 「戻り値代入/ジェネレータ受信」ルールの参照集合を素名正規化して全チャンクへ複製配布する。
        "known_symbols": {
            "visited": sorted({_parse_entry(e)[0] for e in data["visited"]}),
            "searched_frontier": sorted(searched_bases),
            "current_wave": sorted({h["symbol"] for h in hits}),
        },
        # init 時に1回だけ合成された値を毎波そのまま複製する（波・チャンクをまたいで不変）。
        "scope_summary": data.get("scope_summary", ""),
    }
    if args.hits_dir is not None:
        out_path = Path(args.hits_dir) / f"wave-{wave}-hits.json"
    else:
        out_path = Path(args.hits_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(hits_payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # チャンク: スライス用（常に1件。ヒット0件でも書く）と LLM 用（LLM に回るヒットがあるときだけ）。
    # 書き出し前に当該波の既存チャンクを削除し、チャンク数が減る再 search で旧ランのファイルが残らないようにする。
    for stale in sorted(out_path.parent.glob(f"{out_path.stem}-chunk-*.json")):
        stale.unlink()
    commands_by_id = {c["command_id"]: c for c in commands}

    def _write_chunk(chunk_id: str, suffix: str, chunk_hits: list, extra: dict = None) -> str:
        cmd_ids = sorted({h["command_id"] for h in chunk_hits})
        payload = {
            "chunk_id": chunk_id, "wave": wave, "hits": chunk_hits,
            "known_symbols": hits_payload["known_symbols"], "scope_summary": hits_payload["scope_summary"],
            "commands": [commands_by_id[cid] for cid in cmd_ids if cid in commands_by_id],
        }
        payload.update(extra or {})
        path = out_path.parent / f"{out_path.stem}-chunk-{suffix}.json"
        with open(path, "w", encoding="utf-8", newline="\n") as cf:
            json.dump(payload, cf, ensure_ascii=False, indent=2)
            cf.write("\n")
        return str(path)

    slice_chunk = _write_chunk(f"W{wave}-KS", "S", slice_hits, {
        "frontier_summaries": function_summaries,
        # 検索したシンボルの種類（素名 → symbol_kinds の値）とその波のシード（判定のヒット側の除外に使う）。
        "frontier_kinds": {key: kinds[key] for key in sorted(searched_keys) if key in kinds},
        "seed_keys": seed_keys,
    })
    chunk_paths = []
    if llm_hits:
        for idx, chunk_hits in enumerate(_split_hits_into_chunks(llm_hits, args.chunk_size)):
            chunk_paths.append(_write_chunk(f"W{wave}-K{idx}", str(idx), chunk_hits))

    # --- 未ヒット投入シンボルの検出 ---
    # 検出対象は「人または CRS が投入したシード」（seed_high）であり、伝播で生成された frontier と
    # シードのグローバルは含めない。予算・検索ツールの制約で打ち切ったシンボルは打ち切り記録に残るため数えない。
    # MEDIUM エントリのスコープ内0件は cmd_commit_wave のケースB が既に扱うため対象外。
    zero_raw: list = []
    zero_after_filter: list = []
    wave0_seed_count = len([e for e in this_wave if e not in seed_globals]) if wave == 0 else 0
    truncated_syms = {t["symbol"] for t in budget_truncated}
    if seed_high:
        hit_symbols = {h["entry"] for h in hits}
        filtered_symbols = {f.get("entry") or f["symbol"] for f in filtered_out if f.get("symbol")}
        missing = seed_high - hit_symbols - truncated_syms
        zero_raw = sorted(missing - filtered_symbols)
        zero_after_filter = sorted(missing & filtered_symbols)
        _upsert_section(log_path_str, _zero_hit_heading(wave),
                        _zero_hit_section_body(zero_raw, zero_after_filter, entry_syms))

    # --- ヒット過多の投入シンボルの検出（フィルタの後のファイル数。判定先によらない）---
    noisy_seeds: list = []
    all_seeds_noisy = False
    budget_seeds: list = []
    all_seeds_budget_truncated = False
    if seed_high:
        noisy_seeds = [{"symbol": s, "file_count": len(seed_files[s])} for s in sorted(seed_high)
                       if len(seed_files.get(s, ())) > data["max_files_per_module"]]
        all_seeds_noisy = len(noisy_seeds) == len(seed_high)
        _upsert_section(log_path_str, _noisy_seed_heading(wave),
                        _noisy_seed_section_body(noisy_seeds, all_seeds_noisy, entry_syms, data["max_files_per_module"]))
        # --- 予算で丸ごと打ち切った投入シンボル ---
        budget_seeds = [{"symbol": t["symbol"], "hits": t["hits"]} for t in budget_truncated
                        if t["reason"] == LV.TRUNC_HIT_BUDGET and t["symbol"] in seed_high]
        all_seeds_budget_truncated = len(budget_seeds) == len(seed_high)
        _upsert_section(log_path_str, BUDGET_SEED_HEADING_FMT.format(n=wave),
                        _budget_seed_section_body(budget_seeds, all_seeds_budget_truncated, entry_syms,
                                                  int(data.get("wave_hit_budget") or 0)))

    data["wave_write_complete"] = False
    # 分類区間（search と commit-wave の"間"）の開始時刻を2キー対で記録する。search と commit-wave は別プロセスで
    # あり time.monotonic() は基準点がプロセス間で保証されないため time.time()（エポック秒）を用いる。
    data["classify_started_at"] = time.time()
    data["classify_started_wave"] = wave
    _write_state(state_path, data)

    print(json.dumps({
        "ok": True, "wave": wave, "hits_file": str(out_path), "hit_count": len(hits),
        "raw_hits": metrics["raw_hits"], "dedup_removed": metrics["dedup_removed"],
        "filter_removed": metrics["filter_removed"], "search_ms": metrics["search_ms"],
        "index_build_ms": metrics["index_build_ms"],
        "noise_collapse_removed": metrics["noise_collapse_removed"], "pre_noisy": sorted(pre_noisy),
        "hit_budget_removed": metrics["hit_budget_removed"], "llm_budget_removed": metrics["llm_budget_removed"],
        "slice_hit_count": len(slice_hits), "llm_hit_count": len(llm_hits),
        "commands": [{"command_id": c["command_id"], "hit_count": c["hit_count"]} for c in commands],
        "slice_chunk": slice_chunk, "chunks": chunk_paths, "chunk_count": len(chunk_paths),
        "zero_hit_symbols": zero_raw, "zero_after_filter_symbols": zero_after_filter,
        "wave0_seed_count": wave0_seed_count,
        "noisy_seed_symbols": noisy_seeds, "all_seeds_noisy": all_seeds_noisy,
        "budget_truncated_seed_symbols": budget_seeds, "all_seeds_budget_truncated": all_seeds_budget_truncated,
    }, ensure_ascii=False))


# ---------------------------------------------------------------------------
# commit-wave
# ---------------------------------------------------------------------------

def cmd_commit_wave(args) -> None:
    state_path = Path(args.path)
    data = _load_state(state_path)
    hits_payload = json.loads(Path(args.hits).read_text(encoding="utf-8"))
    classification = json.loads(Path(args.classification).read_text(encoding="utf-8"))

    wave = hits_payload["wave"]
    hits = hits_payload["hits"]
    commands = hits_payload["commands"]
    frontier_medium_scopes = hits_payload.get("frontier_medium_scopes", {})
    searched_frontier = hits_payload.get("searched_frontier", [])
    wave_metrics = hits_payload.get("metrics", {})           # PLAN-20260804 Phase 0
    filtered_out = hits_payload.get("filtered_out", [])      # PLAN-20260804 Phase 1a/1b（監査記録）
    pre_noisy = set(hits_payload.get("pre_noisy", []))        # PLAN-20260806 Phase 2A（search 側で前倒し判定済み）
    module_files = hits_payload.get("module_files", {})       # PLAN-20260806 Phase 2A（confirmed_files 網羅維持用）
    budget_truncated = hits_payload.get("budget_truncated", [])
    seed_symbols = set(hits_payload.get("seed_symbols", []))

    # --- コミット妥当性の fail-loud（PLAN-20260806 Phase 3 Stage 1 §4.5(g)）---
    # 検証位置は「hits_payload 読み込み直後・_truncate_wave_section より前」。_truncate_wave_section は
    # hits 由来の wave で discovery-log を破壊的に切り捨てるため、後置すると確定済みログを失ってから
    # エラー終了することになり、ガードが守るはずの誤操作で被害が拡大する。
    if wave != data["current_wave"]:
        # 条件1: 渡された hits が現在の波と異なる（古い hits の誤投入）。
        # §4.5(g) 適用後は deferred_low が LOW フロンティアを古い波の値で上書きするため、
        # 消費済みエントリの復活・現在の繰り越し分の消失を招く。
        _err(f"hits の wave が現在の波と一致しません: hits={wave} / current_wave={data['current_wave']}")
    if data["state"] == "complete":
        # 条件2: 既に BFS が完了している。当該波の search 実行後に set-state complete を実行した state では
        # wave_write_complete: false かつ wave > last_completed_wave のまま complete になるため
        # 条件1・3 では捕捉できない。
        # 案内は re-discover に一本化する: set-state は current_wave を進めないため、
        # 続く search が完了済みの波番号で走り確定済み Wave セクションを破壊する
        # （PLAN-20260808 不具合2）。本条件は既に state == complete であり re-discover の前提を
        # 満たすため、直接 re-discover を案内する。条件3・cmd_search のガードは
        # in-progress へ戻った状態で発火するため、complete へ戻す手順を含む3手順を案内する。
        _err("BFS は既に complete 状態です（commit-wave は実行できません。完了後に追加探索する場合は re-discover を使用してください）")
    if wave <= data.get("last_completed_wave", -1):
        # 条件3: 正常終了済みの波の再コミット（discovery-log・metrics.jsonl の二重追記）。
        # `wave_write_complete` を連言に含めてはならない: cmd_search が同キーを False にするため、
        # 「set-state で in-progress へ戻す → search → commit-wave」という現実の再開経路では
        # 必ず不成立になり、ガードが素通りして確定済み Wave セクションが切り捨てられる
        # （PLAN-20260808 不具合2）。
        # クラッシュ再開（search 済み・commit 未完）は wave == current_wave > last_completed_wave
        # となり本条件に掛からないため、正当な再コミットを妨げない。
        _err(
            f"Wave {wave} は既に正常終了済みです（last_completed_wave={data['last_completed_wave']}）。"
            f"二重コミットはできません。完了後に追加探索する場合は次の3手順で再開してください: "
            f"(1) status --path {args.path} で frontier の残存シンボルを控える "
            f"(2) set-state --path {args.path} --state complete "
            f"(3) re-discover --path {args.path} --symbols '<(1)の残存＋追加シンボル>' "
            f"--entry-point-symbols '<追加シンボルのみ>' --today <YYYY-MM-DD>"
            f"（re-discover は frontier を置換するため、(1) の残存分を --symbols に含めないと黙って失われる。"
            f"--entry-point-symbols には人が追加したシンボルだけを渡す。省略すると由来テーブルと"
            f"未ヒット検出の対象が前回のままになる）"
        )

    # PLAN-20260806 Phase 3 Stage 1 §4.5(g): search が判定した LOW 退避結果をここで state へ反映する。
    # 適用位置を discovery-log 生成部より前に固定するのは、complete 判定（not next_frontier and not
    # low_priority_frontier）だけでなく frontier 行の生成（「探索終了」/「MODULE_PRIORITY_LOW 分へ移行」）も
    # low_priority_frontier を参照するためで、後置すると discovery-log と bfs-state.json が食い違う。
    # キー欠損時（旧形式 hits）は既存値を変更しない（安全側の既定）。
    if "deferred_low" in hits_payload:
        data["low_priority_frontier"] = list(hits_payload["deferred_low"])

    hit_ids = {h["line_id"] for h in hits}
    class_by_id = {}
    for c in classification:
        lid = c.get("line_id")
        cls = c.get("classification")
        if cls not in CLASS_VALUES:
            _err(f"未知の classification 値です: {cls!r}（行 {lid}）")
        class_by_id[lid] = c
    class_ids = set(class_by_id.keys())
    if hit_ids != class_ids:
        missing = hit_ids - class_ids
        extra = class_ids - hit_ids
        _err(f"hits と classification の line_id が一致しません。missing={sorted(missing)} extra={sorted(extra)}")

    log_path = Path(data["discovery_log"])
    if not data["wave_write_complete"]:
        _truncate_wave_section(log_path, wave)

    def _entry_key(hit) -> str:
        return hit.get("entry") or _format_entry(hit["symbol"], hit["scope_file"])

    def _is_llm(hit) -> bool:
        return hit.get("route", "llm") == "llm"

    # 高ノイズシンボル判定（1パス目）。LLM 分類に回るヒットだけが対象（スライス判定・規則判定は予算が代わりを担う）。
    files_by_key = {}
    for h in hits:
        if _is_llm(h):
            files_by_key.setdefault(_entry_key(h), set()).add(h["file"])
    # pre_noisy（search 側の代表サブセット化でファイル数を過小計上しうる）を union することで、
    # 代表サブセット化後も伝播抑止条件（noisy_keys）が等価に保たれる。
    noisy_keys = {k for k, files in files_by_key.items() if len(files) > data["max_files_per_module"]} | pre_noisy

    # 同名 MEDIUM シンボル・異スコープ重複グループの特定
    multi_scope_symbols = {sym: scopes for sym, scopes in frontier_medium_scopes.items() if len(set(scopes)) >= 2}
    case_rows = []
    case_a_symbols = {}  # symbol -> (trigger_scope, discarded_scopes)
    for sym, scopes in multi_scope_symbols.items():
        scopes = sorted(set(scopes))
        sym_hits = [h for h in hits if h["symbol"] == sym and h["scope_file"] in scopes
                    and _entry_scope_kind(_entry_key(h)) == SCOPE_MEDIUM]
        total_hits = len(sym_hits)
        trigger_scope = None
        for h in sym_hits:
            cls = class_by_id[h["line_id"]]
            if cls.get("is_external_api") and cls["classification"] not in NO_PROPAGATION_CLASSES:
                trigger_scope = h["scope_file"]
                break
        if trigger_scope:
            discarded = [s for s in scopes if s != trigger_scope]
            case_a_symbols[sym] = (trigger_scope, discarded)
            case_rows.append((sym, scopes, LV.CASE_A, LV.action_promote_high(discarded)))
        elif total_hits == 0:
            case_rows.append((sym, scopes, LV.CASE_B, LV.ACTION_MANUAL_CHECK))
        else:
            case_rows.append((sym, scopes, LV.CASE_C, LV.ACTION_KEEP_VISITED))

    discarded_command_ids = set()
    for sym, (trigger_scope, discarded) in case_a_symbols.items():
        for c in commands:
            if c["kind"] == "MEDIUM" and c["scope"] in discarded:
                discarded_command_ids.add(c["command_id"])

    # 派生元の解決: シードのグローバル → その波のシード → 派生元の行ID → unknown-origin
    # シードのグローバルはエントリ文字列で持つため、ヒットのエントリで照合する。
    seed_globals = set(data.get("seed_globals") or [])

    def _origin_text(hit) -> str:
        if _entry_key(hit) in seed_globals:
            return LV.origin_seed_global(_entry_key(hit))
        if _entry_key(hit) in seed_symbols:
            return LV.origin_seed(hit["symbol"])
        origins = data["symbol_origin_map"].get(_entry_key(hit))
        if origins:
            return ", ".join(origins)
        return LV.ORIGIN_UNKNOWN

    # 同一性: ヒット1件の値（スライス判定が付けた identity。LLM 分類・値の無いものは name-only）と、検索したエントリの
    # 同一性（entry_identity。値の無いエントリは name-only）がともに resolved なら、経路の同一性は resolved。
    entry_identity = data.setdefault("entry_identity", {})

    def _path_identity(hit) -> str:
        cls = class_by_id[hit["line_id"]]
        if cls["classification"] == "false-positive":
            return LV.IDENTITY_NONE
        own = cls.get("identity") or LV.IDENTITY_NAME_ONLY
        if own == LV.IDENTITY_RESOLVED and entry_identity.get(_entry_key(hit)) == LV.IDENTITY_RESOLVED:
            return LV.IDENTITY_RESOLVED
        return LV.IDENTITY_NAME_ONLY

    path_identity = {h["line_id"]: _path_identity(h) for h in hits}

    rows = []
    next_candidates = []  # list of (entry_string, [origin_line_ids])
    new_symbol_origin = {}
    next_identity = {}    # 次の波のエントリの同一性（送り手の経路の1つでも resolved なら resolved）

    for h in hits:
        cls = class_by_id[h["line_id"]]
        cls_value = cls["classification"]
        key = _entry_key(h)
        enclosing = cls.get("enclosing_function") or "-"
        origin_text = _origin_text(h)
        next_syms = cls.get("next_symbols") or []
        noisy_stop = _is_llm(h) and key in noisy_keys
        if cls_value not in NO_PROPAGATION_CLASSES and not noisy_stop and not _is_discarded_scope(h, case_a_symbols):
            name_only_syms = set(cls.get("name_only_symbols") or [])
            for ns in next_syms:
                next_candidates.append((ns, h["line_id"]))
                new_symbol_origin.setdefault(ns, []).append(h["line_id"])
                resolved = path_identity[h["line_id"]] == LV.IDENTITY_RESOLVED and ns not in name_only_syms
                if resolved:
                    next_identity[ns] = LV.IDENTITY_RESOLVED
                else:
                    next_identity.setdefault(ns, LV.IDENTITY_NAME_ONLY)
        display_next = ", ".join(f"`{s}`" for s in next_syms) if (next_syms and cls_value not in NO_PROPAGATION_CLASSES) else "—"
        rows.append([
            h["line_id"], h["command_id"], f"`{key}`", h["file"], str(h["line_no"]),
            f"`{h['matched_text']}`",
            f"`{enclosing}`" if enclosing != "-" else "-",
            LV.propagation_label(cls_value, cls.get("slice")),
            CONFIDENCE_FOR_CLASS.get(cls_value, "-"),
            path_identity[h["line_id"]],
            display_next, origin_text,
        ])

    # ケースA: symbol(HIGH) を候補へ追加
    for sym, (trigger_scope, discarded) in case_a_symbols.items():
        inherited = []
        for s in set([trigger_scope] + discarded):
            inherited.extend(data["symbol_origin_map"].get(_format_entry(sym, s), []))
        next_candidates.append((sym, None))
        next_identity.setdefault(sym, LV.IDENTITY_NAME_ONLY)   # LLM 分類の is_external_api による昇格
        new_symbol_origin.setdefault(sym, [])
        new_symbol_origin[sym] = list(dict.fromkeys(new_symbol_origin[sym] + inherited))
        # ケースAトリガーとなった sym[MEDIUM:*] 自体の再追加は行わない
        next_candidates = [(e, o) for e, o in next_candidates if not (MEDIUM_RE.match(e) and _parse_entry(e)[0] == sym)]

    # visited 更新
    visited = set(data["visited"])
    for entry in searched_frontier:
        visited.add(entry)

    # シンボルの種類（予算の優先順位・ヒット側の除外に使う）: スライス判定・規則判定のエントリの next_symbol_kinds を
    # summary_key で登録する（同じ鍵に複数の種類が付いたら KIND_PRIORITY の順）。next_symbol_kinds が無いエントリは
    # enclosing_function と同じものを function、それ以外を value とする。LLM 分類の next_symbols は登録しない。
    kinds = data.setdefault("symbol_kinds", {})
    for h in hits:
        cls = class_by_id[h["line_id"]]
        if not cls.get("slice"):
            continue
        given = cls.get("next_symbol_kinds") or {}
        for ns in cls.get("next_symbols") or []:
            base = _parse_entry(ns)[0]
            key = summary_key(ns)
            if ns in given:
                kind = given[ns]
            else:
                kind = "function" if base == cls.get("enclosing_function") else "value"
            if key not in kinds or _kind_rank(kind) < _kind_rank(kinds[key]):
                kinds[key] = kind

    # 要約の拡大による再訪: スライス判定の next_symbol_summaries をシンボルごとにマージし、マージ前の要約より
    # 広がった visited 済みの関数シンボルを次の frontier に戻す（dedup の鍵が変わるため呼び出し元を判定し直す）。
    summaries = data.setdefault("symbol_summaries", {})
    merged_new = {}
    for h in hits:
        cls = class_by_id[h["line_id"]]
        for sym, summ in (cls.get("next_symbol_summaries") or {}).items():
            merged_new[sym] = _merge_summary(merged_new[sym], summ) if sym in merged_new else _merge_summary({}, summ)
    revisits = []
    # 再訪は summary_key で判定する（`f[FILE:p]` の関数シンボルも素名で再訪する。`[CLASS:…]` はそのクラスのエントリだけ。
    # MEDIUM のエントリは対象外）。
    visited_bases = {summary_key(e) for e in visited if _entry_scope_kind(e) != SCOPE_MEDIUM}
    for sym in sorted(merged_new):
        old = summaries.get(sym)
        new = _merge_summary(old, merged_new[sym]) if old else merged_new[sym]
        if old and sym in visited_bases and kinds.get(sym) == "function":
            grown = _summary_growth(old, new)
            if grown:
                revisits.append((sym, grown))
        summaries[sym] = new
    revisit_syms = {sym for sym, _ in revisits}

    # HIGH/MEDIUM 交差ルール + dedup
    seen = set()
    next_frontier = []
    high_visited = {e for e in visited if _parse_entry(e)[1] is None}
    for entry, _origin in next_candidates:
        if entry in seen:
            continue
        symbol, _scope = _parse_entry(entry)
        scope_kind = _entry_scope_kind(entry)
        # 交差ルールは MEDIUM だけ（`[FILE:…]` は同名の修飾なしのエントリとは別物）
        if scope_kind == SCOPE_MEDIUM and symbol in high_visited:
            continue
        if entry in visited and not (scope_kind != SCOPE_MEDIUM and summary_key(entry) in revisit_syms):
            continue
        seen.add(entry)
        next_frontier.append(entry)

    # 次の波のエントリの同一性（visited のエントリも、resolved の経路が届けば entry_identity だけを上げる。下げない）
    for entry, value in next_identity.items():
        _raise_identity(entry_identity, entry, value)

    # symbol_origin_map 更新
    for k, v in new_symbol_origin.items():
        existing = data["symbol_origin_map"].get(k, [])
        merged = list(dict.fromkeys(existing + v))
        data["symbol_origin_map"][k] = merged

    # confirmed_files 更新。false-positive のヒットだけでは確定せず、false_positive_files に記録する
    # （後の波で false-positive 以外の判定でヒットすれば、その波で確定して false_positive_files から外す）。
    # out-of-scope-discard は参照の事実を否定しない判定のため確定する。
    # 同一性（identity）は確信度とは独立に更新する（name-only → resolved に上げ、下げない）。
    fp_files = data.get("false_positive_files") or {}

    def _confirm(path_: str, conf: str, identity: str) -> None:
        existing = data["confirmed_files"].get(path_)
        if existing is None:
            data["confirmed_files"][path_] = {"wave": wave, "confidence": conf, "identity": identity}
            return
        if CONFIDENCE_RANK.get(conf, 0) > CONFIDENCE_RANK.get(existing["confidence"], 0):
            existing.update({"wave": wave, "confidence": conf})
        if identity == LV.IDENTITY_RESOLVED:
            existing["identity"] = LV.IDENTITY_RESOLVED
        else:
            existing.setdefault("identity", LV.IDENTITY_NAME_ONLY)

    for c in commands:
        conf = _confidence_label(c["kind"])
        for h in hits:
            if h["command_id"] != c["command_id"]:
                continue
            if class_by_id[h["line_id"]]["classification"] == "false-positive":
                if h["file"] not in data["confirmed_files"]:
                    fp_files.setdefault(h["file"], wave)
                continue
            fp_files.pop(h["file"], None)
            _confirm(h["file"], conf, path_identity[h["line_id"]])

    # PLAN-20260806 Phase 2A: pre-noisy シンボルの全ファイル（module_files）を confirmed_files へ反映する。
    # 非代表ファイルは hits に現れないためここで補う（confirmed_files 網羅の維持＝漏れゼロの要。全 pre-noisy シンボルは
    # HIGH のため confidence=HIGH）。module_files は代表ファイルも含み、代表行以外は判定していないため、代表行が
    # false-positive でも保守的に確定させる（縮退ありの確定ファイルは縮退なしの上位集合になる）。
    for files in module_files.values():
        for f in files:
            fp_files.pop(f, None)
            _confirm(f, "HIGH", LV.IDENTITY_NAME_ONLY)
    data["false_positive_files"] = fp_files

    # モジュール優先度の初期構築（Wave 0 完了時のみ）
    if data.get("module_catalog_file") and not data.get("module_priority_computed") and wave == 0:
        catalog_path = Path(data["module_catalog_file"])
        if catalog_path.exists():
            confirmed_modules = {_module_dir_for_file(data["repo_path"], f) for f in data["confirmed_files"]}
            _, _, _, symbol_to_module = _parse_module_catalog(catalog_path.read_text(encoding="utf-8"))
            for entry in searched_frontier:
                sym, _scope = _parse_entry(entry)
                if sym in symbol_to_module:
                    confirmed_modules.add(symbol_to_module[sym])
            data["module_priority_map"] = _compute_module_priority(catalog_path.read_text(encoding="utf-8"), confirmed_modules)
            data["module_priority_computed"] = True
            data["module_priority_mode"] = "catalog"
    # PLAN-20260806 Phase 2B: module_catalog_file 不在時の簡易近傍優先（既存の catalog 経路は不変）。
    elif not data.get("module_catalog_file") and not data.get("module_priority_computed") and wave == 0:
        base_dirs = {_dir_for_file(data["repo_path"], f) for f in data["confirmed_files"]}
        if base_dirs:
            data["module_priority_map"] = _simple_neighbor_priority(data["repo_path"], base_dirs)
            data["module_priority_computed"] = True
            data["module_priority_mode"] = "simple"

    # 次波シンボルの module 記録（優先度マップがある場合の次波振り分けに使用）
    if data.get("module_priority_computed"):
        dir_fn = _dir_for_file if data.get("module_priority_mode") == "simple" else _module_dir_for_file
        for entry in next_frontier:
            if entry in data["symbol_module"]:
                continue
            for h in hits:
                if any(ns == entry for ns in (class_by_id[h["line_id"]].get("next_symbols") or [])):
                    data["symbol_module"][entry] = dir_fn(data["repo_path"], h["file"])
                    break

    # 高ノイズシンボルの記録
    newly_noisy = [k for k in noisy_keys if k not in data["high_noise_symbols"]]
    data["high_noise_symbols"].extend(newly_noisy)

    # --- discovery-log.md への書き出し ---
    log_lines = [f"## Wave {wave}", "", "### 実行コマンド一覧",
                 "| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |",
                 "|---|---|---|---|---|"]
    for c in commands:
        log_lines.append(
            f"| {_md_cell(c['command_id'])} | {_md_cell(c['kind'])} | `{_md_cell(c['pattern'])}` "
            f"| {_md_cell(c['scope'])} | {c['hit_count']} |"
        )
    log_lines.append("")
    excl = ",".join(data["exclude_patterns"]) if data["exclude_patterns"] else "(なし)"
    log_lines.append(f"**除外:** {excl}")
    log_lines.append("")
    # 注記の直後には必ず空行を置く（GFM の lazy continuation でテーブルが引用平文に吸収されるのを防ぐ）。
    log_lines.append(r"> セル内の \| はエスケープされた | である。")
    log_lines.append("")
    log_lines.append("| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | 含む関数/クラス | "
                      "伝播種別 | 確信度 | 同一性 | Wave {} 追加シンボル | 派生元 |".format(wave + 1))
    log_lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for row in rows:
        log_lines.append("| " + " | ".join(_md_cell(cell) for cell in row) + " |")
    log_lines.append("")
    if next_frontier:
        log_lines.append(f"→ Wave {wave + 1} frontier: " + ", ".join(
            f"`{_parse_entry(e)[0]}`[{_frontier_tag(e)}]" for e in next_frontier
        ))
    else:
        log_lines.append("→ 空。新規発見なし。探索終了。" if not data.get("low_priority_frontier") else
                          f"→ Wave {wave + 1} frontier: (MODULE_PRIORITY_LOW 分へ移行)")
    log_lines.append("")

    # 見出しの後の空行は specout_verify_counts.py が書き直す表と同じ形にするため（再検証で見出しが重複しない）。
    log_lines.append("### 件数一致検証")
    log_lines.append("")
    log_lines.append("| コマンドID | ヒット行数（生） | dedup除外 | フィルタ除外 | noise-collapse除外 | 記録行数 | 一致 |")
    log_lines.append("|---|---|---|---|---|---|---|")
    for c in commands:
        recorded = sum(1 for h in hits if h["command_id"] == c["command_id"])
        d = c.get("dedup_removed", 0)
        # 「フィルタ除外」列は保守的フィルタと予算による除外の合計（列の構成と照合式は変えない）。
        f = c.get("filter_removed", 0) + c.get("budget_removed", 0)
        nc = c.get("noise_collapse_removed", 0)
        # 生 = 記録 + dedup除外 + フィルタ除外 + noise-collapse除外
        mark = LV.verify_mark(c["hit_count"], recorded, d, f, nc,
                              discarded=c["command_id"] in discarded_command_ids)
        log_lines.append(f"| {_md_cell(c['command_id'])} | {c['hit_count']} | {d} | {f} | {nc} | {recorded} | {_md_cell(mark)} |")
    log_lines.append("")

    if newly_noisy:
        log_lines.append("## 高ノイズシンボル（上限超過のため波及停止）")
        log_lines.append("| シンボル | 発見波 | 発見ファイル数 | 備考 |")
        log_lines.append("|---|---|---|---|")
        for k in newly_noisy:
            sym, scope = _parse_entry(k)
            if k in pre_noisy:
                # PLAN-20260806 Phase 2A: search 側で前倒し縮退済み。真のファイル数は module_files
                # （全ファイル）にあり、files_by_key（代表サブセットのみ反映）より正確。
                file_count = len(module_files.get(k, files_by_key.get(k, set())))
                note = "前倒し縮退（代表行のみ分類、全ファイルはconfirmed_filesへ記録済み）"
            else:
                file_count = len(files_by_key.get(k, set()))
                note = "手動確認推奨"
            log_lines.append(f"| `{_md_cell(sym)}` | Wave {wave} | {file_count} | {_md_cell(note)} |")
        log_lines.append("")

    if case_rows:
        log_lines.append("## 同名 MEDIUM シンボル・異スコープ重複ログ（発生時のみ記録）")
        log_lines.append("| Wave | シンボル | 検出スコープ一覧 | ケース | 処置 |")
        log_lines.append("|---|---|---|---|---|")
        for sym, scopes, case_label, action in case_rows:
            scope_cell = ", ".join("`" + _md_cell(s) + "`" for s in scopes)
            log_lines.append(f"| Wave {wave} | `{_md_cell(sym)}` | {scope_cell} | {_md_cell(case_label)} | {_md_cell(action)} |")
        log_lines.append("")

    # PLAN-20260804 Phase 1a/1b: 除外行の監査記録（無音縮退の禁止）。dedup＝過去波で分類済みの再出現、
    # line-comment＝行全体が行コメント（拡張子で言語別解決）。人が漏れを検知できるよう全件記録する。
    if filtered_out:
        log_lines.append("## フィルタ除外一覧（Wave {}・監査用）".format(wave))
        log_lines.append("| ファイル | 行 | シンボル | 除外理由 |")
        log_lines.append("|---|---|---|---|")
        for fo in filtered_out:
            reason = {"dedup": "分類済み再出現（dedup）", "line-comment": "行コメント（保守的フィルタ）"}.get(fo["reason"], fo["reason"])
            log_lines.append(f"| {_md_cell(fo['file'])} | {fo['line_no']} | `{_md_cell(fo.get('entry') or fo['symbol'])}` "
                             f"| {_md_cell(reason)} |")
        log_lines.append("")

    _append_to_file(log_path, "\n".join(log_lines))

    # 打ち切り記録（予算・検索ツールの制約）。state の truncated が単一情報源。
    if budget_truncated:
        data.setdefault("truncated", []).extend(budget_truncated)
    _upsert_truncation_section(str(log_path), data)

    # 要約の拡大による再訪の記録。
    _upsert_section(str(log_path), REVISIT_HEADING_FMT.format(n=wave),
                    ("| シンボル | 広がった項目 |\n|---|---|\n"
                     + "\n".join(f"| `{_md_cell(sym)}` | {_md_cell(', '.join(grown))} |" for sym, grown in revisits)
                     + "\n") if revisits else "")

    # シードの直接参照ファイル（シードが偽陽性・out-of-scope-discard 以外でヒットしたファイル）。
    seed_direct = set(data.get("seed_direct_files") or [])
    seed_direct_hits = dict(data.get("seed_direct_hits") or {})
    for h in hits:
        if _entry_key(h) in seed_symbols and class_by_id[h["line_id"]]["classification"] not in NO_PROPAGATION_CLASSES:
            seed_direct.add(h["file"])
            seed_direct_hits[h["file"]] = seed_direct_hits.get(h["file"], 0) + 1
    data["seed_direct_files"] = sorted(seed_direct)
    data["seed_direct_hits"] = dict(sorted(seed_direct_hits.items()))

    # PLAN-20260806 Phase 3 Stage 2 §4.5(e): 並列 classifier が discovery-log.md を各自 Edit すると
    # 書き込み競合が起きるため、書き手を commit-wave（単一）に集約する。ファイル未指定時は
    # 何もしない（既存呼び出しと完全に同一挙動＝後方互換）。
    if args.unsupported_patterns:
        unsupported_entries = json.loads(Path(args.unsupported_patterns).read_text(encoding="utf-8"))
        _append_unsupported_patterns(log_path, unsupported_entries)

    # 当該波で分類した (symbol,file,line,scope_class) を classified_locations へ登録する。鍵のスコープ種別は
    # search が検索した時点の値（loc_scope_class。要約付きの関数シンボルは HIGH#{要約の正規形}）をそのまま使う。
    classified_set = set(data.get("classified_locations") or [])
    for h in hits:
        sc_class = h.get("loc_scope_class") or ("HIGH" if h["scope_file"] is None else h["scope_file"])
        classified_set.add("\x00".join([h["symbol"], h["file"], str(h["line_no"]), sc_class]))
    data["classified_locations"] = sorted(classified_set)
    # 肥大対策（PLAN-20260804 §3.1・指摘#6）: サイズを metrics に記録し、閾値超で discovery-log へ一度だけ警告。
    # （confirmed_files 由来キーの自動退避は「最も再ヒットしやすい確定ファイルの dedup 効果を失わせる」ため
    #  既定では行わず、サイズ監視＋警告で肥大を可視化する方針とした。詳細は PLAN §3.1 実装メモ参照。）
    cl_size = len(classified_set)
    CLASSIFIED_LOCATIONS_WARN = 200000
    if cl_size > CLASSIFIED_LOCATIONS_WARN and not data.get("classified_locations_warned"):
        _append_to_file(log_path, f"\n> ⚠️ classified_locations が {cl_size} 件に到達（dedup 用集合の肥大）。"
                                   "state ファイルの load/write コスト増に注意。\n")
        data["classified_locations_warned"] = True

    # PLAN-20260806 Phase 3 Stage 1 §4.5(c)(d): 分類区間の壁時計を算出する。
    # 一次防御は波一致検証（α＝開始時刻の波不一致なら null）。算出の成否によらず2キーは消費後破棄する。
    classify_started_at = data.get("classify_started_at")
    classify_started_wave = data.get("classify_started_wave")
    classify_wall_ms = None
    classify_wall_ms_reused = None
    if classify_started_at is not None and classify_started_wave == wave:
        # 再利用波の判定（過小計測の防止）: §4.7 の再開手順は既存 classification の再利用を許容するため、
        # 再利用波の classify_wall_ms は実際の分類所要時間ではなく数秒〜数十秒の過小値になる。
        # classification ファイルの mtime が再 search より古ければ再利用と機械判定する
        # （LLM の自己申告に依存しない）。mtime が取得できない異常時は判定不能（null）とし、
        # 計測専用の値のため commit-wave 自体は失敗させない。
        # 既知の限界（BUG-005, PLAN-20260901）: NTP補正等でシステム時刻が調整されると、mtime と
        # classify_started_at の前後関係が実態と逆転する可能性があり、本ロジックはこの逆転を
        # 検出しない（両者とも過去時刻のまま相対順序だけが入れ替わるケースは reused の判定を
        # 誤りうる）。完全に検出するには単調クロックの併用や内容ハッシュ化が必要だが、この値は
        # metrics.jsonl の計測専用フィールドでありデータの正しさ（line_id 照合等）には影響しない
        # ため、対応は見送る。
        # PLAN-20260806 Phase 3 Stage 2 §4.5(d)「判定方法〔S2〕」: --classification は
        # merge_classification.py が毎波その場で生成するため OS mtime では再利用を検出できない。
        # --chunk-mtime-min（merge_classification.py が集めたチャンク OUT_FILE mtime の最小値）が
        # 指定されていればその値を優先し、未指定なら従来どおりファイル mtime を用いる（S1 呼び出しは不変）。
        reuse_mtime = args.chunk_mtime_min if args.chunk_mtime_min is not None else _file_mtime(Path(args.classification))
        if reuse_mtime is not None:
            classify_wall_ms_reused = reuse_mtime < classify_started_at
        if not classify_wall_ms_reused:
            classify_wall_ms = int((time.time() - classify_started_at) * 1000)
    _drop_classify_timer(data)
    # 値なし（null）と閾値内（false）を集計側で区別できるよう、null の場合は false ではなく null とする。
    classify_wall_ms_suspect = (
        None if classify_wall_ms is None else classify_wall_ms > CLASSIFY_WALL_MS_SUSPECT_THRESHOLD_MS
    )

    # PLAN-20260804 Phase 0: per-wave metrics を bfs-state.json と同じディレクトリの metrics.jsonl へ1行追記。
    # 時間値（search_ms・classify_wall_ms）は非決定のため metrics 専用とし state 判定には持ち込まない
    # （再開の決定性保持）。
    # slice_classify_ms: スライス用チャンクの判定時間（specout_slice.py classify の elapsed_ms）。
    # classify_wall_ms は「スライス判定・規則判定と LLM 分類の合計」であり、LLM 分類の所要時間を見る場合は
    # llm_hits > 0 の波について classify_wall_ms - slice_classify_ms を使う（波ループで b-0 が b-1 より先に順に走る）。
    slice_classify_ms = None
    slice_class_path = Path(args.hits).parent / f"wave-{wave}-chunk-S-class.json"
    if slice_class_path.is_file():
        try:
            slice_classify_ms = json.loads(slice_class_path.read_text(encoding="utf-8")).get("elapsed_ms")
        except ValueError:
            slice_classify_ms = None
    route_hits = {"slice": 0, "llm": 0}
    for h in hits:
        route_hits["llm" if _is_llm(h) else "slice"] += 1
    engine = data.get("slice_engine") or "rule"
    metrics_line = {
        "wave": wave,
        "search_ms": wave_metrics.get("search_ms", 0),
        "index_build_ms": wave_metrics.get("index_build_ms", 0),
        "raw_hits": wave_metrics.get("raw_hits", 0),
        "dedup_removed": wave_metrics.get("dedup_removed", 0),
        "filter_removed": wave_metrics.get("filter_removed", 0),
        "noise_collapse_removed": wave_metrics.get("noise_collapse_removed", 0),
        "classified": len(hits),
        "hit_budget_removed": wave_metrics.get("hit_budget_removed", 0),
        "llm_budget_removed": wave_metrics.get("llm_budget_removed", 0),
        "slice_hits": route_hits["slice"] if engine == "slice" else 0,
        "rule_hits": route_hits["slice"] if engine != "slice" else 0,
        "llm_hits": route_hits["llm"],
        "slice_classify_ms": slice_classify_ms,
        "revisit_count": len(revisits),
        "classified_locations_size": cl_size,
        "next_frontier": len(next_frontier),
        # PLAN-20260806 Phase 3 Stage 1 §4.5(d)
        "classify_wall_ms": classify_wall_ms,
        "classify_wall_ms_reused": classify_wall_ms_reused,
        "classify_wall_ms_suspect": classify_wall_ms_suspect,
        "chunk_count": args.chunk_count,
        "batch_count": args.batch_count,       # 観測値（呼び出し側が実際に起動したバッチ数）
        "parallelism": args.parallelism,       # 設定値（実際の並列起動数の観測値ではない）
    }
    metrics_path = Path(args.path).parent / "metrics.jsonl"
    with open(metrics_path, "a", encoding="utf-8", newline="\n") as mf:
        mf.write(json.dumps(metrics_line, ensure_ascii=False) + "\n")

    # --- 状態更新 ---
    data["visited"] = sorted(visited)
    data["frontier"] = next_frontier
    data["last_completed_wave"] = wave
    data["wave_write_complete"] = True
    data["confirmed_file_count"] = len(data["confirmed_files"])

    if not next_frontier and not data.get("low_priority_frontier"):
        data["state"] = "complete"
    else:
        data["current_wave"] = wave + 1

    _upsert_confirmed_files_section(log_path, data)
    _upsert_false_positive_files_section(log_path, data)
    _write_state(state_path, data)

    print(json.dumps({
        "ok": True, "wave": wave, "state": data["state"], "next_frontier_count": len(next_frontier),
        "high_noise_symbols": newly_noisy, "case_a_promoted": list(case_a_symbols.keys()),
        "dedup_removed": metrics_line["dedup_removed"], "filter_removed": metrics_line["filter_removed"],
        "noise_collapse_removed": metrics_line["noise_collapse_removed"],
        "classified_locations_size": cl_size, "revisit_count": len(revisits),
        "truncated_count": len(budget_truncated),
    }, ensure_ascii=False))


def _frontier_tag(entry: str) -> str:
    """frontier の行の表示: 修飾なしは HIGH、MEDIUM は MEDIUM、FILE・CLASS はスコープ込み（FILE:path・CLASS:ClassName）。"""
    kind = _entry_scope_kind(entry)
    if kind in (SCOPE_FILE, SCOPE_CLASS):
        return f"{kind}:{_parse_entry(entry)[1]}"
    return "MEDIUM" if kind == SCOPE_MEDIUM else "HIGH"


def _is_discarded_scope(hit, case_a_symbols) -> bool:
    """ケースA の破棄（MEDIUM のヒットだけ。同じファイルの `[FILE:…]` のヒットは破棄しない）。"""
    sym = hit["symbol"]
    scope = hit["scope_file"]
    entry = hit.get("entry") or _format_entry(sym, scope)
    if sym in case_a_symbols and scope is not None and _entry_scope_kind(entry) == SCOPE_MEDIUM:
        _trigger, discarded = case_a_symbols[sym]
        return scope in discarded
    return False


# ---------------------------------------------------------------------------
# status / set-state / merge-frontier / re-discover / import
# ---------------------------------------------------------------------------

def cmd_status(args) -> None:
    data = _load_state(Path(args.path))
    if getattr(args, "brief", False):
        # PLAN-20260806 Phase 3 Stage 2 §4.5(f): remaining_frontier_count は commit-wave の complete 判定
        # （not next_frontier and not low_priority_frontier）と同じ集合＝frontier + low_priority_frontier。
        # bfs-state.json に next_frontier というフィールドは存在しない（state 由来でないことが名前から
        # 分かるよう remaining_frontier_count とする）。
        remaining = len(data.get("frontier") or []) + len(data.get("low_priority_frontier") or [])
        print(json.dumps({
            "ok": True,
            "state": data["state"],
            "current_wave": data["current_wave"],
            "wave_write_complete": data["wave_write_complete"],
            "remaining_frontier_count": remaining,
            "confirmed_file_count": data.get("confirmed_file_count", 0),
            "max_wave_depth": data.get("max_wave_depth", 6),
            "truncated_wave_limit_count": sum(1 for t in data.get("truncated") or []
                                              if t.get("reason") == LV.TRUNC_WAVE_LIMIT),
            "slice_engine": data.get("slice_engine") or "rule",
            "seed_direct_file_count": len(data.get("seed_direct_files") or []),
            "seed_budget_truncated_count": len(_seed_budget_truncated(data)),
            "name_only_file_count": _name_only_file_count(data),
        }, ensure_ascii=False))
        return
    # PLAN-20260809: MODE: document Step 1.5（code-knowledge 参照）が confirmed_modules を
    # 決定的に取得するための追加フィールド。state ファイルへは永続化しない（出力時の派生値のみ）。
    confirmed_modules = sorted({
        _module_dir_for_file(data["repo_path"], f) for f in data.get("confirmed_files", {})
    })
    print(json.dumps({"ok": True, **data, "confirmed_modules": confirmed_modules}, ensure_ascii=False))


def _seed_budget_truncated(data: dict) -> list:
    """予算（hit-budget）で丸ごと打ち切った投入シンボル（第0波のシード・人が入れたシンボル。シードのグローバルを除く）。"""
    seed_globals = set(data.get("seed_globals") or [])
    entry_syms = set(data.get("entry_point_symbols") or [])
    out = []
    for t in data.get("truncated") or []:
        if t.get("reason") != LV.TRUNC_HIT_BUDGET:
            continue
        e = t.get("symbol") or ""
        if _seed_entries([e], int(t.get("wave") or 0), seed_globals, entry_syms):
            out.append(e)
    return sorted(set(out))


def cmd_set_state(args) -> None:
    if args.state not in VALID_STATES:
        _err(f"不正な状態です: {args.state}（有効値: {', '.join(sorted(VALID_STATES))}）")
    state_path = Path(args.path)
    data = _load_state(state_path)
    data["state"] = args.state
    _drop_classify_timer(data)  # PLAN-20260806 Phase 3 Stage 1 §4.5(c)（search を経ない状態遷移）
    _write_state(state_path, data)
    print(json.dumps({"ok": True, "state": data["state"]}, ensure_ascii=False))


def cmd_merge_frontier(args) -> None:
    state_path = Path(args.path)
    data = _load_state(state_path)
    symbols = _split_csv(args.symbols)
    _validate_frontier_format(symbols)
    added = [s for s in symbols if s not in data["frontier"]]
    data["frontier"].extend(added)
    eps_raw = getattr(args, "entry_point_symbols", None)
    eps = _split_csv(eps_raw) if eps_raw is not None else []
    if eps_raw is not None:
        # state は frontier と同じく追記（和集合）。未指定時は既存値を保持する。
        existing = list(data.get("entry_point_symbols") or [])
        data["entry_point_symbols"] = existing + [s for s in eps if s not in existing]
    result = {"ok": True, "added": added, "frontier_count": len(data["frontier"])}
    payload = None
    if getattr(args, "summaries_file", None):
        p = Path(args.summaries_file)
        if not p.is_file():
            _err(f"--summaries-file が見つかりません: {p}")
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
        except ValueError as e:
            _err(f"--summaries-file を JSON として読めません: {p}（{e}）")
        if not isinstance(payload, dict) or not isinstance(payload.get("targets"), list) \
                or not isinstance(payload.get("summaries"), dict):
            _err(f"--summaries-file の形式が不正です（{{targets: [...], summaries: {{...}}}}）: {p}")
    # 同一性: ENTRY_POINTS（--entry-point-symbols）とシードのグローバルは resolved（シードの要約で extern の宣言が
    # 見えない定義として解決したもの〔--summaries-file の name_only〕は name-only）。それ以外は既存の値を保つ。
    resolved = set(eps)
    if getattr(args, "as_seed_globals", False):
        resolved |= set(symbols)
    _set_input_identity(data, list(dict.fromkeys(symbols + eps)), resolved,
                        set((payload or {}).get("name_only") or []))
    if getattr(args, "as_seed_globals", False) and symbols:
        # シード関数が書くグローバル: シードの診断（未ヒット・ヒット過多・予算）に混ぜず、変数シンボルとして扱う。
        existing = list(data.get("seed_globals") or [])
        data["seed_globals"] = existing + [s for s in symbols if s not in existing]
        kinds = data.setdefault("symbol_kinds", {})
        for sym in symbols:
            key = summary_key(sym)
            if key not in kinds or _kind_rank("variable") < _kind_rank(kinds[key]):
                kinds[key] = "variable"
    if payload is not None:
        summaries = data.setdefault("symbol_summaries", {})
        for sym, summ in payload["summaries"].items():
            summaries[sym] = _merge_summary(summaries[sym], summ) if sym in summaries else _merge_summary({}, summ)
        done = set(payload["targets"])
        data["seed_summary_pending"] = [s for s in data.get("seed_summary_pending") or [] if s not in done]
        result["summaries_merged"] = len(payload["summaries"])
        result["seed_summary_pending_count"] = len(data["seed_summary_pending"])
    if getattr(args, "reset_wave_origin", False) and symbols:
        # 人が加えたシンボルを上限の波数まで調べるため、探索の起点を次に検索する波に置き直す。
        data["wave_origin"] = data["current_wave"]
        result["wave_origin"] = data["wave_origin"]
        _mark_seed_summary_pending(data, symbols)
    _write_state(state_path, data)
    if eps:
        unparsed = _update_origin_entry_points(data.get("discovery_log") or "", eps)
        if unparsed:
            result["origin_unparsed_tokens"] = unparsed
    print(json.dumps(result, ensure_ascii=False))


def _mark_seed_summary_pending(data: dict, entries: list) -> None:
    """判定エンジンが slice なら、人が入れたシンボルを「シード要約の取り込み待ち」に加える（search が exit 6 で検出する）。
    `x[FILE:p]`・`x[CLASS:X]` はエントリ文字列のまま記録する（seed-summary が p から呼べる定義・X の定義で要約する）。
    それ以外は素名。"""
    if (data.get("slice_engine") or "rule") != "slice":
        return
    pending = list(data.get("seed_summary_pending") or [])
    for e in entries:
        sym = e if _entry_scope_kind(e) in (SCOPE_FILE, SCOPE_CLASS) else _parse_entry(e)[0]
        if sym and sym not in pending:
            pending.append(sym)
    data["seed_summary_pending"] = pending


def cmd_re_discover(args) -> None:
    state_path = Path(args.path)
    data = _load_state(state_path)
    if data["state"] != "complete":
        _err(f"re-discover は checkpoint 状態が complete の場合のみ実行できます（現在: {data['state']}）")
    symbols = _split_csv(args.symbols)
    n = data["last_completed_wave"]
    data["state"] = "in-progress"
    data["frontier"] = symbols
    data["current_wave"] = n + 1
    # 探索の起点の波を再開する波に置き直す（波数上限はこの波から数え直す）。
    data["wave_origin"] = n + 1
    data["wave_write_complete"] = True
    _mark_seed_summary_pending(data, symbols)
    _drop_classify_timer(data)  # PLAN-20260806 Phase 3 Stage 1 §4.5(c)（search を経ない状態遷移）
    eps_raw = getattr(args, "entry_point_symbols", None)
    eps = _split_csv(eps_raw) if eps_raw is not None else []
    if eps_raw is not None:
        # state は frontier と同じく置換（今回の波の検出スコープ）。
        # 未指定は「空を指定した」ではないため既存値を保持する（空で置換すると検出が静かに無効化される）。
        data["entry_point_symbols"] = eps
    # 同一性: --entry-point-symbols は --entry-identity の値（既定 resolved）。--symbols だけにある残存 frontier 等は
    # 既存の値を保ち、無ければ name-only。既に resolved のエントリは下げない。
    entry_identity = getattr(args, "entry_identity", None) or LV.IDENTITY_RESOLVED
    _set_input_identity(data, list(dict.fromkeys(symbols + eps)),
                        set(eps) if entry_identity == LV.IDENTITY_RESOLVED else set())
    _write_state(state_path, data)
    log_path = Path(data["discovery_log"])
    entry = (
        f"\n---\n## [re-discover] セッション開始: {args.today}\n"
        f"追加エントリポイント: {', '.join(symbols)}\n"
        f"Wave {n + 1} から再開（既存 visited セット引き継ぎ。波数上限はこの波から数え直す）\n"
    )
    if eps_raw is None:
        entry += ("> ⚠️ --entry-point-symbols が未指定のため、投入シンボルの由来は更新していません"
                  "（未ヒット検出の対象は前回までの投入シンボルのままです）。\n")
    _append_to_file(log_path, entry)
    result = {
        "ok": True, "state": "in-progress", "current_wave": n, "resume_wave": n + 1,
        "frontier_count": len(symbols),
    }
    if eps_raw is None:
        result["entry_point_symbols_unspecified"] = True
    if eps:
        # 由来テーブルは provenance の記録であり、state と異なり常に和集合で更新する。
        unparsed = _update_origin_entry_points(data.get("discovery_log") or "", eps)
        if unparsed:
            result["origin_unparsed_tokens"] = unparsed
    print(json.dumps(result, ensure_ascii=False))


def cmd_extend(args) -> None:
    """探索の延長: max_wave_depth を引き上げ、波数上限で打ち切ったエントリを frontier に戻す（状態によらない）。"""
    state_path = Path(args.path)
    data = _load_state(state_path)
    old = int(data.get("max_wave_depth", 6))
    if args.max_wave <= old:
        print(json.dumps({"ok": True, "extended": False, "max_wave_depth": old, "state": data["state"]},
                         ensure_ascii=False))
        return
    data["max_wave_depth"] = args.max_wave
    restored = []
    if data["state"] == "complete":
        keep = []
        for t in data.get("truncated") or []:
            if t.get("reason") == LV.TRUNC_WAVE_LIMIT:
                restored.append(t)
            else:
                keep.append(t)
        if restored:
            data["truncated"] = keep
            for t in restored:
                key = "low_priority_frontier" if t.get("from") == "low" else "frontier"
                if t["symbol"] not in data.setdefault(key, []):
                    data[key].append(t["symbol"])
            data["state"] = "in-progress"
            data["wave_write_complete"] = True
    _drop_classify_timer(data)
    _write_state(state_path, data)
    lines = [f"- {args.today}: 波数上限を {old} → {args.max_wave} に引き上げた（状態: {data['state']}）"]
    if restored:
        lines.append("- 波数上限で打ち切ったところから探索を続けるシンボル: "
                     + ", ".join(f"`{t['symbol']}`" for t in restored))
    _append_to_file(Path(data["discovery_log"]),
                    "\n" + EXTEND_HEADING_FMT.format(old=old, new=args.max_wave) + "\n\n" + "\n".join(lines) + "\n")
    _upsert_truncation_section(data.get("discovery_log") or "", data)
    print(json.dumps({"ok": True, "extended": True, "restored_count": len(restored), "state": data["state"],
                      "max_wave_depth": args.max_wave}, ensure_ascii=False))


def cmd_switch_engine(args) -> None:
    """判定エンジンを rule に切り替える（tree-sitter を使えなくなり、人が規則判定で続けると選んだ場合だけ）。"""
    state_path = Path(args.path)
    data = _load_state(state_path)
    if args.to != "rule":
        _err(f"switch-engine は rule への切り替えだけを行います（--to {args.to}）")
    before = data.get("slice_engine") or "rule"
    if before == "rule":
        print(json.dumps({"ok": True, "switched": False}, ensure_ascii=False))
        return
    wave = data["current_wave"]
    data["slice_engine"] = "rule"
    data["seed_summary_pending"] = []   # 規則判定は要約を使わない（search の exit 6 を解消する）
    data.pop("preprocess", None)        # 規則判定はマクロを置き換えない
    _write_state(state_path, data)
    log_path = data.get("discovery_log") or ""
    _append_to_file(Path(log_path), "\n" + ENGINE_SWITCH_HEADING_FMT.format(n=wave) + "\n\n"
                    f"- {args.today}: 判定エンジンを {before} から rule に切り替えた（理由: tree-sitter unavailable）。"
                    f"Wave {wave} 以降はグローバル変数の読み手・関数の外のヒットの値を追わず、要約を使った判定と再訪をしない。\n")
    _replace_engine_line(log_path, data)
    print(json.dumps({"ok": True, "switched": True, "wave": wave}, ensure_ascii=False))


def _replace_engine_line(log_path_str: str, data: dict) -> None:
    """「## 探索設定」の判定先の行と置き換えたマクロの行を state の値で書き直す。"""
    if not log_path_str or not Path(log_path_str).is_file():
        return
    p = Path(log_path_str)
    text = p.read_text(encoding="utf-8")
    new_line = f"- 判定先: {_engine_desc(data.get('slice_engine') or 'rule', data.get('engine_exts') or [])}"
    new_text = re.sub(r"(?m)^- 判定先: .*$", lambda m: new_line, text, count=1)
    pre_line = _preprocess_line(data.get("slice_engine") or "rule", data.get("preprocess"))
    new_text = re.sub(r"(?m)^- 置き換えたマクロ: .*$", lambda m: pre_line, new_text, count=1)
    if new_text != text:
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_text)


def _read_ignore_calls(path: Path) -> str:
    """slice-ignore-calls.txt を読む: UTF-8、末尾の改行1つ（\\n または \\r\\n）だけを除く。複数行は exit 1。"""
    value = path.read_bytes().decode("utf-8")
    if value.endswith("\r\n"):
        value = value[:-2]
    elif value.endswith("\n"):
        value = value[:-1]
    if "\n" in value or "\r" in value:
        _err(f"影響なしとみなす呼び出しのファイルは1行で書いてください: {path}")
    return value


def cmd_import(args) -> None:
    state_path = Path(args.path)
    md_path = Path(args.__dict__["from"]) if args.__dict__.get("from") else _md_path_for(state_path)
    if not md_path.exists():
        _err(f"インポート元の checkpoint.md が見つかりません: {md_path}")
    text = md_path.read_text(encoding="utf-8")
    # _default_state() から再構築し checkpoint.md に記載のあるラベルのみを復元する方式のため、
    # classify_started_at / classify_started_wave（PLAN-20260806 Phase 3 Stage 1 §4.5(c)）は
    # 自動的に消える。**この2キーを復元対象に加えてはならない**（計測専用であり、
    # 復元すると別の波の開始時刻から差分が算出されて classify_wall_ms が汚染される）。
    data = _default_state()
    for line in text.split("\n"):
        m = re.match(r"^\*\*(?P<label>[^*]+?)：\*\*\s*(?P<value>.*)$", line.strip())
        if not m:
            continue
        label, value = m.group("label"), m.group("value").strip()
        if label == "状態":
            data["state"] = value
        elif label == "現在 Wave 番号":
            data["current_wave"] = int(value) if value.lstrip("-").isdigit() else 0
        elif label == "最終完了 Wave":
            data["last_completed_wave"] = int(value) if value.lstrip("-").isdigit() else -1
        elif label == "Wave 書き込み完了":
            data["wave_write_complete"] = value.lower() == "true"
        elif label == "確定ファイル数":
            data["confirmed_file_count"] = int(value) if value.isdigit() else 0
        elif label == "除外パターン":
            data["exclude_patterns"] = _split_csv(value)
        elif label == "投入シンボル（ENTRY_POINTS）":
            data["entry_point_symbols"] = _split_csv(value)
        elif label == "最大波数" and value.isdigit():
            data["max_wave_depth"] = int(value)
        elif label == "探索の起点の波" and value.isdigit():
            data["wave_origin"] = int(value)
        elif label == "1波の予算" and value.isdigit():
            data["wave_hit_budget"] = int(value)
        elif label == "LLM 分類の上限" and value.isdigit():
            data["llm_hit_budget"] = int(value)
        elif label == "判定エンジン" and value in SLICE_ENGINES:
            data["slice_engine"] = value
        elif label == "判定エンジンの対象拡張子":
            data["engine_exts"] = _split_csv(value)
        elif label == ".h の解析言語" and value in ("c", "cpp"):
            data["slice_h_as"] = value
        elif label == "シードのグローバル":
            data["seed_globals"] = _split_csv(value)
        elif label == "シード要約の取り込み待ち":
            data["seed_summary_pending"] = _split_csv(value)

    def _section(heading: str) -> list:
        lines = text.split("\n")
        try:
            start = lines.index(heading) + 1
        except ValueError:
            return []
        items = []
        for line in lines[start:]:
            stripped = line.strip()
            if stripped.startswith("## "):
                break
            if stripped and stripped != "(なし)":
                items.append(stripped)
        return items

    data["visited"] = _section("## Visited")
    data["frontier"] = _section("## Frontier")
    if args.repo_path:
        data["repo_path"] = args.repo_path
    if args.discovery_log:
        data["discovery_log"] = args.discovery_log
    # 影響なしとみなす呼び出し（正規表現）は人可読ビューから読み戻さず、Step A-Seed が書いたファイルから復元する
    # （バッククォートや前後の空白があっても値が変わらないようにするため）。
    ignore_path = state_path.parent / "slice-ignore-calls.txt"
    ignore_missing = not ignore_path.is_file()
    if not ignore_missing:
        data["slice_ignore_calls"] = _read_ignore_calls(ignore_path)
    _write_state(state_path, data)
    warnings = [
        "checkpoint.md からの import は人可読ビューに含まれる情報のみを復元します。",
        "confirmed_files, false_positive_files, symbol_origin_map, classified_locations, module_priority_map, "
        "low_priority_frontier, symbol_module, scope_summary, truncated, symbol_summaries, symbol_kinds, "
        "seed_direct_files, seed_direct_hits, entry_identity は初期化されるため、既存の探索履歴が失われます"
        "（scope_summary が失われると classifier の out-of-scope-discard 判定が機能しなくなり、"
        "保守的フォールバックにより全ヒットが通常の伝播種別判定へ回ります。truncated が失われると"
        "「## 打ち切り記録」は次の書き出しで空から作り直されます）。",
        "完全な状態を復元する場合は bfs-state.json のバックアップから復元するか、re-discover を使用してください。",
    ]
    if ignore_missing:
        warnings.append(f"{ignore_path} が無いため、slice_ignore_calls（影響なしとみなす呼び出し）は空にしました。")
    log_path_str = data.get("discovery_log") or ""
    if log_path_str:
        log_path = Path(log_path_str)
        if log_path.exists():
            _append_to_file(log_path, "\n> ⚠️ import 警告:\n" + "\n".join("> " + w for w in warnings) + "\n")
    print(json.dumps({"ok": True, "state": data["state"], "imported_from": str(md_path),
                      "warnings": warnings}, ensure_ascii=False))


def _wave0_block_span(text: str):
    """discovery-log.md 全文から Wave 0 ブロックの境界（開始・終了の文字オフセット）を求める。

    `cmd_funcmap_counts`（funcmap 直接呼び出し元数の機械算出）が使う境界検出。
    '## Wave 0' が見つからない場合は (None, None) を返す（呼び出し側が fail-loud する）。
    """
    wave0_heading = "## Wave 0"
    wave0_idx = text.find(wave0_heading)
    if wave0_idx == -1:
        return None, None
    wave1_idx = text.find("## Wave 1", wave0_idx)
    confirmed_idx = text.find(CONFIRMED_FILES_HEADING, wave0_idx)
    boundaries = [b for b in (wave1_idx, confirmed_idx) if b != -1]
    wave0_end = min(boundaries) if boundaries else len(text)
    return wave0_idx, wave0_end


# 第0波のシードの行（派生元 `seed(X)`）だけを数える。シードのグローバル（`seed-global(X)`）は一致しない。
_FUNCMAP_ORIGIN_RE = re.compile(r"^seed\((.+)\)$")
_FUNCMAP_SEED_GLOBAL_RE = re.compile(r"^seed-global\((.+)\)$")


def cmd_funcmap_counts(args) -> None:
    """PLAN-20260913: discovery-log.md の Wave 0 ヒットテーブルから、初期シンボルごとの
    直接呼び出し元数（Wave 0 発見ユニークファイル数。伝播種別が `false-positive` の行は数えない）を機械的に算出する。
    `seed(X)` の行がすべて `false-positive` の X は 0 件の行を出す（測定済みで 0 件。行が無いと未測定と区別できない）。

    従来 xddp-specout-document-agent（funcmap 生成）と reviewer-checklists/SPO.md
    （チェック項目4の再集計）が同じ計数を LLM で2回独立に行っていたのを解消し、本コマンドの
    出力を単一情報源（オラクル）とする。CLAUDE.md「決定的処理はスクリプト・意味判定はLLM」に従う。
    """
    log_path = Path(args.discovery_log)
    out_path = Path(args.out)

    def _fail(msg: str) -> None:
        # 失敗時に陳腐化した既存 --out を残すと、Step A2 側の「存在確認のみ」ロジックが
        # 古い成功実行の counts ファイルを新鮮なオラクルと誤認してしまう（オラクルの陳腐化防止）。
        if out_path.exists():
            out_path.unlink()
        _err(msg)

    if not log_path.exists():
        _fail(f"discovery-log.md が見つかりません: {log_path}")
    text = log_path.read_text(encoding="utf-8")

    wave0_idx, wave0_end = _wave0_block_span(text)
    if wave0_idx is None:
        _fail(f"'## Wave 0' 見出しが見つかりません（discovery-log.md 未生成または旧形式）: {log_path}")

    block_lines = text[wave0_idx:wave0_end].split("\n")

    header_idx = None
    header_cells = None
    for i, line in enumerate(block_lines):
        cells = _split_row(line)
        if cells and cells[0] == "行ID" and "ファイル" in cells and "派生元" in cells and "伝播種別" in cells:
            header_idx = i
            header_cells = cells
            break
    if header_idx is None:
        _fail(f"Wave 0 のヒットテーブルのヘッダ列が期待と不一致です（discovery-log.md 未生成または旧形式）: {log_path}")

    file_col = header_cells.index("ファイル")
    origin_col = header_cells.index("派生元")
    label_col = header_cells.index("伝播種別")
    n_cols = len(header_cells)

    data_start = header_idx + 2  # ヘッダ行の次はセパレータ行（|---|...|）
    data_end = data_start
    while data_end < len(block_lines) and block_lines[data_end].strip().startswith("|"):
        data_end += 1

    n_rows = data_end - data_start
    if n_rows == 0:
        _fail(f"Wave 0 のヒットテーブルにデータ行が1件もありません: {log_path}")

    symbol_files: dict[str, set] = {}
    skipped: list[tuple[str, str]] = []
    seed_global_rows = 0
    false_positive_rows = 0
    for i in range(data_start, data_end):
        cells = _split_row(block_lines[i])
        if len(cells) != n_cols:
            _fail(
                f"Wave 0 ヒットテーブルの行の列数がヘッダと不一致です"
                f"（ヘッダ{n_cols}列/データ{len(cells)}列）: {block_lines[i][:120]}"
            )
        line_id = cells[0]
        file_cell = cells[file_col]
        origin_cell = cells[origin_col]
        if _FUNCMAP_SEED_GLOBAL_RE.match(origin_cell):
            # シードのグローバルの行は数えず、書式不一致の行にも入れない（書式エラーのように見せないため）。
            seed_global_rows += 1
            continue
        m = _FUNCMAP_ORIGIN_RE.match(origin_cell)
        if not m:
            skipped.append((line_id, origin_cell))
            continue
        files = symbol_files.setdefault(m.group(1), set())
        if cells[label_col] == "false-positive":
            # コメント・文字列の中等のヒットは呼び出し元として数えない（書式は解析済みのためスキップにも入れない）。
            false_positive_rows += 1
            continue
        files.add(file_cell)

    skipped_count = len(skipped)
    if skipped_count == n_rows - seed_global_rows:
        _fail(
            f"Wave 0 ヒットテーブルの全 {n_rows - seed_global_rows} 行（シードのグローバルの行を除く）が"
            f"派生元の書式不一致でスキップされました（『seed(...)』形式に一致する行が0件）: {log_path}"
        )

    out_lines = [
        "# funcmap 直接呼び出し元数（機械算出）",
        "",
        f"> 生成元: {log_path} / Wave 0 ブロック",
        "> 本ファイルは `specout_bfs.py funcmap-counts` が生成する中間ファイル（昇格対象外）。",
        "",
        "| 初期シンボル | 直接呼び出し元数 | 発見ファイル |",
        "|---|---|---|",
    ]
    for symbol in sorted(symbol_files):
        files = sorted(symbol_files[symbol])
        files_cell = ", ".join(f"`{_md_cell(f)}`" for f in files) if files else "（なし）"
        out_lines.append(f"| `{_md_cell(symbol)}` | {len(files)} | {files_cell} |")
    out_lines.append("")
    out_lines.append(f"- 解析行数: {n_rows}")
    out_lines.append(f"- 書式不一致でスキップした行数: {skipped_count}")
    out_lines.append(f"- false-positive で除いた行数: {false_positive_rows}")
    if skipped_count > 0:
        out_lines.append("")
        out_lines.append("## スキップされた行（書式不一致）")
        out_lines.append("")
        out_lines.append("| 行ID | 派生元（生テキスト） |")
        out_lines.append("|---|---|")
        for line_id, raw in skipped:
            out_lines.append(f"| `{_md_cell(line_id)}` | `{_md_cell(raw)}` |")
    out_lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out_lines), encoding="utf-8")
    print(json.dumps(
        {"ok": True, "symbols": len(symbol_files), "n_rows": n_rows, "skipped_rows": skipped_count,
         "false_positive_rows": false_positive_rows},
        ensure_ascii=False,
    ))


# ---------------------------------------------------------------------------
# 下調べ・シード確認・SPO の仕上げ（PLAN-20260927-specout-prelim-phase）
#   seed-preview / init --seed-candidates / doc-targets / prelim-metrics が
#   候補表・台帳・観察メモの解析と集合演算を共有する。
# ---------------------------------------------------------------------------

def _strip_code(cell: str) -> str:
    """セル値の前後空白と、値全体を囲むバッククォートを外す。"""
    s = (cell or "").strip()
    if len(s) >= 2 and s.startswith("`") and s.endswith("`"):
        s = s[1:-1].strip()
    return s


def _norm_path(raw: str, repo_path: str = "") -> str:
    """台帳・観察メモ・bfs-state のパスを比較用に正規化する（REPO_PATH 相対・`/` 区切り）。
    リポジトリ直下（`.`・`./`・空文字列）は `.` とする。"""
    s = _strip_code(raw).replace("\\", "/")
    if repo_path and os.path.isabs(s):
        s = _rel_file(s, repo_path).replace("\\", "/")
    s = posixpath.normpath(s) if s else s
    return "." if s in ("", ".") else s


def _file_under(file_path: str, module_dir: str) -> bool:
    """`file_path` が `module_dir` の下にあるか（ディレクトリ境界。`src/a` は `src/ab/x.c` に一致しない）。
    モジュールディレクトリ `.`（リポジトリ直下のファイルからなるモジュール）は、ディレクトリ部分を持たない
    ファイル（`main.c` 等）にだけ一致する。サブディレクトリのファイルには一致しない（全体の受け皿にしない）。"""
    if module_dir == ".":
        return file_path != "." and "/" not in file_path
    return file_path.startswith(module_dir + "/")


def _longest_module(file_path: str, pairs: dict):
    """`pairs`（{モジュール名: モジュールディレクトリ}）のうち、`file_path` にディレクトリ境界で前方一致する
    最長のモジュールディレクトリの組を返す。一致が無ければ ("", "")。"""
    best = ("", "")
    best_len = -1
    for name, d in pairs.items():
        if _file_under(file_path, d):
            length = 0 if d == "." else len(d)
            if length > best_len:
                best, best_len = (name, d), length
    return best


def _md_section_range(lines: list, heading: str):
    """`heading` 行の次の行から、次の `## `（または `# `）見出しの手前までの (start, end)。無ければ None。"""
    for i, line in enumerate(lines):
        if line.strip() == heading:
            end = i + 1
            while end < len(lines) and not lines[end].startswith(("## ", "# ")):
                end += 1
            return i + 1, end
    return None


def _md_table_in(lines: list, start: int, end: int):
    """lines[start:end] の最初の Markdown テーブルを読む。戻り値: (ヘッダのセル, [(行インデックス, セル)])。
    テーブルが無ければ (None, [])。ヘッダ直後の区切り行（|---|）は読み飛ばし、続く連続した `|` 行をデータ行とする。"""
    i = start
    while i < end and not lines[i].strip().startswith("|"):
        i += 1
    if i >= end:
        return None, []
    header = _split_row(lines[i].strip())
    i += 1
    if i < end and re.match(r"^\|\s*:?-{3,}", lines[i].strip()):
        i += 1
    rows = []
    while i < end and lines[i].strip().startswith("|"):
        rows.append((i, _split_row(lines[i].strip())))
        i += 1
    return header, rows


def _md_row(cells: list) -> str:
    return "| " + " | ".join(_md_cell(c) for c in cells) + " |"


def _parse_seed_candidates(path: Path) -> dict:
    """シード候補表を解析する。書式不正は exit 1（stderr に候補表のパスを出す。台帳の書式不正と区別するため、
    メッセージに他のファイルのパスを含めない）。
    戻り値: {"lines", "candidates": [{"index","cells","adopted","symbol","origin","basis","warning","reason"}],
             "unresolved_entry_points": [{"value","reason"}], "unknown_behaviors": [{"behavior","scope"}]}"""
    if not path.is_file():
        _err(f"シード候補表が見つかりません: {path}")
    lines = path.read_text(encoding="utf-8").split("\n")

    def _fail(msg: str) -> None:
        _err(f"シード候補表の書式が不正です: {path}\n{msg}")

    def _table(heading: str, columns: tuple) -> list:
        rng = _md_section_range(lines, heading)
        if rng is None:
            _fail(f"見出し `{heading}` がありません")
        header, rows = _md_table_in(lines, *rng)
        if header is None or tuple(header) != columns:
            _fail(f"`{heading}` の表の見出し行が `| {' | '.join(columns)} |` ではありません")
        for idx, cells in rows:
            if len(cells) != len(columns):
                _fail(f"{idx + 1}行目: 列数が {len(cells)} です（{len(columns)} 列であること）: {lines[idx].strip()}")
        return rows

    candidates = []
    for idx, cells in _table(SEED_SECTION_CANDIDATES, SEED_CANDIDATE_COLUMNS):
        mark, symbol, origin = cells[0].strip(), _strip_code(cells[1]), _strip_code(cells[2])
        if mark not in (SEED_ADOPTED, SEED_REJECTED):
            _fail(f"{idx + 1}行目: 採否が {SEED_ADOPTED} / {SEED_REJECTED} ではありません: {lines[idx].strip()}")
        if not symbol:
            _fail(f"{idx + 1}行目: シンボルが空です: {lines[idx].strip()}")
        if origin not in SEED_ORIGINS:
            _fail(f"{idx + 1}行目: 由来が {' / '.join(SEED_ORIGINS)} のいずれでもありません: {lines[idx].strip()}")
        if mark == SEED_ADOPTED and ("[" in symbol or "]" in symbol) and not _is_qualified_entry(symbol):
            _fail(f"{idx + 1}行目: シンボル形式が不正です（MEDIUM形式は symbol[MEDIUM:filepath]、"
                  f"FILE形式は symbol[FILE:filepath]、CLASS形式は symbol[CLASS:ClassName]）: {lines[idx].strip()}")
        candidates.append({"index": idx, "cells": cells, "adopted": mark == SEED_ADOPTED, "symbol": symbol,
                           "origin": origin, "basis": cells[3], "warning": cells[5], "reason": cells[6]})
    unresolved = [{"value": _strip_code(c[0]), "reason": c[1]}
                  for _, c in _table(SEED_SECTION_UNRESOLVED_EP, SEED_UNRESOLVED_EP_COLUMNS) if any(c)]
    unknown = [{"behavior": c[0], "scope": c[1]}
               for _, c in _table(SEED_SECTION_UNKNOWN, SEED_UNKNOWN_COLUMNS) if any(c)]
    return {"lines": lines, "candidates": candidates,
            "unresolved_entry_points": unresolved, "unknown_behaviors": unknown}


def _seed_adopted_symbols(seeds: dict, origins: tuple = None) -> list:
    """採否 ☑ の行のシンボル（表の順・重複なし）。`origins` 指定時はその由来の行に限る。"""
    return list(dict.fromkeys(c["symbol"] for c in seeds["candidates"]
                              if c["adopted"] and (origins is None or c["origin"] in origins)))


def _origin_rows_from_seeds(seeds: dict) -> dict:
    """候補表から由来テーブルの全行（ENTRY_POINTS 行を含む）を {行名: (シンボル欄, 備考欄)} で決定的に作る。"""
    cands = seeds["candidates"]

    def _syms(rows: list) -> list:
        return list(dict.fromkeys(c["symbol"] for c in rows))

    def _adopted(origin: str) -> list:
        return [c for c in cands if c["adopted"] and c["origin"] == origin]

    def _notes(pairs: list) -> str:
        text = "; ".join(f"`{_md_cell(k)}`: {_md_cell(v.strip())}" for k, v in pairs if v and v.strip())
        return text or "—"

    def _row(rows: list, empty: str, note_key: str = None) -> tuple:
        note = _notes([(c["symbol"], c[note_key]) for c in rows]) if note_key else "—"
        return _format_origin_cell(_syms(rows), empty), note

    rejected = [c for c in cands if not c["adopted"]]
    unresolved = seeds["unresolved_entry_points"]
    unknown = seeds["unknown_behaviors"]
    return {
        ORIGIN_ROW_ENTRY_POINTS: _row(_adopted(SEED_ORIGIN_ENTRY_POINTS), ORIGIN_EMPTY_CELL),
        ORIGIN_ROW_CRS: _row(_adopted(SEED_ORIGIN_CRS), ORIGIN_NONE_CELL),
        ORIGIN_ROW_PRELIM: _row(_adopted(SEED_ORIGIN_PRELIM), ORIGIN_NONE_CELL, "basis"),
        ORIGIN_ROW_CODE: _row(_adopted(SEED_ORIGIN_CODE), ORIGIN_NONE_CELL, "basis"),
        ORIGIN_ROW_INHERIT: _row(_adopted(SEED_ORIGIN_INHERIT), ORIGIN_NONE_CELL),
        ORIGIN_ROW_HUMAN_ADDED: _row(_adopted(SEED_ORIGIN_HUMAN_ADDED), ORIGIN_NONE_CELL, "basis"),
        ORIGIN_ROW_HUMAN_REMOVED: _row(rejected, ORIGIN_NONE_CELL, "reason"),
        ORIGIN_ROW_UNRESOLVED_EP: (
            _format_origin_cell(list(dict.fromkeys(u["value"] for u in unresolved if u["value"])), ORIGIN_NONE_CELL),
            _notes([(u["value"], u["reason"]) for u in unresolved])),
        ORIGIN_ROW_UNKNOWN: (
            (ORIGIN_UNKNOWN_CELL, "; ".join(_md_cell(u["behavior"]) for u in unknown) + "（要確認）")
            if unknown else (ORIGIN_NONE_CELL, "—")),
    }


def _load_unsupported_patterns(path_str) -> list:
    """init --unsupported-patterns の JSON（[{"pattern","location","note"?}]）。未指定・ファイル不在は []。"""
    if not path_str:
        return []
    path = Path(path_str)
    if not path.is_file():
        return []
    try:
        entries = json.loads(path.read_text(encoding="utf-8") or "[]")
    except ValueError as e:
        _err(f"grep 未対応パターンのファイルを JSON として読めません: {path}（{e}）")
    if not isinstance(entries, list) or not all(
            isinstance(e, dict) and isinstance(e.get("pattern"), str) and isinstance(e.get("location"), str)
            for e in entries):
        _err(f"grep 未対応パターンのファイルの形式が不正です（[{{\"pattern\",\"location\",\"note\"}}] の配列）: {path}")
    return entries


def _parse_ledger(path, repo_path: str = "") -> list:
    """文書化済みファイル台帳を解析する。未指定・ファイル不在は []（「不在なら空／0」）。
    書式不正（見出し行不在・列数不一致・空セル・工程の値）は exit 1（stderr に台帳のパスと該当行）。
    戻り値: [{"line","raw","file","module","module_dir","phase","behavior"}]（パスは `_norm_path` で正規化済み）"""
    if path is None or not Path(path).is_file():
        return []
    path = Path(path)
    lines = path.read_text(encoding="utf-8").split("\n")

    def _fail(msg: str) -> None:
        _err(f"文書化済みファイル台帳の書式が不正です: {path}\n{msg}")

    header, rows = _md_table_in(lines, 0, len(lines))
    if header is None or tuple(header) != LEDGER_COLUMNS:
        _fail(f"表の見出し行 `| {' | '.join(LEDGER_COLUMNS)} |` がありません")
    entries = []
    for idx, cells in rows:
        raw = lines[idx].strip()
        if len(cells) != len(LEDGER_COLUMNS):
            _fail(f"{idx + 1}行目: 列数が {len(cells)} です（{len(LEDGER_COLUMNS)} 列であること）: {raw}")
        file_, module, module_dir, phase = (_strip_code(c) for c in cells[:4])
        if not file_ or not module:
            _fail(f"{idx + 1}行目: ファイルパスまたはモジュールが空です: {raw}")
        if phase not in (LEDGER_PHASE_PRELIM, LEDGER_PHASE_ADDITIONAL):
            _fail(f"{idx + 1}行目: 工程が `{LEDGER_PHASE_PRELIM}` / `{LEDGER_PHASE_ADDITIONAL}` ではありません: {raw}")
        entries.append({"line": idx + 1, "raw": raw, "file": _norm_path(file_, repo_path), "module": module,
                        "module_dir": _norm_path(module_dir, repo_path), "phase": phase,
                        "behavior": cells[4].strip()})
    return entries


def _check_ledger(entries: list, path) -> dict:
    """台帳の組の矛盾と行ごとの整合を検査し、{モジュール名: モジュールディレクトリ} を返す。
    違反は exit 1（stderr に台帳のパスと該当行・矛盾する組）。seed-preview と doc-targets が共有する。
    - 同じモジュール名に異なるディレクトリ／同じディレクトリに異なるモジュール名
    - 行のファイルがモジュールディレクトリの下に無い／台帳の組だけで作った対応表での最長前方一致の結果と行のモジュールが異なる"""
    errors = []
    by_name, by_dir = {}, {}
    for e in entries:
        by_name.setdefault(e["module"], {}).setdefault(e["module_dir"], []).append(e["line"])
        by_dir.setdefault(e["module_dir"], {}).setdefault(e["module"], []).append(e["line"])

    def _fmt(group: dict) -> str:
        return ", ".join(f"`{k}`（{', '.join(str(n) for n in v)}行目）" for k, v in group.items())

    for name, dirs in by_name.items():
        if len(dirs) > 1:
            errors.append(f"モジュール `{name}` に異なるモジュールディレクトリがあります: {_fmt(dirs)}")
    for d, names in by_dir.items():
        if len(names) > 1:
            errors.append(f"モジュールディレクトリ `{d}` に異なるモジュール名があります: {_fmt(names)}")
    if not errors:
        pairs = {e["module"]: e["module_dir"] for e in entries}
        for e in entries:
            if not _file_under(e["file"], e["module_dir"]):
                errors.append(f"{e['line']}行目: ファイル `{e['file']}` がモジュールディレクトリ "
                              f"`{e['module_dir']}` の下にありません: {e['raw']}")
                continue
            name, d = _longest_module(e["file"], pairs)
            if name != e["module"]:
                errors.append(f"{e['line']}行目: ファイル `{e['file']}` は台帳の最長前方一致ではモジュール `{name}`"
                              f"（`{d}`）に属します（行のモジュールは `{e['module']}`）: {e['raw']}")
    if errors:
        _err(f"文書化済みファイル台帳の整合違反: {path}\n" + "\n".join(errors))
    return {e["module"]: e["module_dir"] for e in entries}


def _parse_obs_memo(path, repo_path: str = ""):
    """累積観察メモを解析する。未指定・ファイル不在は None。5セクションの見出し不在・表の見出し行に
    「ファイルパス」列が無い・列数不一致は exit 1（stderr に観察メモのパスと該当行）。
    戻り値: {"path", "lines", "rows": [(行インデックス, ファイルパス列の値)]}"""
    if path is None or not Path(path).is_file():
        return None
    path = Path(path)
    lines = path.read_text(encoding="utf-8").split("\n")

    def _fail(msg: str) -> None:
        _err(f"累積観察メモの書式が不正です: {path}\n{msg}")

    rows = []
    for heading in OBS_MEMO_SECTIONS:
        rng = _md_section_range(lines, heading)
        if rng is None:
            _fail(f"見出し `{heading}` がありません")
        header, table_rows = _md_table_in(lines, *rng)
        if header is None or OBS_MEMO_FILE_COLUMN not in header:
            _fail(f"`{heading}` の表の見出し行に `{OBS_MEMO_FILE_COLUMN}` 列がありません")
        col = header.index(OBS_MEMO_FILE_COLUMN)
        for idx, cells in table_rows:
            if len(cells) != len(header):
                _fail(f"{idx + 1}行目: 列数が {len(cells)} です（{len(header)} 列であること）: {lines[idx].strip()}")
            rows.append((idx, cells[col]))
    return {"path": path, "lines": lines, "rows": rows}


def _prune_obs_memo(memo: dict, ledger_files: set, repo_path: str = "") -> int:
    """ファイルパス列が台帳に無い行（前回の中断で台帳に記録される前に書かれた行）を除去して書き戻し、除去件数を返す。"""
    drop = set()
    for idx, raw in memo["rows"]:
        value = _strip_code(raw).replace("\\", "/")
        if _norm_path(value, repo_path) not in ledger_files:
            drop.add(idx)
    if drop:
        kept = [line for i, line in enumerate(memo["lines"]) if i not in drop]
        with open(memo["path"], "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(kept))
    return len(drop)


_ASSIGNED_KEY = "\0assigned"


def _rewritten_rows(ledger_rows, ledger_pairs: dict, d: str) -> list:
    """台帳の組に割り当てのディレクトリ `d` を加えた対応表での最長前方一致が、行のモジュールと異なる（帰属を書き換える）
    台帳の行。`ledger_rows` は `file`・`module` を持つ dict の列。"""
    pairs = {**ledger_pairs, _ASSIGNED_KEY: d}
    return [e for e in ledger_rows if _longest_module(e["file"], pairs)[0] == _ASSIGNED_KEY]


def _check_module_assignments(path: Path, ledger_pairs: dict, repo_path: str = "", ledger_rows=()) -> dict:
    """module-assignments.json（[{"module","module_dir"}]）を検査し、台帳と完全に一致しない組を
    {モジュール名: モジュールディレクトリ} で返す。ファイル不在は {}。違反は exit 5（stderr に該当する組）。
    台帳の組と名前・ディレクトリが完全に一致する組（台帳へ書き込み済みの組）は検査しない。
    台帳のモジュールディレクトリの配下・祖先の割り当ては、台帳の行（`ledger_rows`）の帰属を書き換える場合だけ違反とする。"""
    if not path.is_file():
        return {}

    def _fail(msgs: list) -> None:
        print(f"module-assignments.json の組が不正です: {path}\n" + "\n".join(msgs), file=sys.stderr)
        sys.exit(EXIT_ASSIGNMENTS_INVALID)

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        _fail([f"JSON として読めません（{e}）"])
    if not isinstance(raw, list) or not all(
            isinstance(x, dict) and isinstance(x.get("module"), str) and isinstance(x.get("module_dir"), str)
            for x in raw):
        _fail(['[{"module": ..., "module_dir": ...}] の配列ではありません'])
    errors = []
    checked = []
    ledger_dirs = set(ledger_pairs.values())
    for item in raw:
        name = item["module"].strip()
        label = f'{{"module": "{item["module"]}", "module_dir": "{item["module_dir"]}"}}'
        d = _norm_path(item["module_dir"], repo_path)
        if ledger_pairs.get(name) == d or (name, d) in checked:
            continue
        if not MODULE_NAME_RE.match(name):
            errors.append(f"{label}: モジュール名に使えない文字があります（英数字・`-`・`_` のみ）")
        if d in ledger_dirs:
            errors.append(f"{label}: 台帳のモジュールディレクトリと同じです")
        else:
            rewritten = _rewritten_rows(ledger_rows, ledger_pairs, d)
            for e in rewritten[:5]:
                errors.append(f"{label}: 台帳の行 `{e['file']}`（モジュール `{e['module']}`）の帰属を書き換えます")
            if len(rewritten) > 5:
                errors.append(f"{label}: ほか {len(rewritten) - 5} 行の帰属を書き換えます")
        if name in ledger_pairs:
            errors.append(f"{label}: 台帳のモジュール `{name}`（`{ledger_pairs[name]}`）と名前が同じでディレクトリが異なります")
        checked.append((name, d))
    by_name, by_dir = {}, {}
    for name, d in checked:
        by_name.setdefault(name, set()).add(d)
        by_dir.setdefault(d, set()).add(name)
    for name, dirs in by_name.items():
        if len(dirs) > 1:
            errors.append(f"モジュール `{name}` に異なるモジュールディレクトリがあります: {', '.join(sorted(dirs))}")
    for d, names in by_dir.items():
        if len(names) > 1:
            errors.append(f"モジュールディレクトリ `{d}` に異なるモジュール名があります: {', '.join(sorted(names))}")
    if errors:
        _fail(errors)
    return dict(checked)


def _confirmed_files(data: dict) -> dict:
    """bfs-state の確定ファイル（正規化済み）を {ファイル: 確信度} で返す。"""
    repo_path = data.get("repo_path") or ""
    return {_norm_path(f, repo_path): info["confidence"]
            for f, info in (data.get("confirmed_files") or {}).items()}


def _preview_seed_hits(symbols: list, search_conf: dict) -> tuple:
    """`search` と同じバックエンド・同じ帰属（`_matching_symbol`）・同じ保守的フィルタで投入シンボルを検索する。
    状態ファイルは作らない。戻り値: (生ヒットのあったエントリの集合, {エントリ: フィルタ後のファイル集合},
    {エントリ: フィルタ後のヒット行数}, バックエンド警告)"""
    backend, _effective, warning = resolve_backend(search_conf)
    repo_path = search_conf["repo_path"]
    hit_filter = search_conf.get("hit_filter", "conservative")
    raw_entries = set()
    files = {}
    line_counts = collections.Counter()

    def _consume(results: list, scope, kind=SCOPE_MEDIUM) -> None:
        for sc in results:
            attribute = _attributor(sc.candidates)
            for file_, _line_no, content in sc.rows:
                sym = attribute(content)
                key = _format_entry(sym, scope, kind)
                raw_entries.add(key)
                ext = os.path.splitext(file_)[1].lower()
                if hit_filter == "conservative" and _is_pure_line_comment(content, sym, ext):
                    continue
                files.setdefault(key, set()).add(_rel_file(file_, repo_path))
                line_counts[key] += 1

    high = [s for s in symbols if _parse_entry(s)[1] is None]
    scoped = {}
    class_by_base = {}
    for s in symbols:
        sym, scope = _parse_entry(s)
        if _entry_scope_kind(s) == SCOPE_CLASS:
            class_by_base.setdefault(sym, []).append(scope)
        elif scope is not None:
            scoped.setdefault((_entry_scope_kind(s), scope), []).append(sym)
    if high:
        _consume(backend.search(high, None), None)
    for kind, scope in sorted(scoped, key=lambda k: (k[1], k[0])):
        _consume(backend.search(scoped[(kind, scope)], scope), scope, kind)
    # CLASS 形式: 素の名前ごとに C++ として解析するファイルを検索し、行をエントリごとに数える（search と同じ）。
    h_as = search_conf.get("slice_h_as") or "c"
    for base in sorted(class_by_base):
        results = [sc._replace(rows=[r for r in sc.rows if is_cpp_file(_rel_file(r[0], repo_path), h_as)])
                   for sc in backend.search([base], None)]
        for cls in sorted(set(class_by_base[base])):
            _consume(results, cls, SCOPE_CLASS)
    return raw_entries, files, line_counts, warning


def _load_seed_input(path: Path) -> dict:
    """write-seed-candidates の入力 JSON を検証して返す。違反は exit 1（stderr に入力ファイルのパスと原因）。"""
    if not path.is_file():
        _err(f"シード候補の入力 JSON が見つかりません: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        _err(f"シード候補の入力を JSON として読めません: {path}（{e}）")

    def _fail(msg: str) -> None:
        _err(f"シード候補の入力が不正です: {path}\n{msg}")

    if not isinstance(data, dict):
        _fail("トップレベルがオブジェクトではありません")
    shapes = {"entry_points": None, "crs": None, "inherit": None,
              "prelim": ("symbol", "evidence"), "code_derived": ("symbol", "evidence"),
              "unresolved_entry_points": ("value", "reason"), "unknown_behaviors": ("behavior", "scope")}
    for key, fields in shapes.items():
        if key not in data or not isinstance(data[key], list):
            _fail(f"キー `{key}` がない、または配列ではありません")
        for i, item in enumerate(data[key]):
            if fields is None:
                if not isinstance(item, str):
                    _fail(f"`{key}[{i}]` が文字列ではありません")
            elif not isinstance(item, dict) or not all(isinstance(item.get(f), str) for f in fields):
                _fail(f"`{key}[{i}]` が {{{', '.join(fields)}}}（いずれも文字列）の形ではありません")
    for key in ("entry_points", "crs", "inherit", "prelim", "code_derived"):
        for item in data[key]:
            sym = item if isinstance(item, str) else item["symbol"]
            if not sym.strip():
                _fail(f"`{key}` に空のシンボルがあります")
            if re.search(r"\s", sym):
                _fail(f"`{key}` のシンボルに空白が含まれています（自然文の注記は根拠に書く）: {sym!r}")
            if _is_qualified_entry(sym):
                _fail(f"`{key}` のシンボルに MEDIUM 形式・FILE 形式・CLASS 形式は使えません（識別子のみ）: {sym!r}")
    if "unsupported_patterns" not in data or not isinstance(data["unsupported_patterns"], list):
        _fail("キー `unsupported_patterns` がない、または配列ではありません")
    for i, item in enumerate(data["unsupported_patterns"]):
        if not isinstance(item, dict) or not all(isinstance(item.get(f), str) for f in ("pattern", "location")):
            _fail(f"`unsupported_patterns[{i}]` が {{pattern, location}}（いずれも文字列）の形ではありません")
        if item.get("note") is not None and not isinstance(item["note"], str):
            _fail(f"`unsupported_patterns[{i}].note` が文字列ではありません（無ければキーごと省略する）")
    return data


UNSUPPORTED_NOTE_SEP = "; "


def _unsupported_note_items(note: str) -> list:
    return [s.strip() for s in note.split(UNSUPPORTED_NOTE_SEP) if s.strip()]


def _normalize_unsupported_patterns(entries: list) -> tuple:
    """write-seed-candidates の `unsupported_patterns` を seed-unsupported.json の要素に正規化する。
    前後の空白を除き、location の最初の全角 `（` 以降（末尾の `）` を除く）を注記として note の前へ連結し、
    pattern・location が空の要素は読み飛ばす。(pattern, location) の重複は最初の要素に畳み、後の要素の注記のうち
    `; ` で分けた項目と完全一致しないものだけを末尾へ連結する。戻り値: (要素の配列, 読み飛ばした件数)"""
    result, by_key, skipped = [], {}, 0
    for e in entries:
        pattern = e["pattern"].strip()
        location = e["location"].strip()
        note = (e.get("note") or "").strip()
        if "（" in location:
            location, split_note = location.split("（", 1)
            location = location.strip()
            if split_note.endswith("）"):
                split_note = split_note[:-1]
            note = UNSUPPORTED_NOTE_SEP.join(n for n in (split_note.strip(), note) if n)
        if not pattern or not location:
            skipped += 1
            continue
        key = (pattern, location)
        if key in by_key:
            cur = by_key[key]
            items = _unsupported_note_items(cur.get("note", ""))
            for n in _unsupported_note_items(note):
                if n not in items:
                    items.append(n)
            if items:
                cur["note"] = UNSUPPORTED_NOTE_SEP.join(items)
            continue
        entry = {"pattern": pattern, "location": location}
        if note:
            entry["note"] = note
        by_key[key] = entry
        result.append(entry)
    return result, skipped


def _insert_table_rows(lines: list, heading: str, columns: tuple, rows: list, source: Path) -> list:
    """`heading` 節の最初の表の末尾へ行を足した新しい行リストを返す。見出し・表の見出し行が
    `columns` と一致しなければ exit 1（stderr に source のパス）。既存の行は変更しない。"""
    rng = _md_section_range(lines, heading)
    header, _ = _md_table_in(lines, *rng) if rng else (None, [])
    if header is None or tuple(header) != columns:
        _err(f"シード候補表の書式が不正です: {source}\n見出し `{heading}` と表の見出し行 `| {' | '.join(columns)} |` が必要です")
    i = rng[0]
    while not lines[i].strip().startswith("|"):
        i += 1
    i += 1
    if i < rng[1] and re.match(r"^\|\s*:?-{3,}", lines[i].strip()):
        i += 1
    while i < rng[1] and lines[i].strip().startswith("|"):
        i += 1
    return lines[:i] + [_md_row(r) for r in rows] + lines[i:]


def cmd_write_seed_candidates(args) -> None:
    """discovery-setup が渡した由来別のシンボルと根拠から、シード候補表を決定的に書く。
    採否は常に ☑。同一シンボルは ENTRY_POINTS ＞ CRS SP項目 ＞ 下調べ ＞ 母体コードから補完 ＞ 継承展開 で1行に畳む。
    --append は既存行を変えず、足りない行だけを追記する。同じ入力の unsupported_patterns から grep 未対応パターンの記録
    （--unsupported-out）も書く（--append は既存の要素を変えず、(pattern, location) が無い要素だけを足す）。
    検証と既存ファイルの読み込みをすべて済ませてから一時ファイル経由で書き、失敗したらどちらのファイルも変更しない。"""
    data = _load_seed_input(Path(args.input))
    out = Path(args.out)
    unsupported_out = Path(args.unsupported_out)
    dash = "—"
    new_unsupported, unsupported_skipped = _normalize_unsupported_patterns(data["unsupported_patterns"])
    existing_unsupported = _load_unsupported_patterns(str(unsupported_out)) if args.append else []

    if args.append:
        seeds = _parse_seed_candidates(out)
        lines = seeds["lines"]
        by_symbol = {c["symbol"]: c for c in seeds["candidates"]}
        excluded, add_rows, seen = [], [], set()
        for origin, syms in ((SEED_ORIGIN_ENTRY_POINTS, data["entry_points"]), (SEED_ORIGIN_INHERIT, data["inherit"])):
            for sym in syms:
                if sym in by_symbol:
                    cur = by_symbol[sym]
                    if origin == SEED_ORIGIN_ENTRY_POINTS and not cur["adopted"]:
                        excluded.append({"symbol": sym, "reason": cur["reason"]})
                elif sym not in seen:
                    seen.add(sym)
                    add_rows.append([SEED_ADOPTED, sym, origin, dash, "", "", ""])
        have = {u["value"] for u in seeds["unresolved_entry_points"]}
        add_unresolved = []
        for u in data["unresolved_entry_points"]:
            if u["value"] not in have:
                have.add(u["value"])
                add_unresolved.append([u["value"], u["reason"]])
        if add_rows:
            lines = _insert_table_rows(lines, SEED_SECTION_CANDIDATES, SEED_CANDIDATE_COLUMNS, add_rows, out)
        if add_unresolved:
            lines = _insert_table_rows(lines, SEED_SECTION_UNRESOLVED_EP, SEED_UNRESOLVED_EP_COLUMNS, add_unresolved, out)
        text, appended = "\n".join(lines), len(add_rows)
    else:
        for opt in ("template", "cr", "repo"):
            if not getattr(args, opt):
                _err(f"--{opt} が必要です（--append なしの新規作成）")
        if out.exists():
            if not args.stale_ref or not Path(args.stale_ref).is_file():
                _err(f"シード候補表が既に存在します: {out}\n上書きするには更新時刻の基準になる --stale-ref（下調べ索引または CRS）が必要です。"
                     "人が編集した候補表なら --append を付けてください")
            if out.stat().st_mtime >= Path(args.stale_ref).stat().st_mtime:
                _err(f"シード候補表が {args.stale_ref} より新しいため上書きしません: {out}\n"
                     "人が編集した候補表なら --append を付けるか、候補表を退避してから再実行してください")
        tpl = Path(args.template)
        if not tpl.is_file():
            _err(f"シード候補表のひな形が見つかりません: {tpl}")
        lines = tpl.read_text(encoding="utf-8").replace("{CR}", args.cr).replace("{repo}", args.repo).split("\n")
        rows, seen = [], set()
        for origin, items in ((SEED_ORIGIN_ENTRY_POINTS, data["entry_points"]), (SEED_ORIGIN_CRS, data["crs"]),
                              (SEED_ORIGIN_PRELIM, data["prelim"]), (SEED_ORIGIN_CODE, data["code_derived"]),
                              (SEED_ORIGIN_INHERIT, data["inherit"])):
            for item in items:
                sym, basis = (item, dash) if isinstance(item, str) else (item["symbol"], item["evidence"].strip() or dash)
                if origin in (SEED_ORIGIN_ENTRY_POINTS, SEED_ORIGIN_CRS, SEED_ORIGIN_INHERIT):
                    basis = dash
                if sym not in seen:
                    seen.add(sym)
                    rows.append([SEED_ADOPTED, sym, origin, basis, "", "", ""])
        unresolved, have = [], set()
        for u in data["unresolved_entry_points"]:
            if u["value"] not in have:
                have.add(u["value"])
                unresolved.append([u["value"], u["reason"]])
        unknown = [[u["behavior"], u["scope"]] for u in data["unknown_behaviors"]]
        lines = _insert_table_rows(lines, SEED_SECTION_CANDIDATES, SEED_CANDIDATE_COLUMNS, rows, tpl)
        lines = _insert_table_rows(lines, SEED_SECTION_UNRESOLVED_EP, SEED_UNRESOLVED_EP_COLUMNS, unresolved, tpl)
        lines = _insert_table_rows(lines, SEED_SECTION_UNKNOWN, SEED_UNKNOWN_COLUMNS, unknown, tpl)
        text, appended = "\n".join(lines), 0
        excluded = []

    have_keys = {(e["pattern"], e["location"]) for e in existing_unsupported}
    unsupported = existing_unsupported + [e for e in new_unsupported if (e["pattern"], e["location"]) not in have_keys]

    out.parent.mkdir(parents=True, exist_ok=True)
    unsupported_out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    utmp = unsupported_out.with_name(unsupported_out.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        result = _parse_seed_candidates(tmp)
        utmp.write_text(json.dumps(unsupported, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, out)
        os.replace(utmp, unsupported_out)
    finally:
        for t in (tmp, utmp):
            if t.exists():
                t.unlink()
    by_origin = dict(collections.Counter(c["origin"] for c in result["candidates"]))
    print(json.dumps({"candidate_count": len(result["candidates"]), "by_origin": by_origin,
                      "appended_count": appended, "excluded_entry_points": excluded,
                      "unresolved_count": len(result["unresolved_entry_points"]),
                      "unknown_count": len(result["unknown_behaviors"]),
                      "unsupported_count": len(unsupported),
                      "unsupported_appended_count": len(unsupported) - len(existing_unsupported),
                      "unsupported_skipped_count": unsupported_skipped}, ensure_ascii=False))


def cmd_seed_preview(args) -> None:
    """Step A-Seed: 候補表の採用シンボルのヒット数を試算し、「ヒット（ファイル数）」「警告」列を書き換える。"""
    cand_path = Path(args.seed_candidates)
    seeds = _parse_seed_candidates(cand_path)
    ledger_counts = None
    if args.ledger is not None:
        ledger = _parse_ledger(Path(args.ledger), args.repo_path)
        _check_ledger(ledger, args.ledger)
        prelim = [e for e in ledger if e["phase"] == LEDGER_PHASE_PRELIM]
        ledger_counts = {"prelim_module_count": len({e["module"] for e in prelim}),
                         "prelim_file_count": len({e["file"] for e in prelim})}
    adopted = _seed_adopted_symbols(seeds)
    search_conf = {
        "repo_path": args.repo_path, "backend": args.backend,
        "exclude_patterns": _split_csv(args.exclude), "include_extensions": _split_csv(args.include_ext),
        "hit_filter": (args.hit_filter or "conservative").strip() or "conservative",
        "slice_h_as": resolve_h_as(args.slice_h_as, args.repo_path, _split_csv(args.exclude)),
    }
    raw_entries, files, line_counts, backend_warning = (_preview_seed_hits(adopted, search_conf) if adopted
                                                        else (set(), {}, collections.Counter(), None))

    limit = args.max_files_per_module
    budget = int(args.wave_hit_budget or 0)
    warning_of = {}
    zero_hit, zero_after_filter, noisy, over_budget = [], [], [], []
    for s in adopted:
        count = len(files.get(s, ()))
        words = []
        if _entry_scope_kind(s) == SCOPE_MEDIUM:
            # MEDIUM 形式のエントリは search と同じく未ヒット・ヒット過多・予算超過の検出対象外。
            warning_of[s] = ""
            continue
        if s not in raw_entries:
            words.append(SEED_WARN_ZERO_HIT)
            zero_hit.append(s)
        elif count == 0:
            words.append(SEED_WARN_ZERO_AFTER_FILTER)
            zero_after_filter.append(s)
        elif count > limit:
            words.append(SEED_WARN_NOISY)
            noisy.append({"symbol": s, "file_count": count})
        # 予算超過はヒット過多と独立に判定する（未ヒット・フィルタ後0件はヒット数0のため当たらない）。
        if budget > 0 and line_counts.get(s, 0) > budget:
            words.insert(0, SEED_WARN_OVER_BUDGET)
            over_budget.append({"symbol": s, "hits": line_counts[s]})
        warning_of[s] = SEED_WARN_SEP.join(words)
    adopted_total_hits = sum(line_counts.get(s, 0) for s in adopted)
    over_budget_total = budget > 0 and adopted_total_hits > budget

    lines = seeds["lines"]
    for c in seeds["candidates"]:
        cells = list(c["cells"])
        if c["adopted"]:
            cells[4] = str(len(files.get(c["symbol"], ())))
            cells[5] = warning_of[c["symbol"]]
        else:
            cells[4] = cells[5] = ""
        lines[c["index"]] = _md_row(cells)
    # 採用シンボルの合計ヒット数の注記行（表の行の書き換えの後に削除・挿入して、解析時の行番号をずらさない）。
    rng = _md_section_range(lines, SEED_SECTION_CANDIDATES)
    if rng is not None:
        start, end = rng
        header_i = next((i for i in range(start, end) if lines[i].strip().startswith("|")), None)
        if header_i is not None:
            keep = []
            skip_blank = False
            for i, line in enumerate(lines):
                if start <= i < header_i and line.startswith(SEED_TOTAL_NOTE_PREFIXES):
                    skip_blank = True
                    continue
                if skip_blank and start <= i < header_i and not line.strip():
                    skip_blank = False
                    continue
                skip_blank = False
                keep.append((i, line))
            new_lines = []
            for i, line in keep:
                if i == header_i and budget > 0:
                    has_class = any(_entry_scope_kind(s) == SCOPE_CLASS for s in adopted)
                    new_lines += [_seed_total_note(adopted_total_hits, budget, args.slice_engine, has_class), ""]
                new_lines.append(line)
            lines = new_lines
    new_text = "\n".join(lines)
    if new_text != cand_path.read_text(encoding="utf-8"):
        with open(cand_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_text)

    noisy_symbols = {n["symbol"] for n in noisy}
    flagged = noisy_symbols | {o["symbol"] for o in over_budget}
    result = {
        "ok": True, "adopted_count": len(adopted), "zero_hit": zero_hit, "zero_after_filter": zero_after_filter,
        "noisy": noisy, "all_adopted_noisy": bool(adopted) and all(s in noisy_symbols for s in adopted),
        "over_budget": over_budget,
        "all_adopted_noisy_or_over_budget": bool(adopted) and all(s in flagged for s in adopted),
        "adopted_total_hits": adopted_total_hits, "over_budget_total": over_budget_total,
    }
    if ledger_counts is not None:
        result.update(ledger_counts)
    if backend_warning:
        result["backend_warning"] = backend_warning
    print(json.dumps(result, ensure_ascii=False))


def _seed_total_note(total: int, budget: int, slice_engine: str, has_class: bool = False) -> str:
    """候補表の「## 候補」の表の直前に書く1行の注記（採用シンボルの合計ヒット数）。"""
    tail = ("（シードが書くグローバルは試算に含まれないため、実際の第0波の合計はこれより多くなることがあります）"
            if slice_engine == "slice" else "")
    if has_class:
        tail += "（`名前[CLASS:クラス名]` の行の件数は、クラスで絞る前の件数です）"
    if total <= budget:
        return f"{SEED_TOTAL_NOTE_PREFIXES[0]} {total}（1波の予算 {budget} 以内）{tail}"
    return (f"{SEED_TOTAL_NOTE_PREFIXES[1]} {total}（1波の予算 {budget} を超えています）。第0波で、優先順位の低い"
            "シンボルから打ち切られます。採用するシンボルを分けて実行する（一部の採否を「除外」にして実行し、"
            "残りを /xddp-04-specout {CR} --re-discover {シンボル} で投入する）ことを検討してください。" + tail)


def _warning_words(cell: str) -> list:
    return [w.strip() for w in (cell or "").split(SEED_WARN_SEP) if w.strip()]


def cmd_doc_targets(args) -> None:
    """SPO の仕上げ: 文書化対象・モジュールの割り当て・配置を決定的に求める。
    `--only seed-direct` は対象をシードの直接参照のうち台帳・追加下調べの判断の記録（`--gap-reviewed`）に無いファイルに絞り、
    `--max-files`（repo ごとの累計の上限）を超えた分を `over_limit_files` に返す（追加下調べの対象）。
    処理順: (1) 台帳・観察メモ・判断の記録の書式検査と台帳の検査（exit 1）→ (2) --module-assignments の検査（exit 5）
    → (3) 観察メモの行の除去と書き戻し。前段を通った場合にだけ後段を行う。"""
    if args.only and args.max_files is None:
        print("doc-targets: --only seed-direct には --max-files が必要です", file=sys.stderr)
        sys.exit(EXIT_USAGE)
    if args.max_files is not None and not args.only:
        print("doc-targets: --max-files は --only seed-direct と併用してください", file=sys.stderr)
        sys.exit(EXIT_USAGE)
    state_path = Path(args.path)
    data = _load_state(state_path)
    repo_path = data.get("repo_path") or ""
    # (1)
    ledger = _parse_ledger(args.ledger, repo_path)
    memo = _parse_obs_memo(args.memo, repo_path)
    reviewed = _parse_gap_reviewed(args.gap_reviewed, repo_path)
    ledger_pairs = _check_ledger(ledger, args.ledger)
    # (2)
    assigned_pairs = (_check_module_assignments(Path(args.module_assignments), ledger_pairs, repo_path, ledger)
                      if args.module_assignments else {})
    # (3)
    ledger_files = {e["file"] for e in ledger}
    memo_pruned = _prune_obs_memo(memo, ledger_files, repo_path) if memo is not None else 0

    pairs = {**ledger_pairs, **assigned_pairs}
    confirmed_hm = _confirmed_files(data)
    confirmed_all = set(confirmed_hm)
    over_limit = []
    if args.only:
        candidates, over_limit = _seed_direct_gap(data, ledger, reviewed, args.max_files)
    else:
        candidates = sorted(set(confirmed_hm) - ledger_files)

    def _targets_for(pairs_: dict) -> tuple:
        found, missing = [], []
        for f in sorted(candidates):
            module, module_dir = _longest_module(f, pairs_)
            found.append({"file": f, "confidence": confirmed_hm.get(f, ""), "module": module, "module_dir": module_dir})
            if not module:
                missing.append(f)
        return found, missing

    doc_targets, unassigned = _targets_for(pairs)
    auto_assigned = {}
    if args.auto_assign and unassigned:
        assign_file = Path(args.module_assignments) if args.module_assignments else state_path.parent / "module-assignments.json"
        auto_assigned = _auto_assign_modules(unassigned, pairs, assign_file)
        pairs = {**pairs, **auto_assigned}
        doc_targets, unassigned = _targets_for(pairs)
    counts = {}
    for f in ledger_files | {t["file"] for t in doc_targets if t["module"]}:
        module, _d = _longest_module(f, pairs)
        if module:
            counts[module] = counts.get(module, 0) + 1

    # bfs-state.json は {OUTPUT_DIR}/work/ に置かれる。
    out_dir = state_path.parent.parent if state_path.parent.name == "work" else state_path.parent
    if not (out_dir / f"SPO-{data.get('cr', '')}.md").is_file():
        layout = "none"
    elif (out_dir / "modules").is_dir():
        layout = "split"
    else:
        layout = "integrated"

    print(json.dumps({
        "ok": True,
        "doc_targets": doc_targets,
        "over_limit_files": over_limit,
        "documented_confirmed": sorted(ledger_files & confirmed_all),
        "unconfirmed_documented": sorted(ledger_files - confirmed_all),
        "doc_target_modules": sorted({_module_dir_for_file(repo_path, t["file"]) for t in doc_targets}),
        "unassigned": unassigned,
        "module_file_counts": dict(sorted(counts.items())),
        "current_layout": layout,
        "memo_pruned": memo_pruned,
        "auto_assigned": [{"module": n, "module_dir": d} for n, d in sorted(auto_assigned.items())],
    }, ensure_ascii=False))


def _seed_total_from_note(lines: list):
    """候補表の注記行から採用シンボルの合計ヒット数を読む（注記が無ければ None）。"""
    for line in lines:
        if line.startswith(SEED_TOTAL_NOTE_PREFIXES):
            m = re.search(r"合計ヒット数: (\d+)", line)
            if m:
                return int(m.group(1))
    return None


def cmd_prelim_metrics(args) -> None:
    """波紋調査完了時の件数系計測（prelim_summary）を bfs-state.json と同じディレクトリの metrics.jsonl へ
    1行追記する。既に prelim_summary があれば追記しない（初回の完了時の値だけを記録する）。"""
    state_path = Path(args.path)
    metrics_path = state_path.parent / "metrics.jsonl"
    if metrics_path.is_file():
        for line in metrics_path.read_text(encoding="utf-8").splitlines():
            try:
                if json.loads(line).get("event") == "prelim_summary":
                    print(json.dumps({"ok": True, "skipped": "already_recorded"}, ensure_ascii=False))
                    return
            except (ValueError, AttributeError):
                continue
    data = _load_state(state_path)
    repo_path = data.get("repo_path") or ""
    seeds = _parse_seed_candidates(Path(args.seed_candidates))
    ledger = _parse_ledger(args.ledger, repo_path)

    cands = seeds["candidates"]
    adopted = [c for c in cands if c["adopted"]]
    prelim_files = {e["file"] for e in ledger if e["phase"] == LEDGER_PHASE_PRELIM}
    confirmed_hm = _confirmed_files(data)
    confirmed_all = set(confirmed_hm)
    line = {
        "event": "prelim_summary",
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "seed_gate": args.seed_gate == "true",
        "prelim_file_count": len(prelim_files),
        "prelim_seed_count": sum(1 for c in cands if c["origin"] == SEED_ORIGIN_PRELIM),
        "prelim_seed_adopted_count": sum(1 for c in adopted if c["origin"] == SEED_ORIGIN_PRELIM),
        "human_added_count": sum(1 for c in cands if c["origin"] == SEED_ORIGIN_HUMAN_ADDED),
        "human_removed_count": sum(1 for c in cands if not c["adopted"]),
        "adopted_zero_hit_count": sum(1 for c in adopted
                                      if {SEED_WARN_ZERO_HIT, SEED_WARN_ZERO_AFTER_FILTER} & set(_warning_words(c["warning"]))),
        "adopted_noisy_count": sum(1 for c in adopted if SEED_WARN_NOISY in _warning_words(c["warning"])),
        "adopted_over_budget_count": sum(1 for c in adopted if SEED_WARN_OVER_BUDGET in _warning_words(c["warning"])),
        "adopted_total_hits": _seed_total_from_note(seeds["lines"]),
        "confirmed_file_count": len(confirmed_hm),
        "bfs_only_file_count": len(set(confirmed_hm) - prelim_files),
        "prelim_only_file_count": len(prelim_files - confirmed_all),
    }
    with open(metrics_path, "a", encoding="utf-8", newline="\n") as mf:
        mf.write(json.dumps(line, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, **line}, ensure_ascii=False))


# ---------------------------------------------------------------------------
# SPO の仕上げ: モジュールの自動割り当て・波紋調査の要約・検証スイープ・SPO の組み立て
#   doc-targets / ripple-summary / verify-sweep / assemble-spo / commit-assemble-inputs
# ---------------------------------------------------------------------------

# verify-sweep が「未記録ヒットあり」を、成功（0）・実行エラー（1）・件数不一致（specout_verify_counts.py の 3）と
# 区別して返す終了コード。
EXIT_UNRECORDED_SWEEP = 7

NO_FUNCTION_LABEL = "（関数の外）"
# SPO §5.0（波紋調査の要約）とモジュール資料の「波紋調査の結果」の行数の上限（超えた分は1行にまとめる）。
SUMMARY_MAX_ROWS = 30
MODULE_RIPPLE_MAX_ROWS = 30
SUMMARY_COLUMNS = ["機能（モジュール）", "確定ファイル数", "うち名前の一致のみ", "最も浅い到達波",
                   "シードの直接参照（うち資料に無い）", "資料", "影響の経路の代表"]
MODULE_RIPPLE_COLUMNS = ["ファイル", "主な関数", "発見波", "同一性", "シードの直接参照", "資料に記載", "影響の経路の代表"]
MODULE_RIPPLE_HEADING = "## 波紋調査の結果"
MODULE_RIPPLE_TITLE = "波紋調査の結果"
NO_RIPPLE_TEXT = "波紋調査を行っていない（人の判断）"
NOT_REACHED_TEXT = "波紋調査はこのモジュールのファイルに届いていない"
# 波紋調査を行わないと人が決めた印（{OUTPUT_DIR}/work/no-ripple.json）・追加下調べが関係なしと判断したファイルの記録・
# document agent の入力の指紋・document agent に渡す ENTRY_POINTS の累積。いずれも {OUTPUT_DIR}/work/ に置く。
NO_RIPPLE_MARK = "no-ripple.json"
GAP_REVIEWED_FILE = "prelim-gap-reviewed.md"
GAP_REVIEWED_COLUMNS = ("ファイルパス", "判断", "理由")
GAP_REVIEWED_UNRELATED = "関係なし"
ASSEMBLE_INPUTS_FILE = "assemble-inputs.json"
DOC_ENTRY_POINTS_FILE = "doc-entry-points.json"
# prelim_gap_files の理由（追加下調べの累計の上限で外した／追加下調べの対象だったが資料が無い）。
GAP_OVER_LIMIT = "over-limit"
GAP_NOT_WRITTEN = "not-written"
SWEEP_HEADING = "## 検証スイープ結果"
SWEEP_LIMIT_NOTE = "⚠️ **限界事項**: このスイープはファイル単位の漏れを検出します。伝播パスの正しさは保証しません。"
SWEEP_FP_LIMIT_NOTE = ("判定で関係なし（false-positive のみ）としたファイルは、ファイル単位で突き合わせ済みにします"
                       "（別のシンボルの再検索でヒットしても突き合わせ済みになります）。")
SWEEP_FP_COUNT_FMT = ("判定で関係なし（false-positive のみ）として突き合わせ済みにしたファイル: {n} 件"
                      "（表の「帳簿の記録」の ✅ には、これらのファイルも含む。"
                      "一覧は「" + FALSE_POSITIVE_FILES_HEADING + "」）")
CASE_DUP_HEADING = "## 同名 MEDIUM シンボル・異スコープ重複ログ"
AUTO_NOTE_PREFIX = "[自動転記]"
WRITER_SCRIPT_COMMENT = "<!-- 書き手: スクリプト（specout_bfs.py assemble-spo）。手で直さない（再実行で上書きされる） -->"
# §5.5 は人の修正を残すため専用の文言にする（テンプレートの §5.5 の書き手のコメントもこれと一字一句同じにする）。
WRITER_SCRIPT_KEEP_COMMENT = ("<!-- 書き手: スクリプト（specout_bfs.py assemble-spo）。観察メモに行のあるファイルの値は再実行で"
                              "観察メモの値に置き換わる。それ以外の行の人の修正は再実行で残る（値が `未確認` の行は備考も作り直す） -->")
TESTABILITY_UNCONFIRMED = "未確認"
TESTABILITY_NOTE_UNREAD = "下調べ・追加下調べで読んでいないファイル（波紋調査で到達）"
TESTABILITY_NOTE_NO_MEMO = "累積観察メモにテスト可能性の行が無い"
BRIEF_NOTE = "> quick プロファイルのため代表例のみ記載。詳細は discovery-log.md を参照"
BRIEF_REPRESENTATIVES = 5
# §5.0・§5.2 の表の直後にスクリプトが置く注記（再実行で置き換えるため、テンプレートの注記と重ならない書き出しにする）。
NO_RIPPLE_NOTE = "> ※ 波紋調査は行っていない（人の判断。`work/no-ripple.json`）。"
SCOPE_52_NOTE = "> ※ 資料のあるモジュールのファイルだけを載せる。資料の無いモジュールへの波及は §5.0 と `ripple-summary.md` を参照"
SUMMARY_NOTE_PREFIXES = ("> ※ ",)
SPO_PRELIM_NOTICE_PREFIX = "> ⚠️ 波紋調査前の資料です。"
AUTHOR_PRELIM = "AI（xddp-specout-prelim-agent）"
AUTHOR_BOTH = "AI（xddp-specout-prelim-agent, xddp-specout-document-agent）"
# 版の確定・波紋調査の有無の変化で変更履歴に足す行の変更者と変更内容。
AUTHOR_SCRIPT = "specout_bfs.py assemble-spo"
HISTORY_FINAL_RIPPLE = "確定（波紋調査の結果を反映）"
HISTORY_FINAL_NO_RIPPLE = "確定（波紋調査なし）"
HISTORY_CHANGE_RIPPLE = "波紋調査の結果を反映"
HISTORY_CHANGE_NO_RIPPLE = "波紋調査なしで作り直し"
HISTORY_MOVED = "確定（統合パスから移し替え）"
HISTORY_INDEX = "確定（サブディレクトリ分割の索引）"
HISTORY_PRELIM = "下調べ（波紋調査前）"
# 変更内容 → 波紋調査ありか（版 1.0 以上の SPO で、波紋調査の有無が変わったかの判定に使う）。
HISTORY_RIPPLE_KIND = {HISTORY_FINAL_RIPPLE: True, HISTORY_CHANGE_RIPPLE: True,
                       HISTORY_FINAL_NO_RIPPLE: False, HISTORY_CHANGE_NO_RIPPLE: False}


def _is_sep_row(line: str) -> bool:
    return bool(re.match(r"^\|\s*:?-{3,}", line.strip()))


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _auto_module_name(module_dir: str) -> str:
    """親ディレクトリから作る既定のモジュール名。`/` を `-` に置き換える（リポジトリ直下 `.` は `root`）。
    台帳・module-assignments.json の名前の文字種（英数字・`-`・`_`）に収めるため、他の文字も `-` にする。"""
    if module_dir == ".":
        return "root"
    return re.sub(r"[^A-Za-z0-9_-]", "-", module_dir.replace("/", "-"))


def _auto_assign_modules(unassigned: list, pairs: dict, assign_path: Path) -> dict:
    """どのモジュールにも属さないファイルの親ディレクトリを新しいモジュールディレクトリとし、
    module-assignments.json に追記する。追記した組を {名前: ディレクトリ} で返す。
    - 親ディレクトリが既存の組（台帳の組・module-assignments.json の組・今回追加した組）のディレクトリと同じ場合は
      新しい組を作らない（同名のモジュール名を重複させない）。
    - 置換後の名前が、異なるディレクトリの既存の組・今回追加した組と衝突する場合は exit 1（上書きしない）。"""
    all_pairs = dict(pairs)
    added = {}
    for f in unassigned:
        d = posixpath.dirname(f) or "."
        if d in all_pairs.values():
            continue
        name = _auto_module_name(d)
        if name in all_pairs and all_pairs[name] != d:
            _err(f"モジュール名 `{name}` が衝突します: ディレクトリ `{d}` と `{all_pairs[name]}` の自動割り当てが同じ名前になります。"
                 f"{assign_path} に `{{\"module\": ..., \"module_dir\": ...}}` を人が書いて名前を分け、再実行してください")
        all_pairs[name] = d
        added[name] = d
    if added:
        current = []
        if assign_path.is_file():
            try:
                current = json.loads(assign_path.read_text(encoding="utf-8"))
            except ValueError as e:
                _err(f"module-assignments.json を JSON として読めません: {assign_path}（{e}）")
        current = list(current) + [{"module": n, "module_dir": d} for n, d in sorted(added.items())]
        _write_text(assign_path, json.dumps(current, ensure_ascii=False, indent=2) + "\n")
    return added


def _doc_plan(data: dict, ledger_path, assign_path) -> tuple:
    """doc-targets・ripple-summary・assemble-spo が共有する、台帳と module-assignments.json からの割り当て。
    書式不正は `_parse_ledger` / `_check_ledger`（exit 1）・`_check_module_assignments`（exit 5）。
    戻り値: (台帳の行, {モジュール名: ディレクトリ}, doc_targets, 台帳のファイル集合)。"""
    repo_path = data.get("repo_path") or ""
    ledger = _parse_ledger(ledger_path, repo_path)
    ledger_pairs = _check_ledger(ledger, ledger_path)
    assigned = _check_module_assignments(Path(assign_path), ledger_pairs, repo_path, ledger) if assign_path else {}
    pairs = {**ledger_pairs, **assigned}
    ledger_files = {e["file"] for e in ledger}
    hm = _confirmed_files(data)
    targets = []
    for f in sorted(set(hm) - ledger_files):
        module, module_dir = _longest_module(f, pairs)
        targets.append({"file": f, "confidence": hm[f], "module": module, "module_dir": module_dir})
    return ledger, pairs, targets, ledger_files


def _parse_gap_reviewed(path, repo_path: str = "") -> list:
    """追加下調べが関係なしと判断したファイルの記録（work/prelim-gap-reviewed.md）を解析する。
    未指定・ファイル不在は []。書式不正（表の見出し行不在・列数不一致・空のファイルパス・判断が `関係なし` 以外）は
    exit 1（stderr に記録のパスと該当行）。戻り値: [{"file", "reason"}]（パスは `_norm_path` で正規化済み）"""
    if path is None or not Path(path).is_file():
        return []
    path = Path(path)
    lines = path.read_text(encoding="utf-8").split("\n")

    def _fail(msg: str) -> None:
        _err(f"追加下調べの判断の記録の書式が不正です: {path}\n{msg}")

    header, rows = _md_table_in(lines, 0, len(lines))
    if header is None or tuple(header) != GAP_REVIEWED_COLUMNS:
        _fail(f"表の見出し行 `| {' | '.join(GAP_REVIEWED_COLUMNS)} |` がありません")
    out = []
    for idx, cells in rows:
        raw = lines[idx].strip()
        if len(cells) != len(GAP_REVIEWED_COLUMNS):
            _fail(f"{idx + 1}行目: 列数が {len(cells)} です（{len(GAP_REVIEWED_COLUMNS)} 列であること）: {raw}")
        file_, judge = _strip_code(cells[0]), cells[1].strip()
        if not file_:
            _fail(f"{idx + 1}行目: ファイルパスが空です: {raw}")
        if judge != GAP_REVIEWED_UNRELATED:
            _fail(f"{idx + 1}行目: 判断が `{GAP_REVIEWED_UNRELATED}` ではありません: {raw}")
        out.append({"file": _norm_path(file_, repo_path), "reason": cells[2].strip()})
    return out


def _seed_direct_gap(data: dict, ledger: list, reviewed: list, max_files) -> tuple:
    """シードの直接参照のうち、台帳にも追加下調べの判断の記録にも無いファイルを、追加下調べの順
    （同一性 resolved → シードのヒット行数の多い順 → パス）に並べ、repo ごとの累計の上限で (採る, 外す) に分ける。
    今回採れる件数 = max(0, max_files −（台帳の工程 `追加下調べ` の行数 ＋ 判断の記録の行数）)。max_files が None なら上限なし。
    doc-targets・assemble-spo --layout-only・ripple-summary が同じ state・台帳・判断の記録から同じ結果を得る。"""
    repo_path = data.get("repo_path") or ""
    ledger_files = {e["file"] for e in ledger}
    reviewed_files = {r["file"] for r in reviewed}
    identity = {_norm_path(f, repo_path): (info or {}).get("identity")
                for f, info in (data.get("confirmed_files") or {}).items()}
    hits = {}
    for f, n in (data.get("seed_direct_hits") or {}).items():
        k = _norm_path(f, repo_path)
        hits[k] = hits.get(k, 0) + int(n or 0)
    gap = {_norm_path(f, repo_path) for f in (data.get("seed_direct_files") or [])} - ledger_files - reviewed_files
    order = sorted(gap, key=lambda f: (0 if identity.get(f) == LV.IDENTITY_RESOLVED else 1, -hits.get(f, 0), f))
    if max_files is None:
        return order, []
    used = sum(1 for e in ledger if e["phase"] == LEDGER_PHASE_ADDITIONAL) + len(reviewed)
    room = max(0, int(max_files) - used)
    return order[:room], order[room:]


# -- discovery-log のヒット表の読み取り -----------------------------------------

def _log_symbol_base(cell: str) -> str:
    s = _strip_code(cell)
    return _parse_entry(s)[0]


def _parse_log_hits(text: str, repo_path: str) -> list:
    """discovery-log.md の各 `## Wave N` のヒット表を読む（行ID・波・検索シンボル・ファイル・行・含む関数・伝播種別・
    確信度・派生元）。書式の異なる表・他の節は読まない。"""
    rows = []
    wave = None
    header = None
    idx = {}
    for line in text.split("\n"):
        m = re.match(r"^## Wave (\d+)\s*$", line)
        if m:
            wave, header = int(m.group(1)), None
            continue
        if line.startswith("## "):
            wave, header = None, None
            continue
        if wave is None:
            continue
        s = line.strip()
        if not s.startswith("|"):
            if s:
                header = None
            continue
        cells = _split_row(s)
        if cells and cells[0] == "行ID" and "ファイル" in cells and "派生元" in cells:
            header = cells
            idx = {"sym": cells.index("検索シンボル") if "検索シンボル" in cells else None,
                   "file": cells.index("ファイル"), "line": cells.index("行") if "行" in cells else None,
                   "func": next((i for i, c in enumerate(cells) if c.startswith("含む関数")), None),
                   "label": cells.index("伝播種別") if "伝播種別" in cells else None,
                   "conf": cells.index("確信度") if "確信度" in cells else None,
                   "origin": cells.index("派生元")}
            continue
        if header is None or _is_sep_row(s) or len(cells) != len(header):
            continue

        def _cell(key):
            i = idx.get(key)
            return cells[i] if i is not None else ""

        func = _strip_code(_cell("func"))
        try:
            line_no = int(_cell("line"))
        except ValueError:
            line_no = 0
        rows.append({
            "line_id": cells[0], "wave": wave, "symbol": _log_symbol_base(_cell("sym")),
            "file": _norm_path(_cell("file"), repo_path), "line": line_no,
            "func": "" if func in ("", "-", "—") else func,
            "label": _cell("label"), "confidence": _cell("conf"),
            "origins": [o.strip() for o in _cell("origin").split(",") if o.strip()],
        })
    return rows


def _load_class_ranges(waves_dir: Path, waves: set) -> dict:
    """work/waves/wave-{N}-class.json の enclosing_range を {行ID: [開始行, 終了行]} で返す（無ければ空）。"""
    ranges = {}
    for w in sorted(waves):
        p = waves_dir / f"wave-{w}-class.json"
        if not p.is_file():
            continue
        try:
            entries = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if isinstance(entries, dict):
            entries = entries.get("classification", [])
        for e in entries if isinstance(entries, list) else []:
            rng = e.get("enclosing_range") if isinstance(e, dict) else None
            if isinstance(rng, list) and len(rng) == 2 and all(isinstance(n, int) for n in rng):
                ranges[e.get("line_id")] = rng
    return ranges


def _hit_path(row: dict, by_id: dict) -> str:
    """シードからこのヒットまでの経路（`seed(X) → 経由シンボル… → 第N波`）。最初の派生元だけをたどる。"""
    parts, cur, label, seen = [], row, None, set()
    while True:
        if cur["line_id"] in seen:
            break
        seen.add(cur["line_id"])
        origin = cur["origins"][0] if cur["origins"] else ""
        if origin.startswith(("seed(", "seed-global(")):
            label = origin
            break
        parent = by_id.get(origin)
        parts.insert(0, cur["symbol"])
        if parent is None:
            label = origin or LV.ORIGIN_UNKNOWN
            break
        cur = parent
    return " → ".join([label or LV.ORIGIN_UNKNOWN] + parts + [f"第{row['wave']}波"])


def _is_none_label(label: str) -> bool:
    return label == "false-positive"


def _aggregate_functions(rows: list, ranges: dict, module_of: dict) -> list:
    """ヒット行を (ファイル, 関数) ごとにまとめる。偽陽性の行は含めない。"""
    by_id = {r["line_id"]: r for r in rows}
    funcs = {}
    for r in rows:
        if r["file"] not in module_of or _is_none_label(r["label"]):
            continue
        key = (r["file"], r["func"])
        f = funcs.get(key)
        if f is None:
            f = funcs[key] = {"file": r["file"], "name": r["func"], "range": None, "lines": set(), "waves": set(),
                              "labels": [], "hit_count": 0, "seed_def": False, "_best": None}
        f["lines"].add(r["line"])
        f["waves"].add(r["wave"])
        if r["label"] and r["label"] not in f["labels"]:
            f["labels"].append(r["label"])
        f["hit_count"] += 1
        if r["wave"] == 0 and "self-def" in r["label"]:
            f["seed_def"] = True   # 第0波のシード自身の定義（変更対象）
        rng = ranges.get(r["line_id"])
        if rng and r["func"] and (f["range"] is None or rng[1] - rng[0] > f["range"][1] - f["range"][0]):
            f["range"] = list(rng)
        if f["_best"] is None or r["wave"] < f["_best"]["wave"]:
            f["_best"] = r
    out = []
    for f in funcs.values():
        best = f.pop("_best")
        f["min_wave"] = min(f["waves"])
        f["waves"] = sorted(f["waves"])
        f["lines"] = sorted(f["lines"])
        f["path"] = _hit_path(best, by_id)
        f["origin"] = best["origins"][0] if best["origins"] else LV.ORIGIN_UNKNOWN
        out.append(f)
    return sorted(out, key=lambda x: (x["file"], x["range"][0] if x["range"] else (x["lines"][0] if x["lines"] else 0),
                                      x["name"]))


# -- ripple-summary -------------------------------------------------------------

def _truncation_summary(truncated: list) -> list:
    """打ち切り記録の理由別の件数と、ヒット数の多い順の主なシンボル。[(理由, 件数の表記, [シンボル(ヒット数)])]"""
    by_reason = {}
    for t in truncated:
        by_reason.setdefault(t.get("reason") or "", []).append(t)
    rows = []
    for reason in sorted(by_reason):
        items = by_reason[reason]
        n_sym = len({t.get("symbol") for t in items})
        count = str(n_sym) if n_sym == len(items) else f"{n_sym}（記録 {len(items)} 件）"
        top = sorted(items, key=lambda t: -(t.get("hits") or 0))[:5]
        rows.append((reason, count, [f"`{t.get('symbol')}`" + (f"（{t['hits']}）" if t.get("hits") is not None else "")
                                     for t in top]))
    return rows


def _unsupported_pattern_rows(log_text: str) -> list:
    """discovery-log の「## grep未対応パターン」の表のデータ行（例の行〔`（例）` で始まる〕は除く）。"""
    lines = log_text.split("\n")
    rng = _md_section_range(lines, GREP_UNSUPPORTED_HEADING)
    if rng is None:
        return []
    _h, rows = _md_table_in(lines, *rng)
    return [cells for _i, cells in rows if cells and not cells[0].startswith("（例）")]


def _identity_label(identity: str) -> str:
    return "resolved" if identity == LV.IDENTITY_RESOLVED else "name-only（名前の一致のみ）"


def _fmt_wave_range(waves: list) -> str:
    return "—" if not waves else (str(waves[0]) if waves[0] == waves[-1] else f"{waves[0]}〜{waves[-1]}")


def _seed_direct_cell(count: int, gap: int) -> str:
    if not count:
        return "—"
    return f"{count}（⚠️{gap}）" if gap else str(count)


def _summary_row(m: dict) -> list:
    """SPO §5.0・ripple-summary.md の機能（モジュール）の1行。"""
    return [m["name"], m["confirmed_count"], m["name_only_count"], m["min_wave"],
            _seed_direct_cell(m["seed_direct_count"], m["prelim_gap_count"]),
            "あり" if m["documented"] else "なし", m["path"]]


def _summary_order(mods: list) -> list:
    """§5.0 の並び: 最も浅い到達波 → （確定ファイル数 − 名前の一致のみ）の多い順 → 確定ファイル数の多い順 → 名前。"""
    return sorted(mods, key=lambda m: (m["min_wave"], -(m["confirmed_count"] - m["name_only_count"]),
                                       -m["confirmed_count"], m["name"]))


def _overflow_row(text: str, width: int) -> list:
    return [text] + ["—"] * (width - 1)


def cmd_ripple_summary(args) -> None:
    """波紋調査の結果の要約。機能（モジュール）単位の集計を、人向けの全量（--out。上限なし。LLM には渡さない）と
    スクリプト向けの JSON（--json。assemble-spo が SPO §5.0・§5.1・§5.2・§5.5・§9 とモジュール資料の
    「波紋調査の結果」を書く入力）に書く。どのモジュールにも属さない確定ファイルがあれば exit 1。"""
    state_path = Path(args.path)
    data = _load_state(state_path)
    repo_path = data.get("repo_path") or ""
    log_path = Path(args.discovery_log)
    if not log_path.is_file():
        _err(f"discovery-log.md が見つかりません: {log_path}")
    ledger, pairs, targets, ledger_files = _doc_plan(data, args.ledger, args.module_assignments)
    bad = [t["file"] for t in targets if not t["module"]]
    if bad:
        _err("どのモジュールにも属さない確定ファイルがあります（doc-targets --auto-assign を先に実行してください）: "
             + ", ".join(bad[:10]) + (f" ほか{len(bad) - 10}件" if len(bad) > 10 else ""))
    reviewed = _parse_gap_reviewed(args.gap_reviewed, repo_path)
    taken, over = _seed_direct_gap(data, ledger, reviewed, args.max_files)
    gap_reason = {**{f: GAP_NOT_WRITTEN for f in taken}, **{f: GAP_OVER_LIMIT for f in over}}
    seed_direct = {_norm_path(f, repo_path) for f in (data.get("seed_direct_files") or [])}
    hm = _confirmed_files(data)
    module_of = {}
    for f in hm:
        name, _d = _longest_module(f, pairs)
        if name:
            module_of[f] = name

    log_text = log_path.read_text(encoding="utf-8")
    rows = _parse_log_hits(log_text, repo_path)
    waves_dir = Path(args.waves_dir) if args.waves_dir else state_path.parent / "waves"
    ranges = _load_class_ranges(waves_dir, {r["wave"] for r in rows})
    funcs = _aggregate_functions(rows, ranges, module_of)
    seeds = {o[5:-1] for r in rows for o in r["origins"] if o.startswith("seed(") and o.endswith(")")}
    ledger_modules = {e["module"] for e in ledger}
    prelim_modules = {e["module"] for e in ledger if e["phase"] == LEDGER_PHASE_PRELIM}

    by_file = {}
    for fn in funcs:
        by_file.setdefault(fn["file"], []).append(fn)
    mods = {name: {"name": name, "dir": d, "files": [], "functions": []} for name, d in pairs.items()}
    confirmed_info = {_norm_path(k, repo_path): v for k, v in (data.get("confirmed_files") or {}).items()}
    for f in sorted(module_of):
        info = confirmed_info.get(f) or {}
        fns = sorted(by_file.get(f, []), key=lambda x: (x["min_wave"], -x["hit_count"], x["name"]))
        mods[module_of[f]]["files"].append({
            "file": f, "wave": info.get("wave", 0), "confidence": hm[f],
            "identity": info.get("identity") or LV.IDENTITY_NAME_ONLY,
            "documented": f in ledger_files, "seed_direct": f in seed_direct,
            "functions": list(dict.fromkeys(fn["name"] or NO_FUNCTION_LABEL for fn in fns)),
            "path": fns[0]["path"] if fns else "—"})
    for fn in funcs:
        mods[module_of[fn["file"]]]["functions"].append(fn)
    mods = {n: m for n, m in mods.items() if m["files"]}
    for m in mods.values():
        waves = sorted({fe["wave"] for fe in m["files"]})
        m["min_wave"], m["max_wave"] = waves[0], waves[-1]
        m["direct"] = any(fe["wave"] == 0 for fe in m["files"])
        m["confirmed_count"] = len(m["files"])
        m["name_only_count"] = sum(1 for fe in m["files"] if fe["identity"] != LV.IDENTITY_RESOLVED)
        m["prelim"] = m["name"] in prelim_modules
        m["documented"] = m["name"] in ledger_modules
        m["hit_count"] = sum(fn["hit_count"] for fn in m["functions"])
        m["seed_direct_count"] = sum(1 for fe in m["files"] if fe["seed_direct"])
        m["prelim_gap_count"] = sum(1 for fe in m["files"] if fe["file"] in gap_reason)
        reps = sorted(m["functions"], key=lambda x: (x["min_wave"], -x["hit_count"], x["file"]))
        m["path"] = reps[0]["path"] if reps else "—"
    order = _summary_order(list(mods.values()))
    for k, m in enumerate(order):
        m["in_summary"] = k < SUMMARY_MAX_ROWS

    gap_files = [{"file": f, "reason": gap_reason[f], "module": module_of.get(f, "")} for f in [*taken, *over]]
    direct_modules = sorted(m["name"] for m in mods.values() if m["direct"])

    # 人向けの全量（上限なし）
    out = [f"# 波紋調査の結果（全量） — {data.get('cr', '')} / {data.get('repo', '')}", "",
           "> 人向けの全量（上限なし）。LLM には渡さない。SPO §5.0 はこの表の上位 "
           f"{SUMMARY_MAX_ROWS} 行の要約。件数はスクリプトが数えた値。", "",
           "## 1. 機能（モジュール）の一覧", ""]
    out += _table_lines(SUMMARY_COLUMNS, [_summary_row(m) for m in order]) if order else ["なし"]
    out += ["", "## 2. 調査の打ち切り", ""]
    summ = _truncation_summary(data.get("truncated") or [])
    if summ:
        out += _table_lines(["理由", "シンボル数", "主なシンボル（ヒットの多い順）"],
                            [[r, c, ", ".join(top)] for r, c, top in summ])
    else:
        out.append("なし")
    out += ["", "## 3. 下調べに無いシードの直接参照", ""]
    if gap_files:
        out += _table_lines(["ファイル", "モジュール", "状態"], [[
            g["file"], g["module"] or "—",
            "上限超過（追加下調べの累計の上限 `SPECOUT_MAX_AFFECTED_FILES` を超えたため追加下調べしない）"
            if g["reason"] == GAP_OVER_LIMIT else "資料なし（追加下調べで書けなかった、または未実施）"] for g in gap_files])
    else:
        out.append("なし")
    out += ["", "### 追加下調べが関係なしと判断したファイル", ""]
    out += (_table_lines(["ファイル", "理由"], [[r["file"], r["reason"]] for r in reviewed]) if reviewed else ["なし"])
    out += ["", "## 4. grep 未対応パターン", ""]
    unsupported = _unsupported_pattern_rows(log_text)
    out += (_table_lines(["パターン種別", "根拠（CRS/コードより）", "確認状況"], unsupported) if unsupported else ["なし"])
    out += ["", "## 5. モジュールごとのファイル一覧"]
    for m in order:
        out += ["", f"### {m['name']}（{m['dir']}）", ""]
        files = sorted(m["files"], key=lambda fe: (fe["wave"], 0 if fe["identity"] == LV.IDENTITY_RESOLVED else 1,
                                                   fe["file"]))
        out += _table_lines(["ファイル", "主な関数", "発見波", "同一性", "シードの直接参照", "資料にした", "影響の経路の代表"], [[
            fe["file"], ", ".join(fe["functions"][:3]) or "—", fe["wave"], _identity_label(fe["identity"]),
            "●" if fe["seed_direct"] else "—", "あり" if fe["documented"] else "—", fe["path"]] for fe in files])
    _write_text(Path(args.out), "\n".join(out).rstrip("\n") + "\n")

    summary = {
        "cr": data.get("cr", ""), "repo": data.get("repo", ""), "seeds": sorted(seeds),
        "seed_direct_file_count": len(seed_direct), "confirmed_file_count": len(hm),
        "direct_modules": direct_modules, "prelim_gap_files": gap_files, "gap_reviewed_files": reviewed,
        "modules": [m for m in sorted(mods.values(), key=lambda m: m["name"])],
    }
    _write_text(Path(args.json), json.dumps(summary, ensure_ascii=False, indent=1, default=list) + "\n")
    print(json.dumps({
        "ok": True, "seed_direct_file_count": len(seed_direct), "confirmed_file_count": len(hm),
        "module_count": len(mods), "summary_rows": min(len(mods), SUMMARY_MAX_ROWS), "direct_modules": direct_modules,
        "prelim_gap_files": gap_files, "out": str(args.out), "json": str(args.json),
    }, ensure_ascii=False))


# -- verify-sweep ----------------------------------------------------------------

def _case_a_symbols(log_text: str) -> set:
    """「## 同名 MEDIUM シンボル・異スコープ重複ログ」でケースA（HIGH 昇格）と記録されたシンボル。
    セクション自体が無いログでは空（この例外は適用しない）。"""
    lines = log_text.split("\n")
    rng = _md_section_range(lines, CASE_DUP_HEADING + "（発生時のみ記録）")
    if rng is None:
        rng = _md_section_range(lines, CASE_DUP_HEADING)
    if rng is None:
        return set()
    header, rows = _md_table_in(lines, *rng)
    if header is None or "シンボル" not in header or "ケース" not in header:
        return set()
    si, ci = header.index("シンボル"), header.index("ケース")
    return {_strip_code(c[si]) for _i, c in rows if len(c) > max(si, ci) and c[ci] == LV.CASE_A}


def _upsert_tail_section(log_path: Path, heading: str, body: str) -> None:
    """discovery-log の末尾側の節（検証スイープ結果）を置換する。無ければ末尾へ追加する。"""
    text = log_path.read_text(encoding="utf-8")
    section = heading + "\n\n" + body.strip("\n") + "\n"
    idx = text.find(heading + "\n")
    if idx == -1:
        new_text = text.rstrip("\n") + "\n\n" + section
    else:
        end = text.find("\n## ", idx + len(heading))
        new_text = text[:idx] + section + (("\n" + text[end + 1:]) if end != -1 else "")
    _write_text(log_path, new_text)


def cmd_verify_sweep(args) -> None:
    """検証スイープ。discovery-log の全シンボルを再検索し、ヒットしたファイルと波紋調査の帳簿（確定ファイル・
    判定で関係なしとしたファイル）を突き合わせて、未記録ヒットを discovery-log の「## 検証スイープ結果」に記録する
    （資料にしたかは問わない）。
    - HIGH シンボル: リポジトリ全域。MEDIUM シンボル・FILE シンボル: 記録された `[MEDIUM:filepath]`・
      `[FILE:filepath]` のスコープ内のみ（全域検索すると本来スコープ外だったファイルが誤検出される）。
      例外: 「## 同名 MEDIUM シンボル・異スコープ重複ログ」にケースA（HIGH 昇格）と記録されたシンボルは
      HIGH として全域を検索する（そのセクションが無いログでは例外を適用せず、全 MEDIUM をスコープ限定で検索する）。
    - 突き合わせ先は state の `confirmed_files`（確定ファイル）と `false_positive_files`（判定で関係なしとしたファイル）。
    - このスイープはファイル単位の漏れを検出するだけで、伝播パスの正しさは保証しない。`false_positive_files` も
      ファイル単位で突き合わせ済みにするため、あるシンボルの false-positive で入ったファイルは、別のシンボルの
      再検索でヒットしても突き合わせ済みになる（visited のシンボルのヒットは判定済み・dedup・行コメント除外・
      前倒し縮退・予算の打ち切りのいずれかのため、実害はほぼ無い）。"""
    state_path = Path(args.path)
    data = _load_state(state_path)
    repo_path = data.get("repo_path") or ""
    log_path = Path(args.discovery_log)
    if not log_path.is_file():
        _err(f"discovery-log.md が見つかりません: {log_path}")
    conf = dict(data)
    if args.exclude_patterns and not conf.get("exclude_patterns"):
        conf["exclude_patterns"] = _split_csv(args.exclude_patterns)
    if args.include_extensions and not conf.get("include_extensions"):
        conf["include_extensions"] = _split_csv(args.include_extensions)

    recorded = set(_confirmed_files(data))
    fp_recorded = {_norm_path(f, repo_path) for f in (data.get("false_positive_files") or {})} - recorded

    log_text = log_path.read_text(encoding="utf-8")
    case_a = _case_a_symbols(log_text)
    cut = {_parse_entry(t.get("symbol") or "")[0] for t in (data.get("truncated") or [])
           if t.get("reason") in (LV.TRUNC_HIT_BUDGET, LV.TRUNC_LLM_BUDGET, LV.TRUNC_WAVE_LIMIT)}
    entries = []
    for e in sorted(data.get("visited") or []):
        sym, scope = _parse_entry(e)
        if sym in cut:
            continue
        if _entry_scope_kind(e) == SCOPE_MEDIUM and sym in case_a:
            e = sym
        if e not in entries:
            entries.append(e)
    _raw, files, _lines, warning = _preview_seed_hits(entries, conf)

    table = ["| シンボル | grep ヒット（プロダクションコード） | 帳簿の記録 | 状態 |", "|---|---|---|---|"]
    unrecorded = set()
    fp_matched = set()
    for e in entries:
        fs = sorted(files.get(e, set()))
        missing = [f for f in fs if f not in recorded and f not in fp_recorded]
        unrecorded |= set(missing)
        fp_matched |= set(fs) & fp_recorded
        shown = ", ".join(fs[:5]) + (f" ほか{len(fs) - 5}件" if len(fs) > 5 else "") if fs else "（ヒットなし）"
        table.append(f"| `{_md_cell(e)}` | {_md_cell(shown)} | "
                     + ("✅" if not missing else f"⚠️ 未記録 {len(missing)} 件") + " | "
                     + ("OK" if not missing else "未記録ヒット") + " |")
    now = datetime.datetime.now().isoformat(timespec="minutes")
    body = [f"実行日時: {now}", "", SWEEP_LIMIT_NOTE, "", SWEEP_FP_LIMIT_NOTE, ""] + table + [""]
    body += [SWEEP_FP_COUNT_FMT.format(n=len(fp_matched)), ""]
    if warning:
        body += [f"> ⚠️ バックエンド警告: {warning}", ""]
    if unrecorded:
        body += [f"→ ⚠️ **未記録ヒット: {len(unrecorded)} 件**", "",
                 "波紋調査の帳簿（確定ファイル・関係なしとしたファイル）に無いヒットです。SPO §9 に転記しました。"
                 "探索の漏れの可能性があるため、必要なら `--re-discover` で該当シンボルを追加してください。", "",
                 "未記録ファイル:"]
        body += [f"- `{f}`" for f in sorted(unrecorded)]
    else:
        body.append("→ **未記録ヒット: なし。検証完了。**")
    _upsert_tail_section(log_path, SWEEP_HEADING, "\n".join(body))

    print(json.dumps({"ok": True, "unrecorded_hits": len(unrecorded), "swept_symbols": len(entries),
                      "unrecorded_files": sorted(unrecorded)}, ensure_ascii=False))
    if unrecorded:
        sys.exit(EXIT_UNRECORDED_SWEEP)


# -- assemble-spo: Markdown の節の操作 ----------------------------------------------

def _heading_indices(lines: list) -> list:
    """コードフェンスの外の見出し行 [(行インデックス, レベル, 見出し文字列)]。"""
    out, fence = [], False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            out.append((i, len(m.group(1)), m.group(2).strip()))
    return out


def _find_heading(lines: list, pattern: str):
    rx = re.compile(pattern)
    for i, _lv, _t in _heading_indices(lines):
        if rx.search(lines[i]):
            return i
    return None


def _block_end(lines: list, i: int) -> int:
    """見出し行 `i` の節の終わり（次の見出し行、またはコードフェンスの外の `---` 行。無ければ末尾）。"""
    heads = {h[0] for h in _heading_indices(lines)}
    fence = False
    for k in range(i + 1, len(lines)):
        line = lines[k]
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if k in heads or line.strip() == "---":
            return k
    return len(lines)


def _read_table(lines: list, pattern: str):
    """見出し `pattern` の節の最初の表を (ヘッダのセル, [セル]) で返す。無ければ (None, [])。"""
    i = _find_heading(lines, pattern)
    if i is None:
        return None, []
    header, rows = _md_table_in(lines, i + 1, _block_end(lines, i))
    return header, [cells for _k, cells in rows]


def _replace_table(lines: list, pattern: str, table: list, note=None, drop_note_prefix=None) -> bool:
    """見出し `pattern` の節の最初の表を `table`（行のリスト）で置き換える（無ければ節の末尾に置く）。
    `note`（文字列または文字列のリスト）があれば表の直後に空行を挟んで置く。`drop_note_prefix`（文字列またはそのタプル）で
    始まる既存の行は先に除く。見出しが無ければ False。"""
    i = _find_heading(lines, pattern)
    if i is None:
        return False
    if drop_note_prefix:
        end = _block_end(lines, i)
        drop = {k for k in range(i + 1, end) if lines[k].startswith(drop_note_prefix)}
        # 注記の直前の空行（表と注記の区切り）も除く（再実行で空行が増えないようにする）
        drop |= {k - 1 for k in drop if k - 1 > i and not lines[k - 1].strip()}
        lines[:] = [ln for k, ln in enumerate(lines) if k not in drop]
    end = _block_end(lines, i)
    ts = next((k for k in range(i + 1, end) if lines[k].strip().startswith("|")), None)
    notes = [note] if isinstance(note, str) else list(note or [])
    extra = ["", *notes] if notes else []
    if ts is None:
        lines[end:end] = ["", *table, *extra, ""]
        return True
    te = ts
    while te < end and lines[te].strip().startswith("|"):
        te += 1
    lines[ts:te] = table + extra
    return True


def _ensure_script_comment(lines: list, pattern: str, comment: str = WRITER_SCRIPT_COMMENT) -> None:
    i = _find_heading(lines, pattern)
    if i is None:
        return
    k = i + 1
    while k < len(lines) and not lines[k].strip():
        k += 1
    if k < len(lines) and lines[k].lstrip().startswith("<!-- 書き手"):
        lines[k] = comment
    else:
        lines.insert(i + 1, comment)


def _table_lines(header: list, rows: list) -> list:
    return [_md_row(header), "|" + "|".join("---" for _ in header) + "|"] + [_md_row(r) for r in rows]


def _spo_state_paths(out_dir: Path, cr: str) -> tuple:
    return out_dir / f"SPO-{cr}.md", out_dir / "modules", out_dir / "work" / "module-drafts"


def _module_sections(lines: list) -> list:
    """統合パスの `## 2.A. {モジュール名}` 節 [{letter, name, start, end}]（end は次の `## ` 見出しの手前）。"""
    heads = [h for h in _heading_indices(lines) if h[1] <= 2]
    out = []
    for n, (i, lv, text) in enumerate(heads):
        m = re.match(r"^2\.([A-Z]+)\.\s*(.+)$", text) if lv == 2 else None
        if not m:
            continue
        end = next((h[0] for h in heads[n + 1:]), len(lines))
        out.append({"letter": m.group(1), "name": m.group(2).strip(), "start": i, "end": end})
    return out


def _section_body(lines: list, sec: dict) -> list:
    """節の本文（見出し行と末尾の `---` を除く）。"""
    body = lines[sec["start"] + 1:sec["end"]]
    while body and not body[-1].strip():
        body.pop()
    if body and body[-1].strip() == "---":
        body.pop()
    while body and not body[-1].strip():
        body.pop()
    while body and not body[0].strip():
        body.pop(0)
    return body


def _letter_name(n: int) -> str:
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _strip_ripple_subsection(lines: list) -> list:
    """§2.X… の本文から `### 2.X.9 波紋調査の結果`（スクリプトが毎回作り直す節）を、次の `###` 以上の見出しの手前まで除く。"""
    out, skip, fence = [], False, False
    for ln in lines:
        if ln.lstrip().startswith("```"):
            fence = not fence
        elif not fence:
            if re.match(r"^###\s+2\.[A-Z]+\.9\b", ln):
                skip = True
                continue
            if skip and re.match(r"^#{1,3}\s", ln):
                skip = False
        if not skip:
            out.append(ln)
    return out


def _normalize_draft(text: str, letter: str) -> list:
    """work/module-drafts の本文を、指定の文字の §2.{letter}… 見出しへ直す（先頭の `## 2.X.` 見出しと、
    スクリプトが作り直す `### 2.X.9 波紋調査の結果` は除く）。"""
    lines = _strip_ripple_subsection(text.split("\n"))
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and re.match(r"^##\s+2\.[A-Z]+\.\s", lines[0]):
        lines.pop(0)
    out = []
    for ln in lines:
        out.append(re.sub(r"^(#{3,4}\s+2\.)[A-Z]+(\.)", lambda m: m.group(1) + letter + m.group(2), ln))
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


# -- assemble-spo: モジュール資料の組み立て（配置の移し替え） ---------------------------------

def _doc_header_block(template_text: str, cr: str, name: str, mdir: str, today: str, suffix: str, author: str,
                      version: str) -> list:
    head = template_text.split("\n---")[0].split("\n")
    out = []
    for ln in head:
        ln = (ln.replace("{CR番号}", cr).replace("{モジュール名}", name + suffix)
              .replace("{モジュールパス}", mdir).replace("{YYYY-MM-DD}", today))
        if ln.startswith("**作成者："):
            ln = f"**作成者：** {author}  "
        elif ln.startswith("**版数："):
            ln = f"**版数：** {version}"
        out.append(ln)
    return out


def _version_tuple(version) -> tuple:
    m = re.match(r"^\s*(\d+)\.(\d+)", version or "")
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def _doc_version(text: str) -> str:
    """資料の `**版数：**` の値（無ければ空文字列）。"""
    m = re.search(r"^\*\*版数：\*\*\s*(\S+)", text, re.M)
    return m.group(1) if m else ""


def _history_table(version: str, today: str, final_text: str) -> list:
    """スクリプトが作るモジュール資料の変更履歴。版 0.1 は下調べの行だけ、1.0 以上は確定の行を続ける。"""
    rows = [f"| 0.1 | {today} | {AUTHOR_PRELIM} | {HISTORY_PRELIM} |"]
    if _version_tuple(version) >= (1, 0):
        rows.append(f"| {version} | {today} | {AUTHOR_SCRIPT} | {final_text} |")
    return ["| 版数 | 日付 | 変更者 | 変更内容 |", "|------|------|--------|----------|", *rows]


def _overview_table(name: str, mdir: str, role: str, existing_spec: str) -> list:
    return ["| 項目 | 内容 |", "|------|------|", f"| モジュール名 | {_md_cell(name)} |", f"| ディレクトリ | {_md_cell(mdir)} |",
            f"| 役割・責務 | {_md_cell(role)} |", f"| 既存仕様書 | {_md_cell(existing_spec)} |"]


def _section_to_module_doc(sec_body: list, name: str, mdir: str, template_text: str, cr: str, today: str,
                           version: str) -> str:
    """統合パスの §2.A… の本文を、`MODULE_TEMPLATE` の §2〜§4 へ移して分割パスのモジュール資料にする
    （`### 2.A.n` → `### 2.n`、`### 2.A.7` → `## 3.`、`### 2.A.8` → `## 4.` の対応で節をそのまま移す）。
    `### 2.A.9 波紋調査の結果` は移さない（分割パスの `## 波紋調査の結果` は組み立てのたびにスクリプトが書く）。
    作成者は下調べ、版は `version`（SPO の版が 1.0 未満なら 0.1、1.0 以上なら 1.0）。"""
    sub_re = re.compile(r"^###\s+2\.[A-Z]+\.(\d+)\s*(.*)$")
    pre, subs, cur = [], {}, None
    fence = False
    for ln in sec_body:
        if ln.lstrip().startswith("```"):
            fence = not fence
        m = None if fence else sub_re.match(ln)
        if m:
            cur = int(m.group(1))
            subs[cur] = {"title": m.group(2).strip(), "lines": []}
        elif cur is None:
            pre.append(ln)
        else:
            subs[cur]["lines"].append(ln)
    preamble = [p for p in pre if p.strip()]
    spec = next((re.sub(r"^[-*]?\s*\**既存仕様書\**[:：]\s*", "", p).strip() for p in preamble if "既存仕様書" in p), "なし")
    role_lines = [p for p in preamble if "既存仕様書" not in p and not p.lstrip().startswith("|")]
    role = " ".join(re.sub(r"^[-*]\s*", "", p).strip() for p in role_lines) or "（§2.1 以降を参照）"
    out = _doc_header_block(template_text, cr, name, mdir, today, "", AUTHOR_PRELIM, version)
    out += ["", "---", "", "## 1. モジュール概要", ""] + _overview_table(name, mdir, role, spec)
    out += ["", "---", "", "## 2. 現状仕様", ""]
    for n in range(1, 7):
        if n in subs:
            s = subs[n]
            out += [f"### 2.{n} {s['title']}".rstrip()] + s["lines"]
            while out and not out[-1].strip():
                out.pop()
            out.append("")
    out += ["---", "", "## 3. 既存仕様の文書化（仕様書がない場合）", ""]

    def _renum(lines: list, old: str, new: str) -> list:
        return [re.sub(r"^####\s+2\.[A-Z]+\." + old + r"\.(\d+)", lambda m: f"### {new}.{m.group(1)}", ln) for ln in lines]

    body7 = _renum(subs[7]["lines"], "7", "3") if 7 in subs else ["対象外"]
    out += [ln for ln in body7]
    while out and not out[-1].strip():
        out.pop()
    out += ["", "---", "", "## 4. モジュール内ダイアグラム", ""]
    body8 = _renum(subs[8]["lines"], "8", "4") if 8 in subs else ["対象外"]
    out += [ln for ln in body8]
    while out and not out[-1].strip():
        out.pop()
    out += ["", "---", "", "## 5. 変更履歴", ""] + _history_table(version, today, HISTORY_MOVED)
    return "\n".join(out).rstrip("\n") + "\n"


def _row_matches(row: str, files: list):
    """行に現れるファイルパス（最長一致）。無ければ None。"""
    best = None
    for f in files:
        if f in row and (best is None or len(f) > len(best)):
            best = f
    return best


def _filter_doc_for_sub(old_text: str, cr: str, name: str, mdir: str, sub: str, sub_files: set, all_files: list,
                        keep_unmatched: bool) -> str:
    """サブディレクトリ分割: 元のモジュール資料を写し、表の行をファイルパスで振り分ける（そのサブディレクトリの
    ファイルの行だけを残す。どのファイルにも一致しない行は `keep_unmatched` のサブモジュールにだけ残す）。
    表以外の節は元の記述をそのまま引き継ぐ。"""
    out = []
    in_table = False
    sub_dir = mdir if sub == "root" else f"{mdir}/{sub}"
    for ln in old_text.split("\n"):
        s = ln.strip()
        if ln.startswith("**文書番号："):
            ln = f"**文書番号：** SPO-{cr}-{name}-{sub}  "
        elif ln.startswith("**対象モジュール："):
            ln = f"**対象モジュール：** {sub_dir}  "
        elif re.match(r"^\|\s*ディレクトリ\s*\|", ln):
            ln = f"| ディレクトリ | {sub_dir} |"
        elif re.match(r"^\|\s*モジュール名\s*\|", ln):
            ln = f"| モジュール名 | {name}/{sub} |"
        if s.startswith("|"):
            if not in_table:
                in_table = True
                out.append(ln)
                continue
            if _is_sep_row(s):
                out.append(ln)
                continue
            hit = _row_matches(ln, all_files)
            if hit is None:
                if keep_unmatched:
                    out.append(ln)
            elif hit in sub_files:
                out.append(ln)
            continue
        in_table = False
        out.append(ln)
    return "\n".join(out)


def _sub_of(file: str, mdir: str) -> str:
    rel = file if mdir == "." else file[len(mdir) + 1:]
    return rel.split("/")[0] if "/" in rel else "root"


def _history_of(text: str, default_version: str) -> tuple:
    """資料から (作成者, 版数, 版 0.1 の行があるか) を読む（無い項目は下調べ・`default_version`）。"""
    author = re.search(r"^\*\*作成者：\*\*\s*(.+?)\s*$", text, re.M)
    version = re.search(r"^\*\*版数：\*\*\s*(.+?)\s*$", text, re.M)
    return (author.group(1) if author else AUTHOR_PRELIM, version.group(1) if version else default_version,
            bool(re.search(r"^\|\s*0\.1\s*\|", text, re.M)))


def _index_doc(name: str, mdir: str, subs: dict, cr: str, today: str, template_text: str, old_text,
               prelim_info: tuple) -> str:
    author, version, _had01 = prelim_info
    out = _doc_header_block(template_text, cr, name, mdir, today, "", author, version)
    out += ["", "---", "", "## 1. モジュール概要", ""]
    ov = None
    if old_text:
        lines = old_text.split("\n")
        _h, rows = _read_table(lines, r"^##\s+1\.")
        if rows:
            ov = _table_lines(["項目", "内容"], rows)
    out += ov or _overview_table(name, mdir, "サブモジュール資料を参照", "なし")
    out += ["", "---", "", "## 2. サブモジュール一覧", "",
            "このモジュールはファイル数が `SPECOUT_MAX_FILES_PER_MODULE` を超えたためサブディレクトリ単位に分割した（本ファイルは索引）。", "",
            "| サブモジュール | ファイル | 波及ファイル数 | 概要 |", "|---|---|---|---|"]
    for sub in sorted(subs):
        out.append(f"| {sub} | `modules/{name}/{sub}-spo.md` | {len(subs[sub])} | サブモジュール資料を参照 |")
    out += ["", "---", "", "## 3. サブモジュール間シーケンス図", "", "対象外（サブモジュール間の関係は各サブモジュール資料を参照）",
            "", "---", "", "## 4. サブモジュール間クラス関係図", "", "対象外", "", "---", "",
            "## 5. サブモジュール間データフロー・データアクセスマトリクス／データモデル", "", "対象外", "", "---", "",
            "## 6. 変更履歴", ""]
    out += _history_table(version, today, HISTORY_INDEX)
    return "\n".join(out).rstrip("\n") + "\n"


def _apply_layout(args, data: dict, out_dir: Path, pairs: dict, ledger_files: set, targets: list) -> dict:
    """配置判定（成長型）と、統合→分割の移し替え・サブディレクトリ分割（`module-documentation.md`
    「## 配置判定（成長型）」の規則）。判定の入力は台帳のファイルと今回文書化するファイル（`targets`。
    追加下調べの対象。最終の組み立てでは空）の和集合。波紋調査の確定ファイルは入れない。"""
    cr = args.cr
    spo, modules_dir, drafts_dir = _spo_state_paths(out_dir, cr)
    max_files = args.max_files_per_module
    union = set(ledger_files) | {t["file"] for t in targets if t["module"]}
    mod_files = {}
    for f in sorted(union):
        name, _d = _longest_module(f, pairs)
        if name:
            mod_files.setdefault(name, []).append(f)
    total = len(union)
    current = "split" if modules_dir.is_dir() else ("integrated" if spo.is_file() else "none")
    module_tpl = Path(args.module_template).read_text(encoding="utf-8")
    # 移し替え・索引で作るモジュール資料の版（SPO の版が 1.0 未満なら 0.1、1.0 以上なら 1.0）
    spo_version = _doc_version(spo.read_text(encoding="utf-8")) if spo.is_file() else ""
    new_version = "1.0" if _version_tuple(spo_version) >= (1, 0) else "0.1"
    moved = False
    if current == "none":
        layout = "integrated" if total <= max_files else "split"
        if layout == "split":
            modules_dir.mkdir(parents=True, exist_ok=True)
    elif current == "integrated" and total > max_files:
        layout, moved = "split", True
        modules_dir.mkdir(parents=True, exist_ok=True)
        text = spo.read_text(encoding="utf-8")
        lines = text.split("\n")
        secs = _module_sections(lines)
        for sec in secs:
            name = sec["name"]
            mdir = pairs.get(name, name)
            doc = _section_to_module_doc(_section_body(lines, sec), name, mdir, module_tpl, cr, args.today, new_version)
            _write_text(modules_dir / f"{name}-spo.md", doc)
        for sec in sorted(secs, key=lambda s: -s["start"]):
            del lines[sec["start"]:sec["end"]]
        _write_text(spo, "\n".join(lines))
    else:
        layout = current

    modules_out = []
    if layout == "integrated":
        text = spo.read_text(encoding="utf-8") if spo.is_file() else ""
        lines = text.split("\n")
        secs = {s["name"]: s for s in _module_sections(lines)}
        for name in sorted(mod_files):
            draft = drafts_dir / f"{name}.md"
            existing = None
            if not draft.is_file() and name in secs:
                body = _normalize_draft("\n".join(_section_body(lines, secs[name])), "A")
                _write_text(draft, f"## 2.A. {name}\n\n" + "\n".join(body) + "\n")
            if draft.is_file():
                existing = str(draft)
            modules_out.append({"module": name, "dir": pairs.get(name, ""), "mode": "single",
                                "output_files": [str(draft)], "existing_doc": existing})
    else:
        subdir_modules = []
        for name in sorted(mod_files):
            mdir = pairs.get(name, "")
            files = mod_files[name]
            old = modules_dir / f"{name}-spo.md"
            sub_dir = modules_dir / name
            has_subdirs = mdir not in ("", ".") and (Path(data.get("repo_path") or ".") / mdir).is_dir() and any(
                p.is_dir() and not p.name.startswith(".") for p in (Path(data.get("repo_path") or ".") / mdir).iterdir())
            if sub_dir.is_dir() or (len(files) > max_files and has_subdirs):
                groups = {}
                for f in files:
                    groups.setdefault(_sub_of(f, mdir), set()).add(f)
                old_text = old.read_text(encoding="utf-8") if old.is_file() else None
                is_index = bool(old_text and "サブモジュール一覧" in old_text)
                if not is_index:
                    largest = max(sorted(groups), key=lambda s: len(groups[s]))
                    for sub in sorted(groups):
                        path = sub_dir / f"{sub}-spo.md"
                        if old_text and not path.is_file():
                            _write_text(path, _filter_doc_for_sub(old_text, cr, name, mdir, sub, groups[sub], files,
                                                                  sub == largest))
                    _write_text(old, _index_doc(name, mdir, groups, cr, args.today, module_tpl, old_text,
                                                _history_of(old_text, new_version) if old_text
                                                else (AUTHOR_PRELIM, new_version, False)))
                else:
                    _write_text(old, re.sub(r"(?s)(\| サブモジュール \| ファイル \| 波及ファイル数 \| 概要 \|\n\|---\|---\|---\|---\|\n).*?(\n\n)",
                                            lambda m: m.group(1) + "\n".join(
                                                f"| {sub} | `modules/{name}/{sub}-spo.md` | {len(groups[sub])} | サブモジュール資料を参照 |"
                                                for sub in sorted(groups)) + m.group(2), old_text, count=1))
                subdir_modules.append(name)
                modules_out.append({"module": name, "dir": mdir, "mode": "subdir", "index_file": str(old),
                                    "output_files": [str(sub_dir / f"{s}-spo.md") for s in sorted(groups)],
                                    "existing_doc": str(old) if old.is_file() else None})
            else:
                modules_out.append({"module": name, "dir": mdir, "mode": "single", "output_files": [str(old)],
                                    "existing_doc": str(old) if old.is_file() else None,
                                    "over_threshold": len(files) > max_files})
                if len(files) > max_files and old.is_file():
                    mark = (f"> ⚠️ 波及ファイル数（{len(files)}）が SPECOUT_MAX_FILES_PER_MODULE（{max_files}）を超えています。\n"
                            "> サブディレクトリによる分割候補がないため、単一ファイルに出力しています。")
                    t = old.read_text(encoding="utf-8")
                    if "サブディレクトリによる分割候補がないため" in t:
                        t = re.sub(r"> ⚠️ 波及ファイル数（\d+）が SPECOUT_MAX_FILES_PER_MODULE（\d+）を超えています。\n"
                                   r"> サブディレクトリによる分割候補がないため、単一ファイルに出力しています。", mark, t)
                    else:
                        parts = t.split("\n---", 1)
                        t = parts[0].rstrip("\n") + "\n\n" + mark + "\n\n---" + parts[1] if len(parts) == 2 else mark + "\n" + t
                    _write_text(old, t)
    return {"layout": layout, "moved_to_split": moved, "documented_total": total, "modules": modules_out,
            "module_file_counts": {n: len(v) for n, v in sorted(mod_files.items())}}


# -- assemble-spo: 版と変更履歴・波紋調査の結果の節 ---------------------------------------------

def _history_block(lines: list):
    """「変更履歴」の見出し（最後のもの）の節の表の (最後のデータ行のインデックス, [(インデックス, セル)])。無ければ None。"""
    heads = [i for i, _lv, t in _heading_indices(lines) if "変更履歴" in t]
    if not heads:
        return None
    i = heads[-1]
    _header, rows = _md_table_in(lines, i + 1, _block_end(lines, i))
    if not rows:
        return None
    return rows[-1][0], rows


def _append_history_row(lines: list, row: str) -> bool:
    found = _history_block(lines)
    if found is None:
        return False
    last, _rows = found
    lines.insert(last + 1, row)
    return True


def _set_header_line(lines: list, prefix: str, value: str) -> None:
    for k, ln in enumerate(lines):
        if ln.startswith(prefix):
            lines[k] = value
            return


def _finalize_spo_header(text: str, today: str, ripple: bool) -> str:
    """SPO の版の確定。`**版数：**` が 1.0 未満なら作成者・版数・冒頭の表示を確定にし、変更履歴に 1.0 の行を足す。
    1.0 以上で、変更履歴のスクリプトの行のうち最後のものの種類（波紋調査あり／なし）が今回と違えば、
    変更履歴の最大の版の小数を1つ上げて行を足す。それ以外は何もしない（再実行で二重にしない）。"""
    lines = text.split("\n")
    version = _doc_version(text)
    if _version_tuple(version) < (1, 0):
        lines = [ln for ln in lines if not ln.startswith(SPO_PRELIM_NOTICE_PREFIX)]
        _set_header_line(lines, "**作成者：", f"**作成者：** {AUTHOR_BOTH}  ")
        _set_header_line(lines, "**版数：", "**版数：** 1.0")
        _append_history_row(lines, f"| 1.0 | {today} | {AUTHOR_SCRIPT} | "
                                   f"{HISTORY_FINAL_RIPPLE if ripple else HISTORY_FINAL_NO_RIPPLE} |")
        return "\n".join(lines)
    found = _history_block(lines)
    if found is None:
        return text
    _last, rows = found
    kinds = [HISTORY_RIPPLE_KIND[c[3].strip()] for _k, c in rows
             if len(c) >= 4 and c[2].strip() == AUTHOR_SCRIPT and c[3].strip() in HISTORY_RIPPLE_KIND]
    if not kinds or kinds[-1] == ripple:
        return text
    top = max([_version_tuple(c[0]) for _k, c in rows if c] + [_version_tuple(version)])
    new = f"{top[0]}.{top[1] + 1}"
    _set_header_line(lines, "**版数：", f"**版数：** {new}")
    _append_history_row(lines, f"| {new} | {today} | {AUTHOR_SCRIPT} | "
                               f"{HISTORY_CHANGE_RIPPLE if ripple else HISTORY_CHANGE_NO_RIPPLE} |")
    return "\n".join(lines)


def _finalize_module_doc(text: str, today: str, ripple: bool) -> str:
    """モジュール資料の版の確定（`**版数：**` が 1.0 未満なら 1.0 にし、変更履歴に行を足す）。作成者は変えない。"""
    if _version_tuple(_doc_version(text)) >= (1, 0):
        return text
    lines = text.split("\n")
    _set_header_line(lines, "**版数：", "**版数：** 1.0")
    _append_history_row(lines, f"| 1.0 | {today} | {AUTHOR_SCRIPT} | "
                               f"{HISTORY_FINAL_RIPPLE if ripple else HISTORY_FINAL_NO_RIPPLE} |")
    return "\n".join(lines)


def _module_ripple_body(files, ledger_files: set) -> list:
    """モジュール資料の「波紋調査の結果」の本文（表または1行）。`files` が None は波紋調査なし。
    並び: 発見波 → 同一性 resolved を先 → ファイル名。上限 MODULE_RIPPLE_MAX_ROWS 行（超えた分は1行にまとめる）。"""
    if files is None:
        return [NO_RIPPLE_TEXT]
    if not files:
        return [NOT_REACHED_TEXT]
    order = sorted(files, key=lambda fe: (fe["wave"], 0 if fe["identity"] == LV.IDENTITY_RESOLVED else 1, fe["file"]))
    rows = [[fe["file"], ", ".join((fe.get("functions") or [])[:3]) or "—", fe["wave"],
             "resolved" if fe["identity"] == LV.IDENTITY_RESOLVED else "name-only",
             "●" if fe.get("seed_direct") else "—", "あり" if fe["file"] in ledger_files else "—", fe.get("path") or "—"]
            for fe in order[:MODULE_RIPPLE_MAX_ROWS]]
    if len(order) > MODULE_RIPPLE_MAX_ROWS:
        rows.append(_overflow_row(f"ほか {len(order) - MODULE_RIPPLE_MAX_ROWS} ファイル（`ripple-summary.md` を参照）",
                                  len(MODULE_RIPPLE_COLUMNS)))
    return _table_lines(MODULE_RIPPLE_COLUMNS, rows)


def _upsert_module_ripple(text: str, body: list) -> str:
    """分割パスのモジュール資料の `## 波紋調査の結果` を節ごと置き換える（無ければ `## 5. 変更履歴` の直前に加える）。"""
    block = [MODULE_RIPPLE_HEADING, WRITER_SCRIPT_COMMENT, "", *body, ""]
    lines = text.split("\n")
    i = _find_heading(lines, r"^##\s+" + MODULE_RIPPLE_TITLE + r"\s*$")
    if i is not None:
        lines[i:_block_end(lines, i)] = block
        return "\n".join(lines)
    j = _find_heading(lines, r"^##\s+5\.\s*変更履歴")
    if j is None:
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines + ["", "---", "", *block]).rstrip("\n") + "\n"
    k = j - 1
    while k >= 0 and not lines[k].strip():
        k -= 1
    if k >= 0 and lines[k].strip() == "---":
        lines[k:k] = ["---", "", *block]
    else:
        lines[j:j] = [*block, "---", ""]
    return "\n".join(lines)


# -- assemble-spo: SPO サマリー --------------------------------------------------------------

def _prelim_log_notes(log_text: str) -> list:
    """discovery-log の未対応パターン・未ヒット・ヒット過多・予算打ち切りの記録を、SPO §9 への転記行にする。"""
    notes = []
    for cells in _unsupported_pattern_rows(log_text):
        if len(cells) >= 3:
            notes.append(f"{AUTO_NOTE_PREFIX} grep未対応パターン: {cells[0]}（{cells[1]}）確認状況 {cells[2]}")
    lines = log_text.split("\n")
    for heading_prefix, label in ((ZERO_HIT_HEADING_PREFIX, "未ヒット投入シンボル"),
                                  ("## ヒット過多の投入シンボル（Wave ", "ヒット過多の投入シンボル"),
                                  ("## 予算で打ち切った投入シンボル（Wave ", "予算で打ち切った投入シンボル")):
        for i, ln in enumerate(lines):
            if not ln.startswith(heading_prefix):
                continue
            wave = ln[len(heading_prefix):].rstrip("）").strip()
            rng = _md_section_range(lines, ln.strip())
            if rng is None:
                continue
            for body in lines[rng[0]:rng[1]]:
                if body.startswith("> ⚠️"):
                    notes.append(f"{AUTO_NOTE_PREFIX} {label}（Wave {wave}）: {body[2:].strip()}")
            _h, rows = _md_table_in(lines, *rng)
            for _k, cells in rows:
                notes.append(f"{AUTO_NOTE_PREFIX} {label}（Wave {wave}）: " + " ／ ".join(c for c in cells if c))
    return notes


def _ripple_notes(summary: dict, sweep) -> list:
    """追加下調べでも資料にできなかったシードの直接参照と、検証スイープの未記録ファイルの §9 への転記行。"""
    notes = []
    for g in summary.get("prelim_gap_files") or []:
        why = ("追加下調べの累計の上限（SPECOUT_MAX_AFFECTED_FILES）を超えたため追加下調べしていない"
               if g.get("reason") == GAP_OVER_LIMIT else "追加下調べでも資料にできなかった")
        notes.append(f"{AUTO_NOTE_PREFIX} シードの直接参照で資料の無いファイル: {g['file']}（{why}。§5.0 の ⚠️）")
    files = sorted((sweep or {}).get("unrecorded_files") or [])
    if files:
        shown = ", ".join(files[:10]) + (f" ほか{len(files) - 10}件" if len(files) > 10 else "")
        notes.append(f"{AUTO_NOTE_PREFIX} 検証スイープの未記録ヒット {len(files)} 件（波紋調査の帳簿に無いファイル: {shown}）。"
                     "探索の漏れの可能性があるため、必要なら --re-discover で該当シンボルを追加する")
    return notes


def _memo_testability(memo_path: Path) -> dict:
    """累積観察メモの「テスト可能性」から {ファイル: (テスト可能性, 備考)} を返す（無ければ空）。"""
    if not memo_path.is_file():
        return {}
    lines = memo_path.read_text(encoding="utf-8").split("\n")
    rng = _md_section_range(lines, "## テスト可能性")
    if rng is None:
        return {}
    header, rows = _md_table_in(lines, *rng)
    if not header or "ファイルパス" not in header or "テスト可能性" not in header:
        return {}
    fi, ti = header.index("ファイルパス"), header.index("テスト可能性")
    ni = header.index("備考") if "備考" in header else None
    return {_norm_path(c[fi]): (c[ti], c[ni] if ni is not None and len(c) > ni else "")
            for _i, c in rows if len(c) > max(fi, ti) and c[ti].strip()}


def _fn_effect(fn: dict, seeds: set, wave0: bool) -> str:
    if not wave0:
        return "要確認"
    if fn["name"] in seeds or fn.get("seed_def"):
        return "変更必要"
    return "参照のみ"


def _impact_rows(summary: dict, wave0: bool, seeds: set, modules=None) -> list:
    """§5.1（wave0）・§5.2 の行。`modules` を渡すとそのモジュールの関数だけにする。"""
    rows = []
    for m in summary["modules"]:
        if modules is not None and m["name"] not in modules:
            continue
        for fn in m["functions"]:
            if (fn["min_wave"] == 0) != wave0:
                continue
            desc = f"第{fn['min_wave']}波／派生元 {fn['origin']}／判定 {', '.join(fn['labels']) or '—'}"
            rows.append((fn["min_wave"], -fn["hit_count"], fn["file"], fn["name"],
                         [fn["file"], fn["name"] or NO_FUNCTION_LABEL, _fn_effect(fn, seeds, wave0), m["name"], desc]))
    rows.sort(key=lambda r: r[:4])
    return [r[4] for r in rows]


def _assemble_summary(spo_text: str, summary, data: dict, args, ctx: dict) -> tuple:
    """SPO サマリーのスクリプトが書く欄（§1・§1.x・§5.0・§5.1・§5.2・§5.5・§8・§9）。`summary` が None は波紋調査なし。"""
    lines = spo_text.split("\n")
    ripple = summary is not None
    seeds = set(summary.get("seeds") or []) if ripple else set()
    mods = summary["modules"] if ripple else []
    ledger = ctx["ledger"]
    documented = ctx["documented_modules"]
    written, missing = [], []

    def _put(name: str, ok: bool) -> None:
        (written if ok else missing).append(name)

    # §1 調査概要
    _h, old_rows = _read_table(lines, r"^##\s+1\.")
    old_spec = next((r[1] for r in old_rows if r and r[0] == "既存仕様書"), "")
    if not old_spec or "{" in old_spec or old_spec.startswith("あり（{"):
        old_spec = "未確認"
    n_add = sum(1 for e in ledger if e["phase"] == LEDGER_PHASE_ADDITIONAL)
    prelim_scope = f"下調べ: {len(documented)} モジュール・{len(ledger)} ファイル（うち追加下調べ {n_add}）"
    last = data.get("last_completed_wave", -1)
    if ripple:
        scope = prelim_scope + f"／波紋調査: 第0〜{last}波・確定 {summary.get('confirmed_file_count', 0)} 件"
        origin = ", ".join(f"`{s}`" for s in sorted(seeds)) or "—"
        n_mod = len({m["name"] for m in mods} | documented)
    else:
        scope = prelim_scope + "／波紋調査: 未実施（人の判断）"
        origin = "下調べで特定（モジュール資料を参照）"
        n_mod = len(documented)
    rows = [["調査起点", origin], ["調査範囲", scope], ["検出モジュール数", f"{n_mod} モジュール"], ["既存仕様書", old_spec]]
    _ensure_script_comment(lines, r"^##\s+1\.")
    _put("1", _replace_table(lines, r"^##\s+1\.", _table_lines(["項目", "内容"], rows)))

    # §1.x 調査の打ち切り
    if ripple:
        summ = _truncation_summary(data.get("truncated") or [])
        wb = int(data.get("wave_hit_budget") or 0)
        lb = int(data.get("llm_hit_budget") or 0)
        rows = [["実行した波数／波数上限", f"{last + 1} ／ {data.get('max_wave_depth', '—')}"],
                ["1波の予算／LLM 分類の上限", f"{wb or '無制限'} ／ {lb or '無制限'}"],
                ["打ち切ったシンボル数（理由別）", "／".join(f"{r}: {c}" for r, c, _t in summ) or "なし"],
                ["ヒット数の多い順の主なシンボル", " ".join(t for _r, _c, top in summ for t in top[:3]) or "なし"]]
    else:
        rows = [["波紋調査", NO_RIPPLE_TEXT]]
    pat = r"^###\s+1\.\S+\s+調査の打ち切り"
    if _find_heading(lines, pat) is None:
        i1 = _find_heading(lines, r"^##\s+1\.")
        if i1 is not None:
            end = _block_end(lines, i1)
            lines[end:end] = ["### 1.x 調査の打ち切り", WRITER_SCRIPT_COMMENT, "", "", ""]
    _ensure_script_comment(lines, pat)
    _put("1.x", _replace_table(lines, pat, _table_lines(["項目", "内容"], rows)))

    # §5.0 影響する機能（モジュール）一覧（波紋調査の要約。最大 SUMMARY_MAX_ROWS 行）
    if ripple:
        order = _summary_order(mods)
        shown = [m for m in order if m.get("in_summary", True)][:SUMMARY_MAX_ROWS]
        rest = [m for m in order if m not in shown]
        rows = [_summary_row({**m, "documented": m["name"] in documented}) for m in shown]
        if rest:
            rows.append(_overflow_row(f"ほか {len(rest)} モジュール・{sum(m['confirmed_count'] for m in rest)} ファイル"
                                      "（`ripple-summary.md` を参照）", len(SUMMARY_COLUMNS)))
        note0 = None
    else:
        counts = {}
        for e in ledger:
            counts[e["module"]] = counts.get(e["module"], 0) + 1
        rows = [[name, counts[name], "—", "—", "—", "あり", "—"] for name in sorted(counts)]
        note0 = NO_RIPPLE_NOTE
    pat0 = r"^###\s+5\.0\b"
    if _find_heading(lines, pat0) is None:
        i51 = _find_heading(lines, r"^###\s+5\.1\b")
        if i51 is not None:
            lines[i51:i51] = ["### 5.0 影響する機能（モジュール）一覧", WRITER_SCRIPT_COMMENT, "", "", ""]
    _ensure_script_comment(lines, pat0)
    _put("5.0", _replace_table(lines, pat0, _table_lines(SUMMARY_COLUMNS, rows), note=note0,
                               drop_note_prefix=SUMMARY_NOTE_PREFIXES))

    # §5.1・§5.2
    head = ["ファイルパス", "識別子", "影響種別", "モジュール", "説明"]
    if ripple:
        rows51 = _impact_rows(summary, True, seeds)
    else:
        rows51 = [[e["file"], "（モジュール資料を参照）", "下調べで特定", e["module"], e["behavior"]]
                  for e in sorted(ledger, key=lambda e: (e["module"], e["file"]))]
    _ensure_script_comment(lines, r"^###\s+5\.1\b")
    _put("5.1", _replace_table(lines, r"^###\s+5\.1\b", _table_lines(head, rows51)))
    brief = args.detail_level == "brief"
    if ripple:
        rows52 = _impact_rows(summary, False, seeds, documented)
        if brief:
            rows52 = rows52[:BRIEF_REPRESENTATIVES]
        notes52 = ([BRIEF_NOTE] if brief else []) + [SCOPE_52_NOTE]
    else:
        rows52, notes52 = [], [NO_RIPPLE_NOTE]
    _ensure_script_comment(lines, r"^###\s+5\.2\b")
    _put("5.2", _replace_table(lines, r"^###\s+5\.2\b", _table_lines(head, rows52), note=notes52,
                               drop_note_prefix=("> quick プロファイルのため代表例のみ記載", *SUMMARY_NOTE_PREFIXES)))

    # §5.5 テスト可能性（台帳のファイルと、資料のあるモジュールの確定ファイル。プロダクションコードの観察だけを書く）
    hdr5, old5 = _read_table(lines, r"^###\s+5\.5\b")
    keep_t = {}
    if hdr5 and "ファイルパス" in hdr5 and "テスト可能性" in hdr5:
        fi, ti = hdr5.index("ファイルパス"), hdr5.index("テスト可能性")
        ni = hdr5.index("備考") if "備考" in hdr5 else None
        # 値が `未確認` の行は値が無いものとして扱い、値と備考を作り直す（後で台帳に入ったファイルの備考を古いまま残さない）
        keep_t = {r[fi]: (r[ti], r[ni] if ni is not None and len(r) > ni else "") for r in old5
                  if len(r) > max(fi, ti) and r[ti].strip() and "{" not in r[ti]
                  and r[ti].strip() != TESTABILITY_UNCONFIRMED}
    testab = ctx["testability"]
    ledger_files = {e["file"] for e in ledger}
    files55 = ledger_files | {fe["file"] for m in mods if m["name"] in documented for fe in m["files"]}
    rows = []
    for f in sorted(files55):
        value, note = testab.get(f) or keep_t.get(f) or (
            TESTABILITY_UNCONFIRMED, TESTABILITY_NOTE_NO_MEMO if f in ledger_files else TESTABILITY_NOTE_UNREAD)
        rows.append([f, value, note])
    _ensure_script_comment(lines, r"^###\s+5\.5\b", WRITER_SCRIPT_KEEP_COMMENT)
    _put("5.5", _replace_table(lines, r"^###\s+5\.5\b", _table_lines(["ファイルパス", "テスト可能性", "備考"], rows)))

    # §8 調査済みモジュール一覧（資料のあるモジュール）
    rows = []
    layout = ctx["layout"]
    letters = ctx.get("letters", {})
    for name in sorted(documented | set(letters)):
        mdir = ctx["pairs"].get(name, "")
        if layout == "integrated":
            link = (f"SPO-{args.cr}.md § 2.{letters[name]}, § 5（文書化ファイル数が閾値以下のため modules/ 未生成）"
                    if name in letters else "（統合パスの §2.A… に資料なし）")
        elif name not in documented:
            link = "（資料なし）"
        elif (Path(args.output_dir) / "modules" / name).is_dir():
            n = len(list((Path(args.output_dir) / "modules" / name).glob("*-spo.md")))
            link = f"[modules/{name}-spo.md](modules/{name}-spo.md)（インデックス・{n} サブモジュールに分割）"
        else:
            link = f"[modules/{name}-spo.md](modules/{name}-spo.md)"
        rows.append([name, mdir, link])
    _put("8", _replace_table(lines, r"^##\s+8\.", _table_lines(["モジュール名", "ディレクトリ", "個別資料"], rows)))

    # §9 気づき・提案メモ（自動転記の行だけを作り直し、人・AI が書いた行は残す）
    hdr9, old9 = _read_table(lines, r"^##\s+9\.")
    keep = [r for r in old9 if len(r) >= 4 and not r[2].startswith(AUTO_NOTE_PREFIX) and "{内容}" not in r[2]]
    auto = [["", "懸念", n, "保留"] for n in ctx["notes"]]
    merged = [[str(k + 1), r[1], r[2], r[3]] for k, r in enumerate([*keep, *auto])]
    if not merged:
        merged = [["1", "—", "なし", "—"]]
    _put("9", _replace_table(lines, r"^##\s+9\.", _table_lines(["#", "種別", "内容", "対応方針"], merged)))
    return "\n".join(lines), written, missing


# -- assemble-spo: document agent の入力 ------------------------------------------------------

def _doc_entry_points(work: Path, entry_points: str, propagation_log, repo: str) -> list:
    """document agent に渡す ENTRY_POINTS: 今回の --entry-points・work/doc-entry-points.json（前回までの累積）・
    伝播ログの `propagated`（この repo の分）の和集合を昇順に並べたもの。累積は毎回書き戻す。"""
    acc = set(_split_csv(entry_points or ""))
    path = work / DOC_ENTRY_POINTS_FILE
    if path.is_file():
        try:
            prev = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            _err(f"{DOC_ENTRY_POINTS_FILE} を JSON として読めません: {path}（{e}）")
        if not isinstance(prev, list) or not all(isinstance(x, str) for x in prev):
            _err(f"{DOC_ENTRY_POINTS_FILE} の形式が不正です（文字列の配列）: {path}")
        acc |= set(prev)
    if propagation_log and Path(propagation_log).is_file():
        try:
            log = json.loads(Path(propagation_log).read_text(encoding="utf-8"))
        except ValueError as e:
            _err(f"cross-propagation-log.json を JSON として読めません: {propagation_log}（{e}）")
        for item in log if isinstance(log, list) else []:
            if isinstance(item, dict) and item.get("repo") == repo and item.get("status") == "propagated" \
                    and isinstance(item.get("symbol"), str) and item["symbol"]:
                acc.add(item["symbol"])
    result = sorted(s for s in acc if s)
    _write_text(path, json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    return result


def _inputs_fingerprint(ledger_path: Path, summary_json, no_ripple: bool, crs_path: Path, entry_points: list) -> str:
    """document agent の入力の指紋（台帳・波紋調査の要約・波紋調査の有無・CRS・ENTRY_POINTS の SHA-256）。"""
    h = hashlib.sha256()

    def _put(name: str, value: bytes) -> None:
        h.update(name.encode("utf-8") + b"\n" + value + b"\n")

    _put("ledger", ledger_path.read_bytes() if ledger_path.is_file() else b"")
    _put("ripple_summary", Path(summary_json).read_bytes() if summary_json else b"")
    _put("no_ripple", b"1" if no_ripple else b"0")
    _put("crs", crs_path.read_bytes())
    _put("entry_points", ",".join(entry_points).encode("utf-8"))
    return h.hexdigest()


def _saved_fingerprint(work: Path) -> str:
    path = work / ASSEMBLE_INPUTS_FILE
    if not path.is_file():
        return ""
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get("fingerprint") or "")
    except (ValueError, AttributeError):
        return ""


def cmd_commit_assemble_inputs(args) -> None:
    """document agent の成功の後に、assemble-spo が返した入力の指紋を work/assemble-inputs.json に保存する。"""
    if not re.match(r"^[0-9a-f]{64}$", args.fingerprint or ""):
        _err(f"--fingerprint が SHA-256 の16進表記ではありません: {args.fingerprint}")
    path = Path(args.output_dir) / "work" / ASSEMBLE_INPUTS_FILE
    _write_text(path, json.dumps({"fingerprint": args.fingerprint}, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "file": str(path)}, ensure_ascii=False))


# -- assemble-spo ----------------------------------------------------------------------------

def _assemble_usage(args) -> None:
    """引数の組み合わせの検査（誤りは終了コード 2）。"""
    def _bad(msg: str) -> None:
        print(f"assemble-spo: {msg}", file=sys.stderr)
        sys.exit(EXIT_USAGE)

    if args.layout_only:
        if args.no_ripple:
            _bad("--no-ripple では --layout-only を指定できません")
        if args.only != "seed-direct":
            _bad("--layout-only は --only seed-direct と併用してください")
        if args.max_files is None:
            _bad("--layout-only --only seed-direct には --max-files が必要です")
        if not args.path:
            _bad("--path が必要です")
        return
    if args.only or args.max_files is not None:
        _bad("--only・--max-files は --layout-only と併用してください")
    if args.crs_file is None or args.entry_points is None:
        _bad("--crs-file と --entry-points が必要です（--entry-points は空文字列でよい）")
    if args.no_ripple:
        for flag, value in (("--path", args.path), ("--summary-json", args.summary_json),
                            ("--sweep-json", args.sweep_json)):
            if value:
                _bad(f"--no-ripple では {flag} を指定できません")
        if not args.repo_path or not args.repo:
            _bad("--no-ripple には --repo-path と --repo が必要です")
    else:
        if not args.path:
            _bad("--path が必要です（波紋調査を行わなかった repo は --no-ripple）")
        if not args.summary_json:
            _bad("--summary-json が必要です（ripple-summary の --json）")


def _file_outputs(plan: dict, targets: list, out_dir: Path) -> dict:
    """追加下調べの書き先 {ファイル: {"module", "output_file"}}（サブディレクトリ分割はサブモジュール資料、
    統合パスは work/module-drafts/{モジュール}.md）。"""
    by_mod = {m["module"]: m for m in plan["modules"]}
    out = {}
    for t in targets:
        m = by_mod.get(t["module"])
        if m is None:
            continue
        if m["mode"] == "subdir":
            path = out_dir / "modules" / t["module"] / f"{_sub_of(t['file'], m['dir'])}-spo.md"
        else:
            path = Path(m["output_files"][0])
        out[t["file"]] = {"module": t["module"], "output_file": str(path)}
    return out


def _write_module_ripple_sections(out_dir: Path, plan: dict, files_by_module: dict, ledger_files: set,
                                  ripple: bool, today: str) -> list:
    """分割パス: 資料のある各モジュールの資料（サブディレクトリ分割はサブモジュール資料）に「波紋調査の結果」を書き、
    版を確定する（索引は版の確定だけ）。書いた資料のパスを返す。"""
    written = []
    modules_dir = out_dir / "modules"
    for m in plan["modules"]:
        name = m["module"]
        files = files_by_module.get(name, []) if ripple else None
        if m["mode"] == "subdir":
            docs = [(p, [fe for fe in files if _sub_of(fe["file"], m["dir"]) == p.name[:-len("-spo.md")]]
                     if files is not None else None)
                    for p in sorted((modules_dir / name).glob("*-spo.md"))]
            index = modules_dir / f"{name}-spo.md"
            if index.is_file():
                _write_text(index, _finalize_module_doc(index.read_text(encoding="utf-8"), today, ripple))
        else:
            doc = modules_dir / f"{name}-spo.md"
            docs = [(doc, files)] if doc.is_file() else []
        for path, fs in docs:
            text = _upsert_module_ripple(path.read_text(encoding="utf-8"), _module_ripple_body(fs, ledger_files))
            _write_text(path, _finalize_module_doc(text, today, ripple).rstrip("\n") + "\n")
            written.append(str(path))
    return written


def cmd_assemble_spo(args) -> None:
    """配置判定と SPO の組み立て。
    `--layout-only --only seed-direct`: 台帳と追加下調べの対象（シードの直接参照のうち台帳に無いもの。累計の上限まで）で
    配置判定・統合→分割の移し替え・サブディレクトリ分割を行い、追加下調べの書き先（file_outputs）を返す。
    指定なし: 台帳のファイルだけで配置を判定し、統合パスのモジュール資料の差し込み、モジュール資料の「波紋調査の結果」、
    SPO・モジュール資料の版の確定、SPO サマリーのスクリプトが書く欄（§1・§1.x・§5.0・§5.1・§5.2・§5.5・§8・§9）を書く。
    `--no-ripple` は波紋調査を行わなかった repo（state が無い）。LLM が書く欄は変えない。
    document agent に渡す ENTRY_POINTS（doc_entry_points）と入力の指紋（inputs_fingerprint・inputs_changed）を返す
    （指紋の保存は commit-assemble-inputs が行う）。"""
    _assemble_usage(args)
    out_dir = Path(args.output_dir)
    work = out_dir / "work"
    ledger_path = work / "documented-files.md"
    memo_path = work / "observation-memo.md"
    assign_path = work / "module-assignments.json"
    no_ripple = bool(args.no_ripple)
    if no_ripple:
        data = {"repo_path": args.repo_path, "repo": args.repo, "cr": args.cr}
    else:
        data = _load_state(Path(args.path))
    repo_path = data.get("repo_path") or ""
    ledger, pairs, _all_targets, ledger_files = _doc_plan(data, ledger_path if ledger_path.is_file() else None,
                                                          assign_path if assign_path.is_file() else None)
    if args.layout_only:
        reviewed = _parse_gap_reviewed(work / GAP_REVIEWED_FILE, repo_path)
        taken, over = _seed_direct_gap(data, ledger, reviewed, args.max_files)
        hm = _confirmed_files(data)
        targets = []
        for f in taken:
            module, module_dir = _longest_module(f, pairs)
            targets.append({"file": f, "confidence": hm.get(f, ""), "module": module, "module_dir": module_dir})
        bad = [t["file"] for t in targets if not t["module"]]
        if bad:
            _err("どのモジュールにも属さない追加下調べの対象があります（doc-targets --auto-assign を先に実行してください）: "
                 + ", ".join(bad[:10]))
        plan = _apply_layout(args, data, out_dir, pairs, ledger_files, targets)
        print(json.dumps({"ok": True, **plan, "file_outputs": _file_outputs(plan, targets, out_dir),
                          "over_limit_files": over}, ensure_ascii=False))
        return

    crs_path = Path(args.crs_file)
    if not crs_path.is_file():
        _err(f"CRS が見つかりません: {crs_path}")
    summary = None
    if not no_ripple:
        summary_path = Path(args.summary_json)
        if not summary_path.is_file():
            _err(f"ripple-summary の JSON が見つかりません（ripple-summary を先に実行してください）: {summary_path}")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    sweep = None
    if args.sweep_json and Path(args.sweep_json).is_file():
        try:
            sweep = json.loads(Path(args.sweep_json).read_text(encoding="utf-8"))
        except ValueError as e:
            _err(f"verify-sweep の JSON を読めません: {args.sweep_json}（{e}）")
    ripple = summary is not None

    plan = _apply_layout(args, data, out_dir, pairs, ledger_files, [])
    layout = plan["layout"]
    spo, _modules_dir, drafts_dir = _spo_state_paths(out_dir, args.cr)
    tpl_text = Path(args.summary_template).read_text(encoding="utf-8")
    if spo.is_file():
        text = spo.read_text(encoding="utf-8")
    else:
        text = tpl_text.replace("{CR番号}", args.cr).replace("{YYYY-MM-DD}", args.today)
    text = _finalize_spo_header(text, args.today, ripple)
    lines = text.split("\n")
    files_by_module = {m["name"]: m["files"] for m in summary["modules"]} if ripple else {}

    # 統合パス: モジュール資料（work/module-drafts）を §2.A… へ差し込み、各節に「波紋調査の結果」を付ける
    letters, missing_drafts, used_drafts = {}, [], []
    if layout == "integrated":
        existing = {s["name"]: _normalize_draft("\n".join(_section_body(lines, s)), "A") for s in _module_sections(lines)}
        drafts = {}
        for name in {m["module"] for m in plan["modules"]}:
            d = drafts_dir / f"{name}.md"
            if d.is_file():
                drafts[name] = d.read_text(encoding="utf-8")
                used_drafts.append(d)
            elif name not in existing:
                missing_drafts.append(name)
        names = sorted(set(existing) | set(drafts))
        if len(names) > 26:
            _err(f"統合パスのモジュール数が多すぎます（{len(names)}）。分割パスにしてください")
        for sec in sorted(_module_sections(lines), key=lambda s: -s["start"]):
            del lines[sec["start"]:sec["end"]]
        blocks = []
        for n, name in enumerate(names):
            letters[name] = _letter_name(n)
            body = _normalize_draft(drafts[name], letters[name]) if name in drafts else \
                [re.sub(r"(^#{3,4}\s+2\.)A(\.)", lambda m: m.group(1) + letters[name] + m.group(2), ln) for ln in existing[name]]
            ripple_body = _module_ripple_body(files_by_module.get(name, []) if ripple else None, ledger_files)
            blocks += [f"## 2.{letters[name]}. {name}", "", *body, "",
                       f"### 2.{letters[name]}.9 {MODULE_RIPPLE_TITLE}", WRITER_SCRIPT_COMMENT, "", *ripple_body, "",
                       "---", ""]
        if blocks:
            i3 = _find_heading(lines, r"^##\s+3\.")
            at = i3 if i3 is not None else len(lines)
            lines[at:at] = blocks
        module_docs = []
    else:
        module_docs = _write_module_ripple_sections(out_dir, plan, files_by_module, ledger_files, ripple, args.today)

    log_text = ""
    if ripple and data.get("discovery_log") and Path(data["discovery_log"]).is_file():
        log_text = Path(data["discovery_log"]).read_text(encoding="utf-8")
    notes = (_prelim_log_notes(log_text) + _ripple_notes(summary, sweep)) if ripple else []
    ctx = {"layout": layout, "letters": letters, "pairs": pairs, "ledger": ledger,
           "documented_modules": {e["module"] for e in ledger},
           "testability": _memo_testability(memo_path), "notes": notes}
    new_text, written, missing = _assemble_summary("\n".join(lines), summary, data, args, ctx)
    _write_text(spo, new_text.rstrip("\n") + "\n")
    # 差し込んだ下書きは、SPO の書き込みに成功した後に削除する（次の --layout-only はそのときの §2.A… から抜き出し直す）
    for d in used_drafts:
        if d.is_file():
            d.unlink()
    if drafts_dir.is_dir() and not any(drafts_dir.iterdir()):
        drafts_dir.rmdir()

    entry_points = _doc_entry_points(work, args.entry_points, args.propagation_log, data.get("repo") or args.repo or "")
    fingerprint = _inputs_fingerprint(ledger_path, None if no_ripple else args.summary_json,
                                      (work / NO_RIPPLE_MARK).is_file(), crs_path, entry_points)
    if args.metrics:
        line = {"event": "specout_doc_summary", "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
                "repo": data.get("repo") or args.repo or "", "ripple": ripple,
                "prelim_file_count": sum(1 for e in ledger if e["phase"] == LEDGER_PHASE_PRELIM),
                "additional_file_count": sum(1 for e in ledger if e["phase"] == LEDGER_PHASE_ADDITIONAL)}
        if ripple:
            gaps = summary.get("prelim_gap_files") or []
            line.update({"seed_direct_file_count": summary.get("seed_direct_file_count", 0),
                         "prelim_gap_count": len(gaps),
                         "gap_over_limit_count": sum(1 for g in gaps if g.get("reason") == GAP_OVER_LIMIT),
                         "gap_reviewed_unrelated_count": len(summary.get("gap_reviewed_files") or [])})
        Path(args.metrics).parent.mkdir(parents=True, exist_ok=True)
        with open(args.metrics, "a", encoding="utf-8", newline="\n") as mf:
            mf.write(json.dumps(line, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, **plan, "ripple": ripple,
                      "sections_written": written, "sections_missing": missing, "missing_drafts": sorted(missing_drafts),
                      "module_docs_written": module_docs, "spo_file": str(spo),
                      "doc_entry_points": entry_points, "inputs_fingerprint": fingerprint,
                      "inputs_changed": fingerprint != _saved_fingerprint(work)}, ensure_ascii=False))


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--path", required=True)
    p_init.add_argument("--repo-path", required=True)
    p_init.add_argument("--discovery-log", required=True)
    # 未指定（None）と空指定を区別する（--seed-candidates との排他判定のため）。None は空文字列として扱う。
    p_init.add_argument("--symbols", default=None)
    p_init.add_argument("--today", required=True)
    p_init.add_argument("--cr", required=True)
    p_init.add_argument("--repo", required=True)
    p_init.add_argument("--exclude", default="")
    p_init.add_argument("--include-ext", default="")
    p_init.add_argument("--max-wave", type=int, default=6)
    p_init.add_argument("--max-files-per-module", type=int, default=10)
    p_init.add_argument("--module-catalog", default=None)
    p_init.add_argument("--backend", default="auto")
    p_init.add_argument("--hit-filter", default="conservative")  # PLAN-20260804 Phase 1b（conservative/off）
    p_init.add_argument("--scope-summary-file", default=None)  # PLAN-20260829: classifier scope 要約ファイル
    p_init.add_argument("--entry-point-symbols", default=None)  # 人が明示指定した投入シンボル（カンマ区切り）
    # PLAN-20260927-specout-prelim-phase: 候補表の採用行から初期シンボル・ENTRY_POINTS・由来テーブルを作る
    # （--symbols・--entry-point-symbols とは排他）。--unsupported-patterns は discovery-setup が見つけた
    # grep 未対応パターン（JSON。不在・空配列は no-op）。
    p_init.add_argument("--seed-candidates", default=None)
    p_init.add_argument("--unsupported-patterns", default=None)
    # 1波の予算・LLM 分類の上限（0 は無制限）と判定エンジンの設定（自由文はファイルで渡す）。
    p_init.add_argument("--wave-hit-budget", type=int, default=10000)
    p_init.add_argument("--llm-hit-budget", type=int, default=160)
    p_init.add_argument("--slice-engine", choices=list(SLICE_ENGINES), default="rule")
    p_init.add_argument("--probe-file", default=None)
    p_init.add_argument("--use-probe-warning", action="store_true")
    p_init.add_argument("--slice-ignore-calls-file", default=None)
    p_init.add_argument("--slice-h-as", choices=["auto", "c", "cpp"], default="auto")
    p_init.set_defaults(func=cmd_init)

    p_wsc = sub.add_parser("write-seed-candidates")
    p_wsc.add_argument("--input", required=True)
    p_wsc.add_argument("--out", required=True)
    p_wsc.add_argument("--unsupported-out", required=True)
    p_wsc.add_argument("--template", default=None)
    p_wsc.add_argument("--cr", default=None)
    p_wsc.add_argument("--repo", default=None)
    g_wsc = p_wsc.add_mutually_exclusive_group()
    g_wsc.add_argument("--append", action="store_true")
    g_wsc.add_argument("--stale-ref", default=None)
    p_wsc.set_defaults(func=cmd_write_seed_candidates)

    p_preview = sub.add_parser("seed-preview")
    p_preview.add_argument("--seed-candidates", required=True)
    p_preview.add_argument("--repo-path", required=True)
    p_preview.add_argument("--exclude", default="")
    p_preview.add_argument("--include-ext", default="")
    p_preview.add_argument("--backend", default="auto")
    p_preview.add_argument("--hit-filter", default="conservative")
    p_preview.add_argument("--max-files-per-module", type=int, default=10)
    p_preview.add_argument("--ledger", default=None)
    p_preview.add_argument("--wave-hit-budget", type=int, default=0)
    p_preview.add_argument("--slice-h-as", default="auto")
    p_preview.add_argument("--slice-engine", choices=list(SLICE_ENGINES), default="rule")
    p_preview.set_defaults(func=cmd_seed_preview)

    p_search = sub.add_parser("search")
    p_search.add_argument("--path", required=True)
    # PLAN-20260806 Phase 3 Stage 2 §4.5(b): --hits-out / --hits-dir は相互排他（cmd_search 冒頭で検証）。
    # required=True を解除し、既定 None のうえ実行時に相互排他をチェックする。
    p_search.add_argument("--hits-out", default=None)
    p_search.add_argument("--hits-dir", default=None)
    p_search.add_argument("--chunk-size", type=int, default=0)
    p_search.set_defaults(func=cmd_search)

    p_commit = sub.add_parser("commit-wave")
    p_commit.add_argument("--path", required=True)
    p_commit.add_argument("--hits", required=True)
    p_commit.add_argument("--classification", required=True)
    p_commit.add_argument("--today", required=True)
    # PLAN-20260806 Phase 3 Stage 1 §4.5(d): metrics 専用。いずれも既定 1 で挙動不変
    # （1 以外の値が渡るのは Stage 2 のチャンク並列分類以降）。
    p_commit.add_argument("--chunk-count", type=int, default=1)
    p_commit.add_argument("--batch-count", type=int, default=1)
    p_commit.add_argument("--parallelism", type=int, default=1)
    # PLAN-20260806 Phase 3 Stage 2 §4.5(d)「判定方法〔S2〕」: merge_classification.py が出力する
    # min_chunk_mtime を経由した再利用波検出用（任意引数。未指定なら --classification の OS mtime を使う）。
    p_commit.add_argument("--chunk-mtime-min", type=float, default=None)
    # PLAN-20260806 Phase 3 Stage 2 §4.5(e): grep未対応パターンの discovery-log 追記（任意引数）。
    p_commit.add_argument("--unsupported-patterns", default=None)
    p_commit.set_defaults(func=cmd_commit_wave)

    p_status = sub.add_parser("status")
    p_status.add_argument("--path", required=True)
    # PLAN-20260806 Phase 3 Stage 2 §4.5(f): 判定に必要な最小キーのみを返す軽量出力（既定は現行どおり全体）。
    p_status.add_argument("--brief", action="store_true")
    p_status.set_defaults(func=cmd_status)

    p_ss = sub.add_parser("set-state")
    p_ss.add_argument("--path", required=True)
    p_ss.add_argument("--state", required=True)
    p_ss.set_defaults(func=cmd_set_state)

    p_merge = sub.add_parser("merge-frontier")
    p_merge.add_argument("--path", required=True)
    p_merge.add_argument("--symbols", required=True)
    # 未指定（None）と空指定を区別する。未指定時は state の entry_point_symbols を変更しない。
    p_merge.add_argument("--entry-point-symbols", default=None)
    # seed-summary の出力（要約の取り込み・seed_summary_pending の解消）、シードのグローバルとしての投入、
    # 探索の起点の置き直し（人が --re-discover で加えたシンボルを上限の波数まで調べる）。
    p_merge.add_argument("--summaries-file", default=None)
    p_merge.add_argument("--as-seed-globals", action="store_true")
    p_merge.add_argument("--reset-wave-origin", action="store_true")
    p_merge.set_defaults(func=cmd_merge_frontier)

    p_extend = sub.add_parser("extend")
    p_extend.add_argument("--path", required=True)
    p_extend.add_argument("--max-wave", type=int, required=True)
    p_extend.add_argument("--today", required=True)
    p_extend.set_defaults(func=cmd_extend)

    p_switch = sub.add_parser("switch-engine")
    p_switch.add_argument("--path", required=True)
    p_switch.add_argument("--to", required=True)
    p_switch.add_argument("--today", required=True)
    p_switch.set_defaults(func=cmd_switch_engine)

    p_rediscover = sub.add_parser("re-discover")
    p_rediscover.add_argument("--path", required=True)
    p_rediscover.add_argument("--symbols", required=True)
    p_rediscover.add_argument("--entry-point-symbols", default=None)
    p_rediscover.add_argument("--entry-identity", choices=("resolved", "name-only"), default="resolved")
    p_rediscover.add_argument("--today", required=True)
    p_rediscover.set_defaults(func=cmd_re_discover)

    p_import = sub.add_parser("import")
    p_import.add_argument("--path", required=True)
    p_import.add_argument("--from", dest="from", default=None)
    p_import.add_argument("--repo-path", default=None)
    p_import.add_argument("--discovery-log", default=None)
    p_import.set_defaults(func=cmd_import)

    p_funcmap = sub.add_parser("funcmap-counts")
    p_funcmap.add_argument("--discovery-log", required=True, dest="discovery_log")
    p_funcmap.add_argument("--out", required=True)
    p_funcmap.set_defaults(func=cmd_funcmap_counts)

    p_doc = sub.add_parser("doc-targets")
    p_doc.add_argument("--path", required=True)
    p_doc.add_argument("--ledger", default=None)
    p_doc.add_argument("--memo", default=None)
    p_doc.add_argument("--module-assignments", default=None)
    p_doc.add_argument("--auto-assign", action="store_true")
    # 追加下調べの対象（シードの直接参照のうち台帳・判断の記録に無いもの）に絞る。--max-files は repo ごとの累計の上限。
    p_doc.add_argument("--only", choices=["seed-direct"], default=None)
    p_doc.add_argument("--max-files", type=int, default=None)
    p_doc.add_argument("--gap-reviewed", default=None)
    p_doc.set_defaults(func=cmd_doc_targets)

    p_rs = sub.add_parser("ripple-summary")
    p_rs.add_argument("--path", required=True)
    p_rs.add_argument("--discovery-log", required=True, dest="discovery_log")
    p_rs.add_argument("--ledger", default=None)
    p_rs.add_argument("--module-assignments", default=None)
    p_rs.add_argument("--gap-reviewed", default=None)
    p_rs.add_argument("--max-files", type=int, default=None)
    p_rs.add_argument("--out", required=True)
    p_rs.add_argument("--json", required=True)
    p_rs.add_argument("--waves-dir", default=None)
    p_rs.set_defaults(func=cmd_ripple_summary)

    p_vs = sub.add_parser("verify-sweep")
    p_vs.add_argument("--path", required=True)
    p_vs.add_argument("--discovery-log", required=True, dest="discovery_log")
    p_vs.add_argument("--exclude-patterns", default="")
    p_vs.add_argument("--include-extensions", default="")
    p_vs.set_defaults(func=cmd_verify_sweep)

    # 引数の組み合わせは cmd_assemble_spo（_assemble_usage）が検査する（誤りは終了コード 2）。
    p_as = sub.add_parser("assemble-spo")
    p_as.add_argument("--path", default=None)
    p_as.add_argument("--repo-path", default=None)
    p_as.add_argument("--repo", default=None)
    p_as.add_argument("--output-dir", required=True)
    p_as.add_argument("--summary-template", required=True)
    p_as.add_argument("--module-template", required=True)
    p_as.add_argument("--max-files-per-module", type=int, required=True)
    p_as.add_argument("--layout-only", action="store_true")
    p_as.add_argument("--only", choices=["seed-direct"], default=None)
    p_as.add_argument("--max-files", type=int, default=None)
    p_as.add_argument("--no-ripple", action="store_true")
    p_as.add_argument("--summary-json", default=None)
    p_as.add_argument("--sweep-json", default=None)
    p_as.add_argument("--detail-level", choices=["standard", "brief"], default="standard")
    p_as.add_argument("--metrics", default=None)
    p_as.add_argument("--crs-file", default=None)
    # 未指定（None）と空指定を区別する（空文字列は「人の指定なし」として受け付ける）。
    p_as.add_argument("--entry-points", default=None)
    p_as.add_argument("--propagation-log", default=None)
    p_as.add_argument("--cr", required=True)
    p_as.add_argument("--today", required=True)
    p_as.set_defaults(func=cmd_assemble_spo)

    p_ci = sub.add_parser("commit-assemble-inputs")
    p_ci.add_argument("--output-dir", required=True)
    p_ci.add_argument("--fingerprint", required=True)
    p_ci.set_defaults(func=cmd_commit_assemble_inputs)

    p_pm = sub.add_parser("prelim-metrics")
    p_pm.add_argument("--path", required=True)
    p_pm.add_argument("--seed-candidates", required=True)
    p_pm.add_argument("--ledger", default=None)
    p_pm.add_argument("--seed-gate", required=True, choices=["true", "false"])
    p_pm.set_defaults(func=cmd_prelim_metrics)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 — CLI境界でのエラーはstderrへ集約する
        _err(f"予期しないエラーが発生しました: {e}")


if __name__ == "__main__":
    main()
