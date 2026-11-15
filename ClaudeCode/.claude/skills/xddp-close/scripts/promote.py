"""promote.py — xddp-close Step C2〜C7 成果物昇格・知見ログ／改善バックログの表の作り直し CLI

`{XDDP_DIR}/latest-specs/**` → `{DOCS}/...` への成果物昇格・
lessons-learned/CRS/TSP・TRS/project-rulebook/improvement-backlog の昇格・cross/ 破壊的変更検出を
一括担当する（AI_INDEX.md は書かない。close の Step D2 で `ai_index.py build` が作り直す）。
知見ログ（Layer 1・Layer 2）・改善バックログの表（エントリ一覧・タグ別インデックス・サマリ・バックログ一覧）は
このスクリプトだけが書く（`index`）。LLM・人はエントリだけを書く（設計根拠は docs/adr/ADR-0013・ADR-0035）。

ID: close の LL・IDEA は `LL-{CR}-{NN}`・`IDEA-{CR}-{NN}`。CR を持たない登録（update-knowledge の lesson 等）は
`LL-M{YYYYMMDD}-{NN}`・`IDEA-M{YYYYMMDD}-{NN}`（番号は `index` の `next_manual_id`）。

Usage:
  python3 promote.py run \\
    --cr CR --cr-path CR_PATH --xddp-dir XDDP_DIR --docs DOCS \\
    --repos-keys r1,r2 --affected-repos r1,r2 [--has-cross] [--is-multi] \\
    --today YYYY-MM-DD --lessons-file LESSONS_FILE \\
    --output-file OUTPUT_FILE [--skip-rulebooks]
    project-rulebook の写しは `rulebook_files.promote`（DOCS との競合の判定。repo 別は REPOS のすべて、cross は
    REPOS が2つ以上のとき）。--skip-rulebooks は rulebook を写さない（close の knowledge agent が失敗したとき）。

  python3 promote.py sync-baseline --cr CR --xddp-dir XDDP_DIR --docs DOCS --affected-repos r1,r2 [--has-cross]
    Step C0-3。先に `spec_changes.py record` で progress.md の工程11 の更新一覧・削除一覧を作り直し、
    今の CR の repo・cross（--has-cross）・system について、`{DOCS}` の写しのうちどちらの一覧にも無いファイルを
    latest-specs へ写す（削除したもの・更新したものを書き戻さない）。写したファイルは基準の SHA-256 も合わせる。
    基準が無い・壊れている・progress.md が無いときは exit 1。

  python3 promote.py extract-ll --cr CR --lessons-file LESSONS_FILE --out OUT \\
    --repos-keys r1,r2 [--is-multi]
    今の CR の知見ログ（LL）のうち振り分け先（REPOS のキー・IS_MULTI の cross）のあるエントリだけを OUT に
    書き出す（Step C3.5・C3.6 のエージェントの入力。`run` の前に実行する）。0件なら OUT を書かず、
    前回の OUT が残っていれば消す。

  python3 promote.py index [--cr CR] [--today YYYY-MM-DD] [--check] \\
    [--lessons-file L] [--backlog-file B] [--layer2-file F --area AREA]
    渡したファイルの表を作り直す（内容が変わらなければ書かない）。`--check` は書かずに件数だけを返す。
    Layer 1 の2つのファイルが無ければ扱わない（件数 0）。Layer 2 のファイルが無ければヘッダーだけのファイルを
    作る（`--check` では作らない）。Layer 1・バックログに必要な節が無ければ exit 1。

Output:
  run: stdout へ JSON 1オブジェクト（{"ok": true, "repo_results", "failed", "unresolved_ll", "ll_conflicts",
       "backlog_conflicts", "duplicate_ids", "rulebooks": [{"file", "docs_file", "action", "error"}]|null,
       "rulebooks_skipped", ...}）。OUTPUT_FILE に人向け保留事項レポート（「## project-rulebook の写し」を含む）を書き込む。
  sync-baseline: stdout へ JSON 1行（{"ok": true, "protected_files": 更新一覧, "deleted_files": 削除一覧,
       "copied_files": [...]}。パスは `latest-specs/…`。C0-4 は protected_files・deleted_files を使う）。
  extract-ll: stdout へ JSON 1行（{"count": N, "unparsed": [{"id", "reason": heading|unclosed-fence|no-meta|
       multi-meta}], "dropped": [{"id", "reason": cr-meta|cut}], "unrouted": [{"id", "repo", "reason":
       unknown|invalid}], "out": パス|null, "removed": bool}）。
  index: stdout へ JSON 1行（{"cr_ll_count", "cr_idea_count", "cr_ll_ids", "cr_idea_ids", "ll_count",
       "idea_count", "unknown_tags": [{"id", "tag"}], "cr_unknown_repo_ideas", "bad_ideas": [{"id", "reason":
       table|status|heading|outside-section}], "unparsed_ll": [{"id", "reason"}], "duplicate_ids": [{"id",
       "file"}], "next_manual_id", "written"}）。
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
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "xddp-11-specs" / "scripts"))
import docs_layout as layout  # noqa: E402
import rulebook_files  # noqa: E402
import spec_changes  # noqa: E402

LESSONS_TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "lessons-learned-template.md"

# ---------------------------------------------------------------------------
# 共通ユーティリティ
# ---------------------------------------------------------------------------


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


class SectionError(Exception):
    """知見ログ・バックログに必要な節が無い。"""


def _split(raw: str) -> list:
    return [s.strip() for s in raw.split(",") if s.strip()]


def _split_row(line: str) -> list:
    """Markdown テーブル行をセルへ分割する（`\\|` エスケープ対応。chd_sp_coverage.py と同一方針）。"""
    if "|" not in line:
        return []
    return [p.strip().replace(r"\|", "|") for p in re.split(r"(?<!\\)\|", line)[1:-1]]


def _cell(text: str) -> str:
    return text.replace("|", r"\|")


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


def _write_if_changed(path: Path, old: list, new: list) -> bool:
    if path.exists() and _strip_end(old) == _strip_end(new):
        return False
    _write_lines(path, new)
    return True


def _strip_end(lines: list) -> list:
    out = list(lines)
    while out and out[-1] == "":
        out.pop()
    return out


# ---------------------------------------------------------------------------
# 処理結果（repo・cross・system・共通ファイル）
# ---------------------------------------------------------------------------

COMMON_TARGET = "共通ファイル"


def _new_result() -> dict:
    return {"ok": True, "errors": [], "done": False}


def _init_repo_results(repos) -> dict:
    return {repo: _new_result() for repo in repos}


def _register(repo_results: dict, target: str) -> None:
    repo_results.setdefault(target, _new_result())


def _mark_done(repo_results: dict, target: str) -> None:
    repo_results.setdefault(target, _new_result())["done"] = True


def _record_failure(repo_results: dict, repo: str, step: str, error) -> None:
    entry = repo_results.setdefault(repo, _new_result())
    entry["ok"] = False
    entry["done"] = True
    entry["errors"].append(f"{step}: {error}")


def _status_text(result: dict) -> str:
    if not result["ok"]:
        return f"失敗（{'; '.join(result['errors'])}）"
    return "成功" if result["done"] else "対象外"


# ---------------------------------------------------------------------------
# Step C2: Promote Approved Specs → DOCS_DIR
# ---------------------------------------------------------------------------


def _copy_tree(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)


def _spec_areas(affected_repos: list, has_cross: bool) -> list:
    return list(affected_repos) + ([layout.CROSS_AREA] if has_cross else []) + [layout.SYSTEM_AREA]


def sync_baseline(xddp_dir: Path, docs: Path, cr: str, affected_repos: list, has_cross: bool) -> dict:
    """Step C0-3: `{DOCS}` の写しのうち、工程11 の更新一覧にも削除一覧にも無いファイルを latest-specs へ写す。"""
    rec = spec_changes.record(xddp_dir, cr)
    skip = set(rec["updated"]) | set(rec["deleted"])
    base = spec_changes.load_baseline(xddp_dir, cr)
    copied = []
    for area in _spec_areas(affected_repos, has_cross):
        src_root = layout.docs_specs_root(docs, area)
        if not src_root.is_dir():
            continue
        for src in sorted(src_root.rglob("*")):
            rel_in = src.relative_to(src_root)
            if not src.is_file() or any(part.startswith(".") for part in rel_in.parts):
                continue
            rel = f"{spec_changes.LATEST_DIR}/{area}/{rel_in.as_posix()}"
            if rel in skip:
                continue
            dst = Path(xddp_dir) / rel
            digest = spec_changes.sha256(src)
            if not dst.is_file() or spec_changes.sha256(dst) != digest:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied.append(rel)
            base[rel] = digest
    spec_changes.save_baseline(xddp_dir, cr, base)
    return {"ok": True, "protected_files": rec["updated"], "deleted_files": rec["deleted"], "copied_files": copied}


DELETION_KIND_DIR = "ディレクトリ"
DELETION_KIND_FILE = "ファイル"


def _deleted_file_candidates(xddp_dir: Path, docs: Path, areas: list, deleted: list, covered: list) -> list:
    """工程11 の削除一覧のうち `{DOCS}` に写しのあるものを削除候補にする（ファイル単位。latest-specs で
    ディレクトリごと消えたものは、その最も上のディレクトリにまとめる）。`covered`（既に候補のディレクトリ）の下は除く。"""
    latest = Path(xddp_dir) / "latest-specs"
    out, seen = [], set()
    for rel in deleted:
        parts = Path(rel).parts
        if len(parts) < 3 or parts[0] != "latest-specs" or parts[1] not in areas:
            continue
        target = layout.latest_to_docs_path(docs, rel)
        if not target.is_file():
            continue
        area_root = layout.latest_specs_root(latest, parts[1])
        path, kind = target, DELETION_KIND_FILE
        rel_parts = parts[2:]
        for depth in range(1, len(rel_parts)):
            sub = Path(*rel_parts[:depth])
            if not (area_root / sub).exists() and (layout.docs_specs_root(docs, parts[1]) / sub).is_dir():
                path, kind = layout.docs_specs_root(docs, parts[1]) / sub, DELETION_KIND_DIR
                break
        key = str(path)
        if key in seen or any(key == c or key.startswith(c + os.sep) for c in covered):
            continue
        seen.add(key)
        out.append({"path": key, "kind": kind})
    return out


def promote_specs(xddp_dir: Path, docs: Path, affected_repos: list, has_cross: bool,
                   repo_results: dict, deleted: list = ()) -> list:
    """repo別・cross/・system/ の昇格コピーを行う。

    repo 単位で例外を捕捉し、1 repo の失敗が他 repo の処理を止めないようにする
    （test-fixtures/scratch-workspace/README.md の ENOTDIR 実機シナリオに対応）。
    `repo_results`（{対象: {"ok", "errors", "done"}}）は呼び出し元が用意し、本関数が
    破壊的に更新する（Step C2〜C7 全体で1つの dict を共有し、対象ごとの失敗を集約するため）。
    `deleted`（progress.md の工程11 の削除一覧）のうち `{DOCS}` に写しのあるものも削除候補にする。

    戻り値: deletion_candidates のリスト [{"path", "kind": ディレクトリ|ファイル}]。
    """
    latest_specs = Path(xddp_dir) / "latest-specs"
    deletion_candidates = []

    for repo in affected_repos:
        src = layout.latest_specs_root(latest_specs, repo)
        dst = layout.docs_specs_root(docs, repo)
        try:
            if src.exists():
                _copy_tree(src, dst)
                _mark_done(repo_results, repo)
        except Exception as e:  # noqa: BLE001 — per-repo 失敗を分離して継続するため意図的に広く捕捉
            _record_failure(repo_results, repo, "C2", e)
            continue

        # 削除伝播（repo モジュールディレクトリ）
        if dst.exists() and src.exists():
            existing_modules = set(layout.module_names(dst))
            current_modules = set(layout.subdir_names(src))
            for missing in sorted(existing_modules - current_modules):
                deletion_candidates.append({"path": str(dst / missing), "kind": DELETION_KIND_DIR})

    cross_src = layout.latest_specs_root(latest_specs, layout.CROSS_AREA)
    if has_cross and cross_src.exists():
        try:
            _copy_tree(cross_src, layout.docs_specs_root(docs, layout.CROSS_AREA))
            _mark_done(repo_results, layout.CROSS_AREA)
        except Exception as e:  # noqa: BLE001
            _record_failure(repo_results, layout.CROSS_AREA, "C2", e)

    system_src = layout.latest_specs_root(latest_specs, layout.SYSTEM_AREA)
    if system_src.exists():
        try:
            _copy_tree(system_src, layout.docs_specs_root(docs, layout.SYSTEM_AREA))
            _mark_done(repo_results, layout.SYSTEM_AREA)
            uc_dst = layout.docs_usecases_dir(docs)
            uc_src = layout.latest_usecases_dir(latest_specs)
            if uc_dst.exists():
                existing_uc = set(layout.subdir_names(uc_dst))
                current_uc = set(layout.subdir_names(uc_src))
                for missing in sorted(existing_uc - current_uc):
                    deletion_candidates.append({"path": str(uc_dst / missing), "kind": DELETION_KIND_DIR})
        except Exception as e:  # noqa: BLE001
            _record_failure(repo_results, layout.SYSTEM_AREA, "C2", e)

    covered = [c["path"] for c in deletion_candidates]
    deletion_candidates += _deleted_file_candidates(Path(xddp_dir), Path(docs), _spec_areas(affected_repos, has_cross),
                                                    list(deleted), covered)
    return deletion_candidates


# ---------------------------------------------------------------------------
# LL・IDEA の ID
# ---------------------------------------------------------------------------

LL_ENTRY_RE = re.compile(r"^### (LL-[^\s：]+)：")
IDEA_ENTRY_RE = re.compile(r"^### (IDEA-[^\s：]+)：")
# 見出しの ID（見出しの崩れたもの〔`#` の数・区切り〕も含む。今の CR のエントリを数えるのに使う）
ID_HEADING_RE = re.compile(r"^#{1,6}\s*((?:LL|IDEA)-[^\s：:]+)")
LL_META_RE = re.compile(
    r"\*\*CR：\*\*\s*(?P<cr>\S+)\s*／\s*\*\*工程：\*\*\s*(?P<phase>[^／]+?)\s*／\s*"
    r"\*\*repo：\*\*\s*(?P<repo>[^／]+?)\s*／\s*\*\*タグ：\*\*\s*(?P<tags>.+)$")
TAG_SPLIT_RE = re.compile(r"[,，、\s]+")


def cr_id_re(prefix: str, cr: str):
    """今の CR の ID（`{prefix}-{CR}-{NN}`）に全体で一致する正規表現（前方一致にしない）。"""
    return re.compile(rf"^{prefix}-{re.escape(cr)}-\d{{2,}}$")


def manual_id_prefix(prefix: str, today: str) -> str:
    """CR を持たない登録の ID の接頭辞（`{prefix}-M{YYYYMMDD}-`）。"""
    return f"{prefix}-M{today.replace('-', '')}-"


def parse_tags(raw: str) -> list:
    """メタ行の `**タグ：**` 欄を `,`・`、`・空白で分け、`#` で始まる語を返す。"""
    return [t for t in TAG_SPLIT_RE.split(raw.strip()) if t.startswith("#")]


def _heading_ids(lines: list) -> list:
    """フェンスの外の見出しの ID（見出しの崩れたものも含む）。"""
    mask, _ = _fence_mask(lines)
    out = []
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        m = ID_HEADING_RE.match(line)
        if m:
            out.append(m.group(1))
    return out


def _cr_ids(lines: list, prefix: str, cr) -> list:
    if not cr:
        return []
    pat = cr_id_re(prefix, cr)
    return [i for i in _heading_ids(lines) if pat.match(i)]


def next_manual_id(lines: list, prefix: str, today: str) -> str:
    """書くファイルの中の `{prefix}-M{TODAY}-` の番号の最大値 + 1（無ければ 01）。"""
    head = manual_id_prefix(prefix, today)
    pat = re.compile(rf"^{re.escape(head)}(\d+)$")
    nums = [int(m.group(1)) for m in (pat.match(i) for i in _heading_ids(lines)) if m]
    return f"{head}{(max(nums) + 1 if nums else 1):02d}"


def _duplicate_ids(lines: list, entry_re, file) -> list:
    mask, _ = _fence_mask(lines)
    counts = {}
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        m = entry_re.match(line)
        if m:
            counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return [{"id": i, "file": str(file)} for i, n in counts.items() if n >= 2]


# ---------------------------------------------------------------------------
# フェンスと LL の切り分け
# ---------------------------------------------------------------------------

# 見出しの崩れた LL エントリ（`### LL-{CR}-01: …`・`## LL-{CR}-01：…`・`###LL-{CR}-01：…` 等）
LL_BROKEN_HEADING_RE = re.compile(r"^#{1,6}\s*LL-")
IDEA_BROKEN_HEADING_RE = re.compile(r"^#{1,6}\s*IDEA-")
ANY_HEADING_RE = re.compile(r"^#{1,6}\s")
# エントリを終える見出し（エントリの見出し `###` と同じかより上の水準）
END_HEADING_RE = re.compile(r"^#{1,3}\s")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
FENCE_CLOSE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")
LL_META_WINDOW = 5
LL_ID_MAX = 40


def _heading_label(line: str) -> str:
    """見出しの行から行頭の `#` と空白を除いた文字列（先頭40文字まで）。"""
    return re.sub(r"^\s*#*\s*", "", line).strip()[:LL_ID_MAX]


def _fence_mask(lines: list):
    """各行がフェンス（```・~~~）の中か（開閉の行を含む）と、閉じないフェンスを開いた行の集合。

    閉じるのは、開いたときと同じ文字で、長さが開いたフェンス以上の行（後ろの空白は可）だけ
    （CommonMark「4.5 Fenced code blocks」）。閉じないフェンスの開いた行はフェンスとして扱わない。
    """
    n = len(lines)
    mask = [False] * n
    unclosed = set()
    i = 0
    while i < n:
        m = FENCE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        char, length = m.group(1)[0], len(m.group(1))
        close = None
        for j in range(i + 1, n):
            c = FENCE_CLOSE_RE.match(lines[j])
            if c and c.group(1)[0] == char and len(c.group(1)) >= length:
                close = j
                break
        if close is None:
            unclosed.add(i)
            i += 1
            continue
        for k in range(i, close + 1):
            mask[k] = True
        i = close + 1
    return mask, unclosed


class _Block(list):
    """エントリ（または落とした塊）の行。`unclosed` は閉じないフェンスを開いた行を含むか。"""
    unclosed = False


def _is_heading_line(line: str) -> bool:
    return bool(LL_ENTRY_RE.match(line) or LL_BROKEN_HEADING_RE.match(line)
                or ANY_HEADING_RE.match(line))


def _window_has_meta(lines: list, idx: int, mask: list, unclosed: set) -> bool:
    """idx の見出しの窓（5行まで・次の見出しの手前まで）にフェンスの外のメタ行があるか。"""
    for j in range(idx, min(idx + LL_META_WINDOW, len(lines))):
        if mask[j] or j in unclosed:
            continue
        line = lines[j]
        if j > idx and _is_heading_line(line):
            break
        if LL_META_RE.search(line):
            return True
    return False


def _split_ll_blocks(lines: list):
    """LL のファイルをエントリと落とした塊に分ける。フェンスの中の行は見出しとして扱わない。

    戻り値: (entries, chunks)。entries は _Block のリスト。chunks は
    (_Block, 直前のエントリの index または None) のリスト（エントリにしない塊。
    最初のエントリより前の部分を含む）。
    """
    mask, unclosed = _fence_mask(lines)
    entries = []
    chunks = []
    state = {"current": _Block(), "is_entry": False}

    def _start(line, is_entry):
        current = state["current"]
        if state["is_entry"]:
            entries.append(current)
        elif current:
            chunks.append((current, len(entries) - 1 if entries else None))
        state["current"] = _Block([line])
        state["is_entry"] = is_entry

    for idx, line in enumerate(lines):
        if mask[idx]:
            state["current"].append(line)
            continue
        if idx in unclosed:
            state["current"].append(line)
            state["current"].unclosed = True
            continue
        if LL_ENTRY_RE.match(line) or LL_BROKEN_HEADING_RE.match(line):
            _start(line, True)
            continue
        if ANY_HEADING_RE.match(line):
            if _window_has_meta(lines, idx, mask, unclosed):
                _start(line, True)
                continue
            if END_HEADING_RE.match(line):
                _start(line, False)
                continue
        state["current"].append(line)
    _start("", False)
    return entries, chunks


def _meta_lines_outside_fence(block: list) -> list:
    mask, _ = _fence_mask(block)
    found = []
    for i, line in enumerate(block):
        if mask[i]:
            continue
        m = LL_META_RE.search(line)
        if m:
            found.append(m)
    return found


def _ll_entry_meta(entry: list):
    """エントリの (entry_id, meta_match または None, reason または None) を返す。

    reason: `heading`＝見出しが `### LL-…：` の書式でない、`unclosed-fence`＝コードブロックが閉じていない、
    `multi-meta`＝フェンスの外にメタ行が2つ以上ある、`no-meta`＝先頭5行にメタ行が無い。
    """
    header = entry[0]
    m_id = LL_ENTRY_RE.match(header)
    if not m_id:
        return _heading_label(header), None, "heading"
    entry_id = m_id.group(1)
    if getattr(entry, "unclosed", False):
        return entry_id, None, "unclosed-fence"
    metas = _meta_lines_outside_fence(entry)
    if len(metas) >= 2:
        return entry_id, None, "multi-meta"
    mask, _ = _fence_mask(entry)
    for i, line in enumerate(entry[:LL_META_WINDOW]):
        if mask[i]:
            continue
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


def _ll_title(entry: list) -> str:
    m = LL_ENTRY_RE.match(entry[0])
    return entry[0][m.end():].strip() if m else _heading_label(entry[0])


def _ll_records(lines: list):
    """LL のエントリの (records, unparsed)。records は {id, title, cr, phase, repo, tags}。"""
    entries, _ = _split_ll_blocks(lines)
    records = []
    unparsed = []
    for entry in entries:
        entry_id, meta, reason = _ll_entry_meta(entry)
        if meta is None:
            unparsed.append({"id": entry_id, "reason": reason})
            continue
        records.append({"id": entry_id, "title": _ll_title(entry), "cr": meta.group("cr"),
                        "phase": meta.group("phase").strip(), "repo": meta.group("repo").strip(),
                        "tags": parse_tags(meta.group("tags"))})
    return records, unparsed


# ---------------------------------------------------------------------------
# エントリの比較の正規化と足し方（Layer 2・{DOCS} の backlog で共通）
# ---------------------------------------------------------------------------


def normalize_entry(lines: list) -> list:
    """各行の末尾の空白を除き、エントリの末尾の空行と区切りの `---` の行（フェンスの外）をすべて除く。"""
    out = [line.rstrip() for line in lines]
    mask, _ = _fence_mask(out)
    while out and (out[-1] == "" or (out[-1] == "---" and not mask[len(out) - 1])):
        out.pop()
    return out


def append_entry(target_lines: list, entry: list) -> None:
    """target_lines の末尾にエントリを足す（区切りは空行 + `---`）。"""
    while target_lines and target_lines[-1].strip() == "":
        target_lines.pop()
    if target_lines:
        target_lines.append("")
    target_lines.extend(normalize_entry(entry))
    target_lines.extend(["", "---"])


def insert_entry(lines: list, pos: int, entry: list) -> list:
    """lines の pos（次の節の見出しの位置）の前にエントリを足した行のリスト（区切りは空行 + `---`）。"""
    q = pos
    while q > 0 and lines[q - 1].strip() == "":
        q -= 1
    tail = lines[pos:]
    return lines[:q] + [""] + normalize_entry(entry) + ["", "---", ""] + tail


# ---------------------------------------------------------------------------
# 節と表
# ---------------------------------------------------------------------------


def _find_heading(lines: list, pred, start: int = 0):
    mask, _ = _fence_mask(lines)
    for i in range(start, len(lines)):
        if not mask[i] and pred(lines[i]):
            return i
    return None


def _exact(heading: str):
    return lambda line: line.strip() == heading


def _section_end(lines: list, h_idx: int, end_re=re.compile(r"^## ")) -> int:
    end = _find_heading(lines, lambda l: bool(end_re.match(l)), h_idx + 1)
    return len(lines) if end is None else end


def _table_bounds(lines: list, h_idx: int):
    """節の中の最初の表の (開始, 終わり)。表が無ければ None。"""
    end = _section_end(lines, h_idx)
    mask, _ = _fence_mask(lines)
    for i in range(h_idx + 1, end):
        if not mask[i] and lines[i].strip().startswith("|"):
            j = i
            while j < end and lines[j].strip().startswith("|"):
                j += 1
            return i, j
    return None


def _replace_section_table(lines: list, h_idx: int, table: list) -> list:
    bounds = _table_bounds(lines, h_idx)
    if bounds is None:
        return lines[:h_idx + 1] + ["", *table] + lines[h_idx + 1:]
    start, end = bounds
    return lines[:start] + table + lines[end:]


def _section_table_rows(lines: list, h_idx: int) -> list:
    bounds = _table_bounds(lines, h_idx)
    if bounds is None:
        return []
    start, end = bounds
    return [_split_row(l) for l in lines[start + 2:end]]


def _missing_sections(lines: list, specs) -> list:
    return [name for name, pred in specs if _find_heading(lines, pred) is None]


# ---------------------------------------------------------------------------
# 知見ログ（Layer 1 `{XDDP_DIR}/lessons-learned.md`・Layer 2 `{DOCS}/{area}/knowledge/lessons-learned.md`）
# ---------------------------------------------------------------------------

LL_LIST_HEADING = "## エントリ一覧"
LL_TAG_HEADING = "## タグ別インデックス"
LL_DETAIL_HEADING = "## 知見詳細"
LESSONS_SECTIONS = [(h, _exact(h)) for h in (LL_LIST_HEADING, LL_TAG_HEADING, LL_DETAIL_HEADING)]
LL_TABLE_HEADER = ["| ID | タイトル | CR | 工程 | タグ |", "|----|---------|-----|------|------|"]
TAG_TABLE_HEADER = ["| タグ | エントリ番号（カンマ区切り） |", "|---|---|"]
LAST_CR_RE = re.compile(r"^(\*\*最終更新CR：\*\*\s*)(.*?)(\s*)$")
LAYER2_DESC = ("> xddp-close（CR のクローズ）と xddp-update-knowledge（lesson）がエントリを足す。"
               "`## エントリ一覧` は `promote.py index` が作り直す（手で直さない）。")


def layer2_header(area: str) -> list:
    return [f"# 知見ログ: {area}", LAYER2_DESC, ""]


def _ll_table(records: list) -> list:
    rows = [f"| {r['id']} | {_cell(r['title'])} | {_cell(r['cr'])} | {_cell(r['phase'])} | "
            f"{_cell(', '.join(r['tags']))} |" for r in records]
    return LL_TABLE_HEADER + rows


def _template_tags() -> list:
    """LL テンプレートのタグ別インデックスの行のタグ（Layer 2 の unknown_tags の判定に使う）。"""
    lines = _read_lines(LESSONS_TEMPLATE)
    h = _find_heading(lines, _exact(LL_TAG_HEADING))
    return [] if h is None else [r[0] for r in _section_table_rows(lines, h) if r]


def _unknown_tags(records: list, known: list) -> list:
    return [{"id": r["id"], "tag": t} for r in records for t in r["tags"] if t not in known]


def _empty_result() -> dict:
    return {"cr_ll_count": 0, "cr_idea_count": 0, "cr_ll_ids": [], "cr_idea_ids": [],
            "ll_count": 0, "idea_count": 0, "unknown_tags": [], "cr_unknown_repo_ideas": [],
            "bad_ideas": [], "unparsed_ll": [], "duplicate_ids": [], "next_manual_id": None,
            "written": []}


def rebuild_lessons(lines: list, cr=None):
    """Layer 1 の知見ログの表を作り直す。戻り値: (new_lines, info)。必要な節が無ければ SectionError。"""
    missing = _missing_sections(lines, LESSONS_SECTIONS)
    if missing:
        raise SectionError(", ".join(missing))
    detail = _find_heading(lines, _exact(LL_DETAIL_HEADING))
    records, unparsed = _ll_records(lines[detail + 1:])
    cr_ids = _cr_ids(lines, "LL", cr)

    new = _replace_section_table(lines, _find_heading(lines, _exact(LL_LIST_HEADING)), _ll_table(records))
    tag_h = _find_heading(new, _exact(LL_TAG_HEADING))
    tags = [r[0] for r in _section_table_rows(new, tag_h) if r]
    rows = []
    for tag in tags:
        ids = [r["id"] for r in records if tag in r["tags"]]
        rows.append(f"| {tag} | {', '.join(ids) if ids else '—'} |")
    new = _replace_section_table(new, tag_h, TAG_TABLE_HEADER + rows)
    if cr and cr_ids:
        for i, line in enumerate(new):
            m = LAST_CR_RE.match(line)
            if m:
                new[i] = f"{m.group(1)}{cr}{m.group(3)}"
                break
    info = {"cr_ll_count": len(cr_ids), "cr_ll_ids": cr_ids, "ll_count": len(records),
            "unknown_tags": _unknown_tags(records, tags), "unparsed_ll": unparsed}
    return new, info


def rebuild_layer2(lines: list, area: str):
    """Layer 2 の知見ログのヘッダーと `## エントリ一覧` を作り直す。戻り値: (new_lines, records, unparsed)。"""
    records, unparsed = _ll_records(lines)
    table = _ll_table(records)
    if not any(l.strip() for l in lines):
        return layer2_header(area) + [LL_LIST_HEADING, "", *table, ""], records, unparsed
    new = list(lines)
    h = _find_heading(new, _exact(LL_LIST_HEADING))
    if h is None:
        pos = _find_heading(new, lambda l: l.startswith("### "))
        pos = len(new) if pos is None else pos
        # 最初の `### ` の直前が `## ` の見出し（間は空行だけ）なら、その見出しの前に入れる
        q = pos
        while q > 0 and new[q - 1].strip() == "":
            q -= 1
        if q > 0 and new[q - 1].startswith("## "):
            pos = q - 1
        block = [LL_LIST_HEADING, "", *table, ""]
        if pos > 0 and new[pos - 1].strip():
            block = [""] + block
        new = new[:pos] + block + new[pos:]
        first = next((l for l in new if l.strip()), "")
        if not first.startswith("# "):
            new = layer2_header(area) + new
    else:
        end = _find_heading(new, lambda l: bool(END_HEADING_RE.match(l)), h + 1)
        end = len(new) if end is None else end
        new = new[:h + 1] + ["", *table, ""] + new[end:]
    return new, records, unparsed


def index_lessons(path: Path, cr=None, check=False) -> dict:
    result = _empty_result()
    if not path.exists():
        return result
    lines = _read_lines(path)
    try:
        new, info = rebuild_lessons(lines, cr)
    except SectionError as e:
        raise SectionError(f"{path}: 必要な節がありません: {e}") from None
    result.update(info)
    result["duplicate_ids"] = _duplicate_ids(lines, LL_ENTRY_RE, path)
    if not check and _write_if_changed(path, lines, new):
        result["written"].append(str(path))
    return result


def index_layer2(path: Path, area: str, today=None, check=False) -> dict:
    result = _empty_result()
    lines = _read_lines(path)
    new, records, unparsed = rebuild_layer2(lines, area)
    result["ll_count"] = len(records)
    result["unparsed_ll"] = unparsed
    result["unknown_tags"] = _unknown_tags(records, _template_tags())
    result["duplicate_ids"] = _duplicate_ids(lines, LL_ENTRY_RE, path)
    if today:
        result["next_manual_id"] = next_manual_id(lines, "LL", today)
    if not check and _write_if_changed(path, lines, new):
        result["written"].append(str(path))
    return result


# ---------------------------------------------------------------------------
# 改善バックログ（`{XDDP_DIR}/improvement-backlog.md`・`{DOCS}/improvement-backlog.md`）
# ---------------------------------------------------------------------------

BACKLOG_SECTIONS = [(f"## {n}.", (lambda n: lambda l: l.startswith(f"## {n}."))(n)) for n in (1, 2, 3)]
IDEA_STATUSES = ("🆕 新規", "🔍 検討中", "📋 CR化済み", "⏸️ 保留", "❌ 却下")
IDEA_REQUIRED_ITEMS = ("カテゴリ", "優先度", "発生源", "ステータス")
SUMMARY_TABLE_HEADER = ["| ステータス | 件数 |", "|-----------|:----:|"]
BACKLOG_TABLE_HEADER = ["| ID | タイトル | カテゴリ | 優先度 | 発生源 | ステータス |",
                        "|----|---------|---------|:------:|--------|-----------|"]
LAST_UPDATED_RE = re.compile(r"^(\*\*最終更新：\*\*\s*)(.*?)(\s*)$")
# {DOCS} の backlog で今の CR の IDEA を比べる部分（close が書き、人が直さない部分）。
# 比べない部分（人が {DOCS} で直す）: 項目の表の 優先度・ステータス・対応CR と **CR化の判断メモ：**
IDEA_COMPARED_ITEMS = ("カテゴリ", "repo", "発生源")
IDEA_COMPARED_LABELS = ("内容", "発生経緯", "期待効果", "推定影響範囲")
IDEA_LABEL_RE = re.compile(r"^\*\*([^*：]+)：\*\*(.*)$")


def _idea_entries(lines: list):
    """(§3 の IDEA のエントリ [{id, title, start, end}], bad_ideas)。"""
    mask, _ = _fence_mask(lines)
    s3 = _find_heading(lines, BACKLOG_SECTIONS[2][1])
    s3_end = _section_end(lines, s3)
    entries = []
    bad = []
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        in_s3 = s3 < i < s3_end
        m = IDEA_ENTRY_RE.match(line)
        broken = IDEA_BROKEN_HEADING_RE.match(line)
        if (m or broken) and not in_s3:
            bad.append({"id": m.group(1) if m else _heading_label(line), "reason": "outside-section"})
            continue
        if not in_s3:
            continue
        if m or broken or END_HEADING_RE.match(line):
            if entries and entries[-1]["end"] is None:
                entries[-1]["end"] = i
            if m:
                entries.append({"id": m.group(1), "title": line[m.end():].strip(), "start": i, "end": None})
            elif broken:
                bad.append({"id": _heading_label(line), "reason": "heading"})
    if entries and entries[-1]["end"] is None:
        entries[-1]["end"] = s3_end
    return entries, bad


def _idea_items(entry_lines: list) -> dict:
    """IDEA のエントリの項目の表（`| 項目 | 内容 |`）の {項目: 値}。"""
    items = {}
    for line in entry_lines[1:]:
        s = line.strip()
        if not s.startswith("|"):
            if items:
                break
            continue
        cells = _split_row(s)
        if len(cells) < 2 or cells[0] == "項目" or re.match(r"^:?-+:?$", cells[0]):
            continue
        items[cells[0]] = cells[1]
    return items


def _idea_label_bodies(entry_lines: list) -> dict:
    bodies = {}
    current = None
    mask, _ = _fence_mask(entry_lines)
    for i, line in enumerate(entry_lines[1:], start=1):
        m = None if mask[i] else IDEA_LABEL_RE.match(line.strip())
        if m:
            current = m.group(1)
            bodies[current] = [m.group(2)] if m.group(2).strip() else []
            continue
        if current is not None:
            bodies[current].append(line)
    out = {}
    for k, v in bodies.items():
        v = normalize_entry(v)
        while v and v[0] == "":
            v.pop(0)
        out[k] = v
    return out


def idea_compared_parts(entry_lines: list) -> dict:
    m = IDEA_ENTRY_RE.match(entry_lines[0])
    parts = {"title": entry_lines[0][m.end():].strip() if m else entry_lines[0].strip()}
    items = _idea_items(entry_lines)
    for k in IDEA_COMPARED_ITEMS:
        parts[k] = items.get(k, "")
    labels = _idea_label_bodies(entry_lines)
    for k in IDEA_COMPARED_LABELS:
        parts[k] = labels.get(k, [])
    return parts


def rebuild_backlog(lines: list, cr=None, today=None):
    """バックログの §1・§2 を §3 から作り直す。戻り値: (new_lines, info)。必要な節が無ければ SectionError。"""
    missing = _missing_sections(lines, BACKLOG_SECTIONS)
    if missing:
        raise SectionError(", ".join(missing))
    entries, bad = _idea_entries(lines)
    counts = {s: 0 for s in IDEA_STATUSES}
    rows = []
    unknown_repo = []
    cr_pat = cr_id_re("IDEA", cr) if cr else None
    for e in entries:
        items = _idea_items(lines[e["start"]:e["end"]])
        lacking = [k for k in IDEA_REQUIRED_ITEMS if k not in items]
        if lacking:
            bad.append({"id": e["id"], "reason": "table"})
        status = items.get("ステータス", "")
        if status in counts:
            counts[status] += 1
        elif "ステータス" in items:
            bad.append({"id": e["id"], "reason": "status"})
        if cr_pat and cr_pat.match(e["id"]) and items.get("repo", "").strip().startswith("unknown"):
            unknown_repo.append(e["id"])
        vals = [items.get(k, "—") for k in ("カテゴリ", "優先度", "発生源", "ステータス")]
        rows.append(f"| {e['id']} | {_cell(e['title'])} | " + " | ".join(_cell(v) for v in vals) + " |")
    summary = SUMMARY_TABLE_HEADER + [f"| {s} | {n} |" for s, n in counts.items()]
    summary.append(f"| **合計** | {len(entries)} |")

    new = _replace_section_table(lines, _find_heading(lines, BACKLOG_SECTIONS[0][1]), summary)
    new = _replace_section_table(new, _find_heading(new, BACKLOG_SECTIONS[1][1]), BACKLOG_TABLE_HEADER + rows)
    if today and _strip_end(new) != _strip_end(lines):
        for i, line in enumerate(new):
            m = LAST_UPDATED_RE.match(line)
            if m:
                new[i] = f"{m.group(1)}{today}{m.group(3)}"
                break
    cr_ids = _cr_ids(lines, "IDEA", cr)
    info = {"cr_idea_count": len(cr_ids), "cr_idea_ids": cr_ids, "idea_count": len(entries),
            "cr_unknown_repo_ideas": unknown_repo, "bad_ideas": bad}
    return new, info


def index_backlog(path: Path, cr=None, today=None, check=False) -> dict:
    result = _empty_result()
    if not path.exists():
        return result
    lines = _read_lines(path)
    try:
        new, info = rebuild_backlog(lines, cr, today)
    except SectionError as e:
        raise SectionError(f"{path}: 必要な節がありません: {e}") from None
    result.update(info)
    result["duplicate_ids"] = _duplicate_ids(lines, IDEA_ENTRY_RE, path)
    if not check and _write_if_changed(path, lines, new):
        result["written"].append(str(path))
    return result


# ---------------------------------------------------------------------------
# extract-ll と Step C3: Promote Lessons Learned Log
# ---------------------------------------------------------------------------


def route_ll(repo: str, repos_keys: list, is_multi: bool):
    """LL の `repo` 欄の振り分け先。戻り値: (area または None, None または理由 unknown|invalid)。"""
    repo = repo.strip()
    if repo in repos_keys:
        return repo, None
    if repo == layout.CROSS_AREA and is_multi:
        return layout.CROSS_AREA, None
    if repo == "unknown":
        return None, "unknown"
    return None, "invalid"


def extract_ll(lessons_file: Path, cr: str, out: Path, repos_keys: list, is_multi: bool) -> dict:
    """今の CR の LL のうち振り分け先のあるエントリだけを out に書く（Step C3.5・C3.6 のエージェントの入力）。

    0件なら out を書かず、前回の out が残っていれば消す。
    """
    lines = _read_lines(lessons_file)
    entries, dropped = _split_ll_entries(lines, cr)
    selected = []
    unparsed = []
    unrouted = []
    for entry in entries:
        entry_id, meta, reason = _ll_entry_meta(entry)
        if meta is None:
            unparsed.append({"id": entry_id, "reason": reason})
            continue
        if meta.group("cr") != cr:
            continue
        repo = meta.group("repo").strip()
        area, why = route_ll(repo, repos_keys, is_multi)
        if area is None:
            unrouted.append({"id": entry_id, "repo": repo, "reason": why})
            continue
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
    return {"count": len(selected), "unparsed": unparsed, "dropped": dropped, "unrouted": unrouted,
            "out": out_written, "removed": removed}


def layer2_path(docs: Path, area: str) -> Path:
    return Path(docs) / area / "knowledge" / "lessons-learned.md"


def promote_lessons_learned(lessons_file: Path, docs: Path, cr: str, repos_keys: list, is_multi: bool,
                             repo_results: dict) -> dict:
    """今の CR の LL のエントリを `repo` 欄で Layer 2 に振り分ける。

    Layer 2 に同じ ID のエントリが無ければ足す。1つあり正規化した本文が違えば上書きせず ll_conflicts に出す。
    2つ以上あれば足さない（duplicate_ids で示す）。書いた後に `## エントリ一覧` を作り直す。
    戻り値: {"unresolved": [{id, title, repo, reason}], "conflicts": [{id, area}], "files": {area: path}}。
    """
    lines = _read_lines(lessons_file)
    entries, _ = _split_ll_entries(lines)
    unresolved = []
    by_area = {}
    for entry in entries:
        entry_id, meta, _ = _ll_entry_meta(entry)
        if meta is None or meta.group("cr") != cr:
            continue
        repo = meta.group("repo").strip()
        area, why = route_ll(repo, repos_keys, is_multi)
        if area is None:
            unresolved.append({"id": entry_id, "title": _ll_title(entry), "repo": repo, "reason": why})
            continue
        by_area.setdefault(area, []).append((entry_id, entry))

    conflicts = []
    files = {}
    for area, area_entries in by_area.items():
        target = layer2_path(docs, area)
        try:
            old = _read_lines(target)
            work, _, _ = rebuild_layer2(old, area)
            existing = {}
            for e in _split_ll_blocks(work)[0]:
                m = LL_ENTRY_RE.match(e[0])
                if m:
                    existing.setdefault(m.group(1), []).append(normalize_entry(e))
            for entry_id, entry in area_entries:
                found = existing.get(entry_id, [])
                norm = normalize_entry(entry)
                if not found:
                    append_entry(work, entry)
                    existing[entry_id] = [norm]
                elif len(found) == 1 and found[0] != norm:
                    conflicts.append({"id": entry_id, "area": area})
            work, _, _ = rebuild_layer2(work, area)
            _write_if_changed(target, old, work)
            _mark_done(repo_results, area)
            files[area] = target
        except Exception as e:  # noqa: BLE001 — per-repo 失敗を分離して継続するため意図的に広く捕捉
            _record_failure(repo_results, area, "C3", e)

    return {"unresolved": unresolved, "conflicts": conflicts, "files": files}


# ---------------------------------------------------------------------------
# Step C4〜C7: 既存ファイルの存在チェック→コピー・backlog の足し込み
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
            _mark_done(repo_results, repo)
        except Exception as e:  # noqa: BLE001
            _record_failure(repo_results, repo, "C4", e)
    if has_cross:
        try:
            dst = docs / "cross" / "crs"
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst / f"CRS-{cr}.md")
            _mark_done(repo_results, "cross")
        except Exception as e:  # noqa: BLE001
            _record_failure(repo_results, "cross", "C4", e)


def _copy_test_artifacts(cr_path: Path, area_dir: str, tsp_name: str, cr: str, test_target: Path) -> bool:
    copied = False
    tsp = Path(cr_path) / "09_test-spec" / area_dir / tsp_name
    if tsp.exists():
        test_target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tsp, test_target / tsp.name)
        copied = True
    trs_dir = Path(cr_path) / "10_test-results" / area_dir
    if trs_dir.exists():
        for trs in sorted(trs_dir.glob(f"TRS-{cr}-*.md")):
            test_target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(trs, test_target / trs.name)
            copied = True
    return copied


def promote_test_artifacts(cr_path: Path, docs: Path, cr: str, affected_repos: list,
                            has_cross: bool, repo_results: dict) -> None:
    for repo in affected_repos:
        try:
            if _copy_test_artifacts(cr_path, repo, f"TSP-{cr}.md", cr, docs / repo / "test"):
                _mark_done(repo_results, repo)
        except Exception as e:  # noqa: BLE001
            _record_failure(repo_results, repo, "C5", e)
    if has_cross:
        try:
            if _copy_test_artifacts(cr_path, "cross", f"TSP-{cr}-cross.md", cr, docs / "cross" / "test"):
                _mark_done(repo_results, "cross")
        except Exception as e:  # noqa: BLE001
            _record_failure(repo_results, "cross", "C5", e)


RULEBOOK_ACTION_TEXT = {
    "copied": "写した",
    "updated-from-docs": "DOCS から取り込んだ",
    "same": "同じ内容",
    "absent": "無い（写していない）",
    "conflict": "競合（写していない。両方が前回そろえた後に変わっている）",
    "failed": "失敗",
}


def promote_rulebooks(xddp_dir: Path, docs: Path, repos_keys: list, repo_results: dict) -> list:
    """project-rulebook の写し（`rulebook_files.promote`）。結果を処理結果一覧に反映して返す。

    copied・updated-from-docs・same はその対象を成功に、failed は失敗にし、conflict・absent は変えない。
    """
    results = rulebook_files.promote(Path(xddp_dir), Path(docs), repos_keys)
    for r in results:
        target = {"shared": COMMON_TARGET, "cross": layout.CROSS_AREA}.get(r["kind"], r["repo"])
        if r["action"] in ("copied", "updated-from-docs", "same"):
            _mark_done(repo_results, target)
        elif r["action"] == "failed":
            _record_failure(repo_results, target, f"C6({r['file']})", r["error"])
    return results


def promote_backlog(xddp_dir: Path, docs: Path, cr: str, today, repo_results: dict) -> dict:
    """`{XDDP_DIR}/improvement-backlog.md` の IDEA を `{DOCS}/improvement-backlog.md`（正）に足し込む。

    `{DOCS}` に無ければ写す。あれば `{DOCS}` に無い ID のエントリを §3 の末尾に足し、§1・§2 を作り直す。
    同じ ID があるものは何もしない。ただし今の CR の ID で比べる部分が違えば backlog_conflicts に出す。
    `{DOCS}` に必要な節が無ければ足し込まず「共通ファイル」の失敗にする。
    """
    result = {"promoted": False, "added": [], "conflicts": [], "duplicates": []}
    src = Path(xddp_dir) / "improvement-backlog.md"
    if not src.exists():
        return result
    dst = Path(docs) / "improvement-backlog.md"
    step = "C7(improvement-backlog.md)"
    try:
        if not dst.exists():
            docs.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            _mark_done(repo_results, COMMON_TARGET)
            result["promoted"] = True
            return result
        src_lines = _read_lines(src)
        old = _read_lines(dst)
        for path, lines in ((dst, old), (src, src_lines)):
            missing = _missing_sections(lines, BACKLOG_SECTIONS)
            if missing:
                _record_failure(repo_results, COMMON_TARGET, step,
                                f"{path} に必要な節がありません: {', '.join(missing)}")
                return result
        dst_lines = list(old)
        dst_counts = {}
        for i in _heading_ids(dst_lines):
            dst_counts[i] = dst_counts.get(i, 0) + 1
        cr_pat = cr_id_re("IDEA", cr)
        src_entries, _ = _idea_entries(src_lines)
        for e in src_entries:
            entry = src_lines[e["start"]:e["end"]]
            n = dst_counts.get(e["id"], 0)
            if n == 0:
                s3 = _find_heading(dst_lines, BACKLOG_SECTIONS[2][1])
                dst_lines = insert_entry(dst_lines, _section_end(dst_lines, s3), entry)
                dst_counts[e["id"]] = 1
                result["added"].append(e["id"])
            elif n == 1 and cr_pat.match(e["id"]):
                d = next(x for x in _idea_entries(dst_lines)[0] if x["id"] == e["id"])
                if idea_compared_parts(dst_lines[d["start"]:d["end"]]) != idea_compared_parts(entry):
                    result["conflicts"].append({"id": e["id"]})
        new, _ = rebuild_backlog(dst_lines, None, today)
        _write_if_changed(dst, old, new)
        result["duplicates"] = _duplicate_ids(new, IDEA_ENTRY_RE, dst)
        _mark_done(repo_results, COMMON_TARGET)
        result["promoted"] = True
    except Exception as e:  # noqa: BLE001
        _record_failure(repo_results, COMMON_TARGET, step, e)
    return result


# ---------------------------------------------------------------------------
# cross/ 破壊的変更検出
# ---------------------------------------------------------------------------

CROSS_SUMMARY_HEADING_RE = re.compile(r"^#{2,3}\s*(?:\d+\.\s*)?インタフェース変更サマリー?\s*$")


def detect_breaking_changes(cr_path: Path, cr: str, has_cross: bool):
    """cross CHD の「インタフェース変更サマリ」表から breaking 変更を検出する。

    戻り値: (breaking_found: bool|None, interfaces: list, parseable: bool)
    `parseable=False` は breaking 列が存在しない・パースできないことを示す（fail-loud。
    無警告で「なし」扱いにしてはならない）。
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


