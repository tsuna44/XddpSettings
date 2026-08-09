"""
artifact_lint.py — 成果物の機械検査（フロントマター必須キー・Mermaid基本構文・Markdownテーブル列数・CRS構造）CLI

xddp-reviewer（AIレビュアー）へ渡す前段の機械検査。検出のみを行い、レビューを停止させない
（`xddp.common/SKILL.md`「## Invoke Reviewer」から呼び出され、結果 JSON は `LINT_RESULTS` として
レビュアーに渡される）。

検査内容:
- フロントマター必須キー: `--doc-type SPEC` かつファイル先頭が YAML フロントマター（`---` 区切り）の
  場合のみ実施する（他の DOCUMENT_TYPE・フロントマターを持たない SPEC 以外の文書は自動スキップ）。
  必須キーはベースキー（`version`・`last-updated-cr`・`last-verified-cr`・`source`・`has_insights`）
  ＋ `latest-specs/` 配下の相対パスパターンごとの追加キーで決まる。
- Mermaid ブロック基本構文: 図種別キーワードの有無・空ブロック検出・括弧/引用符の対応・
  `-->` 系エッジ記法の明白な破損（全 DOCUMENT_TYPE 共通）。
- Markdown テーブル: ヘッダ行と本体行の列数一致（全 DOCUMENT_TYPE 共通）。
- CRS 構造チェック: `--doc-type CRS` のときのみ実施する USDM 構造の決定的検査（L1〜L13）。
  理由の必須性・ID一意性・仕様グループ配下のSP存在・グループ名 `＜＞` 表記・「等」等の曖昧表現・
  SP本文の重複・否定表現候補・分割軸の列挙値・要求3階層の兆候（SR-a-b-c）・H7見出しの不在（L12）・
  CR プレフィクスを欠く要求 ID の検出（L13 fail-loud）を検出する。ID 形式は形式 B（CR 名前空間先頭。
  例 `CR-2026-970-UR-001`・`CR-2026-970-SR-001-001`・`CR-2026-970-SP-001-001.010`）。
  見出し体系は USDM Canonical（カテゴリ=H3 ＜＞・UR=H4・要求グループ=H5 ＜＞・SR=H6・仕様グループ=太字行・SP=リスト項目）。
  出典: AFFORDD USDM小冊子（基礎編4.5.3-4.5.5・4.2.4・3.1-3.2）・AFFORDD usdm-schema v1.1.0。
- ANA §0 degraded mode 注記チェック（A1）: `--doc-type ANA` のときのみ実施する。「参照した既存ドキュメント」
  セクション（`## 0.`〜次の `## ` 見出し直前）のテーブル出典ファイル列に `latest-specs/` 由来の参照が
  1件以上含まれる場合、同セクションに `degraded mode` を含む注記があるかを検査する（`xddp-analyst-agent.md`
  Analysis Method 手順10 が要求する注記の欠落を検知する）。この判定は呼び出し元からモードを受け取らず
  §0 の内容自体から再構成するため、`xddp.02.analysis` 経由・`xddp.review` 経由のいずれの呼び出しでも
  同一に働く（PLAN-20260807-ana-degraded-note-lint-check 参照）。

完全な YAML パーサ・Mermaid パーサの再実装はしない（標準ライブラリのみという制約、および
「構文が明白に壊れた図/フロントマターが人レビューまで流れる」大半のケースを止めることが目的のため）。

Usage:
  python3 artifact_lint.py --file TARGET_FILE --doc-type DOCUMENT_TYPE
  python3 artifact_lint.py --files f1,f2,... --doc-type DOCUMENT_TYPE

Output: 成功時は stdout に JSON 1オブジェクト（{"ok": true, ...}）。
        失敗時（ファイル不在等）は exit code 非0 + stderr にメッセージ。
"""

import argparse
import json
import re
import sys
from pathlib import Path

BASE_FRONTMATTER_KEYS = ["version", "last-updated-cr", "last-verified-cr", "source", "has_insights"]

