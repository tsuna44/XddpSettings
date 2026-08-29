"""promote.py — xddp.close Step C2〜C7 成果物昇格 CLI

`{XDDP_DIR}/latest-specs/**` → `{DOCS}/...` への成果物昇格・AI_INDEX.md 全セクション upsert・
lessons-learned/CRS/TSP・TRS/project-rulebook/improvement-backlog の昇格・cross/ 破壊的変更検出を
一括担当する。旧 `xddp-close-promote-agent.md`（LLM が Read→Write で全文転写）を置き換える決定的処理
（判断業務を含まない。設計根拠は docs/adr/ADR-0013-close-promote-script.md 参照）。

Usage:
  python3 promote.py run \
    --cr CR --cr-path CR_PATH --xddp-dir XDDP_DIR --docs DOCS \
    --repos-keys r1,r2 --affected-repos r1,r2 [--has-cross] [--is-multi] \
    --today YYYY-MM-DD --lessons-file LESSONS_FILE [--force-full-ai-index] \
    --output-file OUTPUT_FILE

Output: 成功時は stdout に JSON 1オブジェクト（{"ok": true, ...}）を出力し、OUTPUT_FILE に
        人向け保留事項レポートを書き込む。失敗時は exit code 非0 + stderr にメッセージ。
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

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


def _join_row(cells: list) -> str:
    return "| " + " | ".join(cells) + " |"


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


def _parse_frontmatter(text: str) -> dict:
    """先頭 `---`〜`---` の YAML ライクなフロントマターを最小限パースする（外部依存なし）。

    対応形式: `key: value`（クォート除去）・`key:` 直後に `  - "item"` が続くリスト。
    それ以外の複雑な YAML（ネストしたマップ等）は本リポジトリのフロントマターには現れないため対象外。
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}
    result = {}
    i = 1
    while i < end:
        line = lines[i]
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        if val == "":
            # リストの可能性を確認
            items = []
            j = i + 1
            while j < end and re.match(r"^\s*-\s+", lines[j]):
                item = re.sub(r"^\s*-\s+", "", lines[j]).strip()
                item = item.strip('"').strip("'")
                items.append(item)
                j += 1
            if items:
                result[key] = items
                i = j
                continue
            result[key] = ""
            i += 1
            continue
        result[key] = val.strip('"').strip("'")
        i += 1
    return result


