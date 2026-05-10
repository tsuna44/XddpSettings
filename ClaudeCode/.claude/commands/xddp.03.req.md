You are executing XDDP Step 03: Create Change Requirements Specification.

**Arguments:** $ARGUMENTS = [CR_NUMBER]（省略可。省略時は XDDP_DIR 配下から自動検出）

Delegate to the **xddp.03.req** skill:

1. Invoke `xddp-spec-writer-agent` (MODE=create) to create `{CR}/03_change-requirements/CRS-{CR}.md`.
2. Run AI review loop (up to `REVIEW_MAX_ROUNDS.CRS` rounds from `xddp.config.md`, default 2) using `xddp-reviewer` + `xddp-spec-writer-agent` (MODE=fix).
3. **Human review gate**: pause for human review of `CRS-{CR}.md`.
   - If changes made: run one final AI review pass.
4. Generate `{CR}/03_change-requirements/CRS-{CR}.xlsx` from the Markdown CRS (UR-016).
5. Update `{CR}/progress.md`: step 3 ✅, next → `/xddp.04.specout {CR}`.

See `.claude/skills/xddp.03.req.md` for full orchestration logic.