MERMAID_KEYWORDS = (
    "sequenceDiagram", "stateDiagram-v2", "stateDiagram", "classDiagram",
    "erDiagram", "graph", "flowchart",
)
FLOWCHART_KEYWORDS = ("graph", "flowchart")

MERMAID_FENCE_RE = re.compile(r"^```mermaid\s*$")
FENCE_END_RE = re.compile(r"^```\s*$")
KEY_LINE_RE = re.compile(r"^([A-Za-z0-9_-]+):(.*)$")

# ── CRS 構造チェック用パターン（USDM Canonical heading system。H1〜H6 のみ使用し H7 は使わない）──
# crs_md2excel.py parse_crs_md と同じ見出し→種別マッピングを持つ。
CRS_CATEGORY_RE = re.compile(r"^### ＜(.+)＞")          # H3 カテゴリ（機能要求／非機能要求）
CRS_H4_RE = re.compile(r"^#### (.*)")                   # H4 UR（または親URなしプレースホルダ）
CRS_H5_RE = re.compile(r"^##### (.*)")                  # H5 要求グループ
CRS_H6_RE = re.compile(r"^###### (.*)")                 # H6 SR
CRS_SPEC_GROUP_RE = re.compile(r"^\*\*(＜.+＞)\*\*\s*$")  # 仕様グループ（太字行。名前は ＜＞ 込みで捕捉）
# SP（リスト項目）: 形式 B（CR 名前空間先頭）。CR 部（\S+）＋種別インフィクス -SP- ＋数字始まりの
# ローカル番号でアンカーし、CR の内部構造を仮定しない（CLAUDE.md「CR 形式可変」＝決定 2）。
CRS_SP_ITEM_RE = re.compile(r"^\s*-\s+\*\*(\S+-SP-\d\S*)\*\*[：:]")
CRS_H7_MARKER_RE = re.compile(r"^####### ")            # H7 検出用（新体系では不在であるべき L12）
# UR/SR も同様に CR プレフィクス（非空）＋種別インフィクスでアンカー。旧形式 `UR-001`（種別が先頭・
# CR プレフィクスなし）はマッチせず、新形式厳格化（決定 1）を regex で担保する。
CRS_UR_ID_RE = re.compile(r"^(\S+-UR-\d\S*)\s*(.*)")
CRS_SR_ID_RE = re.compile(r"^(\S+-SR-\d\S*)\s*(.*)")
# CR プレフィクスを欠く（種別プレフィクスが先頭の）旧形式 ID 検出用（L13 fail-loud）。
# これらは正規の ID として扱わず、黙殺せず error として顕在化させる（§3.3(c)）。
CRS_UR_NO_CR_RE = re.compile(r"^UR-\d")
CRS_SR_NO_CR_RE = re.compile(r"^SR-\d")
CRS_SP_ITEM_NO_CR_RE = re.compile(r"^\s*-\s+\*\*(SP-\d\S*)\*\*[：:]")
CRS_FIELD_RE = re.compile(r"^\s*-\s+\*\*([^*：:]+)[：:]\*\*\s*(.*)$")
CRS_GROUP_NAME_RE = re.compile(r"^＜.+＞$")
CRS_NOISE_TERMS = ("等", "その他", "T.B.D.", "TBD", "etc")
CRS_SPLIT_AXES = {"時系列分割", "構成分割", "状態分割", "共通分割"}


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def _required_keys_for_path(rel_path: str) -> list:
    parts = Path(rel_path).parts
    extra = []
    if len(parts) >= 3 and parts[0] == "cross" and parts[1] == "interfaces":
        filename = parts[-1]
        if filename == "spec.md":
            extra = ["interface", "breaking", "provider", "affected-repos"]
        elif filename == "schema.md":
            extra = ["interface", "provider"]
    elif len(parts) >= 2 and parts[0] == "cross" and parts[1] == "sequences":
        extra = []
    elif len(parts) >= 2 and parts[0] == "system" and parts[1] == "use-cases":
        if parts[-1] == "description.md":
            extra = ["related-modules"]
        else:
            extra = []
    elif len(parts) >= 2 and parts[1] == "overview":
        extra = ["repo"]
    elif len(parts) >= 2:
        extra = ["module", "repo"]
    return BASE_FRONTMATTER_KEYS + extra


