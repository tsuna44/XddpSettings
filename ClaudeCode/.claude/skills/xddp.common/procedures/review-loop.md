# Review Loop

> xddp.common の共通プロシージャ。呼び出し元スキルから apply される。

## Review Loop

AIレビュー → Fixer の反復ループ共通制御フロー。各スキルの Step B から apply して使用する。

**Input:**
- `DOCUMENT_TYPE`: レビュアーに渡す文書種別（ANA / CRS / DSN / CHD / TSP）
- `CONFIG_KEY`: xddp.config.md から読む REVIEW_MAX_ROUNDS のキー名（例: `REVIEW_MAX_ROUNDS.ANA`）。デフォルト値は 2。
- `MAX_ROUNDS_OVERRIDE`（任意）: 指定時は、`{CONFIG_KEY}` が明示的に `0`（レビュー完全スキップ）で
  ない限り `CONFIG_KEY` の値より優先して `max_rounds` に採用する。`{CONFIG_KEY}` が明示的に `0` の
  場合は運用者がレビューを意図的にスキップした設定であるため、`MAX_ROUNDS_OVERRIDE` より優先して
  常にスキップする（quick プロファイルが「1ラウンドに強制」しても、運用者が明示的に無効化した
  レビューを復活させない）。`CR_PROFILE: quick` 等、呼び出し元スキルがプロファイルに応じてラウンド数を
  強制上書きしたい場合に使用する。
- `TARGET_FILE`: レビュー対象ファイルのパス
- `REFERENCE_FILES`: レビュー時に参照するファイル一覧
- `REVIEW_OUTPUT_FILE`: レビュー結果の出力先パス
- `FIXER_AGENT`: 修正担当エージェントの subagent_type 名
- `FIXER_PARAMS`: 修正エージェントへの入力パラメータ（key-value 形式）
- `NEXT_DOCUMENT_TYPE`（任意）: 次工程の文書種別（例: ANA→CRS, CRS→SPO（change モード）/ CRS→DSN（新規開発モード）/ CRS→CHD（新規開発モード × `CR_PROFILE: quick`。工程4・5がともにスキップされる経路）, SPO→DSN, DSN→CHD, CHD→TSP）。指定時に xddp-reviewer へ渡し、次工程受け取り可否レビューを実施させる。ダウンストリーム ❌ 項目は xddp-reviewer が `## 2.` に 🔴 として転記するため、ループ判定ロジックの変更は不要。
- `PROGRESS_CR_PATH`（任意）: progress.md のある CR フォルダパス
- `PROGRESS_STEP_NUM`（任意）: 警告フラグ・`reviewer_call`／`review_loop` イベントを記録するステップ番号
- `EXTRA_REVIEWER_PARAMS`（任意, key-value 形式, default: 空）: `xddp-reviewer` への Agent tool 呼び出し
  （Process 5a）に追加でそのまま渡すパラメータ。`DOCUMENT_TYPE` 固有の
  判定基準値を `xddp-reviewer` に伝える汎用の受け渡し口（例: `TSP` レビュー時の `MIN_COVERAGE`）。
  呼び出し元が指定しない場合は Process 5a の呼び出しに何も追加しない（既存の呼び出しと完全に同一）。
- `METRICS_TARGET`（任意, default: 空）: `record --event review_loop` および Process 5a 経由で
  `record --event reviewer_call` の `--target` にそのまま渡す識別子文字列（例: リポジトリ名・
  `{repo}/{UR_ID}`）。1つの工程内で `## Review Loop` を複数回呼び出すスキル
  （`xddp.05.arch`／`xddp.06.design`／`xddp.09.test`）が、`metrics.jsonl` のイベントをどの呼び出しか
  事後に区別するために渡す。単一呼び出しのスキル（02/03）は省略可（省略時は `--target` オプション
  自体を付与しない）。

**Process:**
1. Read `{WORKSPACE_ROOT}/xddp.config.md`.
   - Extract `{CONFIG_KEY}` (default: 2 if absent). Set `config_max_rounds`.
   - Extract `FIX_STRATEGY.{DOCUMENT_TYPE}` (default: `balanced` if absent). Set `fix_strategy`.
     修正方針: `efficiency`（最小インパクト優先）/ `ideal`（理想状態優先）/ `balanced`（コストと理想の
     バランス）。`FIXER_PARAMS` に含めてフィクサーエージェントへ伝達する（Process 手順5d参照）。
     AI フィクサーエージェントでは `balanced` は `ideal` と同等に動作する（人への確認は
     xddp.plan-review のインライン修正のみサポート）。
