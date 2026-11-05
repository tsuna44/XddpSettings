"""promote.py — xddp-close Step C2〜C7 成果物昇格 CLI

`{XDDP_DIR}/latest-specs/**` → `{DOCS}/...` への成果物昇格・
lessons-learned/CRS/TSP・TRS/project-rulebook/improvement-backlog の昇格・cross/ 破壊的変更検出を
一括担当する（AI_INDEX.md は書かない。close の Step D2 で `ai_index.py build` が作り直す）。旧 `xddp-close-promote-agent.md`（LLM が Read→Write で全文転写）を置き換える決定的処理
（判断業務を含まない。設計根拠は docs/adr/ADR-0013-close-promote-script.md 参照）。

Usage:
  python3 promote.py run \
    --cr CR --cr-path CR_PATH --xddp-dir XDDP_DIR --docs DOCS \
    --repos-keys r1,r2 --affected-repos r1,r2 [--has-cross] [--is-multi] \
    --today YYYY-MM-DD --lessons-file LESSONS_FILE \
    --output-file OUTPUT_FILE

  python3 promote.py extract-ll --cr CR --lessons-file LESSONS_FILE --out OUT
    今の CR の知見ログ（LL）のエントリだけを OUT に書き出す（Step C3.5・C3.6 のエージェントの入力。
    `run` の前に実行する）。0件なら OUT を書かず、前回の OUT が残っていれば消す。

Output: run は成功時に stdout へ JSON 1オブジェクト（{"ok": true, ...}）を出力し、OUTPUT_FILE に
        人向け保留事項レポートを書き込む。extract-ll は stdout へ JSON 1行
        （{"count": N, "unparsed": [{"id", "reason": heading|no-meta|multi-meta}],
        "dropped": [{"id", "reason": cr-meta|cut}], "out": パス|null, "removed": bool}）を出力する。
        失敗時は exit code 非0 + stderr にメッセージ。
"""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "xddp-common" / "scripts"))
import docs_layout as layout  # noqa: E402

# ---------------------------------------------------------------------------
# 共通ユーティリティ
# ---------------------------------------------------------------------------


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def _split(raw: str) -> list:
    return [s.strip() for s in raw.split(",") if s.strip()]


def _split_row(line: str) -> list:
    """Markdown テーブル行をセルへ分割する（`\\|` エスケープ対応。chd_sp_coverage.py と同一方針）。"""
    if "|" not in line:
        return []
    return [p.strip().replace(r"\|", "|") for p in re.split(r"(?<!\\)\|", line)[1:-1]]


def _read_lines(path: Path) -> list:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").split("\n")


