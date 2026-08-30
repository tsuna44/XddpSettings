"""
specout_bfs.py — Discovery BFS 帳簿エンジン（段階3）

`xddp-specout-agent.md` の Step 2（BFS ループ）が担っていた帳簿処理（visited/frontier 管理・
複合 grep コマンド組み立てと実行・コマンドID採番・件数記録・SYMBOL_ORIGIN_MAP・HIGH/MEDIUM
交差ルール・同名 MEDIUM 異スコープのケースA/B/C分岐・高ノイズシンボル判定・
discovery-log.md/checkpoint 相当状態の書き出し）を機械化する。

真実は `{OUTPUT_DIR}/bfs-state.json`（checkpoint.json は段階1で廃止・本ファイルに統合）。
`checkpoint.md` は本スクリプトが状態から再生成する人可読ビュー（表示フォーマットは
段階1 `specout_checkpoint.py` と互換）。discovery-log.md はテンプレート
（`04_specout-discovery-log-template.md`）と同一の見出し・テーブル列構成で生成する。

LLM とのプロトコル（PLAN-20260806 Phase 3 Stage 2: 波ループの実行主体は SKILL 側オーケストレータ）:
  1. `init` で BFS を開始（Wave 0 の initial_symbols は呼び出し元 LLM が CRS から抽出済みの値）
  2. オーケストレータ（SKILL）が `search` で現波の frontier を grep/rg 実行し、
     `wave-{N}-hits.json` と分割済みチャンク `wave-{N}-hits-chunk-{K}.json`（`known_symbols` 複製込み）
     を出力する
  3. classifier サブエージェント（チャンク単位・並列起動）が各チャンクの hits を意味判定し
     `wave-{N}-chunk-{K}-class.json` を作成する
     （偽陽性判定・伝播種別・次波シンボル・含む関数/クラス・外部公開パターンの有無）
  4. `merge_classification.py` がチャンク結果を検証・結合して `wave-{N}-class.json`（および
     grep未対応パターン `wave-{N}-unsupported.json`）を作る
  5. `commit-wave` が classification を検証し、帳簿を更新して discovery-log.md に書き出す
  6. frontier が尽きるまで 2〜5 を繰り返す。`status --brief` で再開・一時停止判定を確認する

Usage:
  python3 specout_bfs.py init --path STATE_JSON --repo-path REPO_PATH --discovery-log LOG_MD
      --symbols SYMS --today TODAY --cr CR --repo REPO [--exclude PATTERNS] [--include-ext EXTS]
      [--max-wave N] [--max-files-per-module N] [--module-catalog FILE]
  python3 specout_bfs.py search --path STATE_JSON (--hits-out HITS_JSON | --hits-dir DIR)
      [--chunk-size N]
  python3 specout_bfs.py commit-wave --path STATE_JSON --hits HITS_JSON --classification CLASS_JSON --today TODAY
      [--chunk-count N] [--batch-count N] [--parallelism N] [--chunk-mtime-min EPOCH]
      [--unsupported-patterns FILE]
  python3 specout_bfs.py status --path STATE_JSON [--brief]
  python3 specout_bfs.py prune --path STATE_JSON --remove SYMS --reason TEXT
  python3 specout_bfs.py merge-frontier --path STATE_JSON --symbols SYMS
  python3 specout_bfs.py re-discover --path STATE_JSON --symbols SYMS --today TODAY
  python3 specout_bfs.py record-module --path STATE_JSON --module DIR --today TODAY [--confidence LEVEL]
  python3 specout_bfs.py finish --path STATE_JSON --mode complete|out-of-scope [--reason TEXT] --today TODAY
  python3 specout_bfs.py set-state --path STATE_JSON --state STATE
  python3 specout_bfs.py import --path STATE_JSON --from CHECKPOINT_MD

Output: 成功時は stdout に JSON 1オブジェクト（{"ok": true, ...}）。
        失敗時は exit code 非0 + stderr にメッセージ。
"""

import argparse
import collections
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

VALID_STATES = {"in-progress", "paused-at-limit", "paused-at-limit-2nd", "complete"}
MEDIUM_RE = re.compile(r"^(?P<symbol>.+)\[MEDIUM:(?P<scope>.+)\]$")
CLASS_VALUES = {
    "false-positive",
    "propagation-direct",
    "propagation-argument",
    "propagation-return",
    "out-of-scope-discard",
}
PROPAGATION_LABEL = {
    "false-positive": "コメント/文字列（偽陽性）",
    "propagation-direct": "制御フロー＋データフロー",
    "propagation-argument": "引数伝播",
    "propagation-return": "データフロー（戻り値/公開）",
    "out-of-scope-discard": "➖ 対象外（廃棄）",
}
CONFIDENCE_FOR_CLASS = {
    "false-positive": "—",
    "propagation-direct": "HIGH",
    "propagation-argument": "MEDIUM",
    "propagation-return": "HIGH",
    "out-of-scope-discard": "—",
}
NO_PROPAGATION_CLASSES = {"false-positive", "out-of-scope-discard"}
CONFIDENCE_RANK = {"HIGH": 3, "MEDIUM": 2, "MODULE-LEVEL": 1}

# PLAN-20260806 Phase 3 Stage 1 §4.5(d): classify_wall_ms は「search → commit-wave 間の壁時計」であり
# LLM の実行時間そのものではなくその上界（規定外の手動操作では人の待ち時間が丸ごと混入する）。
# 閾値超過は汚染の疑いとして metrics に併記し、ゲート判定の集計から除外できるようにする。
# 暫定値であり実測分布が得られた時点で見直す（固定閾値ではなく中央値の N 倍という相対基準も選択肢）。
CLASSIFY_WALL_MS_SUSPECT_THRESHOLD_MS = 1800000  # 30分

# PLAN-20260806 Phase 3 Stage 2 §4.5(e): discovery-log ヘッダ部の見出し文字列。
# `_discovery_log_header` の生成側と `_append_unsupported_patterns` の挿入側で同一定数を参照し、
# 見出し文言のドリフトによる「セクション不在（no-op）」の再発を防ぐ。
GREP_UNSUPPORTED_HEADING = "## grep未対応パターン（手動確認必要）"


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
    （finish / re-discover / prune / set-state / 波数上限の早期 return）の後に古い開始時刻が
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


def _split_csv(raw: str) -> list:
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


def _parse_entry(entry: str):
    m = MEDIUM_RE.match(entry)
    if m:
        return m.group("symbol"), m.group("scope")
    return entry, None


def _format_entry(symbol: str, scope) -> str:
    return f"{symbol}[MEDIUM:{scope}]" if scope else symbol


def _validate_frontier_format(symbols: list) -> None:
    for s in symbols:
        if "[" in s or "]" in s:
            if not MEDIUM_RE.match(s):
                _err(f"Frontier のシンボル形式が不正です: {s!r}（MEDIUM形式は symbol[MEDIUM:filepath]）")


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
    return not re.search(r"\b" + escape_symbol(symbol) + r"\b", code_part)


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


def _grep_compound(syms: list) -> str:
    """複数シンボルを1本にまとめた grep 形式の複合パターン `(A|B|C)`。
    各シンボルの境界有無は `_word_boundary` で個別に解決する。
    """
    return "(" + "|".join(_word_boundary(s) for s in syms) + ")"


