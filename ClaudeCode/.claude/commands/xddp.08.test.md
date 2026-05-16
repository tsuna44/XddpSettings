You are executing XDDP Step 08: Test Spec + Execution + Bug Fix + Feedback.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional; auto-detected from XDDP_DIR if omitted)

Delegate to the **xddp.08.test** skill:

0. Read `REPOS:` from `xddp.config.md`. Identify AFFECTED_REPOS and HAS_CROSS.
   Reference past TSPs from DOCS_DIR: read up to 3 past `{DOCS}/{repo}/test/TSP-*.md` per affected repo.
A. For each repo in AFFECTED_REPOS: invoke `xddp-test-writer-agent` with:
   - `REPO_NAME`, per-repo `CHD_FILE`, `SPO_FILE`, `VERIFY_FILE`, `OUTPUT_FILE={repo}/TSP-{CR}.md`
   - Per-repo `TEST_FRAMEWORK` (from `TEST_FRAMEWORK_REPOS:` or config default)
   If HAS_CROSS: also generate `cross/TSP-{CR}-cross.md` focused on inter-repo interface contracts
   (≥1 happy-path TC and ≥1 error TC per interface in cross/CHD インタフェース変更サマリ).
B. Run per-repo AI review loops (up to `REVIEW_MAX_ROUNDS.TSP` rounds from `xddp.config.md`, default 2).
B2. **Human review gate**: pause for human review of all TSP files.
   - If changes made: run one final AI review pass per repo.
C. For each repo: invoke `xddp-test-runner-agent` with per-repo `TSP_FILE`, `OUTPUT_FILE={repo}/TRS-{CR}-0{n}.md`.
   If HAS_CROSS: also run cross integration tests → `cross/TRS-{CR}-0{n}.md`.
D. If all pass: update progress.md steps 11-14 ✅, next → `/xddp.09.specs {CR}`.
   If NG implementation bug: apply fix, re-run static verification, then re-run tests.
   If NG design/requirement impact: guide user to `/xddp.revise {CR}` and rollback path (do not modify CHD/CRS directly).

See `.claude/skills/xddp.08.test.md` for full orchestration logic.