def append_breaking_warning(target: Path, cr: str, interfaces: list, area: str) -> None:
    """Layer 2 の知見ログに破壊的変更の警告を足す（ヘッダーが無ければ作り、表を作り直す）。"""
    old = _read_lines(target)
    marker = f"### 破壊的変更警告（{cr}）"
    lines, _, _ = rebuild_layer2(old, area)
    if not any(line.strip() == marker for line in lines):
        while lines and lines[-1].strip() == "":
            lines.pop()
        lines.append("")
        lines.append(marker)
        lines.append("")
        for iface in interfaces:
            lines.append(f"⚠️ 破壊的インタフェース変更あり。{iface}の旧バージョンへの依存コードを確認すること。")
        lines.append("")
        lines.append("---")
        lines, _, _ = rebuild_layer2(lines, area)
    _write_if_changed(target, old, lines)


# ---------------------------------------------------------------------------
# Output Format
# ---------------------------------------------------------------------------

UNROUTED_REASON_TEXT = {"unknown": "repo: unknown", "invalid": "REPOS に無い値"}


def _target_order(repo_results: dict, affected_repos: list) -> list:
    rest = [k for k in repo_results if k not in affected_repos and k != COMMON_TARGET]
    common = [COMMON_TARGET] if COMMON_TARGET in repo_results else []
    return list(affected_repos) + rest + common