def _write_lines(path: Path, lines: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# ---------------------------------------------------------------------------
# Step C2: Promote Approved Specs → DOCS_DIR
# ---------------------------------------------------------------------------


def _copy_tree(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)


def _init_repo_results(repos) -> dict:
    return {repo: {"ok": True, "errors": []} for repo in repos}


def _record_failure(repo_results: dict, repo: str, step: str, error) -> None:
    entry = repo_results.setdefault(repo, {"ok": True, "errors": []})
    entry["ok"] = False
    entry["errors"].append(f"{step}: {error}")


def promote_specs(xddp_dir: Path, docs: Path, affected_repos: list, has_cross: bool,
                   repo_results: dict) -> list:
    """repo別・cross/・system/ の昇格コピーを行う。

    repo 単位で例外を捕捉し、1 repo の失敗が他 repo の処理を止めないようにする
    （test-fixtures/scratch-workspace/README.md の ENOTDIR 実機シナリオに対応。レビュー指摘#10）。
    `repo_results`（{repo: {"ok": bool, "errors": [str]}}）は呼び出し元が用意し、本関数が
    破壊的に更新する（Step C2〜C7 全体で1つの dict を共有し、repo 単位の失敗を集約するため）。

    戻り値: deletion_candidates のリスト。
    """
    latest_specs = Path(xddp_dir) / "latest-specs"
    deletion_candidates = []

    for repo in affected_repos:
        src = layout.latest_specs_root(latest_specs, repo)
        dst = layout.docs_specs_root(docs, repo)
        try:
            if src.exists():
                _copy_tree(src, dst)
        except Exception as e:  # noqa: BLE001 — per-repo 失敗を分離して継続するため意図的に広く捕捉
            _record_failure(repo_results, repo, "C2", e)
            continue

        # 削除伝播（repo モジュールディレクトリ）
        if dst.exists() and src.exists():
            existing_modules = set(layout.module_names(dst))
            current_modules = set(layout.subdir_names(src))
            for missing in sorted(existing_modules - current_modules):
                deletion_candidates.append(str(dst / missing))

    cross_src = layout.latest_specs_root(latest_specs, layout.CROSS_AREA)
    if has_cross and cross_src.exists():
        try:
            _copy_tree(cross_src, layout.docs_specs_root(docs, layout.CROSS_AREA))
            repo_results.setdefault("cross", {"ok": True, "errors": []})
        except Exception as e:  # noqa: BLE001
            _record_failure(repo_results, "cross", "C2", e)

    system_src = layout.latest_specs_root(latest_specs, layout.SYSTEM_AREA)
    if system_src.exists():
        try:
            _copy_tree(system_src, layout.docs_specs_root(docs, layout.SYSTEM_AREA))
            repo_results.setdefault("system", {"ok": True, "errors": []})
            uc_dst = layout.docs_usecases_dir(docs)
            uc_src = layout.latest_usecases_dir(latest_specs)
            if uc_dst.exists():
                existing_uc = set(layout.subdir_names(uc_dst))
                current_uc = set(layout.subdir_names(uc_src))
                for missing in sorted(existing_uc - current_uc):
                    deletion_candidates.append(str(uc_dst / missing))
        except Exception as e:  # noqa: BLE001
            _record_failure(repo_results, "system", "C2", e)

    return deletion_candidates


# ---------------------------------------------------------------------------
# Step C3: Promote Lessons Learned Log
# ---------------------------------------------------------------------------

LL_ENTRY_RE = re.compile(r"^### (LL-[^\s：]+)：")
LL_META_RE = re.compile(
    r"\*\*CR：\*\*\s*(?P<cr>\S+)\s*／\s*\*\*工程：\*\*\s*(?P<phase>[^／]+?)\s*／\s*"
    r"\*\*repo：\*\*\s*(?P<repo>[^／]+?)\s*／\s*\*\*タグ：\*\*\s*(?P<tags>.+)$")
# 見出しの崩れた LL エントリ（`### LL-005: …`・`## LL-005：…`・`###LL-005：…` 等）
LL_BROKEN_HEADING_RE = re.compile(r"^#{1,6}\s*LL-")
ANY_HEADING_RE = re.compile(r"^#{1,6}\s")
# エントリを終える見出し（エントリの見出し `###` と同じかより上の水準）
END_HEADING_RE = re.compile(r"^#{1,3}\s")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
LL_META_WINDOW = 5
LL_ID_MAX = 40


def _heading_label(line: str) -> str:
    """見出しの行から行頭の `#` と空白を除いた文字列（先頭40文字まで）。"""
    return re.sub(r"^\s*#*\s*", "", line).strip()[:LL_ID_MAX]


class _Fence:
    """行頭（空白3つまで）の ``` / ~~~ のフェンスの開閉を追う。"""

    def __init__(self):
        self.char = None

    def feed(self, line: str) -> bool:
        """line がフェンスの内側（開閉の行を含む）なら True を返し、状態を進める。"""
        m = FENCE_RE.match(line)
        if self.char is None:
            if m:
                self.char = m.group(1)[0]
                return True
            return False
        if m and m.group(1)[0] == self.char and line.strip() == line.strip()[0] * len(line.strip()):
            self.char = None
        return True

    def reset(self):
        self.char = None


def _is_heading_line(line: str) -> bool:
    return bool(LL_ENTRY_RE.match(line) or LL_BROKEN_HEADING_RE.match(line)
                or ANY_HEADING_RE.match(line))


def _window_has_meta(lines: list, idx: int) -> bool:
    """idx の見出しの窓（5行まで・次の見出しの手前まで）にフェンスの外のメタ行があるか。"""
    fence = _Fence()
    for j in range(idx, min(idx + LL_META_WINDOW, len(lines))):
        line = lines[j]
        if j > idx:
            if LL_ENTRY_RE.match(line):
                break
            if fence.char is None and _is_heading_line(line):
                break
        if fence.feed(line):
            continue
        if LL_META_RE.search(line):
            return True
    return False


def _split_ll_blocks(lines: list):
    """LL のファイルをエントリと落とした塊に分ける。

    戻り値: (entries, chunks)。entries は行のリストのリスト。chunks は
    (行のリスト, 直前のエントリの index または None) のリスト（エントリにしない塊。
    最初のエントリより前の部分を含む）。
    """
    entries = []
    chunks = []
    current = []
    current_is_entry = False
    fence = _Fence()

    def _close():
        if current_is_entry:
            entries.append(current)
        elif current:
            chunks.append((current, len(entries) - 1 if entries else None))

    for idx, line in enumerate(lines):
        if LL_ENTRY_RE.match(line):
            _close()
            current, current_is_entry = [line], True
            fence.reset()
            continue
        if fence.char is not None:
            fence.feed(line)
            current.append(line)
            continue
        if fence.feed(line):
            current.append(line)
            continue
        if LL_BROKEN_HEADING_RE.match(line):
            _close()
            current, current_is_entry = [line], True
            continue
        if ANY_HEADING_RE.match(line):
            if _window_has_meta(lines, idx):
                _close()
                current, current_is_entry = [line], True
                continue
            if END_HEADING_RE.match(line):
                _close()
                current, current_is_entry = [line], False
                continue
        current.append(line)
    _close()
    return entries, chunks


def _meta_lines_outside_fence(block: list) -> list:
    fence = _Fence()
    found = []
    for line in block:
        if fence.feed(line):
            continue
        m = LL_META_RE.search(line)
        if m:
            found.append(m)
    return found


def _ll_entry_meta(entry: list):
    """エントリの (entry_id, meta_match または None, reason または None) を返す。

    reason: `heading`＝見出しが `### LL-{NNN}：` の書式でない、`multi-meta`＝フェンスの外に
    メタ行が2つ以上ある、`no-meta`＝先頭5行にメタ行が無い。
    """
    header = entry[0]
    m_id = LL_ENTRY_RE.match(header)
    if not m_id:
        return _heading_label(header), None, "heading"
    entry_id = m_id.group(1)
    if len(_meta_lines_outside_fence(entry)) >= 2:
        return entry_id, None, "multi-meta"
    for line in entry[:LL_META_WINDOW]:
        m = LL_META_RE.search(line)
        if m:
            return entry_id, m, None
    return entry_id, None, "no-meta"


def _split_ll_entries(lines: list, cr=None):
    """エントリのリストと、`cr` 指定時は落とした塊のうち人に示すもの（dropped）を返す。

    dropped の要素は {"id": 見出しの文字列, "reason": "cr-meta" | "cut"}。
    `cr-meta`＝塊のフェンスの外に `CR：` 欄が cr のメタ行がある、`cut`＝直前のエントリが cr のエントリ。
    """
    entries, chunks = _split_ll_blocks(lines)
    dropped = []
    if cr is None:
        return entries, dropped
    for chunk, prev in chunks:
        reason = None
        if any(m.group("cr") == cr for m in _meta_lines_outside_fence(chunk)):
            reason = "cr-meta"
        elif prev is not None:
            _, prev_meta, _ = _ll_entry_meta(entries[prev])
            if prev_meta is not None and prev_meta.group("cr") == cr:
                reason = "cut"
        if reason:
            label = next((_heading_label(l) for l in chunk if l.strip()), "")
            dropped.append({"id": label, "reason": reason})
    return entries, dropped


def extract_ll(lessons_file: Path, cr: str, out: Path) -> dict:
    """今の CR の LL のエントリだけを out に書く（Step C3.5・C3.6 のエージェントの入力）。

    0件なら out を書かず、前回の out が残っていれば消す。
    """
    lines = _read_lines(lessons_file)
    entries, dropped = _split_ll_entries(lines, cr)
    selected = []
    unparsed = []
    for entry in entries:
        entry_id, meta, reason = _ll_entry_meta(entry)
        if meta is None:
            unparsed.append({"id": entry_id, "reason": reason})
            continue
        if meta.group("cr") == cr:
            selected.append(entry)

    removed = False
    out_written = None
    if selected:
        body = []
        for entry in selected:
            body.extend(entry)
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name(out.name + ".tmp")
        _write_lines(tmp, body)
        os.replace(tmp, out)
        out_written = str(out)
    elif out.exists():
        out.unlink()
        removed = True
    return {"count": len(selected), "unparsed": unparsed, "dropped": dropped,
            "out": out_written, "removed": removed}


def promote_lessons_learned(lessons_file: Path, docs: Path, cr: str, has_cross: bool,
                             repo_results: dict) -> list:
    """今回 CR の LL エントリを repo: タグでファイル振り分けする。戻り値: 要確認LL（repo:unknown）一覧。

    repo 単位で書き込みを try/except し、1 repo の失敗（例: ENOTDIR）が他 repo の振り分けを
    止めないようにする（promote_specs と同じ方針。レビュー指摘#10 相当）。
    """
    lines = _read_lines(lessons_file)
    entries, _ = _split_ll_entries(lines)
    unresolved = []

    by_repo = {}
    for entry in entries:
        header = entry[0]
        entry_id, meta_match, _ = _ll_entry_meta(entry)
        if meta_match is None:
            continue
        if meta_match.group("cr") != cr:
            continue
        repo = meta_match.group("repo").strip()
        if repo == "unknown":
            title = header.split("：", 1)[1] if "：" in header else header
            unresolved.append(f"{entry_id}：{title}")
            continue
        by_repo.setdefault(repo, []).append(entry)

    for repo, repo_entries in by_repo.items():
        if repo == "cross":
            if not has_cross:
                continue
            target = docs / "cross" / "knowledge" / "lessons-learned.md"
        else:
            target = docs / repo / "knowledge" / "lessons-learned.md"
        try:
            target_lines = _read_lines(target)
            if not target_lines:
                target_lines = [f"# 知見ログ: {repo}", "> xddp-close が CR クローズ時に自動追記します。", ""]
            existing_text = "\n".join(target_lines)
            appended = False
            for entry in repo_entries:
                entry_id_m = LL_ENTRY_RE.match(entry[0])
                entry_id = entry_id_m.group(1) if entry_id_m else None
                if entry_id and f"### {entry_id}：" in existing_text:
                    continue
                if target_lines and target_lines[-1].strip() != "":
                    target_lines.append("")
                target_lines.extend(entry)
                if target_lines[-1].strip() != "":
                    target_lines.append("")
                target_lines.append("---")
                appended = True
            if appended:
                _write_lines(target, target_lines)
        except Exception as e:  # noqa: BLE001 — per-repo 失敗を分離して継続するため意図的に広く捕捉
            _record_failure(repo_results, repo, "C3", e)

    return unresolved


# ---------------------------------------------------------------------------
# Step C4〜C7: 既存ファイルの存在チェック→コピー
# ---------------------------------------------------------------------------


def promote_crs(cr_path: Path, docs: Path, cr: str, affected_repos: list, has_cross: bool,
                 repo_results: dict) -> None:
    src = Path(cr_path) / "03_change-requirements" / f"CRS-{cr}.md"
    if not src.exists():
        return
    for repo in affected_repos:
        try:
            dst = docs / repo / "crs"
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst / f"CRS-{cr}.md")
        except Exception as e:  # noqa: BLE001
            _record_failure(repo_results, repo, "C4", e)
    if has_cross:
        try:
            dst = docs / "cross" / "crs"
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst / f"CRS-{cr}.md")
        except Exception as e:  # noqa: BLE001
            _record_failure(repo_results, "cross", "C4", e)


