You are executing XDDP Step 04: Specout + Step 05: CRS Update.

**Arguments:** $ARGUMENTS = CR_NUMBER [ENTRY_POINTS...]

Delegate to the **xddp.04.specout** skill:

1. Read `xddp.config.md` to extract `MULTI_REPO` and `REPOS_MAP` (マルチリポジトリ対応).
2. Invoke `xddp-specout-agent` (with `REPOS_MAP`) to create `{CR}/04_specout/SPO-{CR}.md`.
   - マルチリポジトリ時はリポジトリ境界を越えた波及調査を実施する。
   - Warn user if 20+ files affected (CR split recommended).
3. Run SPO AI review loop (up to `REVIEW_MAX_ROUNDS.SPO` rounds from `xddp.config.md`, default 3) using `xddp-reviewer`.
4. **Human review gate**: pause for human review of `SPO-{CR}.md`.
   - If changes made: run one final AI review pass.
5. Invoke `xddp-spec-writer-agent` (MODE=update) to feed SPO findings back into the CRS.
6. Regenerate `{CR}/03_change-requirements/CRS-{CR}.xlsx` (UR-016).
7. Update `{CR}/progress.md`: steps 4 and 5 ✅, next → `/xddp.05.arch {CR}`.

See `.claude/skills/xddp.04.specout.md` for full orchestration logic.
