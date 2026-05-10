You are executing XDDP Step 08: Test Spec + Execution + Bug Fix + Feedback.

**Arguments:** $ARGUMENTS = [CR_NUMBER]（省略可。省略時は XDDP_DIR 配下から自動検出）

Delegate to the **xddp.08.test** skill:

0. DOCS_DIR 過去 TSP 参照: `{DOCS_DIR}/{REPO_NAME}/test/TSP-*.md` から CHD 関連の
   過去テスト仕様書（最新 3 件上限）と共通 test パターン・anti-pattern を読み込む。
   TSP の「参照した過去テスト仕様」節に読み込んだファイルと知見要約を記録する。
1. Invoke `xddp-test-writer-agent` to create `{CR}/09_test-spec/TSP-{CR}.md`.
2. Run AI review loop (up to `REVIEW_MAX_ROUNDS.TSP` rounds from `xddp.config.md`, default 2) using `xddp-reviewer` agent.
3. **Human review gate**: pause for human review of `TSP-{CR}.md`.
   - If changes made: run one final AI review pass.
4. Invoke `xddp-test-runner-agent` to execute tests and fix implementation bugs.
   - CHD/CRS への影響は TRS に記録するのみ（直接変更しない）。
5. NG時: 設計/要求影響があれば `/xddp.revise` + ロールバックパスを案内する。
6. Update `{CR}/progress.md`: steps 11-14 (テスト設計/実行/不具合修正/フィードバック), next → `/xddp.09.specs {CR}` or re-run.

See `.claude/skills/xddp.08.test.md` for full orchestration logic.