def promote_test_artifacts(cr_path: Path, docs: Path, cr: str, affected_repos: list,
                            has_cross: bool, repo_results: dict) -> None:
    for repo in affected_repos:
        try:
            test_target = docs / repo / "test"
            tsp = Path(cr_path) / "09_test-spec" / repo / f"TSP-{cr}.md"
            if tsp.exists():
                test_target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(tsp, test_target / tsp.name)
            trs_dir = Path(cr_path) / "10_test-results" / repo
            if trs_dir.exists():
                for trs in sorted(trs_dir.glob(f"TRS-{cr}-*.md")):
                    test_target.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(trs, test_target / trs.name)
        except Exception as e:  # noqa: BLE001
            _record_failure(repo_results, repo, "C5", e)
    if has_cross:
        try:
            test_target = docs / "cross" / "test"
            tsp = Path(cr_path) / "09_test-spec" / "cross" / f"TSP-{cr}-cross.md"
            if tsp.exists():
                test_target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(tsp, test_target / tsp.name)
            trs_dir = Path(cr_path) / "10_test-results" / "cross"
            if trs_dir.exists():
                for trs in sorted(trs_dir.glob(f"TRS-{cr}-*.md")):
                    test_target.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(trs, test_target / trs.name)
        except Exception as e:  # noqa: BLE001
            _record_failure(repo_results, "cross", "C5", e)