def _relative_to_latest_specs(path: Path) -> str:
    parts = path.parts
    if "latest-specs" in parts:
        idx = parts.index("latest-specs")
        return str(Path(*parts[idx + 1:]))
    return str(path)


def _lint_frontmatter(lines: list, doc_type: str, rel_path: str) -> dict:
    result = {"applicable": False}
    if doc_type != "SPEC":
        return result
    if not lines or lines[0].strip() != "---":
        return result
    result["applicable"] = True
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        result["valid_yaml"] = False
        result["missing_keys"] = []
        result["issues"] = ["フロントマターの閉じ `---` が見つかりません"]
        return result

    block = lines[1:end_idx]
    found_keys = []
    valid = True
    issues = []
    for line in block:
        if not line.strip():
            continue
        if line.startswith((" ", "\t", "-")):
            continue  # リスト項目・継続行
        m = KEY_LINE_RE.match(line)
        if not m:
            valid = False
            issues.append(f"YAML として解釈できない行: {line!r}")
            continue
        found_keys.append(m.group(1))

    required = _required_keys_for_path(rel_path)
    missing = [k for k in required if k not in found_keys]

    result["valid_yaml"] = valid
    result["required_keys"] = required
    result["missing_keys"] = missing
    if issues:
        result["issues"] = issues
    return result


def _lint_mermaid(lines: list) -> list:
    blocks = []
    i = 0
    block_index = 0
    while i < len(lines):
        if MERMAID_FENCE_RE.match(lines[i]):
            start = i + 1
            j = start
            body = []
            while j < len(lines) and not FENCE_END_RE.match(lines[j]):
                body.append(lines[j])
                j += 1
            issues = _check_mermaid_block(body)
            blocks.append({"block_index": block_index, "start_line": i + 1, "issues": issues})
            block_index += 1
            i = j + 1
            continue
        i += 1
    return blocks


def _check_mermaid_block(body: list) -> list:
    issues = []
    non_empty = [l for l in body if l.strip()]
    if not non_empty:
        issues.append("Mermaid ブロックが空です")
        return issues

    first_line = non_empty[0].strip()
    diagram_type = None
    for kw in MERMAID_KEYWORDS:
        if first_line.startswith(kw):
            diagram_type = kw
            break
    if diagram_type is None:
        issues.append(f"図種別キーワードが先頭行に見つかりません: {first_line!r}")

    text = "\n".join(body)
    for open_c, close_c, name in (("(", ")", "丸括弧"), ("[", "]", "角括弧"), ("{", "}", "波括弧")):
        if text.count(open_c) != text.count(close_c):
            issues.append(f"{name}の対応が取れていません（{open_c}: {text.count(open_c)} / {close_c}: {text.count(close_c)}）")

    if text.count('"') % 2 != 0:
        issues.append("二重引用符の対応が取れていません")

    if diagram_type in FLOWCHART_KEYWORDS:
        for line in non_empty[1:]:
            if "->" in line and "-->" not in line:
                issues.append(f"エッジ記法が破損している可能性があります（`-->` ではなく `->`）: {line.strip()!r}")

    return issues


def _iter_table_body_rows(lines: list):
    """Markdownテーブルの本体行を (行インデックス, ヘッダ列数, セル値リスト) として順に yield する。"""
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]) and "-" in lines[i + 1]:
            header_cols = len(_split_row(line))
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                yield j, header_cols, _split_row(lines[j])
                j += 1
            i = j
            continue
        i += 1


def _lint_tables(lines: list) -> list:
    issues = []
    for j, header_cols, cells in _iter_table_body_rows(lines):
        row_cols = len(cells)
        if row_cols != header_cols:
            issues.append({
                "line": j + 1,
                "issue": f"テーブルの列数がヘッダ（{header_cols}列）と一致しません（{row_cols}列）",
            })
    return issues


