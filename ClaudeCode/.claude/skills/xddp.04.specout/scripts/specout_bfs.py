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

LLM とのプロトコル:
  1. `init` で BFS を開始（Wave 0 の initial_symbols は呼び出し元 LLM が CRS から抽出済みの値）
  2. `search` で現波の frontier を grep/rg 実行し `wave-{N}-hits.json` を出力
  3. LLM が hits の各行を意味判定し `wave-{N}-class.json` を作成
     （偽陽性判定・伝播種別・次波シンボル・含む関数/クラス・外部公開パターンの有無）
  4. `commit-wave` が classification を検証し、帳簿を更新して discovery-log.md に書き出す
  5. frontier が尽きるまで 2〜4 を繰り返す。`status` で再開・一時停止判定を確認する

Usage:
  python3 specout_bfs.py init --path STATE_JSON --repo-path REPO_PATH --discovery-log LOG_MD
      --symbols SYMS --today TODAY --cr CR --repo REPO [--exclude PATTERNS] [--include-ext EXTS]
      [--max-wave N] [--max-files-per-module N] [--module-catalog FILE]
  python3 specout_bfs.py search --path STATE_JSON --hits-out HITS_JSON
  python3 specout_bfs.py commit-wave --path STATE_JSON --hits HITS_JSON --classification CLASS_JSON --today TODAY
  python3 specout_bfs.py status --path STATE_JSON
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
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


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
        "symbol_module": {},
        "symbol_origin_map": {},
        "high_noise_symbols": [],
        "confirmed_files": {},
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
        "## grep未対応パターン（手動確認必要）\n"
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


def _confidence_label(kind: str) -> str:
    return "HIGH" if kind == "HIGH複合" else "MEDIUM"