def _grep_compound_repr(syms: list) -> str:
    """複合パターンの人間可読な表示形式（ログ・pattern_repr 用）。

    全シンボルが単語文字（[A-Za-z0-9_]）で囲まれている場合は旧形式
    `\\b(alpha|beta)\\b` を返し、過去の discovery-log 表記との一貫性を保つ。
    非単語文字端シンボルが含まれる場合は、各シンボルの境界を個別に表現した
    `(A|B|C)` を返し、技術的正確性を保つ。
    単一シンボルの場合はグループ化しない。
    """
    if not syms:
        return "()"
    if len(syms) == 1:
        return _word_boundary(syms[0])
    # 全シンボルが両端単語文字なら旧形式を維持
    if all(_is_word_char(s[0]) and _is_word_char(s[-1]) for s in syms):
        return r"\b(" + "|".join(escape_symbol(s) for s in syms) + r")\b"
    # 非単語文字端シンボルが含まれる場合は個別境界表示
    return "(" + "|".join(_word_boundary(s) for s in syms) + ")"


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
        "limit_reached_count": 0,
        "confirmed_file_count": 0,
        "exclude_patterns": [],
        "include_extensions": [],
        "max_wave_depth": 10,
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
    }


def _md_path_for(json_path: Path) -> Path:
    return json_path.with_suffix(".md") if json_path.suffix == ".json" else json_path.parent / "checkpoint.md"


def _render_md(data: dict) -> str:
    lines = [
        "# BFS Checkpoint",
        "",
        "> このファイルは `specout_bfs.py` が `bfs-state.json` から生成する人可読ビューです。",
        "> 直接編集せず `prune`/`merge-frontier`/`re-discover`/`finish` 等の専用サブコマンドを使用してください。",
        "",
        f"**状態：** {data['state']}",
        f"**現在 Wave 番号：** {data['current_wave']}",
        f"**最終完了 Wave：** {data['last_completed_wave']}",
        f"**Wave 書き込み完了：** {'true' if data['wave_write_complete'] else 'false'}",
        f"**上限到達回数：** {data['limit_reached_count']}",
        f"**確定ファイル数：** {data['confirmed_file_count']}",
        f"**除外パターン：** {','.join(data['exclude_patterns'])}",
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

def _discovery_log_header(cr: str, repo: str, today: str, exclude_patterns: list,
                           include_extensions: list, max_wave_depth: int, initial_symbols: list) -> str:
    excl = ",".join(exclude_patterns) if exclude_patterns else "(なし)"
    incl = ",".join(include_extensions) if include_extensions else "(全ファイル対象)"
    symbol_lines = "\n".join(f"  - `{s}` （CRS SP項目より）" for s in initial_symbols) or "  - （未設定）"
    return (
        f"# Discovery Log — {cr} / {repo}\n\n"
        "## 探索設定\n"
        f"- 開始日時: {today}\n"
        "- 検索ツール: rg（ripgrep）優先 / 不在の場合は grep -rn -E\n"
        "- 検索対象: プロダクションコードのみ\n"
        f"- 除外パターン: {excl}\n"
        f"- 検索拡張子: {incl}（空の場合は全ファイル対象）\n"
        f"- 最大波数: {max_wave_depth}（上限到達時は frontier を記録して一時停止）\n"
        "- ⚠️ MEDIUM スコープ限定の既知制約: `param[MEDIUM:src/process.py]` は指定ファイル内のみ検索する。\n"
        "  同スコープ外でインポート・再利用されている同名シンボルは検出されない。\n"
        "  MEDIUM ヒットファイルが他ファイルへ公開 API としてエクスポートしている場合は手動確認すること。\n"
        "- 初期シンボル（Wave 0）:\n"
        f"{symbol_lines}\n\n"
        r"> **セル記法:** 本ログのテーブルのセル値に含まれる `|` は、Markdown の列区切りと" "\n"
        r"> 衝突するため `\|` にエスケープして記録されている（`specout_bfs.py` の `_md_cell()`）。" "\n"
        r"> セル値を他の成果物へ転記する際は `\|` を `|` に戻すこと。" "\n"
        r"> `\|` は元のソースコード／正規表現では単なる `|` である。" "\n\n"
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
            # location（"（" を含まない file:line 形式）のみを dedup キーへ用いる。
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


def _confidence_label(kind: str) -> str:
    return "HIGH" if kind == "HIGH複合" else "MEDIUM"


def _upsert_confirmed_files_section(log_path: Path, data: dict) -> None:
    """Step 3「確定ファイル一覧の書き出し」相当。commit-wave/finish のたびに全体を再構築する。"""
    heading = "## 確定した波及ファイル一覧（Documentation チェックリスト）"
    section = [heading, "",
               r"> **セル記法:** 本ログのテーブルのセル値に含まれる `|` は、Markdown の列区切りと",
               r"> 衝突するため `\|` にエスケープして記録されている（`specout_bfs.py` の `_md_cell()`）。",
               r"> セル値を他の成果物へ転記する際は `\|` を `|` に戻すこと。",
               r"> `\|` は元のソースコード／正規表現では単なる `|` である。",
               "",
               "| ファイル | 発見波 | 最高確信度 | ドキュメント化 |", "|---|---|---|---|"]
    for path_, info in sorted(data["confirmed_files"].items()):
        section.append(f"| {_md_cell(path_)} | Wave {info['wave']} | {info['confidence']} | ⬜ 未 |")
    section.append("")
    text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    idx = text.find(heading)
    if idx != -1:
        end = text.find("\n## ", idx + len(heading))
        end_dash = text.find("\n---", idx + len(heading))
        boundaries = [b for b in (end, end_dash) if b != -1]
        end = min(boundaries) if boundaries else len(text)
        text = text[:idx] + text[end:].lstrip("\n")
        idx = -1  # 差し替え後は末尾へ再追加する
    with open(log_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.rstrip("\n") + "\n\n" + "\n".join(section) + "\n")


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

def cmd_init(args) -> None:
    json_path = Path(args.path)
    if json_path.exists():
        _err(f"bfs-state.json が既に存在します: {json_path}（re-discover か import を使用してください）")
    symbols = _split_csv(args.symbols)
    _validate_frontier_format(symbols)
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
        "exclude_patterns": _split_csv(args.exclude),
        "include_extensions": _split_csv(args.include_ext),
        "max_wave_depth": args.max_wave,
        "max_files_per_module": args.max_files_per_module,
        "module_catalog_file": args.module_catalog or "",
        "hit_filter": (getattr(args, "hit_filter", None) or "conservative").strip() or "conservative",
        "scope_summary": scope_summary,
    })
    _write_state(json_path, data)

    log_path = Path(args.discovery_log)
    if not log_path.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(_discovery_log_header(
                args.cr, args.repo, args.today, data["exclude_patterns"],
                data["include_extensions"], data["max_wave_depth"], symbols,
            ))
    result = {"ok": True, "current_wave": 0, "frontier_count": len(symbols)}
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

def _build_exclude_include_grep(exclude_patterns: list, include_extensions: list) -> list:
    opts = []
    for p in exclude_patterns:
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