def _split_row(line: str) -> list:
    r"""Markdown テーブル行をセルへ分割する。

    GFM ではセル内の `|` を `\|` でエスケープでき、コードスパン内でも同様に扱われる。
    これを区切りとして数えると、正しく書かれたテーブルを列数不一致と誤判定する
    （PLAN-20260808 不具合1・二次被害B。本スクリプトは Invoke Reviewer 経由で
    LINT_RESULTS としてレビュアーへ渡されるため、誤検出は全 DOCUMENT_TYPE の
    レビューへ偽指摘として波及する）。
    """
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return re.split(r"(?<!\\)\|", stripped)


def _crs_normalize(text: str) -> str:
    """空白類を除去して比較用に正規化する。"""
    return re.sub(r"\s+", "", text or "")


def _crs_is_negation(text: str) -> bool:
    """述語が「〜しない」で終わるか（末尾の句点・鉤括弧・空白を除いて判定）。"""
    return _crs_normalize(text).rstrip("。」）)").endswith("しない")


def _parse_crs(lines: list) -> dict:
    """CRS Markdown を構造化する。crs_md2excel.py parse_crs_md と同じ見出し規則を用いる。

    Returns dict: categories / urs / srs / req_groups / spec_groups / sps / all_ids。
    """
    categories = []
    urs = []          # {id, reason}
    srs = []          # {id, reason, group_idx}
    req_groups = []   # {name, split_axis, sr_count}
    spec_groups = []  # {name, sp_count}
    sps = []          # {id, before, after, spec}
    all_ids = []      # 出現順の全ID（UR/SR/SP）
    cr_missing = []   # CR プレフィクスを欠く（種別が先頭の）ID（L13 fail-loud 用）

    cur = None            # ('ur'|'sr'|'sp', index) — フィールド行の帰属先
    cur_group_idx = None  # 現在の要求グループ（UR切替でリセット）
    cur_spec_idx = None   # 現在の仕様グループ

    for raw in lines:
        line = raw.rstrip("\n")

        # カテゴリ（H3 ＜…＞）: 機能要求／非機能要求の要求種別軸
        m = CRS_CATEGORY_RE.match(line)
        if m:
            categories.append(m.group(1).strip())
            cur = None
            cur_group_idx = None
            cur_spec_idx = None
            continue

        # 仕様グループ（太字行 **＜…＞**）: H7 廃止に伴い見出しではなく太字行で表す
        m = CRS_SPEC_GROUP_RE.match(line)
        if m:
            spec_groups.append({"name": m.group(1).strip(), "sp_count": 0})
            cur_spec_idx = len(spec_groups) - 1
            cur = None
            continue

        # SP（リスト項目 - **SP-…**: …）: 属性 field 行より先に評価する（#26 の順序契約）
        m = CRS_SP_ITEM_RE.match(line)
        if m:
            sps.append({"id": m.group(1), "before": "", "after": "", "spec": ""})
            all_ids.append(m.group(1))
            cur = ("sp", len(sps) - 1)
            if cur_spec_idx is not None:
                spec_groups[cur_spec_idx]["sp_count"] += 1
            continue
        # CR プレフィクスを欠く SP 項目（`- **SP-…**：`）は正規 SP として扱わず記録する（L13）
        nm = CRS_SP_ITEM_NO_CR_RE.match(line)
        if nm:
            cr_missing.append(nm.group(1))
            continue

        # UR（H4）: UR-プレフィックスなら実UR、それ以外は親URなしプレースホルダ
        m = CRS_H4_RE.match(line)
        if m:
            body = m.group(1).strip()
            um = CRS_UR_ID_RE.match(body)
            if um:
                urs.append({"id": um.group(1), "reason": ""})
                all_ids.append(um.group(1))
                cur = ("ur", len(urs) - 1)
            else:
                if CRS_UR_NO_CR_RE.match(body):
                    # CR プレフィクスを欠く UR 見出し（`#### UR-001 …`）を記録（L13）
                    cr_missing.append(body.split()[0])
                cur = None  # UR-プレフィックスでない h4（プレースホルダグループ等）
            cur_group_idx = None
            cur_spec_idx = None
            continue

        # 要求グループ（H5 ＜…＞）
        m = CRS_H5_RE.match(line)
        if m:
            req_groups.append({"name": m.group(1).strip(), "split_axis": None, "sr_count": 0})
            cur_group_idx = len(req_groups) - 1
            cur_spec_idx = None
            cur = None
            continue

        # SR（H6）: 要求グループが H5 へ移ったため H6 は SR 専用
        m = CRS_H6_RE.match(line)
        if m:
            body = m.group(1).strip()
            sm = CRS_SR_ID_RE.match(body)
            if sm:
                srs.append({"id": sm.group(1), "reason": "", "group_idx": cur_group_idx})
                all_ids.append(sm.group(1))
                cur = ("sr", len(srs) - 1)
                if cur_group_idx is not None:
                    req_groups[cur_group_idx]["sr_count"] += 1
                cur_spec_idx = None
            else:
                if CRS_SR_NO_CR_RE.match(body):
                    # CR プレフィクスを欠く SR 見出し（`###### SR-001-001 …`）を記録（L13）
                    cr_missing.append(body.split()[0])
                cur = None
            continue

        fm = CRS_FIELD_RE.match(line)
        if not fm:
            continue
        marker = fm.group(1).strip()
        value = fm.group(2).strip()
        if cur is not None:
            kind, idx = cur
            if kind == "ur" and marker == "理由":
                urs[idx]["reason"] = value
            elif kind == "sr" and marker == "理由":
                srs[idx]["reason"] = value
            elif kind == "sp":
                if marker == "Before":
                    sps[idx]["before"] = value
                elif marker == "After":
                    sps[idx]["after"] = value
                elif marker == "仕様":
                    sps[idx]["spec"] = value
        # 分割軸は要求グループ見出し直後（cur=None）に現れる
        if marker == "分割軸" and cur_group_idx is not None:
            req_groups[cur_group_idx]["split_axis"] = value

    return {
        "categories": categories,
        "urs": urs,
        "srs": srs,
        "req_groups": req_groups,
        "spec_groups": spec_groups,
        "sps": sps,
        "all_ids": all_ids,
        "cr_missing": cr_missing,
    }