def promote_rulebooks(xddp_dir: Path, docs: Path, repos_keys: list, has_cross: bool,
                       repo_results: dict, global_errors: list) -> None:
    common = Path(xddp_dir) / "project-rulebook.md"
    if common.exists():
        try:
            docs.mkdir(parents=True, exist_ok=True)
            shutil.copy2(common, docs / "project-rulebook.md")
        except Exception as e:  # noqa: BLE001
            global_errors.append(f"C6(project-rulebook.md): {e}")
    for repo in repos_keys:
        repo_rb = Path(xddp_dir) / f"project-rulebook-{repo}.md"
        if repo_rb.exists():
            try:
                (docs / repo).mkdir(parents=True, exist_ok=True)
                shutil.copy2(repo_rb, docs / repo / "project-rulebook.md")
            except Exception as e:  # noqa: BLE001
                _record_failure(repo_results, repo, "C6", e)
    if has_cross:
        cross_rb = Path(xddp_dir) / "project-rulebook-cross.md"
        if cross_rb.exists():
            try:
                (docs / "cross").mkdir(parents=True, exist_ok=True)
                shutil.copy2(cross_rb, docs / "cross" / "project-rulebook.md")
            except Exception as e:  # noqa: BLE001
                _record_failure(repo_results, "cross", "C6", e)