def _read_frontmatter(path: Path) -> dict:
    if not path.exists():
        return {}
    return _parse_frontmatter(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Markdown セクション・テーブル操作（AI_INDEX.md upsert 用）
# ---------------------------------------------------------------------------


def _find_heading(lines: list, heading: str):
    for i, line in enumerate(lines):
        if line.strip() == heading:
            return i
    return None


def _section_bounds(lines: list, heading_idx: int):
    """heading 行の直後から次の `## `（同レベル以上）見出しまたは EOF までを返す。"""
    start = heading_idx + 1
    end = start
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    return start, end


def _find_table_bounds(lines: list, start: int, end: int):
    """[start, end) 内で最初の `|` 開始行から連続する範囲を返す（ヘッダ+区切り+データ行込み）。"""
    i = start
    while i < end and not lines[i].strip().startswith("|"):
        i += 1
    if i >= end:
        return None
    table_start = i
    j = i
    while j < end and lines[j].strip().startswith("|"):
        j += 1
    return table_start, j


def _ensure_section(lines: list, heading: str) -> int:
    """heading が存在すればその行 index を返す。無ければファイル末尾に新設して index を返す。"""
    idx = _find_heading(lines, heading)
    if idx is not None:
        return idx
    if lines and lines[-1].strip() != "":
        lines.append("")
    lines.append(heading)
    lines.append("")
    return len(lines) - 2


def upsert_table(lines: list, heading: str, header_cells: list, key_col_indices: list,
                  rows: list) -> None:
    """`heading` 配下のテーブルへ `rows`（cells のリスト）を upsert する。

    既存テーブルのヘッダが `header_cells` と一致しない場合はヘッダ・データ行を丸ごと
    `header_cells` 基準へ作り直す（後方互換性は保証しない方針。CLAUDE.md 参照）。
    `key_col_indices` で指定した列の値が一致する既存行を更新し、なければ追記する。
    """
    if not rows:
        # 行が0件でもヘッダ自体は用意しておく（テーブルの見出しだけは常に存在させる）
        pass
    heading_idx = _ensure_section(lines, heading)
    start, end = _section_bounds(lines, heading_idx)
    table = _find_table_bounds(lines, start, end)
    sep_cells = ["---"] * len(header_cells)
    if table is None:
        new_block = [_join_row(header_cells), _join_row(sep_cells)]
        for row in rows:
            new_block.append(_join_row(row))
        insert_at = start
        lines[insert_at:insert_at] = new_block + [""]
        return
    table_start, table_end = table
    existing_header = _split_row(lines[table_start])
    if existing_header != header_cells:
        # スキーマ不一致: ヘッダ・データを作り直す（既存データは破棄。後方互換性なしポリシー）
        data_rows = []
    else:
        data_rows = [_split_row(lines[i]) for i in range(table_start + 2, table_end)]

    def _match(existing_row):
        return all(existing_row[k] == rows_row[k] for k in key_col_indices)

    for rows_row in rows:
        replaced = False
        for i, existing_row in enumerate(data_rows):
            if len(existing_row) > max(key_col_indices) and \
                    all(existing_row[k] == rows_row[k] for k in key_col_indices):
                data_rows[i] = rows_row
                replaced = True
                break
        if not replaced:
            data_rows.append(rows_row)

    new_block = [_join_row(header_cells), _join_row(sep_cells)]
    for row in data_rows:
        new_block.append(_join_row(row))
    lines[table_start:table_end] = new_block


def section_exists(lines: list, heading: str) -> bool:
    return _find_heading(lines, heading) is not None


# ---------------------------------------------------------------------------
# AI_INDEX.md 先行更新セクション（progress.md）の読み取り
# ---------------------------------------------------------------------------

PREUPDATED_HEADING = "## 工程11 AI_INDEX先行更新セクション"
PREUPDATED_ROW_RE = re.compile(r"^-\s*([^:：]+)[:：]\s*(.+)$")


def read_ai_index_preupdated(cr_path: Path) -> dict:
    progress_path = Path(cr_path) / "progress.md"
    lines = _read_lines(progress_path)
    idx = _find_heading(lines, PREUPDATED_HEADING)
    if idx is None:
        return {}
    _, end = _section_bounds(lines, idx)
    result = {}
    for i in range(idx + 1, end):
        m = PREUPDATED_ROW_RE.match(lines[i].strip())
        if m:
            result[m.group(1).strip()] = m.group(2).strip()
    return result


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
        src = latest_specs / repo
        dst = docs / repo / "specs"
        try:
            if src.exists():
                _copy_tree(src, dst)
        except Exception as e:  # noqa: BLE001 — per-repo 失敗を分離して継続するため意図的に広く捕捉
            _record_failure(repo_results, repo, "C2", e)
            continue

        # 削除伝播（repo モジュールディレクトリ）
        if dst.exists() and src.exists():
            existing_modules = {p.name for p in dst.iterdir() if p.is_dir() and p.name != "overview"}
            current_modules = {p.name for p in src.iterdir() if p.is_dir()}
            for missing in sorted(existing_modules - current_modules):
                deletion_candidates.append(str(dst / missing))

    if has_cross and (latest_specs / "cross").exists():
        try:
            _copy_tree(latest_specs / "cross", docs / "cross" / "specs")
            repo_results.setdefault("cross", {"ok": True, "errors": []})
        except Exception as e:  # noqa: BLE001
            _record_failure(repo_results, "cross", "C2", e)

    system_src = latest_specs / "system"
    if system_src.exists():
        system_dst = docs / "system" / "specs"
        try:
            _copy_tree(system_src, system_dst)
            repo_results.setdefault("system", {"ok": True, "errors": []})
            uc_dst = system_dst / "use-cases"
            uc_src = system_src / "use-cases"
            if uc_dst.exists():
                existing_uc = {p.name for p in uc_dst.iterdir() if p.is_dir()}
                current_uc = {p.name for p in uc_src.iterdir() if p.is_dir()} if uc_src.exists() else set()
                for missing in sorted(existing_uc - current_uc):
                    deletion_candidates.append(str(uc_dst / missing))
        except Exception as e:  # noqa: BLE001
            _record_failure(repo_results, "system", "C2", e)

    return deletion_candidates


# ---------------------------------------------------------------------------
# Step C2 続き: AI_INDEX.md update
# ---------------------------------------------------------------------------

KNOWLEDGE_GUIDE_BLOCK = """## 知識参照ガイド

> `{repo}` は `xddp.config.md` の `REPOS:` エントリ名が入るパターン表記（例: `repo-a`）。
> 具体的なファイルは上記各テーブルのリンクを参照のこと。

| 知りたいこと | 参照先パターン |
|---|---|
| 現在の機能仕様（What it does） | `{DOCS_DIR}/{repo}/specs/{module}/spec.md`（→「モジュール別最新仕様」テーブル） |
| 変更要求・設計判断の根拠（Why it was changed） | `{DOCS_DIR}/{repo}/crs/CRS-{CR}.md`（→「変更要求仕様書」テーブル） |
| 過去の実装パターン・知見 | `{XDDP_DIR}/lessons-learned.md`（作業中）/ `{DOCS_DIR}/{repo}/knowledge/lessons-learned.md`（クローズ済み）<br>タグ検索例: `#方式検討` `#設計` `#コーディング` `#リスク` `#テスト` `#プロセス` |
| プロジェクト規約・禁止事項 | `{XDDP_DIR}/project-rulebook.md` / `{XDDP_DIR}/project-rulebook-{repo}.md` |
| テスト仕様 | → 上記「テスト仕様（TSP）」テーブルを参照 |

> このセクションは初回 xddp.close 時に自動生成されます。知識ディレクトリ構造変更後に更新するには、このセクションを削除して xddp.close を再実行してください。""".split("\n")

AI_INDEX_SKELETON = """# AI向けナビゲーションインデックス
> 新規開発開始時に clone してこのファイルを AI に注入してください。

<!-- セクション管理: 各スキルが対応セクションを自動 upsert する。手動編集時は見出し名を変えないこと。 -->

## ユースケース一覧
| ユースケース | 目的（1行） | description | 関連モジュール | 最終更新CR |
|---|---|---|---|---|

## リポジトリ別仕様書
| リポジトリ | バージョン | overview | モジュール数 | 最終更新CR |
|---|---|---|---|---|

## モジュール別最新仕様
| リポジトリ | モジュール | spec | structure | state | 最終更新CR |
|---|---|---|---|---|---|
"""


def _usecase_rows(xddp_dir: Path, cr: str) -> list:
    uc_root = Path(xddp_dir) / "latest-specs" / "system" / "use-cases"
    rows = []
    if not uc_root.exists():
        return rows
    for uc_dir in sorted(p for p in uc_root.iterdir() if p.is_dir()):
        desc = uc_dir / "description.md"
        if not desc.exists():
            continue
        fm = _read_frontmatter(desc)
        text = desc.read_text(encoding="utf-8")
        purpose = "—"
        m = re.search(r"^##\s*(?:\d+\.\s*)?目的・ゴール\s*$", text, re.MULTILINE)
        if m:
            rest = text[m.end():]
            for line in rest.split("\n"):
                if line.strip() and not line.strip().startswith(("---", "#")):
                    purpose = line.strip()
                    break
        related = fm.get("related-modules") or []
        if isinstance(related, str):
            related = [related] if related else []
        rows.append([
            uc_dir.name,
            purpose,
            f"[description.md](system/specs/use-cases/{uc_dir.name}/description.md)",
            ", ".join(related) if related else "—",
            fm.get("last-updated-cr", cr),
        ])
    return rows


def _repo_spec_rows(xddp_dir: Path, docs: Path, affected_repos: list, cr: str) -> list:
    rows = []
    for repo in affected_repos:
        repo_latest = Path(xddp_dir) / "latest-specs" / repo
        if not repo_latest.exists():
            continue
        arch = repo_latest / "overview" / "architecture.md"
        fm = _read_frontmatter(arch)
        version = fm.get("version", "1.0.0")
        module_count = len([p for p in repo_latest.iterdir() if p.is_dir() and p.name != "overview"])
        rows.append([
            f"[{repo}]({repo}/specs/)",
            f"v{version}（最終更新CR: {cr}）",
            f"[overview]({repo}/specs/overview/)",
            f"{module_count} モジュール",
            cr,
        ])
    return rows


def _module_spec_rows(xddp_dir: Path, affected_repos: list, cr: str) -> list:
    rows = []
    for repo in affected_repos:
        repo_latest = Path(xddp_dir) / "latest-specs" / repo
        if not repo_latest.exists():
            continue
        for module_dir in sorted(p for p in repo_latest.iterdir() if p.is_dir() and p.name != "overview"):
            module = module_dir.name
            spec = f"[spec.md]({repo}/specs/{module}/spec.md)" if (module_dir / "spec.md").exists() else "—"
            structure = f"[structure.md]({repo}/specs/{module}/structure.md)" \
                if (module_dir / "structure.md").exists() else "—"
            rows.append([repo, module, spec, structure, "—", cr])
    return rows


def _cross_interface_rows(xddp_dir: Path, cr: str, breaking_interfaces: set) -> list:
    if_root = Path(xddp_dir) / "latest-specs" / "cross" / "interfaces"
    rows = []
    if not if_root.exists():
        return rows
    for if_dir in sorted(p for p in if_root.iterdir() if p.is_dir()):
        spec = if_dir / "spec.md"
        if not spec.exists():
            continue
        fm = _read_frontmatter(spec)
        name = if_dir.name
        if name in breaking_interfaces:
            name = f"{name} ⚠️ 破壊的変更あり（CR: {cr}）"
        schema = f"[schema.md](cross/specs/interfaces/{if_dir.name}/schema.md)" \
            if (if_dir / "schema.md").exists() else "—"
        rows.append([
            name,
            f"[spec.md](cross/specs/interfaces/{if_dir.name}/spec.md)",
            schema,
            f"v{fm.get('version', '1.0.0')}",
            fm.get("last-updated-cr", cr),
        ])
    return rows


def _glossary_term_count(path: Path) -> int:
    """`## 用語一覧` 見出し配下のテーブルのデータ行数（＝用語数）を数える。"""
    if not path.exists():
        return 0
    lines = path.read_text(encoding="utf-8").split("\n")
    idx = _find_heading(lines, "## 用語一覧")
    if idx is None:
        return 0
    start, end = _section_bounds(lines, idx)
    table = _find_table_bounds(lines, start, end)
    if table is None:
        return 0
    table_start, table_end = table
    return max(0, table_end - (table_start + 2))


def _crs_nav_rows(cr_path: Path, docs: Path, cr: str, affected_repos: list, has_cross: bool) -> list:
    rows = []
    crs_exists = (Path(cr_path) / "03_change-requirements" / f"CRS-{cr}.md").exists()
    if not crs_exists:
        return rows
    for repo in affected_repos:
        rows.append([f"{cr} {repo} 変更要求仕様", f"[CRS-{cr}.md]({repo}/crs/CRS-{cr}.md)"])
    if has_cross:
        rows.append([f"{cr} cross 変更要求仕様", f"[CRS-{cr}.md](cross/crs/CRS-{cr}.md)"])
    return rows


def _test_nav_rows(cr_path: Path, cr: str, affected_repos: list, has_cross: bool) -> list:
    rows = []
    targets = list(affected_repos) + (["cross"] if has_cross else [])
    for repo in targets:
        tsp_name = f"TSP-{cr}.md" if repo != "cross" else f"TSP-{cr}-cross.md"
        tsp_src = Path(cr_path) / "09_test-spec" / repo / tsp_name
        trs_dir = Path(cr_path) / "10_test-results" / repo
        trs_matches = sorted(trs_dir.glob(f"TRS-{cr}-*.md")) if trs_dir.exists() else []
        if not tsp_src.exists() and not trs_matches:
            continue
        tsp_cell = f"[{tsp_name}]({repo}/test/{tsp_name})" if tsp_src.exists() else "—"
        trs_cell = ", ".join(
            f"[{p.name}]({repo}/test/{p.name})" for p in trs_matches) if trs_matches else "—"
        rows.append([repo, tsp_cell, trs_cell, cr])
    return rows


def _glossary_rows(xddp_dir: Path, docs: Path, affected_repos: list, is_multi: bool) -> list:
    rows = []
    common = docs / "glossary.md"
    if common.exists():
        rows.append(["プロジェクト共通", f"[glossary.md](glossary.md)（用語数: {_glossary_term_count(common)}）"])
    for repo in affected_repos:
        repo_glossary = docs / repo / "knowledge" / "glossary.md"
        if repo_glossary.exists():
            rows.append([
                repo,
                f"[glossary.md]({repo}/knowledge/glossary.md)（用語数: {_glossary_term_count(repo_glossary)}）",
            ])
    if is_multi:
        cross_glossary = docs / "cross" / "knowledge" / "glossary.md"
        if cross_glossary.exists():
            rows.append([
                "cross",
                f"[glossary.md](cross/knowledge/glossary.md)（用語数: {_glossary_term_count(cross_glossary)}）",
            ])
    return rows


def _common_knowledge_rows(xddp_dir: Path, docs: Path, repos_keys: list, has_cross: bool,
                            cr: str) -> list:
    rows = []
    for repo in repos_keys:
        repo_rb = Path(xddp_dir) / f"project-rulebook-{repo}.md"
        if repo_rb.exists():
            rows.append([repo, f"[project-rulebook.md]({repo}/project-rulebook.md)", cr])
    if has_cross and (Path(xddp_dir) / "project-rulebook-cross.md").exists():
        rows.append(["cross", "[project-rulebook.md](cross/project-rulebook.md)", cr])
    return rows


def update_ai_index(xddp_dir: Path, docs: Path, cr: str, affected_repos: list, is_multi: bool,
                     has_cross: bool, force_full: bool, preupdated: dict,
                     breaking_interfaces: set, cr_path=None, repos_keys=None) -> dict:
    ai_index_path = docs / "AI_INDEX.md"
    if ai_index_path.exists():
        lines = _read_lines(ai_index_path)
    else:
        lines = AI_INDEX_SKELETON.split("\n")

    def _skip(section_key: str) -> bool:
        if force_full:
            return False
        return preupdated.get(section_key) == "済"

    # 1. ユースケース一覧
    if not _skip("ユースケース一覧"):
        rows = _usecase_rows(xddp_dir, cr)
        if rows or section_exists(lines, "## ユースケース一覧"):
            upsert_table(lines, "## ユースケース一覧",
                         ["ユースケース", "目的（1行）", "description", "関連モジュール", "最終更新CR"],
                         [0], rows)

    # 2. リポジトリ別仕様書（常時 upsert）
    repo_rows = _repo_spec_rows(xddp_dir, docs, affected_repos, cr)
    if repo_rows:
        upsert_table(lines, "## リポジトリ別仕様書",
                     ["リポジトリ", "バージョン", "overview", "モジュール数", "最終更新CR"],
                     [0], repo_rows)

    # 3. モジュール別最新仕様
    if not _skip("モジュール別最新仕様"):
        mod_rows = _module_spec_rows(xddp_dir, affected_repos, cr)
        if mod_rows:
            upsert_table(lines, "## モジュール別最新仕様",
                         ["リポジトリ", "モジュール", "spec", "structure", "state", "最終更新CR"],
                         [0, 1], mod_rows)

    # 4. クロスインタフェース一覧（IS_MULTI のみ）
    if is_multi and not _skip("クロスインタフェース一覧"):
        cross_rows = _cross_interface_rows(xddp_dir, cr, breaking_interfaces)
        if cross_rows:
            upsert_table(lines, "## クロスインタフェース一覧",
                         ["インタフェース", "spec", "schema", "バージョン", "最終更新CR"],
                         [0], cross_rows)

    # 5. 知識参照ガイド（初回のみ生成。docs/adr/ADR-0005 参照）
    if not section_exists(lines, "## 知識参照ガイド"):
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.extend(KNOWLEDGE_GUIDE_BLOCK)

    # 6. code-knowledge インデックス（常時 upsert）
    ck_rows = []
    for repo in list(affected_repos) + (["cross"] if is_multi else []):
        ck_root = docs / repo / "knowledge" / "code-knowledge"
        if not ck_root.exists():
            continue
        for module_dir in sorted(p for p in ck_root.iterdir() if p.is_dir() and not p.name.startswith("_")):
            if (module_dir / "constraints.md").exists():
                ck_rows.append([
                    f"{repo}/{module_dir.name} 制約・注意事項",
                    f"[constraints.md]({repo}/knowledge/code-knowledge/{module_dir.name}/constraints.md)",
                ])
        for special, label in (("_structures", "構造体関連図"), ("_constants", "共有定数"), ("_flows", "機能間フロー")):
            if (ck_root / special).exists():
                ck_rows.append([f"{repo} {label}", f"[{special}/]({repo}/knowledge/code-knowledge/{special}/)"])
    if ck_rows:
        upsert_table(lines, "## code-knowledge インデックス", ["知りたいこと", "参照先"], [0], ck_rows)

    # 7. 変更要求仕様書（CRS）ナビゲーション（常時 upsert。CRS が存在する場合のみ行を持つ）
    if cr_path is not None:
        crs_rows = _crs_nav_rows(cr_path, docs, cr, affected_repos, has_cross)
        if crs_rows:
            upsert_table(lines, "## 変更要求仕様書（CRS）ナビゲーション", ["知りたいこと", "参照先"], [0], crs_rows)

        # テスト仕様（TSP）・テスト結果（TRS）（常時 upsert）
        test_rows = _test_nav_rows(cr_path, cr, affected_repos, has_cross)
        if test_rows:
            upsert_table(lines, "## テスト仕様（TSP）・テスト結果（TRS）",
                         ["リポジトリ", "TSP", "TRS", "最終更新CR"], [0], test_rows)

    # 8. 用語集（常時 upsert）
    glossary_rows = _glossary_rows(xddp_dir, docs, affected_repos, is_multi)
    if glossary_rows:
        upsert_table(lines, "## 用語集", ["知りたいこと", "参照先"], [0], glossary_rows)

    # 共通知識（Step C6 が project-rulebook 昇格時に upsert）
    common_rows = _common_knowledge_rows(xddp_dir, docs, repos_keys or affected_repos, has_cross, cr)
    if common_rows:
        upsert_table(lines, "## 共通知識", ["リポジトリ", "project-rulebook", "最終更新CR"], [0], common_rows)

    return {"lines": lines}


# ---------------------------------------------------------------------------
# Step C2 サイズポリシー（500行超のアーカイブ候補検出）
# ---------------------------------------------------------------------------

ARCHIVE_ROW_CR_RE = re.compile(r"\bCR-[A-Za-z0-9_-]+\b")


def detect_archive_candidates(lines: list) -> list:
    if len(lines) <= 500:
        return []
    candidates = []
    for line in lines:
        s = line.strip()
        if not s.startswith("|") or s.startswith("|---"):
            continue
        cells = _split_row(s)
        if not cells:
            continue
        crs = ARCHIVE_ROW_CR_RE.findall(cells[-1])
        if crs:
            candidates.append((cells[0], crs[-1]))
    candidates.sort(key=lambda t: t[1])
    return [f"{name} — 最終更新CR: {cr}" for name, cr in candidates]


# ---------------------------------------------------------------------------
# Step C3: Promote Lessons Learned Log
# ---------------------------------------------------------------------------

LL_ENTRY_RE = re.compile(r"^### (LL-\S+)：")
LL_META_RE = re.compile(
    r"\*\*CR：\*\*\s*(?P<cr>\S+)\s*／\s*\*\*工程：\*\*\s*(?P<phase>[^／]+?)\s*／\s*"
    r"\*\*repo：\*\*\s*(?P<repo>[^／]+?)\s*／\s*\*\*タグ：\*\*\s*(?P<tags>.+)$")


def _split_ll_entries(lines: list) -> list:
    """`### LL-NNN：` 見出しを持つブロックのリストを返す（各要素は行のリスト）。"""
    entries = []
    current = None
    for line in lines:
        if LL_ENTRY_RE.match(line):
            if current is not None:
                entries.append(current)
            current = [line]
        elif current is not None:
            current.append(line)
    if current is not None:
        entries.append(current)
    return entries


def promote_lessons_learned(lessons_file: Path, docs: Path, cr: str, has_cross: bool,
                             repo_results: dict) -> list:
    """今回 CR の LL エントリを repo: タグでファイル振り分けする。戻り値: 要確認LL（repo:unknown）一覧。

    repo 単位で書き込みを try/except し、1 repo の失敗（例: ENOTDIR）が他 repo の振り分けを
    止めないようにする（promote_specs と同じ方針。レビュー指摘#10 相当）。
    """
    lines = _read_lines(lessons_file)
    entries = _split_ll_entries(lines)
    unresolved = []

    by_repo = {}
    for entry in entries:
        header = entry[0]
        entry_id_m = LL_ENTRY_RE.match(header)
        entry_id = entry_id_m.group(1) if entry_id_m else "LL-???"
        meta_match = None
        for line in entry[:5]:
            m = LL_META_RE.search(line)
            if m:
                meta_match = m
                break
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
                target_lines = [f"# 知見ログ: {repo}", "> xddp.close が CR クローズ時に自動追記します。", ""]
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
                       archive_candidates: list, global_errors: list) -> None:
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

    lines.append("## AI_INDEX.md アーカイブ候補")
    if archive_candidates:
        for a in archive_candidates:
            lines.append(f"- {a}")
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
    breaking_set = set(breaking_interfaces) if breaking_parseable else set()

    preupdated = read_ai_index_preupdated(cr_path)
    try:
        ai_index_result = update_ai_index(
            xddp_dir, docs, args.cr, affected_repos, args.is_multi, args.has_cross,
            args.force_full_ai_index, preupdated, breaking_set, cr_path=cr_path,
            repos_keys=repos_keys)
        ai_lines = ai_index_result["lines"]
        archive_candidates = detect_archive_candidates(ai_lines)
        _write_lines(docs / "AI_INDEX.md", ai_lines)
    except Exception as e:  # noqa: BLE001 — AI_INDEX.md 更新失敗で他ステップまで止めない
        archive_candidates = []
        global_errors.append(f"AI_INDEX.md 更新: {e}")

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
        archive_candidates, global_errors)

    print(json.dumps({
        "ok": True,
        "repo_results": repo_results,
        "unresolved_ll": unresolved_ll,
        "breaking_found": breaking_found,
        "breaking_parseable": breaking_parseable,
        "deletion_candidates": deletion_candidates,
        "archive_candidates": archive_candidates,
        "backlog_promoted": backlog_promoted,
        "global_errors": global_errors,
        "output_file": str(args.output_file),
    }, ensure_ascii=False))


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
    p_run.add_argument("--force-full-ai-index", action="store_true")
    p_run.add_argument("--output-file", required=True)
    p_run.set_defaults(func=cmd_run)

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