def write_output_file(output_file: Path, cr: str, repo_results: dict, affected_repos: list,
                       unresolved_ll: list, ll_conflicts: list, backlog_conflicts: list,
                       duplicate_ids: list, breaking_found, breaking_interfaces: list,
                       breaking_parseable: bool, deletion_candidates: list, rulebooks=None) -> None:
    lines = ["# Step C2-C7 保留事項", f"CR: {cr}", ""]
    lines.append("## 処理結果一覧（repo・cross・system・共通ファイル）")
    for target in _target_order(repo_results, affected_repos):
        result = repo_results.get(target, _new_result())
        label = f"{COMMON_TARGET}（`{{DOCS}}` 直下）" if target == COMMON_TARGET else target
        lines.append(f"- {label}: {_status_text(result)}")
    lines.append("")

    def _section(title, items, fmt):
        lines.append(title)
        if items:
            lines.extend(fmt(x) for x in items)
        else:
            lines.append("なし")
        lines.append("")

    _section("## 要確認LL一覧（repo 欄が unknown か REPOS に無い値 — 昇格スキップ）", unresolved_ll,
             lambda u: f"- {u['id']}：{u['title']} — repo: {u['repo']}（{UNROUTED_REASON_TEXT[u['reason']]}）")
    _section("## Layer 2 と内容が違う LL（上書きしていない）", ll_conflicts,
             lambda c: f"- {c['id']}（{c['area']}）")
    _section("## `{DOCS}` と内容が違う今の CR の IDEA（上書きしていない）", backlog_conflicts,
             lambda c: f"- {c['id']}")
    _section("## 同じ ID が2つ以上あるエントリ", duplicate_ids,
             lambda d: f"- {d['id']}（{d['file']}）")

    lines.append("## 破壊的変更フラグ・対象インタフェース一覧")
    if not breaking_parseable:
        lines.append("- 破壊的変更: 判定不能（cross CHD の「インタフェース変更サマリ」表に breaking 列が"
                      "見つからないか、パースできませんでした。手動で確認してください）")
    else:
        lines.append(f"- 破壊的変更: {'あり' if breaking_found else 'なし'}")
        lines.append(f"- 対象インタフェース: {', '.join(breaking_interfaces) if breaking_interfaces else 'なし'}")
    lines.append("")

    _section("## 削除候補一覧（ディレクトリ・ファイル）", deletion_candidates,
             lambda d: f"- {d['path']}（{d['kind']}）")

    lines.append("## project-rulebook の写し")
    if rulebooks is None:
        lines.append("- 見送り（knowledge agent の失敗）。rulebook は `{DOCS}` に写していない")
    elif not rulebooks:
        lines.append("なし")
    else:
        for r in rulebooks:
            text = RULEBOOK_ACTION_TEXT[r["action"]]
            if r["action"] == "failed":
                text = f"{text}（{r['error']}）"
            lines.append(f"- `{r['file']}` → `{{DOCS}}/{r['docs_file']}`: {text}")
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

    # Step C2〜C7 全体で1つの repo_results を共有し、対象ごとの失敗を全ステップにわたって集約する。
    # 処理する対象を先に登録し、成功／失敗／対象外を書き分ける。
    repo_results = _init_repo_results(affected_repos)
    if args.is_multi:
        _register(repo_results, layout.CROSS_AREA)
    if layout.latest_specs_root(xddp_dir / "latest-specs", layout.SYSTEM_AREA).exists():
        _register(repo_results, layout.SYSTEM_AREA)
    _register(repo_results, COMMON_TARGET)

    deleted = layout.read_step11_lists(cr_path / "progress.md")["deleted"] or []
    deletion_candidates = promote_specs(xddp_dir, docs, affected_repos, args.has_cross, repo_results, deleted)

    breaking_found, breaking_interfaces, breaking_parseable = detect_breaking_changes(
        cr_path, args.cr, args.has_cross)

    ll = promote_lessons_learned(Path(args.lessons_file), docs, args.cr, repos_keys, args.is_multi,
                                 repo_results)
    layer2_files = dict(ll["files"])

    if breaking_parseable and breaking_found:
        areas = list(affected_repos) + ([layout.CROSS_AREA] if args.has_cross else [])
        for area in areas:
            target = layer2_path(docs, area)
            try:
                append_breaking_warning(target, args.cr, breaking_interfaces, area)
                _mark_done(repo_results, area)
                layer2_files[area] = target
            except Exception as e:  # noqa: BLE001
                _record_failure(repo_results, area, "C2(破壊的変更警告)", e)

    promote_crs(cr_path, docs, args.cr, affected_repos, args.has_cross, repo_results)
    promote_test_artifacts(cr_path, docs, args.cr, affected_repos, args.has_cross, repo_results)
    rulebooks = None if args.skip_rulebooks else promote_rulebooks(xddp_dir, docs, repos_keys, repo_results)
    backlog = promote_backlog(xddp_dir, docs, args.cr, args.today, repo_results)

    duplicate_ids = []
    for target in layer2_files.values():
        duplicate_ids.extend(_duplicate_ids(_read_lines(target), LL_ENTRY_RE, target))
    duplicate_ids.extend(backlog["duplicates"])

    write_output_file(
        Path(args.output_file), args.cr, repo_results, affected_repos, ll["unresolved"],
        ll["conflicts"], backlog["conflicts"], duplicate_ids, breaking_found, breaking_interfaces,
        breaking_parseable, deletion_candidates, rulebooks)

    failed = [t for t in _target_order(repo_results, affected_repos) if not repo_results[t]["ok"]]
    print(json.dumps({
        "ok": True,
        "repo_results": repo_results,
        "failed": failed,
        "unresolved_ll": ll["unresolved"],
        "ll_conflicts": ll["conflicts"],
        "backlog_conflicts": backlog["conflicts"],
        "duplicate_ids": duplicate_ids,
        "breaking_found": breaking_found,
        "breaking_parseable": breaking_parseable,
        "deletion_candidates": deletion_candidates,
        "backlog_promoted": backlog["promoted"],
        "backlog_added": backlog["added"],
        "rulebooks": rulebooks,
        "rulebooks_skipped": rulebooks is None,
        "output_file": str(args.output_file),
    }, ensure_ascii=False))


