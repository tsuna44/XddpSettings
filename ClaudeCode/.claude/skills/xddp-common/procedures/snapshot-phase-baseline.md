# Snapshot Phase Baseline

> xddp-common の共通プロシージャ。呼び出し元スキルから apply される。

## Snapshot Phase Baseline

工程開始時点（成果物生成前）のCRフォルダ状態を記録する共通手順。人レビューゲートの
レビューブリーフ（## Human Review Gate 参照）が「前工程からの差分」を算出するために使う。
各スキルの「Mark In-Progress」ステップ直後から apply する。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `STEP_NUM`: progress.md 上の対象ステップ番号（ゲートに渡すものと同一値）

**Process:**
1. Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_review_brief.py baseline --root {CR_PATH} --step {STEP_NUM} --out {CR_PATH}/.phase-baseline-{STEP_NUM}.json`
   （スキル再実行時はベースラインを上書きする＝今回の実行が生んだ増減を差分とする意図的挙動）
2. If the script is not found: tell the user to run `setup.sh` and continue（ベースラインが無くてもブリーフは差分省略で動作するため、停止はしない）。If it errors: display stderr and continue.
3. Also run via Bash（工程所要時間テレメトリの開始マーカー。ベストエフォート）:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_metrics.py phase-start --cr-path {CR_PATH} --step {STEP_NUM}`
   If the script is not found or errors: continue silently（テレメトリは工程本体を止めない。
   `## Progress Update` 側で `duration_ms` が省略されるのみ）。

> 停止しない設計理由: ベースラインはブリーフの補助情報であり、取得失敗が工程本体を止めるべきではない
> （`generate` はベースライン欠損時に差分を省略して正常動作する）。
