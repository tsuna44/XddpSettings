You are executing XDDP Step 09: Generate/Update Latest Specifications.

**Arguments:** $ARGUMENTS = CR_NUMBER

Delegate to the **xddp.09.specs** skill:

1. Read SPO, CHD, CRS to determine which modules changed.
2. Update or create spec files in `latest-specs/`.
3. Run AI review loop (up to `REVIEW_MAX_ROUNDS.SPEC` rounds from `xddp.config.md`).
4. Human review gate — wait for user confirmation.
5. Update `{CR}/progress.md`: step 15 ✅, announce CR completion.

See `.claude/skills/xddp.09.specs.md` for full orchestration logic.