2. `max_rounds` を決定する（優先順位: `{CONFIG_KEY}` が明示的に `0` > `MAX_ROUNDS_OVERRIDE` > `{CONFIG_KEY}` の値）:
   - `config_max_rounds` が明示的に `0` の場合: `max_rounds` = `0`（`MAX_ROUNDS_OVERRIDE` の指定有無に
     関わらずスキップする。運用者の明示的なスキップ意図を尊重する）。
   - 上記以外で `MAX_ROUNDS_OVERRIDE` が指定されている場合: `max_rounds` = `MAX_ROUNDS_OVERRIDE`。
   - 上記いずれでもない場合: `max_rounds` = `config_max_rounds`。
3. If `max_rounds = 0`: レビューをスキップして終了する（`REVIEW_MAX_ROUNDS.*: 0` 設定時、または上記
   手順2の優先順位判定によりスキップと決定した場合）。PROGRESS_CR_PATH と PROGRESS_STEP_NUM が
   指定されている場合、Bash で以下を実行する（ベストエフォート）:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_metrics.py record --cr-path {PROGRESS_CR_PATH} --step {PROGRESS_STEP_NUM} --event review_loop --document-type {DOCUMENT_TYPE} --review-rounds 0 --review-max-rounds 0 --review-outcome skipped [--target "{METRICS_TARGET}"]`
   （`METRICS_TARGET` が指定されている場合のみ `--target` を付与する。以下2箇所の `record` 呼び出しも同様）
4. Initialize: `round = 1`, `issues_remain = true`
5. While `issues_remain` and `round ≤ max_rounds`:
   a. Read `~/.claude/skills/xddp.common/procedures/invoke-reviewer.md`, apply "## Invoke Reviewer" with:
      DOCUMENT_TYPE: {DOCUMENT_TYPE}, TARGET_FILE: {TARGET_FILE}, REFERENCE_FILES: {REFERENCE_FILES},
      REVIEW_ROUND: {round}, OUTPUT_FILE: {REVIEW_OUTPUT_FILE},
      （NEXT_DOCUMENT_TYPE が指定されている場合のみ）NEXT_DOCUMENT_TYPE: {NEXT_DOCUMENT_TYPE},
      （EXTRA_REVIEWER_PARAMS が指定されている場合のみ）EXTRA_REVIEWER_PARAMS: {EXTRA_REVIEWER_PARAMS},
      （PROGRESS_CR_PATH が指定されている場合のみ）PROGRESS_CR_PATH: {PROGRESS_CR_PATH},
      （PROGRESS_STEP_NUM が指定されている場合のみ）PROGRESS_STEP_NUM: {PROGRESS_STEP_NUM},
      （METRICS_TARGET が指定されている場合のみ）METRICS_TARGET: {METRICS_TARGET}
   b. Read `{REVIEW_OUTPUT_FILE}`.
      - No 🔴/🟡 → `issues_remain = false`. If PROGRESS_CR_PATH and PROGRESS_STEP_NUM are
        provided, run via Bash（ベストエフォート）:
        `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_metrics.py record --cr-path {PROGRESS_CR_PATH} --step {PROGRESS_STEP_NUM} --event review_loop --document-type {DOCUMENT_TYPE} --review-rounds {round} --review-max-rounds {max_rounds} --review-outcome converged [--target "{METRICS_TARGET}"]`
        Exit loop.
      - 🔴/🟡 found and `round < max_rounds`:
        c. **横展開調査:** 各指摘の根本原因パターンを特定する。対象ファイルの他セクションおよび REFERENCE_FILES に列挙された関連ファイルに同一パターンが存在しないかをスキャンし、追加修正箇所を `ADDITIONAL_FIXES` に記録する。
        d. `FIXER_PARAMS` に `FIX_STRATEGY` = `{fix_strategy}` と `ADDITIONAL_FIXES` を追加する。
        e. **Agent tool** `subagent_type={FIXER_AGENT}` with updated `{FIXER_PARAMS}`. Increment `round`. Continue loop.
      - `round = max_rounds` and issues remain:
        1. Append `"⚠️ 未解決の重大指摘あり。人間の判断が必要です。"` to `{REVIEW_OUTPUT_FILE}`.
        2. If PROGRESS_CR_PATH and PROGRESS_STEP_NUM are provided, run via Bash:
           `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_progress.py note-add --cr-path {PROGRESS_CR_PATH} --step {PROGRESS_STEP_NUM} --text "未解決指摘あり（{REVIEW_OUTPUT_FILE}）"`
        3. Same condition, also run via Bash（ベストエフォート）:
           `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_metrics.py record --cr-path {PROGRESS_CR_PATH} --step {PROGRESS_STEP_NUM} --event review_loop --document-type {DOCUMENT_TYPE} --review-rounds {round} --review-max-rounds {max_rounds} --review-outcome max_rounds_exhausted [--target "{METRICS_TARGET}"]`
        Exit loop.
