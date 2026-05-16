You are executing XDDP Step 04: Specout + Step 05: CRS Update.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional) [ENTRY_POINTS...] (CR auto-detected from XDDP_DIR if omitted)

Delegate to the **xddp.04.specout** skill:

0. Read `REPOS:` from `xddp.config.md`. Identify AFFECTED_REPOS from CRS "1.5 影響リポジトリ"; default to all REPOS: keys if absent.
   Confirm repos and cross/ status with user before proceeding.
0.5. When IS_MULTI: create per-repo progress table in `progress.md` for step 4.
1. For each repo in AFFECTED_REPOS: invoke `xddp-specout-agent` with:
   - `REPO_NAME`, `REPO_PATH`, `OUTPUT_DIR={CR_PATH}/04_specout/{repo}/`
   - `BASELINE_SPECS_DIR={DOCS}/{repo}/specs/`, `CROSS_SPECS_DIR={DOCS}/cross/specs/`
   - Artifacts go to `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` and `{repo}/modules/`
   - Warn if 20+ files affected (CR split recommended).
   - Split module files by subdirectory when per-module file count exceeds `SPECOUT_MAX_FILES_PER_MODULE`.
2. If ≥2 repos affected: synthesise `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md` from repo boundary calls
   recorded in each per-repo SPO. Skip if no inter-repo dependencies are found.
3. Run per-repo SPO AI review loops (up to `REVIEW_MAX_ROUNDS.SPO` rounds from `xddp.config.md`, default 3).
4. **Human review gate**: pause for human review of per-repo SPO files and cross/SPO (if created).
   - If changes made: run one final AI review pass per repo.
5. Invoke `xddp-spec-writer-agent` (MODE=update, SPO_DIR=`{CR_PATH}/04_specout/`) to feed all SPO findings back into the CRS.
6. Regenerate `{CR}/03_change-requirements/CRS-{CR}.xlsx` (UR-016).
7. Update `{CR}/progress.md`: steps 4 and 5 ✅, next → `/xddp.05.arch {CR}`.

See `.claude/skills/xddp.04.specout.md` for full orchestration logic.
