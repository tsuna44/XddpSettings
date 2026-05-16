You are executing XDDP Step 04: Specout + Step 05: CRS Update.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional) [ENTRY_POINTS...] (CR auto-detected from XDDP_DIR if omitted)

Delegate to the **xddp.04.specout** skill:

0. DOCS_DIR baseline reference (read-only): if `{DOCS_DIR}/{REPO_NAME}/specs/` exists,
   read all files there and retain as motherbase investigation context (do not write to latest-specs/).
   Record the file list in the SPO's "参照したベースライン仕様書" section.
1. Read `xddp.config.md` to extract `MULTI_REPO` and `REPOS_MAP` (multi-repo support).
2. Invoke `xddp-specout-agent` (with `REPOS_MAP`) to create `{CR}/04_specout/SPO-{CR}.md`.
   - For multi-repo: extend ripple investigation across repository boundaries.
   - Warn user if 20+ files affected (CR split recommended).
   - If affected files per module exceed `SPECOUT_MAX_FILES_PER_MODULE` (default: 10),
     split the module file by subdirectory (index file + per-sub-module files).
3. Run SPO AI review loop (up to `REVIEW_MAX_ROUNDS.SPO` rounds from `xddp.config.md`, default 3) using `xddp-reviewer`.
4. **Human review gate**: pause for human review of `SPO-{CR}.md`.
   - If changes made: run one final AI review pass.
5. Invoke `xddp-spec-writer-agent` (MODE=update) to feed SPO findings back into the CRS.
6. Regenerate `{CR}/03_change-requirements/CRS-{CR}.xlsx` (UR-016).
7. Update `{CR}/progress.md`: steps 4 and 5 ✅, next → `/xddp.05.arch {CR}`.

See `.claude/skills/xddp.04.specout.md` for full orchestration logic.
