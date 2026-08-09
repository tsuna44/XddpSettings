"""
merge_classification.py — チャンク並列 classification の検証・結合（PLAN-20260806 Phase 3 Stage 2 §4.6）

Discovery BFS の1波を分割した各チャンクファイルへ、classifier サブエージェントが並列に書き出した
classification 結果を、commit-wave が読める単一の配列へ検証しつつ結合する。判定はすべて本スクリプト
（決定的処理）が行い、SKILL（LLM オーケストレータ）は再投入対象チャンクの特定を本スクリプトの stderr
出力に委ねる（CLAUDE.md「決定的処理はスクリプト・意味判定はLLM」）。

処理の要旨:
  1. 各チャンクの分類結果ファイルを読み、classification 配列を結合する。
  2. hits 全体の行識別子集合と照合し、欠落・重複があれば明示エラーで停止する。
  3. 既定の分類値以外が含まれていれば、commit-wave に到達する前に明示エラーで停止する。
  4. grep未対応パターンを全チャンク分マージ（同一パターン・出典は1件に集約）する。
  5. 結合結果は hits の出現順に整列して書き出す（commit-wave の入力契約と同一）。
  6. チャンク単位でも行識別子集合を照合し、旧ランの結果が紛れ込んでいないかを検出する。
  7. 各チャンク結果ファイルの更新時刻を収集し、実効並列度の裏付けと再利用判定に用いる値を出力する。
  8. 分類側のファイルが見つからない場合は例外の生の出力ではなく、再投入すべき対象の一覧を出力する。

実装制約（§4.6・必須）: 本スクリプトはサブコマンドを持たないため、
`tools/harness/refcheck.py` 検査D の有効フラグ集合は「--help の全出力」に由来する。
そのためモジュール docstring 中でオプション名を記号付きで列挙してはならない
（ArgumentParser の description に本 docstring を渡してもいない。二重の防御については
plans/PLAN-20260806-specout-phase3-parallel-classification.md §4.6 を参照）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from specout_bfs import CLASS_VALUES  # noqa: E402


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _collect_chunk_mtimes(entries: list) -> tuple:
    """`entries`: [(chunk_id, class_path), ...]。mtime が取得できないチャンクがあっても
    エラーにしない（計測専用であり correctness に関与しないため。§4.6 処理7）。"""
    chunk_mtimes = []
    for chunk_id, class_path in entries:
        try:
            mtime = class_path.stat().st_mtime
        except OSError:
            continue
        chunk_mtimes.append({"chunk_id": chunk_id, "mtime": mtime})
    chunk_mtimes.sort(key=lambda e: e["mtime"])
    min_chunk_mtime = chunk_mtimes[0]["mtime"] if chunk_mtimes else None
    return chunk_mtimes, min_chunk_mtime


def merge(hits_path: Path, hits_chunk_paths: list, chunk_paths: list,
          out_path: Path, unsupported_out_path: Path) -> dict:
    if len(hits_chunk_paths) != len(chunk_paths):
        print(
            f"ヒットチャンク数（{len(hits_chunk_paths)}）と classifier 出力数（{len(chunk_paths)}）が"
            "一致しません（呼び出し側の対応関係を確認してください）",
            file=sys.stderr,
        )
        sys.exit(1)

    hits_payload = _load_json(hits_path)
    global_hit_ids = [h["line_id"] for h in hits_payload.get("hits", [])]
    global_hit_id_set = set(global_hit_ids)

    # --- 処理6・8: チャンク単位の検証（欠落チャンク・stale チャンクの特定） ---
    missing = []
    stale = []
    loaded = []  # [(chunk_id, classification_list, unsupported_patterns_list, class_path)]
    for hc_path_str, class_path_str in zip(hits_chunk_paths, chunk_paths):
        hc_data = _load_json(Path(hc_path_str))
        chunk_id = hc_data.get("chunk_id", hc_path_str)
        expected_ids = {h["line_id"] for h in hc_data.get("hits", [])}
        class_path = Path(class_path_str)
        if not class_path.exists():
            missing.append({"chunk_id": chunk_id, "expected_path": str(class_path)})
            continue
        class_data = _load_json(class_path)
        classification_list = class_data.get("classification", [])
        actual_ids = {c.get("line_id") for c in classification_list}
        if actual_ids != expected_ids:
            stale.append({
                "chunk_id": chunk_id,
                "path": str(class_path),
                "missing_line_ids": sorted(expected_ids - actual_ids),
                "unknown_line_ids": sorted(actual_ids - expected_ids),
            })
            continue
        loaded.append((chunk_id, classification_list, class_data.get("unsupported_patterns", []), class_path))

    if missing or stale:
        for m in missing:
            print(f"欠落チャンク: chunk_id={m['chunk_id']} expected_path={m['expected_path']}", file=sys.stderr)
        for s in stale:
            print(
                f"再投入対象チャンク（line_id 不一致）: chunk_id={s['chunk_id']} path={s['path']} "
                f"missing_line_ids={s['missing_line_ids']} unknown_line_ids={s['unknown_line_ids']}",
                file=sys.stderr,
            )
        sys.exit(1)

    # --- 処理1・2: 結合と hits 全体との照合（欠落・重複） ---
    combined = []
    seen_ids = set()
    dup_ids = []
    for _chunk_id, classification_list, _unsupported, _path in loaded:
        for c in classification_list:
            lid = c.get("line_id")
            if lid in seen_ids:
                dup_ids.append(lid)
            else:
                seen_ids.add(lid)
            combined.append(c)

    missing_global = sorted(global_hit_id_set - seen_ids)
    extra_global = sorted(seen_ids - global_hit_id_set)
    if missing_global or extra_global or dup_ids:
        if missing_global:
            print(f"欠落 line_id（hits に存在するが classification に無い）: {missing_global}", file=sys.stderr)
        if extra_global:
            print(f"未知の line_id（hits に存在しない）: {extra_global}", file=sys.stderr)
        if dup_ids:
            print(f"重複 line_id: {sorted(set(dup_ids))}", file=sys.stderr)
        sys.exit(1)

    # --- 処理3: 既定の分類値以外を commit-wave 到達前に検出 ---
    unknown_values = [(c.get("line_id"), c.get("classification")) for c in combined
                       if c.get("classification") not in CLASS_VALUES]
    if unknown_values:
        for lid, val in unknown_values:
            print(f"未知の classification 値です: {val!r}（行 {lid}）", file=sys.stderr)
        sys.exit(1)

    # --- 処理5: hits の出現順に整列 ---
    class_by_id = {c["line_id"]: c for c in combined}
    ordered = [class_by_id[lid] for lid in global_hit_ids]
    _write_json(out_path, ordered)

    # --- 処理4: grep未対応パターンのマージ（同一 pattern + location は1件に集約） ---
    unsupported_merged = []
    seen_up = set()
    for _chunk_id, _classification, unsupported_list, _path in loaded:
        for u in unsupported_list:
            key = (u.get("pattern"), u.get("location"))
            if key in seen_up:
                continue
            seen_up.add(key)
            unsupported_merged.append(u)
    _write_json(unsupported_out_path, unsupported_merged)

    # --- 処理7: チャンク mtime の収集（実効並列度の裏付け・再利用判定用の別チャンネル） ---
    chunk_mtimes, min_chunk_mtime = _collect_chunk_mtimes(
        [(chunk_id, class_path) for chunk_id, _classification, _unsupported, class_path in loaded]
    )

    return {
        "ok": True,
        "chunk_count": len(loaded),
        "chunk_mtimes": chunk_mtimes,
        "min_chunk_mtime": min_chunk_mtime,
    }


def build_parser() -> argparse.ArgumentParser:
    # PLAN-20260806 Phase 3 Stage 2 §4.6 必須制約: description に __doc__ を渡さない
    # （渡すと --help 全文にモジュール docstring が含まれ、refcheck.py 検査D の有効フラグ集合が
    # docstring 由来の記述まで拾ってしまい未定義フラグの誤りを検出できなくなる）。
    parser = argparse.ArgumentParser(
        description="Discovery BFS のチャンク並列分類結果を検証・結合する。",
    )
    parser.add_argument("--hits", required=True, help="wave-N-hits.json（波全体のヒット）")
    parser.add_argument("--hits-chunks", nargs="+", required=True,
                         help="wave-N-hits-chunk-K.json の一覧（search が出力したヒットチャンク）")
    parser.add_argument("--chunks", nargs="+", required=True,
                         help="wave-N-chunk-K-class.json の一覧（classifier の出力。hits-chunks と同じ順序）")
    parser.add_argument("--out", required=True, help="結合済み classification の出力先")
    parser.add_argument("--unsupported-out", required=True, help="grep未対応パターンのマージ結果の出力先")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = merge(
        Path(args.hits), args.hits_chunks, args.chunks, Path(args.out), Path(args.unsupported_out),
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