def _lint_crs(lines: list, doc_type: str) -> dict:
    """CRS 構造チェック（L1〜L12）。`--doc-type CRS` 以外では applicable=False。"""
    result = {"applicable": False}
    if doc_type != "CRS":
        return result
    result["applicable"] = True
    issues = []

    def add(check, level, message, ident=""):
        issues.append({"check": check, "level": level, "id": ident, "message": message})

    data = _parse_crs(lines)

    # L1: SP本文（Before/After）に「等」「その他」「T.B.D.」「TBD」「etc」を含む
    for sp in data["sps"]:
        body = f"{sp['before']} {sp['after']} {sp['spec']}"
        low = body.lower()
        for term in CRS_NOISE_TERMS:
            if (term.lower() in low) if term == "etc" else (term in body):
                add("L1", "warning", f"SP本文に曖昧表現「{term}」を含みます（基礎編4.5.5）", sp["id"])
                break

    # L2: UR の理由が空でない
    for ur in data["urs"]:
        if not ur["reason"]:
            add("L2", "error", "UR の理由が空です（理由は必須）", ur["id"])

    # L3: SR の理由が空でない（強制2層＝要求グループ内SR単一のときは除外）
    for sr in data["srs"]:
        if sr["reason"]:
            continue
        gidx = sr["group_idx"]
        forced_two_layer = gidx is not None and data["req_groups"][gidx]["sr_count"] == 1
        if not forced_two_layer:
            add("L3", "warning", "SR の理由が空です（強制2層以外では記載を推奨）", sr["id"])

    # L4: 各仕様グループ配下に SP が1件以上
    for g in data["spec_groups"]:
        if g["sp_count"] == 0:
            add("L4", "error", f"仕様グループ「{g['name']}」配下に SP がありません", g["name"])

    # L5: SR の ID が3セグメント以上（SR-a-b-c＝要求3階層の兆候）
    #     形式 B では ID に CR プレフィクスが付くため、ID から `SR-` 以降のローカル番号部のみを
    #     取り出し、その数値セグメント数で判定する（CR プレフィクスを 3 階層と誤検知しない）。
    for sr in data["srs"]:
        m = re.search(r"SR-(\d+(?:-\d+)*)", sr["id"])
        segs = m.group(1).split("-") if m else []
        if len(segs) >= 3:
            add("L5", "error", "SR の ID が3階層構造（SR-a-b-c）です（要求3階層は禁止）", sr["id"])

    # L6: SP本文（Before+After）の重複（正規化後の完全一致）
    seen_bodies = {}
    for sp in data["sps"]:
        after_n = _crs_normalize(sp["after"])
        if not after_n or after_n == "なし" or after_n.startswith("{"):
            continue  # 空After・「なし」・未編集プレースホルダ {…} は重複判定から除外
        key = _crs_normalize(sp["before"]) + "\x00" + after_n
        if key in seen_bodies:
            add("L6", "warning", f"SP本文が {seen_bodies[key]} と重複しています（ペースト作文の疑い）", sp["id"])
        else:
            seen_bodies[key] = sp["id"]

    # L7: ID（UR/SR/SP）が文書全体で一意
    seen_ids = set()
    dup_ids = set()
    for i in data["all_ids"]:
        if i in seen_ids:
            dup_ids.add(i)
        seen_ids.add(i)
    for i in sorted(dup_ids):
        add("L7", "error", "ID が文書内で重複しています", i)

    # L8: カテゴリ（### ＜…＞）が1件以上
    if not data["categories"]:
        add("L8", "error", "カテゴリ（### ＜…＞）が1件もありません", "")

    # L9: グループ名が ^＜.+＞$ にマッチ
    for g in data["req_groups"]:
        if not CRS_GROUP_NAME_RE.match(g["name"]):
            add("L9", "warning", f"要求グループ名が ＜＞ 表記ではありません: {g['name']!r}", g["name"])
    for g in data["spec_groups"]:
        if not CRS_GROUP_NAME_RE.match(g["name"]):
            add("L9", "warning", f"仕様グループ名が ＜＞ 表記ではありません: {g['name']!r}", g["name"])

    # L10: SP本文の述語が「〜しない」で終わる（否定表現の候補）
    for sp in data["sps"]:
        for field_val in (sp["before"], sp["after"], sp["spec"]):
            if _crs_is_negation(field_val):
                add("L10", "warning", "SP本文が否定表現「〜しない」で終わります（else側の仕様併記を確認）", sp["id"])
                break

    # L11: 分割軸の値が列挙値のいずれか（未編集プレースホルダ {…} は対象外）
    for g in data["req_groups"]:
        axis = g["split_axis"]
        if axis is None or axis.startswith("{") or not axis:
            continue
        if axis not in CRS_SPLIT_AXES:
            add("L11", "warning", f"分割軸の値が列挙外です: {axis!r}", g["name"])

    # L12: H7見出し（#######）の不在（見出しレベルと要素種別の1対1・CommonMarkはH6まで）
    #      新体系では仕様グループは太字行・SPはリスト項目で表すため H7 は使用しない（schema §9.9-1）
    for raw in lines:
        if CRS_H7_MARKER_RE.match(raw.rstrip("\n")):
            add("L12", "error",
                "H7見出し（#######）は使用しません（H1〜H6のみ。仕様グループは太字行・SPはリスト項目で表す）",
                "")
            break

    # L13: CR プレフィクスを欠く要求 ID（種別プレフィクスが先頭の旧形式）を検出（§3.3(c) fail-loud）
    #      新形式厳格化（決定 1）により `#### UR-001`・`- **SP-001-001.001**：` 等は正規 ID として
    #      解析されず黙って消える。これを error として顕在化させ、生成側の CR プレフィクス付与漏れが
    #      lint 段階で発覚するようにする。
    for ident in data["cr_missing"]:
        add("L13", "error",
            "要求 ID に CR プレフィクスがありません（形式 B: {CR}-UR/SR/SP-…。例 CR-2026-970-UR-001）",
            ident)

    result["issues"] = issues
    return result