def promote_backlog(xddp_dir: Path, docs: Path) -> bool:
    src = Path(xddp_dir) / "improvement-backlog.md"
    if not src.exists():
        return False
    docs.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, docs / "improvement-backlog.md")
    return True


# ---------------------------------------------------------------------------
# cross/ 破壊的変更検出
# ---------------------------------------------------------------------------

CROSS_SUMMARY_HEADING_RE = re.compile(r"^#{2,3}\s*(?:\d+\.\s*)?インタフェース変更サマリー?\s*$")


def detect_breaking_changes(cr_path: Path, cr: str, has_cross: bool):
    """cross CHD の「インタフェース変更サマリ」表から breaking 変更を検出する。

    戻り値: (breaking_found: bool|None, interfaces: list, parseable: bool)
    `parseable=False` は breaking 列が存在しない・パースできないことを示す（fail-loud。
    無警告で「なし」扱いにしてはならない。3.1 参照）。
    """
    if not has_cross:
        return False, [], True
    chd_path = Path(cr_path) / "06_design" / "cross" / f"CHD-{cr}-cross.md"
    if not chd_path.exists():
        return False, [], True
    lines = chd_path.read_text(encoding="utf-8").split("\n")
    heading_idx = None
    for i, line in enumerate(lines):
        if CROSS_SUMMARY_HEADING_RE.match(line.strip()):
            heading_idx = i
            break
    if heading_idx is None:
        return None, [], False

    table_start = None
    j = heading_idx + 1
    while j < len(lines):
        s = lines[j].strip()
        if s.startswith("|"):
            table_start = j
            break
        if re.match(r"^#{2,3}\s", s):
            break
        j += 1
    if table_start is None:
        return None, [], False

    header_cells = _split_row(lines[table_start])
    breaking_idx = None
    iface_idx = None
    for idx, cell in enumerate(header_cells):
        if cell.strip().lower() == "breaking" and breaking_idx is None:
            breaking_idx = idx
        if "インタフェース" in cell and iface_idx is None:
            iface_idx = idx
    if breaking_idx is None or iface_idx is None:
        return None, [], False

    breaking_interfaces = []
    k = table_start + 2
    while k < len(lines) and lines[k].strip().startswith("|"):
        cells = _split_row(lines[k])
        if len(cells) > max(breaking_idx, iface_idx):
            if cells[breaking_idx].strip().lower() == "true":
                breaking_interfaces.append(cells[iface_idx].strip())
        k += 1
    return (len(breaking_interfaces) > 0), breaking_interfaces, True


