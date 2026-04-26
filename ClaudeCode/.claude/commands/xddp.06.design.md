You are executing XDDP Step 06: Change Design Document + CRS Feedback.

**Arguments:** $ARGUMENTS = CR_NUMBER

Delegate to the **xddp.06.design** skill:

1. Invoke `xddp-designer-agent` to create `{CR}/06_design/CHD-{CR}.md`.
   - 第3章の詳細設計は **仕様（SP）単位** で記述する（ファイル単位ではない）。
   - 変更内容に応じて Mermaid 図を自動選択して挿入する（クラス図・関数呼び出し図・シーケンス図・フローチャート・状態遷移図・ER図）。
   - 第4章にトレーサビリティマトリクス（SP × ファイル × 関数）を作成する。
   - Warn user if >500 lines changed (CR split recommended).
2. Run AI review loop (up to `REVIEW_MAX_ROUNDS.CHD` rounds from `xddp.config.md`, default 2) using `xddp-reviewer` agent.
3. **Human review gate**: pause for human review of `CHD-{CR}.md`.
   - If changes made: run one final AI review pass.
4. Feed design findings back to CRS via `xddp-spec-writer-agent` (MODE=update).
5. Regenerate `{CR}/03_change-requirements/CRS-{CR}.xlsx` if CRS was updated (UR-016).
6. Update `{CR}/progress.md`: steps 7 and 8 ✅, next → `/xddp.07.code {CR}`.

See `.claude/skills/xddp.06.design.md` for full orchestration logic.