def cmd_sync_baseline(args) -> None:
    result = sync_baseline(Path(args.xddp_dir), Path(args.docs), args.cr, _split(args.affected_repos), args.has_cross)
    print(json.dumps(result, ensure_ascii=False))


def cmd_extract_ll(args) -> None:
    result = extract_ll(Path(args.lessons_file), args.cr, Path(args.out), _split(args.repos_keys),
                        args.is_multi)
    print(json.dumps(result, ensure_ascii=False))


def run_index(cr=None, today=None, check=False, lessons_file=None, backlog_file=None,
              layer2_file=None, area=None) -> dict:
    result = _empty_result()

    def _merge(part):
        for k, v in part.items():
            if isinstance(v, list):
                result[k].extend(v)
            elif k.endswith("_count"):
                result[k] += v
            elif v is not None:
                result[k] = v

    if lessons_file:
        _merge(index_lessons(Path(lessons_file), cr, check))
    if backlog_file:
        _merge(index_backlog(Path(backlog_file), cr, today, check))
    if layer2_file:
        _merge(index_layer2(Path(layer2_file), area, today, check))
    return result


def cmd_index(args) -> None:
    if args.layer2_file and not args.area:
        _err("--layer2-file には --area が必要です")
    try:
        result = run_index(args.cr, args.today, args.check, args.lessons_file, args.backlog_file,
                           args.layer2_file, args.area)
    except SectionError as e:
        _err(str(e))
    print(json.dumps(result, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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
    p_run.add_argument("--skip-rulebooks", action="store_true")
    p_run.set_defaults(func=cmd_run)

    p_sync = sub.add_parser("sync-baseline")
    p_sync.add_argument("--cr", required=True)
    p_sync.add_argument("--xddp-dir", required=True)
    p_sync.add_argument("--docs", required=True)
    p_sync.add_argument("--affected-repos", required=True)
    p_sync.add_argument("--has-cross", action="store_true")
    p_sync.set_defaults(func=cmd_sync_baseline)

    p_ll = sub.add_parser("extract-ll")
    p_ll.add_argument("--cr", required=True)
    p_ll.add_argument("--lessons-file", required=True)
    p_ll.add_argument("--out", required=True)
    p_ll.add_argument("--repos-keys", required=True)
    p_ll.add_argument("--is-multi", action="store_true")
    p_ll.set_defaults(func=cmd_extract_ll)

    p_idx = sub.add_parser("index")
    p_idx.add_argument("--cr")
    p_idx.add_argument("--today")
    p_idx.add_argument("--check", action="store_true")
    p_idx.add_argument("--lessons-file")
    p_idx.add_argument("--backlog-file")
    p_idx.add_argument("--layer2-file")
    p_idx.add_argument("--area")
    p_idx.set_defaults(func=cmd_index)

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
