You are executing XDDP Step 08: Test Spec + Execution + Bug Fix + Feedback.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional; auto-detected from XDDP_DIR if omitted)

Delegate to the **xddp.08.test** skill:

0. Reference past TSPs from DOCS_DIR: read up to 3 past `{DOCS_DIR}/{REPO_NAME}/test/TSP-*.md`
   related to the CHD, plus shared test patterns and anti-patterns.
   Record files read and key insights in the TSP's "参照した過去テスト仕様" section.
1. Invoke `xddp-test-writer-agent` to create `{CR}/09_test-spec/TSP-{CR}.md`.
2. Run AI review loop (up to `REVIEW_MAX_ROUNDS.TSP` rounds from `xddp.config.md`, default 2) using `xddp-reviewer` agent.
3. **Human review gate**: pause for human review of `TSP-{CR}.md`.
   - If changes made: run one final AI review pass.
4. Invoke `xddp-test-runner-agent` to execute tests and fix implementation bugs.
   - CHD/CRS impacts are recorded in TRS only (not modified directly).
5. If NG: if design/requirement impact found, guide user to use `/xddp.revise` and the rollback path.
6. Update `{CR}/progress.md`: steps 11-14 (テスト設計/実行/不具合修正/フィードバック), next → `/xddp.09.specs {CR}` or re-run.

See `.claude/skills/xddp.08.test.md` for full orchestration logic.
