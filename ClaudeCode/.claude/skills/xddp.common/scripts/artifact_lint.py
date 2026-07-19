"""
artifact_lint.py — 成果物の機械検査（フロントマター必須キー・Mermaid基本構文・Markdownテーブル列数）CLI

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


def _lint_tables(lines: list) -> list:
    issues = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]) and "-" in lines[i + 1]:
            header_cols = len(_split_row(line))
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                row_cols = len(_split_row(lines[j]))
                if row_cols != header_cols:
                    issues.append({
                        "line": j + 1,
                        "issue": f"テーブルの列数がヘッダ（{header_cols}列）と一致しません（{row_cols}列）",
                    })
                j += 1
            i = j
            continue
        i += 1
    return issues


def _split_row(line: str) -> list:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return stripped.split("|")


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
