You are executing XDDP Step 08: Test Spec + Execution + Bug Fix + Feedback.

**Arguments:** $ARGUMENTS = CR_NUMBER

Delegate to the **xddp.08.test** skill:

1. Invoke `xddp-test-writer-agent` to create `{CR}/09_test-spec/TSP-{CR}.md`.
2. Run AI review loop (up to 5 rounds) using `xddp-reviewer` agent.
3. **Human review gate**: pause for human review of `TSP-{CR}.md`.
   - If changes made: run one final AI review pass.
4. Invoke `xddp-test-runner-agent` to execute tests and fix implementation bugs.
   - CHD/CRS への影響は TRS に記録するのみ（直接変更しない）。
5. NG時: 設計/要求影響があれば `/xddp.revise` + ロールバックパスを案内する。
6. Update `{CR}/progress.md`: steps 11-14 (テスト設計/実行/不具合修正/フィードバック), next → `/xddp.09.specs {CR}` or re-run.

See `.claude/skills/xddp.08.test.md` for full orchestration logic.