def _run_grep_batch(pattern: str, scope, exclude_opts_grep, repo_path: str) -> list:
    """`grep -rn -E pattern [scope|repo_path]` を実行し (file, line, content) を返す。"""
    target = _resolve_scope_target(scope, repo_path)
    cmd = ["grep", "-rn", "-E"] + (exclude_opts_grep if not scope else []) + [pattern, target]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode not in (0, 1):
        _err(f"grep 実行に失敗しました: {' '.join(cmd)}\n{proc.stderr}")
    rows = []
    for line in proc.stdout.split("\n"):
        if not line:
            continue
        m = _HIT_LINE_RE.match(line)
        if m:
            rows.append((m.group("file"), int(m.group("line")), m.group("content")))
    return rows


def _run_rg_patternfile(patterns: list, scope, exclude_opts_rg, repo_path: str) -> list:
    with tempfile.NamedTemporaryFile("w", suffix=".patterns", delete=False, encoding="utf-8") as tf:
        tf.write("\n".join(patterns) + "\n")
        patternfile = tf.name
    try:
        target = _resolve_scope_target(scope, repo_path)
        cmd = ["rg", "-n", "--no-heading"] + (exclude_opts_rg if not scope else []) + ["-f", patternfile, target]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode not in (0, 1):
            _err(f"rg 実行に失敗しました: {' '.join(cmd)}\n{proc.stderr}")
        rows = []
        for line in proc.stdout.split("\n"):
            if not line:
                continue
            m = _HIT_LINE_RE.match(line)
            if m:
                rows.append((m.group("file"), int(m.group("line")), m.group("content")))
        return rows
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


class GrepBackend:
    """`grep -rn -E` による参照探索。HIGH は _batch_symbols で複数コマンドへ分割（現行 grep 経路の再現）。"""

    name = "grep"

    def __init__(self, exclude_patterns: list, include_extensions: list, repo_path: str):
        self.exclude_opts = _build_exclude_include_grep(exclude_patterns, include_extensions)
        self.repo_path = repo_path

    def search(self, symbols: list, scope) -> list:
        if scope is None:
            commands = []
            for batch in _batch_symbols(symbols):
                pattern = _grep_compound(batch)
                rows = _run_grep_batch(pattern, None, self.exclude_opts, self.repo_path)
                pattern_repr = _grep_compound_repr(batch)
                commands.append(SearchCommand(pattern_repr, rows, list(batch)))
            return commands
        pattern = _grep_compound(symbols)
        rows = _run_grep_batch(pattern, scope, self.exclude_opts, self.repo_path)
        pattern_repr = _grep_compound_repr(symbols)
        return [SearchCommand(pattern_repr, rows, list(symbols))]


class RgBackend:
    """ripgrep patternfile による参照探索。HIGH/MEDIUM とも単一コマンドへ集約（現行 rg 経路の再現）。"""

    name = "rg"

    def __init__(self, exclude_patterns: list, include_extensions: list, repo_path: str):
        self.exclude_opts = _build_exclude_include_rg(exclude_patterns, include_extensions)
        self.repo_path = repo_path

    def search(self, symbols: list, scope) -> list:
        patterns = [_word_boundary(s) for s in symbols]
        rows = _run_rg_patternfile(patterns, scope, self.exclude_opts, self.repo_path)
        pattern_repr = _grep_compound_repr(symbols)
        return [SearchCommand(pattern_repr, rows, list(symbols))]


