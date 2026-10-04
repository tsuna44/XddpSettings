"""
specout_log_values.py — discovery-log.md に書く英語の値の共通定義

`specout_bfs.py`（discovery-log の書き手）と `specout_verify_counts.py`（件数一致検証の独立再チェック）が
同じ文字列を書くための定数と書式関数だけを持つ。サブコマンドは持たない。標準ライブラリのみ。

共有するのは表示の文字列だけであり、件数の照合（生 = 記録 + dedup + フィルタ除外 + noise-collapse）は
各スクリプトが別々に行う。値の日本語の説明は discovery-log 冒頭の「## 凡例」（`specout_bfs.py` が書く）にある。
"""

# 実行コマンド一覧「種別」
KIND_HIGH = "HIGH-compound"
KIND_MEDIUM = "MEDIUM"

# ヒット表「派生元」
ORIGIN_UNKNOWN = "unknown-origin"


def origin_seed(symbol: str) -> str:
    return f"seed({symbol})"


def origin_seed_global(symbol: str) -> str:
    return f"seed-global({symbol})"


# 打ち切り記録「理由」（bfs-state.json の truncated の reason と同じ値）
TRUNC_HIT_BUDGET = "hit-budget"
TRUNC_LLM_BUDGET = "llm-budget"
TRUNC_WAVE_LIMIT = "wave-limit"
# 資料の確定（doc-digest）の上限で材料から外したモジュール・関数。波の検索後の件数ではなく資料化の上限なので、
# 件数照合（生 = 記録 + dedup + フィルタ除外 + noise-collapse）の対象外。
TRUNC_DOC_LIMIT = "doc-limit"
TRUNC_REASONS = (TRUNC_HIT_BUDGET, TRUNC_LLM_BUDGET, TRUNC_WAVE_LIMIT, TRUNC_DOC_LIMIT)

# 同名 MEDIUM シンボル・異スコープ重複ログ「ケース」「処置」
CASE_A = "case-a"
CASE_B = "case-b"
CASE_C = "case-c"
ACTION_MANUAL_CHECK = "manual-check"
ACTION_KEEP_VISITED = "keep-visited"
ACTION_DISCARD_KEY = "discard="


def action_promote_high(discarded_scopes: list) -> str:
    """ケースA の処置。`discard=` の後にバッククォートで囲んだスコープをカンマ区切りで並べる
    （`specout_verify_counts.py` が `discard=` の後を読み、廃棄したコマンドを件数照合から外す）。"""
    return "promote-high; " + ACTION_DISCARD_KEY + ",".join(f"`{s}`" for s in discarded_scopes)


# 件数一致検証「一致」
VERIFY_OK = "✅"
VERIFY_DISCARDED_CASE_A = "➖ discarded(case-a)"


def verify_mark(raw: int, recorded: int, dedup: int, filtered: int, noise_collapse: int,
                discarded: bool = False) -> str:
    """件数一致検証の判定の文字列。`filtered` は保守的フィルタと予算による除外の合計。"""
    if discarded:
        return VERIFY_DISCARDED_CASE_A
    excluded = dedup + filtered + noise_collapse
    if raw == recorded + excluded:
        if excluded == 0:
            return VERIFY_OK
        return f"{VERIFY_OK} excluded(dedup={dedup},filter={filtered},noise-collapse={noise_collapse})"
    return f"⚠️ mismatch(raw={raw},recorded={recorded},excluded={excluded})"


def is_mismatch(mark: str) -> bool:
    return mark.startswith("⚠️ mismatch(")


# ヒット表「伝播種別」（スライス判定・規則判定の行）。LLM 分類の行と偽陽性は分類の値をそのまま書く。
def propagation_label(classification: str, slice_info) -> str:
    """`slice_info` は classification エントリの `slice`（無ければ None）。"""
    if not slice_info or classification == "false-positive":
        return classification
    engine = slice_info.get("engine") or "slice"
    status = slice_info.get("status") or ""
    if engine == "rule":
        if status == "rule":
            return "rule(enclosing)"
        return f"rule(none={status or 'unknown'})"
    if status == "sliced":
        kinds = sorted({e[0] for e in slice_info.get("escapes") or [] if e})
        return f"slice(escape={','.join(kinds)})" if kinds else "slice(none=no-escape)"
    if status == "file-scope":
        note = slice_info.get("file_scope") or ""
        if note in ("macro-def", "global-init", "module/class-assign") and slice_info.get("propagates"):
            return f"slice(file-scope={note})"
        return "slice(none=file-scope)"
    if status == "rule":  # スライス判定の解析に失敗し、規則判定で代わりに判定した行
        return "rule(enclosing)"
    return f"slice(none={status or 'unknown'})"
