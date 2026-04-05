You are executing XDDP Step 04: Specout + Step 05: CRS Update.

**Arguments:** $ARGUMENTS = CR_NUMBER [ENTRY_POINTS...]

Delegate to the **xddp.04.specout** skill:

1. Invoke `xddp-specout-agent` to create `{CR}/04_specout/SPO-{CR}.md`.
   - Warn user if 20+ files affected (CR split recommended).
2. Run SPO AI review loop (up to 5 rounds) using `xddp-reviewer`.
3. **Human review gate**: pause for human review of `SPO-{CR}.md`.
   - If changes made: run one final AI review pass.
4. Invoke `xddp-spec-writer-agent` (MODE=update) to feed SPO findings back into the CRS.
5. Regenerate `{CR}/03_change-requirements/CRS-{CR}.xlsx` (UR-016).
6. Update `{CR}/progress.md`: steps 4 and 5 ✅, next → `/xddp.05.arch {CR}`.

See `.claude/skills/xddp.04.specout.md` for full orchestration logic.