def resolve_backend(data: dict):
    """`data["backend"]` から Backend 実装を解決する。

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
    if name == "auto":
        return (_rg(), "rg", None) if have_rg else (_grep(), "grep", None)
    if name in STATIC_BACKENDS:
        return _grep(), "grep", (
            f"SPECOUT_BACKEND={name} は段階2以降で実装予定の静的解析バックエンドです（未実装）。"
            "grep にフォールバックしました。")
    return _grep(), "grep", (
        f"SPECOUT_BACKEND={name} は未知のバックエンド値です。grep にフォールバックしました。")


def _pause_for_wave_limit(data: dict, state_path: Path, log_path: Path) -> dict:
    data["limit_reached_count"] += 1
    if data["limit_reached_count"] == 1:
        data["state"] = "paused-at-limit"
    else:
        data["state"] = "paused-at-limit-2nd"
    # PLAN-20260806 Phase 3 Stage 1 §4.5(c): 早期 return では hits を生成せず分類区間が存在しないため
    # 開始時刻は書かず、古い波の値が残らないよう既存値を削除する。
    _drop_classify_timer(data)
    _write_state(state_path, data)
    frontier_desc = "\n".join(f"- {e}" for e in data["frontier"]) or "(なし)"
    msg = (
        f"\n---\n## ⚠️ 探索上限到達（Wave {data['current_wave']}, 上限到達回数={data['limit_reached_count']}）\n"
        f"残存フロンティア:\n{frontier_desc}\n"
    )
    if data["limit_reached_count"] == 1:
        msg += "影響調査は未完了です。人がフロンティアを精査し、下記 A/B/C のいずれかを選択して続行してください。\n"
    else:
        msg += "2回目の探索上限到達。継続パス B（モジュール一括記録）へ自動移行します。`finish --mode complete` を実行してください。\n"
    _append_to_file(log_path, msg)
    return {"ok": True, "paused": True, "state": data["state"], "limit_reached_count": data["limit_reached_count"]}


def cmd_search(args) -> None:
    # PLAN-20260806 Phase 3 Stage 2 §4.5(b): --hits-out / --hits-dir は相互排他。
    # 両方未指定・両方指定はいずれも明示エラーとし、暗黙の優先順位を作らない。
    if (args.hits_out is None) == (args.hits_dir is None):
        _err("--hits-out と --hits-dir はどちらか一方のみを指定してください（同時未指定・同時指定はエラー）")
    state_path = Path(args.path)
    data = _load_state(state_path)
    if data["state"] == "complete":
        _err("BFS は既に complete 状態です（search 不要）")
    if data["state"] in ("paused-at-limit", "paused-at-limit-2nd"):
        _err(f"BFS は {data['state']} で一時停止中です。prune / finish で継続パスを選択してから search してください")
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
            f"(3) re-discover --path {args.path} --symbols <(1)の残存＋追加シンボル> --today <YYYY-MM-DD>"
            f"（re-discover は frontier を置換するため、(1) の残存分を --symbols に含めないと黙って失われる）"
        )

    if data["current_wave"] > data["max_wave_depth"]:
        result = _pause_for_wave_limit(data, state_path, Path(data["discovery_log"]))
        print(json.dumps(result, ensure_ascii=False))
        return

    module_map = data.get("module_priority_map") or {}
    symbol_module = data.get("symbol_module") or {}
    frontier = list(data["frontier"])
    low = list(data.get("low_priority_frontier") or [])

    if data.get("module_priority_computed") and module_map:
        # PLAN-20260806 Phase 2B: catalog モードは未知モジュールを HIGH（既存挙動不変）、
        # simple モード（module-catalog 不在）は未知ディレクトリを LOW とする（§3.2。捨てず低優先で退避）。
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
        _err("frontier が空です（search 対象がありません）")

    high_symbols = [e for e in this_wave if _parse_entry(e)[1] is None]
    medium_entries = [_parse_entry(e) for e in this_wave if _parse_entry(e)[1] is not None]
    medium_by_scope = {}
    for symbol, scope in medium_entries:
        medium_by_scope.setdefault(scope, []).append(symbol)

    repo_path = data["repo_path"]
    backend, effective_backend, backend_warning = resolve_backend(data)
    data["backend_effective"] = effective_backend
    if backend_warning and not data.get("backend_fallback_logged"):
        _append_to_file(Path(data["discovery_log"]), f"\n> ⚠️ バックエンド警告: {backend_warning}\n")
        data["backend_fallback_logged"] = True

    commands = []
    hits = []
    cmd_n = 0
    wave = data["current_wave"]

    def _next_cmd_id():
        nonlocal cmd_n
        cmd_n += 1
        return f"W{wave}-C{cmd_n}"

    def _matching_symbol(content: str, candidates: list) -> str:
        for sym in candidates:
            if re.search(r"\b" + escape_symbol(sym) + r"\b", content):
                return sym
        return candidates[0] if candidates else ""

    line_n = 0

    def _next_line_id():
        nonlocal line_n
        line_n += 1
        return f"W{wave}-R{line_n}"

    # PLAN-20260804 Phase 0/1a/1b: 計測・dedup・保守的フィルタ
    classified_set = set(data.get("classified_locations") or [])  # cross-wave dedup（scope_class 込み）
    hit_filter = data.get("hit_filter", "conservative")
    metrics = {"wave": wave, "search_ms": 0, "raw_hits": 0, "dedup_removed": 0, "filter_removed": 0,
               "noise_collapse_removed": 0}
    filtered_out = []  # discovery-log 記録用: {file, line_no, symbol, reason}

    def _loc_key(sym: str, rel_file: str, line_no, scope_class: str) -> str:
        # scope_class は HIGH（scope=None）または MEDIUM のスコープ文字列。ケースA多スコープ判定の
        # 入力（HIGH/各 MEDIUM スコープの初出）を落とさないため dedup キーへ含める（PLAN §3.1・指摘#4）。
        return "\x00".join([sym, rel_file, str(line_no), scope_class])

    def _process_command(cmd_id: str, sc, scope_file, scope_class: str, buffer=None):
        """1コマンド（下位ツール1実行）の生行を dedup＋保守的フィルタしつつ hits へ積む。
        `buffer` を渡すと、フィルタ通過分は hits へ直接積まず buffer（symbol別グルーピング用の一時list）へ
        積む（PLAN-20260806 Phase 2A: HIGH の pre-noisy 判定・代表サブセット選定用。MEDIUM は常に buffer=None）。
        戻り値: (dedup_removed, filter_removed)。生ヒット数は commands 側 hit_count に保持。"""
        d = f = 0
        for file_, line_no, content in sc.rows:
            metrics["raw_hits"] += 1
            sym = _matching_symbol(content, sc.candidates)
            rel = _rel_file(file_, repo_path)
            key = _loc_key(sym, rel, line_no, scope_class)
            if key in classified_set:  # 過去波で同一スコープ種別で分類済みの再出現（新情報なし）
                metrics["dedup_removed"] += 1; d += 1
                filtered_out.append({"file": rel, "line_no": line_no, "symbol": sym, "reason": "dedup"})
                continue
            ext = os.path.splitext(file_)[1].lower()
            if hit_filter == "conservative" and _is_pure_line_comment(content, sym, ext):
                metrics["filter_removed"] += 1; f += 1
                filtered_out.append({"file": rel, "line_no": line_no, "symbol": sym, "reason": "line-comment"})
                continue
            if buffer is not None:
                buffer.append({"cmd_id": cmd_id, "symbol": sym, "file": rel, "line_no": line_no, "matched_text": content})
            else:
                hits.append({"line_id": _next_line_id(), "command_id": cmd_id, "symbol": sym, "scope_file": scope_file,
                             "file": rel, "line_no": line_no, "matched_text": content})
        return d, f

    pre_noisy = set()   # PLAN-20260806 Phase 2A: 前倒し縮退対象シンボル（HIGH のみ。MEDIUM は常に非該当）
    module_files = {}   # {symbol: [file, ...]}（post-dedup/filter emitted 全ファイル。confirmed_files 網羅維持用）

    if high_symbols:
        t0 = time.monotonic()
        high_results = backend.search(high_symbols, None)
        metrics["search_ms"] += int((time.monotonic() - t0) * 1000)
        all_emitted = []
        cmd_meta = {}
        for sc in high_results:
            cmd_id = _next_cmd_id()
            d, f = _process_command(cmd_id, sc, None, "HIGH", buffer=all_emitted)
            cmd_meta[cmd_id] = {"command_id": cmd_id, "kind": "HIGH複合", "pattern": sc.pattern_repr, "scope": "全域",
                                 "hit_count": len(sc.rows), "dedup_removed": d, "filter_removed": f,
                                 "noise_collapse_removed": 0}

        # PLAN-20260806 Phase 2A: post-dedup/filter のシンボル別ファイル数（commit-wave の noisy_keys と
        # 同一入力・同一指標）で pre-noisy を判定する。生ヒット数指標は用いない（境界シンボルの取りこぼしを
        # 避けるため。詳細は PLAN-20260806-specout-phase2-noise-priority.md §3.1）。
        by_symbol = {}
        for i, e in enumerate(all_emitted):
            by_symbol.setdefault(e["symbol"], []).append(i)
        skip_indices = set()
        for sym, idxs in by_symbol.items():
            files = sorted({all_emitted[i]["file"] for i in idxs})
            if len(files) <= data["max_files_per_module"]:
                continue
            pre_noisy.add(sym)
            module_files[sym] = files  # F(S)＝全ファイル。代表 hits に現れないファイルも confirmed_files へ載せる
            # 代表サブセット: ファイルパス昇順で先頭 max_files_per_module 件・各ファイル最大1行（先頭出現行）
            first_index_by_file = {}
            for i in idxs:
                first_index_by_file.setdefault(all_emitted[i]["file"], i)
            rep_indices = {first_index_by_file[f] for f in files[: data["max_files_per_module"]]}
            skip_indices.update(i for i in idxs if i not in rep_indices)

        for i, e in enumerate(all_emitted):
            if i in skip_indices:
                filtered_out.append({"file": e["file"], "line_no": e["line_no"], "symbol": e["symbol"],
                                      "reason": "noise-collapse"})
                cmd_meta[e["cmd_id"]]["noise_collapse_removed"] += 1
                continue
            hits.append({"line_id": _next_line_id(), "command_id": e["cmd_id"], "symbol": e["symbol"],
                         "scope_file": None, "file": e["file"], "line_no": e["line_no"],
                         "matched_text": e["matched_text"]})

        metrics["noise_collapse_removed"] = len(skip_indices)
        commands.extend(cmd_meta.values())

    for scope in sorted(medium_by_scope.keys()):
        syms = medium_by_scope[scope]
        t0 = time.monotonic()
        medium_results = backend.search(syms, scope)
        metrics["search_ms"] += int((time.monotonic() - t0) * 1000)
        for sc in medium_results:
            cmd_id = _next_cmd_id()
            d, f = _process_command(cmd_id, sc, scope, scope)
            commands.append({"command_id": cmd_id, "kind": "MEDIUM", "pattern": sc.pattern_repr, "scope": scope,
                             "hit_count": len(sc.rows), "dedup_removed": d, "filter_removed": f})

    frontier_medium_scopes = {}
    for symbol, scope in medium_entries:
        frontier_medium_scopes.setdefault(symbol, []).append(scope)

    hits_payload = {
        "wave": wave,
        "commands": commands,
        "hits": hits,
        "frontier_medium_scopes": frontier_medium_scopes,
        "searched_frontier": this_wave,
        "metrics": metrics,            # PLAN-20260804 Phase 0（commit-wave で classified 数を足して確定）
        "filtered_out": filtered_out,  # PLAN-20260804 Phase 1a/1b（discovery-log 監査記録用）
        "pre_noisy": sorted(pre_noisy),   # PLAN-20260806 Phase 2A（commit-wave の noisy_keys 拡張入力）
        "module_files": module_files,     # PLAN-20260806 Phase 2A（confirmed_files 網羅維持用）
        # PLAN-20260806 Phase 3 Stage 1 §4.5(g): LOW 退避の結果は search が state へ書き戻さず
        # commit-wave（フロンティア状態の単一書き手）へ渡して適用させる。これにより search は
        # フロンティア状態に対して読み取り専用となり、再 search が冪等になる。
        "deferred_low": low,
        # PLAN-20260806 Phase 3 Stage 2 §4.1: チャンク分割で判定入力が狭まらないよう、
        # 「戻り値代入/ジェネレータ受信」ルールの参照集合（visited ∪ searched_frontier ∪
        # current-wave-hits）を素名正規化して全チャンクへ複製配布する。
        "known_symbols": {
            "visited": sorted({_parse_entry(e)[0] for e in data["visited"]}),
            "searched_frontier": sorted({_parse_entry(e)[0] for e in this_wave}),
            "current_wave": sorted({h["symbol"] for h in hits}),
        },
        # PLAN-20260829: known_symbols と同じ配布パターン。init 時に1回だけ合成された値を
        # 毎波そのまま複製する（波・チャンクをまたいで不変）。
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

    # PLAN-20260806 Phase 3 Stage 2 §4.5(b): 常にチャンクファイルを出力する（分割の有無を問わず
    # 呼び出し側に分岐を作らない統一契約）。書き出し前に当該波の既存チャンクを削除し、
    # チャンク数が減る再 search で旧ランのファイルが残らないようにする。
    for stale in sorted(out_path.parent.glob(f"{out_path.stem}-chunk-*.json")):
        stale.unlink()
    commands_by_id = {c["command_id"]: c for c in commands}
    chunk_groups = _split_hits_into_chunks(hits, args.chunk_size)
    chunk_paths = []
    for idx, chunk_hits in enumerate(chunk_groups):
        cmd_ids = sorted({h["command_id"] for h in chunk_hits})
        chunk_payload = {
            "chunk_id": f"W{wave}-K{idx}",
            "wave": wave,
            "hits": chunk_hits,
            "known_symbols": hits_payload["known_symbols"],
            "scope_summary": hits_payload["scope_summary"],
            "commands": [commands_by_id[cid] for cid in cmd_ids if cid in commands_by_id],
        }
        chunk_path = out_path.parent / f"{out_path.stem}-chunk-{idx}.json"
        with open(chunk_path, "w", encoding="utf-8", newline="\n") as cf:
            json.dump(chunk_payload, cf, ensure_ascii=False, indent=2)
            cf.write("\n")
        chunk_paths.append(str(chunk_path))

    data["wave_write_complete"] = False
    # PLAN-20260806 Phase 3 Stage 1 §4.5(c): 分類区間（search と commit-wave の"間"）の開始時刻を
    # 2キー対で記録する。search と commit-wave は別プロセスであり time.monotonic() は基準点が
    # プロセス間で保証されないため time.time()（エポック秒）を用いる。同じ波を再 search した場合は
    # 最新の開始時刻で上書きされる（＝最後の試行を計測する）。
    data["classify_started_at"] = time.time()
    data["classify_started_wave"] = wave
    _write_state(state_path, data)

    print(json.dumps({
        "ok": True, "wave": wave, "hits_file": str(out_path), "hit_count": len(hits),
        "raw_hits": metrics["raw_hits"], "dedup_removed": metrics["dedup_removed"],
        "filter_removed": metrics["filter_removed"], "search_ms": metrics["search_ms"],
        "noise_collapse_removed": metrics["noise_collapse_removed"], "pre_noisy": sorted(pre_noisy),
        "commands": [{"command_id": c["command_id"], "hit_count": c["hit_count"]} for c in commands],
        "chunks": chunk_paths, "chunk_count": len(chunk_paths),
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
        # 条件2: 既に BFS が完了している。当該波の search 実行後に finish を実行した state では
        # wave_write_complete: false かつ wave > last_completed_wave のまま complete になるため
        # 条件1・3 では捕捉できない（cmd_finish は state 以外のこれらのキーを触らない）。
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
            f"(3) re-discover --path {args.path} --symbols <(1)の残存＋追加シンボル> --today <YYYY-MM-DD>"
            f"（re-discover は frontier を置換するため、(1) の残存分を --symbols に含めないと黙って失われる）"
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
        return _format_entry(hit["symbol"], hit["scope_file"])

    # 高ノイズシンボル判定（1パス目）
    files_by_key = {}
    for h in hits:
        files_by_key.setdefault(_entry_key(h), set()).add(h["file"])
    # PLAN-20260806 Phase 2A: pre_noisy（search 側の代表サブセット化でファイル数を過小計上しうる）を
    # union することで、代表サブセット化後も伝播抑止条件（noisy_keys）が現行と等価に保たれる（§3.1）。
    noisy_keys = {k for k, files in files_by_key.items() if len(files) > data["max_files_per_module"]} | pre_noisy

    # 同名 MEDIUM シンボル・異スコープ重複グループの特定
    multi_scope_symbols = {sym: scopes for sym, scopes in frontier_medium_scopes.items() if len(set(scopes)) >= 2}
    case_rows = []
    case_a_symbols = {}  # symbol -> (trigger_scope, discarded_scopes)
    for sym, scopes in multi_scope_symbols.items():
        scopes = sorted(set(scopes))
        sym_hits = [h for h in hits if h["symbol"] == sym and h["scope_file"] in scopes]
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
            case_rows.append((sym, scopes, "A（HIGH昇格）",
                               f"HIGH へ昇格（`{trigger_scope}` で外部公開パターン検出）。"
                               f"`{'`, `'.join(discarded)}` の grep 結果を廃棄。次波で全域 grep"))
        elif total_hits == 0:
            case_rows.append((sym, scopes, "B（ヒットなし）",
                               "スコープファイル内で参照なし（同名パラメータが複数スコープで定義されているが、"
                               "いずれのスコープでも grep ヒットなし。別経路で利用されている可能性あり）。⚠️ 手動確認推奨"))
        else:
            case_rows.append((sym, scopes, "C（スコープ内参照のみ）", "両エントリを visited 保持。伝播なし"))

    discarded_command_ids = set()
    for sym, (trigger_scope, discarded) in case_a_symbols.items():
        for c in commands:
            if c["kind"] == "MEDIUM" and c["scope"] in discarded:
                discarded_command_ids.add(c["command_id"])

    # 派生元の解決
    def _origin_text(hit) -> str:
        key = _entry_key(hit)
        origins = data["symbol_origin_map"].get(key)
        if wave == 0:
            return f"CRS（初期シンボル: {hit['symbol']}）"
        if origins:
            return ", ".join(origins)
        return "— （非BFS伝播。理由を備考に記載）"

    rows = []
    next_candidates = []  # list of (entry_string, [origin_line_ids])
    new_symbol_origin = {}

    for h in hits:
        cls = class_by_id[h["line_id"]]
        cls_value = cls["classification"]
        key = _entry_key(h)
        enclosing = cls.get("enclosing_function") or "-"
        origin_text = _origin_text(h)
        next_syms = cls.get("next_symbols") or []
        if cls_value not in NO_PROPAGATION_CLASSES and key not in noisy_keys and not _is_discarded_scope(h, case_a_symbols):
            for ns in next_syms:
                next_candidates.append((ns, h["line_id"]))
                new_symbol_origin.setdefault(ns, []).append(h["line_id"])
        display_next = ", ".join(f"`{s}`" for s in next_syms) if (next_syms and cls_value not in NO_PROPAGATION_CLASSES) else "—"
        rows.append([
            h["line_id"], h["command_id"], f"`{key}`", h["file"], str(h["line_no"]),
            f"`{h['matched_text']}`",
            f"`{enclosing}`" if enclosing != "-" else "-",
            PROPAGATION_LABEL.get(cls_value, cls_value),
            CONFIDENCE_FOR_CLASS.get(cls_value, "-"),
            display_next, origin_text,
        ])

    # ケースA: symbol(HIGH) を候補へ追加
    for sym, (trigger_scope, discarded) in case_a_symbols.items():
        inherited = []
        for s in set([trigger_scope] + discarded):
            inherited.extend(data["symbol_origin_map"].get(_format_entry(sym, s), []))
        next_candidates.append((sym, None))
        new_symbol_origin.setdefault(sym, [])
        new_symbol_origin[sym] = list(dict.fromkeys(new_symbol_origin[sym] + inherited))
        # ケースAトリガーとなった sym[MEDIUM:*] 自体の再追加は行わない
        next_candidates = [(e, o) for e, o in next_candidates if not (MEDIUM_RE.match(e) and _parse_entry(e)[0] == sym)]

    # visited 更新
    visited = set(data["visited"])
    for entry in searched_frontier:
        visited.add(entry)

    # HIGH/MEDIUM 交差ルール + dedup
    seen = set()
    next_frontier = []
    high_visited = {e for e in visited if _parse_entry(e)[1] is None}
    for entry, _origin in next_candidates:
        if entry in seen:
            continue
        symbol, scope = _parse_entry(entry)
        if scope and symbol in high_visited:
            continue
        if entry in visited:
            continue
        seen.add(entry)
        next_frontier.append(entry)

    # symbol_origin_map 更新
    for k, v in new_symbol_origin.items():
        existing = data["symbol_origin_map"].get(k, [])
        merged = list(dict.fromkeys(existing + v))
        data["symbol_origin_map"][k] = merged

    # confirmed_files 更新
    for c in commands:
        conf = _confidence_label(c["kind"])
        for h in hits:
            if h["command_id"] != c["command_id"]:
                continue
            existing = data["confirmed_files"].get(h["file"])
            if existing is None or CONFIDENCE_RANK.get(conf, 0) > CONFIDENCE_RANK.get(existing["confidence"], 0):
                data["confirmed_files"][h["file"]] = {"wave": wave, "confidence": conf}

    # PLAN-20260806 Phase 2A: pre-noisy シンボルの全ファイル（module_files）を confirmed_files へ反映する。
    # 代表サブセットにのみ現れるファイルは上記ループで既に登録済みだが、非代表ファイルは hits に現れないため
    # ここで補う（confirmed_files 網羅の維持＝漏れゼロの要。全 pre-noisy シンボルは HIGH のため confidence=HIGH）。
    for files in module_files.values():
        for f in files:
            existing = data["confirmed_files"].get(f)
            if existing is None or CONFIDENCE_RANK.get("HIGH", 0) > CONFIDENCE_RANK.get(existing["confidence"], 0):
                data["confirmed_files"][f] = {"wave": wave, "confidence": "HIGH"}

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
    log_lines.append("| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | 含む関数/クラス（ファイル読み込みで確認） | "
                      "伝播種別 | 確信度 | Wave {} 追加シンボル | 派生元 |".format(wave + 1))
    log_lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for row in rows:
        log_lines.append("| " + " | ".join(_md_cell(cell) for cell in row) + " |")
    log_lines.append("")
    if next_frontier:
        log_lines.append(f"→ Wave {wave + 1} frontier: " + ", ".join(
            f"`{_parse_entry(e)[0]}`[{'MEDIUM' if _parse_entry(e)[1] else 'HIGH'}]" for e in next_frontier
        ))
    else:
        log_lines.append("→ 空。新規発見なし。探索終了。" if not data.get("low_priority_frontier") else
                          f"→ Wave {wave + 1} frontier: (MODULE_PRIORITY_LOW 分へ移行)")
    log_lines.append("")

    log_lines.append("### 件数一致検証")
    log_lines.append("| コマンドID | ヒット行数（生） | dedup除外 | フィルタ除外 | noise-collapse除外 | 記録行数 | 一致 |")
    log_lines.append("|---|---|---|---|---|---|---|")
    for c in commands:
        recorded = sum(1 for h in hits if h["command_id"] == c["command_id"])
        d = c.get("dedup_removed", 0)
        f = c.get("filter_removed", 0)
        nc = c.get("noise_collapse_removed", 0)
        # 生 = 記録 + dedup除外 + フィルタ除外 + noise-collapse除外
        # （PLAN-20260804 Phase 1: dedup/filter、PLAN-20260806 Phase 2A: noise-collapse を件数照合に織り込む）
        if c["command_id"] in discarded_command_ids:
            mark = "➖ 廃棄（ケースA, 次波でHIGH昇格済）"
        elif c["hit_count"] == recorded + d + f + nc:
            mark = "✅" if (d == 0 and f == 0 and nc == 0) else f"✅（dedup {d}/filter {f}/noise-collapse {nc} 除外）"
        else:
            mark = f"⚠️ {c['command_id']} 件数不一致（生{c['hit_count']}件/記録{recorded}+除外{d + f + nc}件）"
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
            log_lines.append(f"| {_md_cell(fo['file'])} | {fo['line_no']} | `{_md_cell(fo['symbol'])}` | {_md_cell(reason)} |")
        log_lines.append("")

    _append_to_file(log_path, "\n".join(log_lines))

    # PLAN-20260806 Phase 3 Stage 2 §4.5(e): 並列 classifier が discovery-log.md を各自 Edit すると
    # 書き込み競合が起きるため、書き手を commit-wave（単一）に集約する。ファイル未指定時は
    # 何もしない（既存呼び出しと完全に同一挙動＝後方互換）。
    if args.unsupported_patterns:
        unsupported_entries = json.loads(Path(args.unsupported_patterns).read_text(encoding="utf-8"))
        _append_unsupported_patterns(log_path, unsupported_entries)

    # PLAN-20260804 Phase 1a: 当該波で分類した (symbol,file,line,scope_class) を classified_locations へ登録。
    classified_set = set(data.get("classified_locations") or [])
    for h in hits:
        sc_class = "HIGH" if h["scope_file"] is None else h["scope_file"]
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

    # PLAN-20260804 Phase 0: per-wave metrics を metrics.jsonl（{OUTPUT_DIR}）へ1行追記。
    # 時間値（search_ms・classify_wall_ms）は非決定のため metrics 専用とし state 判定には持ち込まない
    # （再開の決定性保持）。
    metrics_line = {
        "wave": wave,
        "search_ms": wave_metrics.get("search_ms", 0),
        "raw_hits": wave_metrics.get("raw_hits", 0),
        "dedup_removed": wave_metrics.get("dedup_removed", 0),
        "filter_removed": wave_metrics.get("filter_removed", 0),
        "noise_collapse_removed": wave_metrics.get("noise_collapse_removed", 0),
        "classified": len(hits),
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
    metrics_path = Path(args.hits).parent / "metrics.jsonl"
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
    _write_state(state_path, data)

    print(json.dumps({
        "ok": True, "wave": wave, "state": data["state"], "next_frontier_count": len(next_frontier),
        "high_noise_symbols": newly_noisy, "case_a_promoted": list(case_a_symbols.keys()),
        "dedup_removed": metrics_line["dedup_removed"], "filter_removed": metrics_line["filter_removed"],
        "noise_collapse_removed": metrics_line["noise_collapse_removed"],
        "classified_locations_size": cl_size,
    }, ensure_ascii=False))


def _is_discarded_scope(hit, case_a_symbols) -> bool:
    sym = hit["symbol"]
    scope = hit["scope_file"]
    if sym in case_a_symbols and scope is not None:
        _trigger, discarded = case_a_symbols[sym]
        return scope in discarded
    return False


# ---------------------------------------------------------------------------
# status / set-state / prune / merge-frontier / re-discover / import
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
        }, ensure_ascii=False))
        return
    # PLAN-20260809: MODE: document Step 1.5（code-knowledge 参照）が confirmed_modules を
    # 決定的に取得するための追加フィールド。state ファイルへは永続化しない（出力時の派生値のみ）。
    confirmed_modules = sorted({
        _module_dir_for_file(data["repo_path"], f) for f in data.get("confirmed_files", {})
    })
    print(json.dumps({"ok": True, **data, "confirmed_modules": confirmed_modules}, ensure_ascii=False))


def cmd_set_state(args) -> None:
    if args.state not in VALID_STATES:
        _err(f"不正な状態です: {args.state}（有効値: {', '.join(sorted(VALID_STATES))}）")
    state_path = Path(args.path)
    data = _load_state(state_path)
    data["state"] = args.state
    _drop_classify_timer(data)  # PLAN-20260806 Phase 3 Stage 1 §4.5(c)（search を経ない状態遷移）
    _write_state(state_path, data)
    print(json.dumps({"ok": True, "state": data["state"]}, ensure_ascii=False))


def cmd_prune(args) -> None:
    if not args.reason or not args.reason.strip():
        _err("--reason は必須です（削除根拠の監査証跡として discovery-log.md へ記録するため）")
    state_path = Path(args.path)
    data = _load_state(state_path)
    remove = _split_csv(args.remove)
    missing = [s for s in remove if s not in data["frontier"]]
    if missing:
        _err(f"Frontier に存在しないため削除できません: {', '.join(missing)}")
    data["frontier"] = [s for s in data["frontier"] if s not in remove]
    if data["state"] == "paused-at-limit":
        data["state"] = "in-progress"
    _drop_classify_timer(data)  # PLAN-20260806 Phase 3 Stage 1 §4.5(c)（search を経ない状態遷移）
    _write_state(state_path, data)
    log_path = Path(data["discovery_log"])
    today = datetime.date.today().isoformat()
    entry = f"\n## Frontier剪定ログ\n\n- {today}: 削除シンボル: {', '.join(remove)} / 理由: {args.reason}\n"
    if log_path.exists() and "## Frontier剪定ログ" in log_path.read_text(encoding="utf-8"):
        entry = f"\n- {today}: 削除シンボル: {', '.join(remove)} / 理由: {args.reason}\n"
    _append_to_file(log_path, entry)
    print(json.dumps({"ok": True, "removed": remove, "frontier_count": len(data["frontier"])}, ensure_ascii=False))


def cmd_merge_frontier(args) -> None:
    state_path = Path(args.path)
    data = _load_state(state_path)
    symbols = _split_csv(args.symbols)
    added = [s for s in symbols if s not in data["frontier"]]
    data["frontier"].extend(added)
    _write_state(state_path, data)
    print(json.dumps({"ok": True, "added": added, "frontier_count": len(data["frontier"])}, ensure_ascii=False))


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
    data["wave_write_complete"] = True
    data["limit_reached_count"] = 0
    _drop_classify_timer(data)  # PLAN-20260806 Phase 3 Stage 1 §4.5(c)（search を経ない状態遷移）
    _write_state(state_path, data)
    log_path = Path(data["discovery_log"])
    entry = (
        f"\n---\n## [re-discover] セッション開始: {args.today}\n"
        f"追加エントリポイント: {', '.join(symbols)}\n"
        f"Wave {n + 1} から再開（既存 visited セット引き継ぎ）\n"
    )
    _append_to_file(log_path, entry)
    print(json.dumps({
        "ok": True, "state": "in-progress", "current_wave": n, "resume_wave": n + 1,
        "frontier_count": len(symbols),
    }, ensure_ascii=False))


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
        elif label == "上限到達回数":
            data["limit_reached_count"] = int(value) if value.isdigit() else 0
        elif label == "確定ファイル数":
            data["confirmed_file_count"] = int(value) if value.isdigit() else 0
        elif label == "除外パターン":
            data["exclude_patterns"] = _split_csv(value)

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
    _write_state(state_path, data)
    warnings = [
        "checkpoint.md からの import は人可読ビューに含まれる情報のみを復元します。",
        "confirmed_files, symbol_origin_map, classified_locations, module_priority_map, "
        "low_priority_frontier, symbol_module, scope_summary は初期化されるため、既存の探索履歴が失われます"
        "（scope_summary が失われると classifier の out-of-scope-discard 判定が機能しなくなり、"
        "保守的フォールバックにより全ヒットが通常の伝播種別判定へ回ります）。",
        "完全な状態を復元する場合は bfs-state.json のバックアップから復元するか、re-discover を使用してください。",
    ]
    log_path_str = data.get("discovery_log") or ""
    if log_path_str:
        log_path = Path(log_path_str)
        if log_path.exists():
            _append_to_file(log_path, "\n> ⚠️ import 警告:\n" + "\n".join("> " + w for w in warnings) + "\n")
    print(json.dumps({"ok": True, "state": data["state"], "imported_from": str(md_path),
                      "warnings": warnings}, ensure_ascii=False))


# ---------------------------------------------------------------------------
# record-module / finish（継続パス B / C）
# ---------------------------------------------------------------------------

def _glob_module_files(repo_path: str, module_dir: str, exclude_patterns: list, include_extensions: list) -> list:
    base = Path(repo_path) / module_dir
    if not base.exists():
        return []
    results = []
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        rel = str(p.relative_to(repo_path))
        if any(pat.rstrip("/") in rel.split(os.sep) for pat in exclude_patterns if pat.endswith("/")):
            continue
        if include_extensions and not any(rel.endswith(ext) for ext in include_extensions):
            continue
        results.append(rel)
    return results


def cmd_record_module(args) -> None:
    state_path = Path(args.path)
    data = _load_state(state_path)
    files = _glob_module_files(data["repo_path"], args.module, data["exclude_patterns"], data["include_extensions"])
    confidence = args.confidence or "MODULE-LEVEL"
    added = 0
    for f in files:
        existing = data["confirmed_files"].get(f)
        if existing is None or CONFIDENCE_RANK.get(confidence, 0) > CONFIDENCE_RANK.get(existing["confidence"], 0):
            data["confirmed_files"][f] = {"wave": data["current_wave"], "confidence": confidence}
            added += 1
    data["confirmed_file_count"] = len(data["confirmed_files"])
    log_path = Path(data["discovery_log"])
    _append_to_file(log_path, f"\n- {args.today}: モジュール `{args.module}` を {confidence} として一括記録（{len(files)} ファイル）\n")
    _upsert_confirmed_files_section(log_path, data)
    _write_state(state_path, data)
    print(json.dumps({"ok": True, "module": args.module, "file_count": len(files), "newly_recorded": added}, ensure_ascii=False))


def cmd_finish(args) -> None:
    state_path = Path(args.path)
    data = _load_state(state_path)
    log_path = Path(data["discovery_log"])
    # PLAN-20260806 Phase 3 Stage 1 §4.5(c)（search を経ない状態遷移）。
    # 不正 --mode で _err する経路では state を書かないため、ここでの削除は disk へ反映されない。
    _drop_classify_timer(data)
    residual = list(data["frontier"]) + list(data.get("low_priority_frontier") or [])

    if args.mode == "complete":
        modules = set()
        unresolved = []
        for entry in residual:
            sym, scope = _parse_entry(entry)
            module = data["symbol_module"].get(entry)
            if module is None and scope:
                module = _module_dir_for_file(data["repo_path"], scope)
            if module:
                modules.add(module)
            else:
                unresolved.append(entry)
        _append_to_file(log_path, (
            "\n---\n## ⚠️ 継続パス B（モジュール一括記録）\n"
            "以下のモジュールは探索上限により個別ファイル単位の調査未完了。\n"
            "モジュール全体を影響可能性ありとして SPO に記録する。設計書・テスト工程での追加確認を推奨する。\n"
            f"対象モジュール: {', '.join(sorted(modules)) if modules else '(なし)'}\n"
        ))
        for m in sorted(modules):
            files = _glob_module_files(data["repo_path"], m, data["exclude_patterns"], data["include_extensions"])
            for f in files:
                existing = data["confirmed_files"].get(f)
                if existing is None or CONFIDENCE_RANK.get("MODULE-LEVEL", 0) > CONFIDENCE_RANK.get(existing["confidence"], 0):
                    data["confirmed_files"][f] = {"wave": data["current_wave"], "confidence": "MODULE-LEVEL"}
        if unresolved:
            _append_to_file(log_path, f"⚠️ モジュール未解決のため手動確認が必要なシンボル: {', '.join(unresolved)}\n")
        data["frontier"] = []
        data["low_priority_frontier"] = []
        data["state"] = "complete"
        data["confirmed_file_count"] = len(data["confirmed_files"])
        _upsert_confirmed_files_section(log_path, data)
        _write_state(state_path, data)
        print(json.dumps({"ok": True, "state": "complete", "mode": "complete", "modules": sorted(modules), "unresolved": unresolved}, ensure_ascii=False))
    elif args.mode == "out-of-scope":
        if not args.reason or not args.reason.strip():
            _err("--reason は必須です（継続パスCの根拠記録として discovery-log.md へ記録するため）")
        _append_to_file(log_path, (
            "\n---\n## 継続パス C（残存フロンティアをスコープ外として承認）\n"
            f"- {args.today}: 根拠: {args.reason}\n"
            f"- 残存フロンティア: {', '.join(residual) if residual else '(なし)'}\n"
        ))
        data["frontier"] = []
        data["low_priority_frontier"] = []
        data["state"] = "complete"
        _write_state(state_path, data)
        print(json.dumps({"ok": True, "state": "complete", "mode": "out-of-scope", "reason": args.reason}, ensure_ascii=False))
    else:
        _err(f"不正な --mode です: {args.mode}（complete または out-of-scope）")


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
    p_init.add_argument("--symbols", default="")
    p_init.add_argument("--today", required=True)
    p_init.add_argument("--cr", required=True)
    p_init.add_argument("--repo", required=True)
    p_init.add_argument("--exclude", default="")
    p_init.add_argument("--include-ext", default="")
    p_init.add_argument("--max-wave", type=int, default=10)
    p_init.add_argument("--max-files-per-module", type=int, default=10)
    p_init.add_argument("--module-catalog", default=None)
    p_init.add_argument("--backend", default="auto")
    p_init.add_argument("--hit-filter", default="conservative")  # PLAN-20260804 Phase 1b（conservative/off）
    p_init.add_argument("--scope-summary-file", default=None)  # PLAN-20260829: classifier scope 要約ファイル
    p_init.set_defaults(func=cmd_init)

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

    p_prune = sub.add_parser("prune")
    p_prune.add_argument("--path", required=True)
    p_prune.add_argument("--remove", required=True)
    p_prune.add_argument("--reason", required=True)
    p_prune.set_defaults(func=cmd_prune)

    p_merge = sub.add_parser("merge-frontier")
    p_merge.add_argument("--path", required=True)
    p_merge.add_argument("--symbols", required=True)
    p_merge.set_defaults(func=cmd_merge_frontier)

    p_rediscover = sub.add_parser("re-discover")
    p_rediscover.add_argument("--path", required=True)
    p_rediscover.add_argument("--symbols", required=True)
    p_rediscover.add_argument("--today", required=True)
    p_rediscover.set_defaults(func=cmd_re_discover)

    p_import = sub.add_parser("import")
    p_import.add_argument("--path", required=True)
    p_import.add_argument("--from", dest="from", default=None)
    p_import.add_argument("--repo-path", default=None)
    p_import.add_argument("--discovery-log", default=None)
    p_import.set_defaults(func=cmd_import)

    p_record = sub.add_parser("record-module")
    p_record.add_argument("--path", required=True)
    p_record.add_argument("--module", required=True)
    p_record.add_argument("--today", required=True)
    p_record.add_argument("--confidence", default=None)
    p_record.set_defaults(func=cmd_record_module)

    p_finish = sub.add_parser("finish")
    p_finish.add_argument("--path", required=True)
    p_finish.add_argument("--mode", required=True)
    p_finish.add_argument("--reason", default=None)
    p_finish.add_argument("--today", required=True)
    p_finish.set_defaults(func=cmd_finish)

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
