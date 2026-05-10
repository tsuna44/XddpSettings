You are executing XDDP Step 09: Generate/Update Latest Specifications.

**Arguments:** $ARGUMENTS = [CR_NUMBER]（省略可。省略時は XDDP_DIR 配下から自動検出）

Delegate to the **xddp.09.specs** skill:

1. Read SPO, CHD, CRS to determine which modules changed.
2. Update or create spec files in `latest-specs/`.
3. Run AI review loop (up to `REVIEW_MAX_ROUNDS.SPEC` rounds from `xddp.config.md`).
4. Human review gate — wait for user confirmation.
5. Update `{CR}/progress.md`: step 15 ✅, announce CR completion。更新した仕様書ファイル一覧を
   「工程15 更新仕様書ファイル一覧」セクションに記録する（xddp.close Step C0-3 の保護対象判定に使用）。

See `.claude/skills/xddp.09.specs.md` for full orchestration logic.
