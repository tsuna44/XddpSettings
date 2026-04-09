You are executing XDDP Close: CR Closeout & Knowledge Capture.

**Arguments:** $ARGUMENTS = CR_NUMBER

Delegate to the **xddp.close** skill:

1. 前提確認: 工程15（最新仕様書作成）が完了済みであることを確認する。
2. 各工程の資料から「気づき・提案メモ」を収集する。
3. 今回対応以外のエントリを `improvement-backlog.md` に追記する。
4. CR 全体の教訓を分析し、`lessons-learned.md` に知見エントリを追記する。
   - 抽出観点：要求分析の漏れ・方式検討の判断・テストで発覚した問題・プロセス改善
5. **Human review gate**: ユーザによる確認を待つ。
6. `{CR}/progress.md` にクローズ情報を記録する。

See `ClaudeCode/.claude/skills/xddp.close.md` for full orchestration logic.