def append_breaking_warning(target: Path, cr: str, interfaces: list) -> None:
    lines = _read_lines(target)
    marker = f"### 破壊的変更警告（{cr}）"
    for line in lines:
        if line.strip() == marker:
            return
    if not lines:
        lines = []
    if lines and lines[-1].strip() != "":
        lines.append("")
    lines.append(marker)
    lines.append("")
    for iface in interfaces:
        lines.append(f"⚠️ 破壊的インタフェース変更あり。{iface}の旧バージョンへの依存コードを確認すること。")
    lines.append("")
    lines.append("---")
    _write_lines(target, lines)


# ---------------------------------------------------------------------------
# Output Format
# ---------------------------------------------------------------------------


def write_output_file(output_file: Path, cr: str, repo_results: dict, affected_repos: list,
                       unresolved_ll: list, breaking_found, breaking_interfaces: list,
                       breaking_parseable: bool, deletion_candidates: list,
                       global_errors: list) -> None:
    lines = ["# Step C2-C7 保留事項", f"CR: {cr}", ""]
    lines.append("## リポジトリ別処理結果一覧")
    for repo in affected_repos:
        result = repo_results.get(repo, {"ok": True, "errors": []})
        if result["ok"]:
            lines.append(f"- {repo}: 成功")
        else:
            lines.append(f"- {repo}: 失敗（{'; '.join(result['errors'])}）")
    if global_errors:
        lines.append("")
        lines.append("**共通ファイルの昇格エラー（repo 非依存）:**")
        for err in global_errors:
            lines.append(f"- {err}")
    lines.append("")

    lines.append("## 要確認LL一覧（repo:unknown スキップ分）")
    if unresolved_ll:
        for entry in unresolved_ll:
            lines.append(f"- {entry} — repo: unknown")
    else:
        lines.append("なし")
    lines.append("")

    lines.append("## 破壊的変更フラグ・対象インタフェース一覧")
    if not breaking_parseable:
        lines.append("- 破壊的変更: 判定不能（cross CHD の「インタフェース変更サマリ」表に breaking 列が"
                      "見つからないか、パースできませんでした。手動で確認してください）")
    else:
        lines.append(f"- 破壊的変更: {'あり' if breaking_found else 'なし'}")
        lines.append(f"- 対象インタフェース: {', '.join(breaking_interfaces) if breaking_interfaces else 'なし'}")
    lines.append("")

    lines.append("## 削除候補一覧（system/use-cases・repo モジュールディレクトリ）")
    if deletion_candidates:
        for d in deletion_candidates:
            lines.append(f"- {d}")
    else:
        lines.append("なし")
    lines.append("")

    _write_lines(output_file, lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_run(args) -> None:
    cr_path = Path(args.cr_path)
    xddp_dir = Path(args.xddp_dir)
    docs = Path(args.docs)
    repos_keys = _split(args.repos_keys)
    affected_repos = _split(args.affected_repos)

    # Step C2〜C7 全体で1つの repo_results を共有し、repo 単位の失敗を全ステップにわたって集約する
    # （1 repo の失敗が他 repo の処理を止めない・かつ同一 repo の複数ステップ失敗も漏れなく記録する。
    # レビュー指摘#10: test-fixtures/scratch-workspace/README.md の ENOTDIR 実機シナリオ）。
    repo_results = _init_repo_results(affected_repos)
    global_errors = []

    deletion_candidates = promote_specs(xddp_dir, docs, affected_repos, args.has_cross, repo_results)

    breaking_found, breaking_interfaces, breaking_parseable = detect_breaking_changes(
        cr_path, args.cr, args.has_cross)

    unresolved_ll = promote_lessons_learned(
        Path(args.lessons_file), docs, args.cr, args.has_cross, repo_results)

    if breaking_parseable and breaking_found:
        for repo in affected_repos:
            try:
                append_breaking_warning(docs / repo / "knowledge" / "lessons-learned.md", args.cr,
                                         breaking_interfaces)
            except Exception as e:  # noqa: BLE001
                _record_failure(repo_results, repo, "C2(破壊的変更警告)", e)
        if args.has_cross:
            try:
                append_breaking_warning(docs / "cross" / "knowledge" / "lessons-learned.md", args.cr,
                                         breaking_interfaces)
            except Exception as e:  # noqa: BLE001
                _record_failure(repo_results, "cross", "C2(破壊的変更警告)", e)

    promote_crs(cr_path, docs, args.cr, affected_repos, args.has_cross, repo_results)
    promote_test_artifacts(cr_path, docs, args.cr, affected_repos, args.has_cross, repo_results)
    promote_rulebooks(xddp_dir, docs, repos_keys, args.has_cross, repo_results, global_errors)
    try:
        backlog_promoted = promote_backlog(xddp_dir, docs)
    except Exception as e:  # noqa: BLE001
        backlog_promoted = False
        global_errors.append(f"C7(improvement-backlog.md): {e}")

    write_output_file(
        Path(args.output_file), args.cr, repo_results, affected_repos, unresolved_ll,
        breaking_found, breaking_interfaces, breaking_parseable, deletion_candidates,
        global_errors)

    print(json.dumps({
        "ok": True,
        "repo_results": repo_results,
        "unresolved_ll": unresolved_ll,
        "breaking_found": breaking_found,
        "breaking_parseable": breaking_parseable,
        "deletion_candidates": deletion_candidates,
        "backlog_promoted": backlog_promoted,
        "global_errors": global_errors,
        "output_file": str(args.output_file),
    }, ensure_ascii=False))


def cmd_extract_ll(args) -> None:
    result = extract_ll(Path(args.lessons_file), args.cr, Path(args.out))
    print(json.dumps(result, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run")
    p_run.add_argument("--cr", required=True)
    p_run.add_argument("--cr-path", required=True)
    p_run.add_argument("--xddp-dir", required=True)
    p_run.add_argument("--docs", required=True)
    p_run.add_argument("--repos-keys", required=True)
    p_run.add_argument("--affected-repos", required=True)
    p_run.add_argument("--has-cross", action="store_true")
    p_run.add_argument("--is-multi", action="store_true")
    p_run.add_argument("--today", required=True)
    p_run.add_argument("--lessons-file", required=True)
    p_run.add_argument("--output-file", required=True)
    p_run.set_defaults(func=cmd_run)

    p_ll = sub.add_parser("extract-ll")
    p_ll.add_argument("--cr", required=True)
    p_ll.add_argument("--lessons-file", required=True)
    p_ll.add_argument("--out", required=True)
    p_ll.set_defaults(func=cmd_extract_ll)

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