def _upsert_confirmed_files_section(log_path: Path, data: dict) -> None:
    """Step 3「確定ファイル一覧の書き出し」相当。commit-wave/finish のたびに全体を再構築する。"""
    heading = "## 確定した波及ファイル一覧（Documentation チェックリスト）"
    section = [heading, "", "| ファイル | 発見波 | 最高確信度 | ドキュメント化 |", "|---|---|---|---|"]
    for path_, info in sorted(data["confirmed_files"].items()):
        section.append(f"| {path_} | Wave {info['wave']} | {info['confidence']} | ⬜ 未 |")
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
    data.update({
        "repo_path": args.repo_path,
        "discovery_log": args.discovery_log,
        "cr": args.cr,
        "repo": args.repo,
        "frontier": symbols,
        "exclude_patterns": _split_csv(args.exclude),
        "include_extensions": _split_csv(args.include_ext),
        "max_wave_depth": args.max_wave,
        "max_files_per_module": args.max_files_per_module,
        "module_catalog_file": args.module_catalog or "",
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
    print(json.dumps({"ok": True, "current_wave": 0, "frontier_count": len(symbols)}, ensure_ascii=False))


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
                cells = [c.strip() for c in line.split("|")[1:-1]]
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
    try:
        rel = os.path.relpath(file_path, repo_path)
    except ValueError:
        rel = file_path
    parts = Path(rel).parts
    if len(parts) <= 1:
        return "_root"
    return parts[0]


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


def _run_grep_batch(pattern: str, scope, exclude_opts_grep, repo_path: str) -> list:
    """`grep -rn -E pattern [scope|repo_path]` を実行し (file, line, content) を返す。"""
    target = scope if scope else repo_path
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
        target = scope if scope else repo_path
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


def _pause_for_wave_limit(data: dict, state_path: Path, log_path: Path) -> dict:
    data["limit_reached_count"] += 1
    if data["limit_reached_count"] == 1:
        data["state"] = "paused-at-limit"
    else:
        data["state"] = "paused-at-limit-2nd"
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
    state_path = Path(args.path)
    data = _load_state(state_path)
    if data["state"] == "complete":
        _err("BFS は既に complete 状態です（search 不要）")
    if data["state"] in ("paused-at-limit", "paused-at-limit-2nd"):
        _err(f"BFS は {data['state']} で一時停止中です。prune / finish で継続パスを選択してから search してください")

    if data["current_wave"] > data["max_wave_depth"]:
        result = _pause_for_wave_limit(data, state_path, Path(data["discovery_log"]))
        print(json.dumps(result, ensure_ascii=False))
        return

    module_map = data.get("module_priority_map") or {}
    symbol_module = data.get("symbol_module") or {}
    frontier = list(data["frontier"])
    low = list(data.get("low_priority_frontier") or [])

    if data.get("module_priority_computed") and module_map:
        this_wave, new_low = [], []
        for entry in frontier:
            module = symbol_module.get(entry)
            prio = module_map.get(module, "HIGH") if module else "HIGH"
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

    rg_path = shutil.which("rg")
    exclude_grep = _build_exclude_include_grep(data["exclude_patterns"], data["include_extensions"])
    exclude_rg = _build_exclude_include_rg(data["exclude_patterns"], data["include_extensions"])
    repo_path = data["repo_path"]

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

    if high_symbols:
        if rg_path:
            patterns = [r"\b" + escape_symbol(s) + r"\b" for s in high_symbols]
            rows = _run_rg_patternfile(patterns, None, exclude_rg, repo_path)
            cmd_id = _next_cmd_id()
            commands.append({"command_id": cmd_id, "kind": "HIGH複合", "pattern": "|".join(patterns), "scope": "全域", "hit_count": len(rows)})
            for file_, line_no, content in rows:
                sym = _matching_symbol(content, high_symbols)
                hits.append({"line_id": _next_line_id(), "command_id": cmd_id, "symbol": sym, "scope_file": None,
                             "file": _rel_file(file_, repo_path), "line_no": line_no, "matched_text": content})
        else:
            for batch in _batch_symbols(high_symbols):
                pattern = r"\b(" + "|".join(escape_symbol(s) for s in batch) + r")\b"
                rows = _run_grep_batch(pattern, None, exclude_grep, repo_path)
                cmd_id = _next_cmd_id()
                commands.append({"command_id": cmd_id, "kind": "HIGH複合", "pattern": pattern, "scope": "全域", "hit_count": len(rows)})
                for file_, line_no, content in rows:
                    sym = _matching_symbol(content, batch)
                    hits.append({"line_id": _next_line_id(), "command_id": cmd_id, "symbol": sym, "scope_file": None,
                                 "file": _rel_file(file_, repo_path), "line_no": line_no, "matched_text": content})

    for scope in sorted(medium_by_scope.keys()):
        syms = medium_by_scope[scope]
        pattern = r"\b(" + "|".join(escape_symbol(s) for s in syms) + r")\b"
        if rg_path:
            rows = _run_rg_patternfile([r"\b" + escape_symbol(s) + r"\b" for s in syms], scope, exclude_rg, repo_path)
        else:
            rows = _run_grep_batch(pattern, scope, exclude_grep, repo_path)
        cmd_id = _next_cmd_id()
        commands.append({"command_id": cmd_id, "kind": "MEDIUM", "pattern": pattern, "scope": scope, "hit_count": len(rows)})
        for file_, line_no, content in rows:
            sym = _matching_symbol(content, syms)
            hits.append({"line_id": _next_line_id(), "command_id": cmd_id, "symbol": sym, "scope_file": scope,
                         "file": _rel_file(file_, repo_path), "line_no": line_no, "matched_text": content})

    frontier_medium_scopes = {}
    for symbol, scope in medium_entries:
        frontier_medium_scopes.setdefault(symbol, []).append(scope)

    hits_payload = {
        "wave": wave,
        "commands": commands,
        "hits": hits,
        "frontier_medium_scopes": frontier_medium_scopes,
        "searched_frontier": this_wave,
    }
    out_path = Path(args.hits_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(hits_payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    data["wave_write_complete"] = False
    data["low_priority_frontier"] = low
    _write_state(state_path, data)

    print(json.dumps({
        "ok": True, "wave": wave, "hits_file": str(out_path), "hit_count": len(hits),
        "commands": [{"command_id": c["command_id"], "hit_count": c["hit_count"]} for c in commands],
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
    noisy_keys = {k for k, files in files_by_key.items() if len(files) > data["max_files_per_module"]}

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

    # 次波シンボルの module 記録（優先度マップがある場合の次波振り分けに使用）
    if data.get("module_priority_computed"):
        for entry in next_frontier:
            if entry in data["symbol_module"]:
                continue
            for h in hits:
                if any(ns == entry for ns in (class_by_id[h["line_id"]].get("next_symbols") or [])):
                    data["symbol_module"][entry] = _module_dir_for_file(data["repo_path"], h["file"])
                    break

    # 高ノイズシンボルの記録
    newly_noisy = [k for k in noisy_keys if k not in data["high_noise_symbols"]]
    data["high_noise_symbols"].extend(newly_noisy)

    # --- discovery-log.md への書き出し ---
    log_lines = [f"## Wave {wave}", "", "### 実行コマンド一覧",
                 "| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |",
                 "|---|---|---|---|---|"]
    for c in commands:
        log_lines.append(f"| {c['command_id']} | {c['kind']} | `{c['pattern']}` | {c['scope']} | {c['hit_count']} |")
    log_lines.append("")
    excl = ",".join(data["exclude_patterns"]) if data["exclude_patterns"] else "(なし)"
    log_lines.append(f"**除外:** {excl}")
    log_lines.append("")
    log_lines.append("| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | 含む関数/クラス（ファイル読み込みで確認） | "
                      "伝播種別 | 確信度 | Wave {} 追加シンボル | 派生元 |".format(wave + 1))
    log_lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for row in rows:
        log_lines.append("| " + " | ".join(row) + " |")
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
    log_lines.append("| コマンドID | ヒット行数（生） | 記録行数 | 一致 |")
    log_lines.append("|---|---|---|---|")
    for c in commands:
        recorded = sum(1 for h in hits if h["command_id"] == c["command_id"])
        if c["command_id"] in discarded_command_ids:
            mark = "➖ 廃棄（ケースA, 次波でHIGH昇格済）"
        elif c["hit_count"] == recorded:
            mark = "✅"
        else:
            mark = f"⚠️ {c['command_id']} 件数不一致（ヒット{c['hit_count']}件/記録{recorded}件）"
        log_lines.append(f"| {c['command_id']} | {c['hit_count']} | {recorded} | {mark} |")
    log_lines.append("")

    if newly_noisy:
        log_lines.append("## 高ノイズシンボル（上限超過のため波及停止）")
        log_lines.append("| シンボル | 発見波 | 発見ファイル数 | 備考 |")
        log_lines.append("|---|---|---|---|")
        for k in newly_noisy:
            sym, scope = _parse_entry(k)
            log_lines.append(f"| `{sym}` | Wave {wave} | {len(files_by_key[k])} | 手動確認推奨 |")
        log_lines.append("")

    if case_rows:
        log_lines.append("## 同名 MEDIUM シンボル・異スコープ重複ログ（発生時のみ記録）")
        log_lines.append("| Wave | シンボル | 検出スコープ一覧 | ケース | 処置 |")
        log_lines.append("|---|---|---|---|---|")
        for sym, scopes, case_label, action in case_rows:
            log_lines.append(f"| Wave {wave} | `{sym}` | {', '.join('`' + s + '`' for s in scopes)} | {case_label} | {action} |")
        log_lines.append("")

    _append_to_file(log_path, "\n".join(log_lines))

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
    print(json.dumps({"ok": True, **data}, ensure_ascii=False))


def cmd_set_state(args) -> None:
    if args.state not in VALID_STATES:
        _err(f"不正な状態です: {args.state}（有効値: {', '.join(sorted(VALID_STATES))}）")
    state_path = Path(args.path)
    data = _load_state(state_path)
    data["state"] = args.state
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
    print(json.dumps({"ok": True, "state": data["state"], "imported_from": str(md_path)}, ensure_ascii=False))


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
    p_init.set_defaults(func=cmd_init)

    p_search = sub.add_parser("search")
    p_search.add_argument("--path", required=True)
    p_search.add_argument("--hits-out", required=True)
    p_search.set_defaults(func=cmd_search)

    p_commit = sub.add_parser("commit-wave")
    p_commit.add_argument("--path", required=True)
    p_commit.add_argument("--hits", required=True)
    p_commit.add_argument("--classification", required=True)
    p_commit.add_argument("--today", required=True)
    p_commit.set_defaults(func=cmd_commit_wave)

    p_status = sub.add_parser("status")
    p_status.add_argument("--path", required=True)
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