ANA_SECTION0_RE = re.compile(r"^## 0\. ")
ANA_DEGRADED_MARKER = "degraded mode"
ANA_LATEST_SPECS_SEGMENT = "/latest-specs/"


def _extract_h2_section(lines: list, start_re) -> list:
    """指定した見出し（H2）の直後から次のH2見出し直前までの行を抽出する。見出しが無ければ空リスト。"""
    start = None
    for i, line in enumerate(lines):
        if start_re.match(line):
            start = i + 1
            break
    if start is None:
        return []
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return lines[start:end]


def _extract_table_first_column(lines: list) -> list:
    """Markdownテーブルの1列目（ヘッダ・区切り行を除く本体行）の値一覧を返す。"""
    return [cells[0].strip() for _, _, cells in _iter_table_body_rows(lines) if cells and cells[0].strip()]


def _find_first_table_header_index(lines: list) -> int:
    """最初のMarkdownテーブルのヘッダ行インデックスを返す（テーブルが無ければ len(lines)）。"""
    for i in range(len(lines) - 1):
        if lines[i].strip().startswith("|") and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]) and "-" in lines[i + 1]:
            return i
    return len(lines)


def _lint_ana(lines: list, doc_type: str) -> dict:
    """ANA §0 の degraded mode 注記チェック（A1）。`--doc-type ANA` 以外では applicable=False。

    呼び出し元から DOMAIN_REF_MODE を受け取らず、§0 テーブルの出典ファイル列自体から
    degraded 由来（`latest-specs/` 参照）の有無を判定する。xddp-analyst-agent.md の
    DOMAIN_REF_MODE 判定規則（1件以上が latest-specs/ 由来なら degraded）と数学的に同値の
    判定を ANA の内容から直接再構成することで、呼び出し元ごとの配線を不要にする。
    """
    result = {"applicable": False}
    if doc_type != "ANA":
        return result
    result["applicable"] = True
    issues = []

    section = _extract_h2_section(lines, ANA_SECTION0_RE)
    if not section:
        issues.append({
            "check": "A1", "level": "error", "id": "",
            "message": "ANA §0「参照した既存ドキュメント」見出し（`## 0.`）が見つかりません",
        })
    else:
        has_degraded_source = any(
            ANA_LATEST_SPECS_SEGMENT in cell for cell in _extract_table_first_column(section)
        )
        if has_degraded_source:
            note_end = _find_first_table_header_index(section)
            normalized = _crs_normalize("\n".join(section[:note_end])).lower()
            if _crs_normalize(ANA_DEGRADED_MARKER).lower() not in normalized:
                issues.append({
                    "check": "A1", "level": "error", "id": "",
                    "message": "ANA §0 の出典ファイルに `latest-specs/` 由来の参照が含まれていますが、"
                               "「degraded mode」を含む注記が見つかりません"
                               "（xddp-analyst-agent.md Analysis Method 手順10 参照）",
                })

    result["issues"] = issues
    return result


def lint_file(path: Path, doc_type: str) -> dict:
    if not path.exists():
        _err(f"ファイルが見つかりません: {path}")
    lines = path.read_text(encoding="utf-8").split("\n")
    rel_path = _relative_to_latest_specs(path)
    return {
        "file": str(path),
        "frontmatter": _lint_frontmatter(lines, doc_type, rel_path),
        "mermaid": _lint_mermaid(lines),
        "tables": _lint_tables(lines),
        "crs": _lint_crs(lines, doc_type),
        "ana": _lint_ana(lines, doc_type),
    }


def cmd_run(args) -> None:
    if args.files:
        paths = [Path(p.strip()) for p in args.files.split(",") if p.strip()]
        results = [lint_file(p, args.doc_type) for p in paths]
        print(json.dumps({"ok": True, "results": results}, ensure_ascii=False))
    else:
        result = lint_file(Path(args.file), args.doc_type)
        print(json.dumps({"ok": True, **result}, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file")
    group.add_argument("--files")
    parser.add_argument("--doc-type", required=True)
    parser.set_defaults(func=cmd_run)
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
