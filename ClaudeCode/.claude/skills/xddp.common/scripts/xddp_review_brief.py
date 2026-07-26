"""
xddp_review_brief.py — Human Review Gate 向けレビューブリーフ生成（baseline / generate）

人レビューゲート表示時に、成果物内に既に存在する不確実性データ（AIレビューの未解決指摘・
grep未対応パターン・要確認/推定注記・確信度 MEDIUM/MODULE-LEVEL）を機械的に集約し、
「人が見るべき箇所トップN」「前工程からの差分サマリー」「推奨レビュー順序と目安時間」の
3セクションからなる1ページのブリーフを生成する。意味判定（どれが本当に重要か）はしない。
機械的な語彙一致による surface（可視化）とランク付けに留め、最終判断は人に委ねる。

Usage:
  python3 xddp_review_brief.py baseline --root CR_PATH --step STEP_NUM --out OUT_JSON
  python3 xddp_review_brief.py generate --root CR_PATH --step STEP_NUM \
    [--baseline BASELINE_JSON] --out OUT_MD [--top-n N]

Output: 成功時は stdout に JSON 1オブジェクト（{"ok": true, ...}）。
        失敗時（root ディレクトリ不在等）は exit code 非0 + stderr にメッセージ。
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

DEFAULT_TOP_N = 10
MAX_MINUTES_PER_FILE = 30
BASE_MINUTES = 2

MARKER_WEIGHTS = {
    "review_critical": 100,
    "grep_uncovered": 50,
    "needs_confirmation": 50,
    "module_level": 20,
    "medium_confidence": 20,
    "estimated": 5,
}

MARKER_LABELS = {
    "review_critical": "未解決レビュー指摘",
    "grep_uncovered": "grep未対応パターン",
    "needs_confirmation": "要確認注記",
    "module_level": "確信度MODULE-LEVEL",
    "medium_confidence": "確信度MEDIUM",
    "estimated": "推定注記",
}

TABLE_SEPARATOR_RE = re.compile(r"^\|?[\s:|-]+\|?$")


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def _sha256_and_lines(path: Path):
    h = hashlib.sha256()
    data = path.read_bytes()
    h.update(data)
    lines = data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
    return h.hexdigest(), lines


def _is_control_file(path: Path, root: Path) -> bool:
    if path.parent != root:
        return False
    name = path.name
    if name == ".gate-snapshot.json":
        return True
    if name == ".review-brief.md":
        return True
    if name.startswith(".phase-baseline-") and name.endswith(".json"):
        return True
    return False


def _scan(root: Path, exclude_abs: set) -> dict:
    files = {}
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        if p.resolve() in exclude_abs:
            continue
        if _is_control_file(p, root):
            continue
        rel = p.relative_to(root).as_posix()
        sha, lines = _sha256_and_lines(p)
        files[rel] = {"sha256": sha, "lines": lines}
    return files


def cmd_baseline(args) -> None:
    root = Path(args.root)
    if not root.exists():
        _err(f"root ディレクトリが見つかりません: {root}")
    out_path = Path(args.out)
    exclude_abs = {out_path.resolve()}
    files = _scan(root, exclude_abs)
    data = {"root": str(root.resolve()), "step": args.step, "files": files}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"ok": True, "file_count": len(files), "out": str(out_path)}, ensure_ascii=False))


def _extract_markers(rel_path: str, text: str) -> list:
    markers = []
    parts = Path(rel_path).parts
    is_review = "review" in parts and rel_path.endswith(".md")
    is_discovery_log = Path(rel_path).name == "discovery-log.md"
    in_grep_section = False
    for i, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()
        if is_discovery_log:
            if stripped.startswith("## "):
                in_grep_section = stripped.startswith("## grep未対応パターン")
            elif in_grep_section and stripped.startswith("|"):
                if (
                    "（例）" not in stripped
                    and "パターン種別" not in stripped
                    and not TABLE_SEPARATOR_RE.match(stripped)
                ):
                    markers.append((i, "grep_uncovered"))
        if is_review and ("⚠️ 未解決の重大指摘あり" in line or "🔴" in line):
            markers.append((i, "review_critical"))
        if "（要確認）" in line:
            markers.append((i, "needs_confirmation"))
        if "MODULE-LEVEL" in line:
            markers.append((i, "module_level"))
        if "MEDIUM" in line:
            markers.append((i, "medium_confidence"))
        if "（推定）" in line:
            markers.append((i, "estimated"))
    return markers


def _read_text(path: Path):
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _estimate_minutes(lines: int, marker_count: int) -> float:
    est = BASE_MINUTES + lines / 80.0 + marker_count * 0.5
    return min(est, MAX_MINUTES_PER_FILE)


def _render_brief(step, target_files, markers_by_file, diff_text, ranking, total_min) -> str:
    lines = [f"# レビューブリーフ — 工程{step}", ""]

    lines.append("## ① 確信度が低い箇所トップN")
    lines.append("")
    all_markers = []
    for rel, items in markers_by_file.items():
        for line_no, key in items:
            all_markers.append((MARKER_WEIGHTS[key], rel, line_no, key))
    all_markers.sort(key=lambda t: (-t[0], t[1], t[2]))
    if not all_markers:
        lines.append("特筆すべき不確実箇所は検出されませんでした。")
    else:
        lines.append("| 順位 | ファイル | 種別 | 行 | 重み |")
        lines.append("|---|---|---|---|---|")
        for rank, (weight, rel, line_no, key) in enumerate(all_markers, start=1):
            lines.append(f"| {rank} | {rel} | {MARKER_LABELS[key]} | {line_no}行目 | {weight} |")
    lines.append("")

    lines.append("## ② 差分サマリー（前工程からの変更）")
    lines.append("")
    lines.append(diff_text)
    lines.append("")

    lines.append("## ③ 推奨レビュー順序と目安時間")
    lines.append("")
    lines.append("> 目安（暫定値・実測で調整）: 基準2分 + 行数/80 + マーカー件数×0.5分（上限"
                  f"{MAX_MINUTES_PER_FILE}分でクリップ）")
    lines.append("")
    if not ranking:
        lines.append("対象成果物はありません。")
    else:
        lines.append("| 順位 | ファイル | マーカー件数 | 目安時間（分） |")
        lines.append("|---|---|---|---|")
        for rank, (rel, marker_count, est_min) in enumerate(ranking, start=1):
            lines.append(f"| {rank} | {rel} | {marker_count} | {est_min:.1f} |")
        lines.append("")
        lines.append(f"合計目安時間: 約 {total_min:.0f} 分")
    lines.append("")

    return "\n".join(lines)


def cmd_generate(args) -> None:
    root = Path(args.root)
    if not root.exists():
        _err(f"root ディレクトリが見つかりません: {root}")
    out_path = Path(args.out)
    exclude_abs = {out_path.resolve()}

    baseline_data = None
    if args.baseline:
        baseline_path = Path(args.baseline)
        if baseline_path.exists():
            baseline_data = json.loads(baseline_path.read_text(encoding="utf-8"))

    current = _scan(root, exclude_abs)

    if baseline_data is not None:
        old_files = baseline_data["files"]
        added = sorted(rel for rel in current if rel not in old_files)
        changed = sorted(
            rel for rel in current
            if rel in old_files and current[rel]["sha256"] != old_files[rel]["sha256"]
        )
        deleted = sorted(rel for rel in old_files if rel not in current)
        target_files = sorted(added + changed)

        diff_lines = []
        diff_lines.append(f"- 追加: {len(added)}件")
        for rel in added:
            diff_lines.append(f"  - {rel}（+{current[rel]['lines']}行）")
        diff_lines.append(f"- 変更: {len(changed)}件")
        for rel in changed:
            delta = current[rel]["lines"] - old_files[rel]["lines"]
            diff_lines.append(f"  - {rel}（{delta:+d}行）")
        diff_lines.append(f"- 削除: {len(deleted)}件")
        for rel in deleted:
            diff_lines.append(f"  - {rel}（-{old_files[rel]['lines']}行）")
        diff_text = "\n".join(diff_lines)
    else:
        target_files = sorted(current.keys())
        diff_text = "（ベースライン未取得のため差分省略）"

    markers_by_file = {}
    for rel in target_files:
        text = _read_text(root / rel)
        if text is None:
            continue
        found = _extract_markers(rel, text)
        if found:
            markers_by_file[rel] = found

    ranking = []
    for rel in target_files:
        marker_count = len(markers_by_file.get(rel, []))
        weight_sum = sum(MARKER_WEIGHTS[key] for _, key in markers_by_file.get(rel, []))
        est_min = _estimate_minutes(current[rel]["lines"], marker_count)
        ranking.append((rel, marker_count, est_min, weight_sum))
    ranking.sort(key=lambda t: (-t[3], target_files.index(t[0])))
    ranking_display = [(rel, marker_count, est_min) for rel, marker_count, est_min, _ in ranking]
    total_min = sum(est_min for _, _, est_min in ranking_display)

    all_markers = []
    for rel, items in markers_by_file.items():
        for line_no, key in items:
            all_markers.append((MARKER_WEIGHTS[key], rel, line_no, key))
    all_markers.sort(key=lambda t: (-t[0], t[1], t[2]))
    top_n = args.top_n
    top = [
        {
            "file": rel,
            "line": line_no,
            "marker_type": MARKER_LABELS[key],
            "weight": weight,
            "location": f"{line_no}行目",
        }
        for weight, rel, line_no, key in all_markers[:top_n]
    ]

    counts = {}
    for _, _, _, key in all_markers:
        label = MARKER_LABELS[key]
        counts[label] = counts.get(label, 0) + 1

    brief_text = _render_brief(args.step, target_files, markers_by_file, diff_text, ranking_display, total_min)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(brief_text)

    print(json.dumps({
        "ok": True,
        "top": top,
        "counts": counts,
        "brief_path": str(out_path),
        "est_total_min": round(total_min),
    }, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_baseline = sub.add_parser("baseline")
    p_baseline.add_argument("--root", required=True)
    p_baseline.add_argument("--step", required=True)
    p_baseline.add_argument("--out", required=True)
    p_baseline.set_defaults(func=cmd_baseline)

    p_generate = sub.add_parser("generate")
    p_generate.add_argument("--root", required=True)
    p_generate.add_argument("--step", required=True)
    p_generate.add_argument("--baseline")
    p_generate.add_argument("--out", required=True)
    p_generate.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    p_generate.set_defaults(func=cmd_generate)

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
