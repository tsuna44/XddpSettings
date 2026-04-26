You are executing XDDP Step 05: Implementation Approach Design.

**Arguments:** $ARGUMENTS = CR_NUMBER

Delegate to the **xddp.05.arch** skill:

1. Invoke `xddp-architect-agent` to create `{CR}/05_architecture/DSN-{CR}.md`.
   - 実装方式の候補は **3案以上**、互いに実質的に異なるアプローチで検討する。
   - 変更の性質に応じて **Mermaid図を1〜3枚** 自動選択して挿入する（影響範囲図・DFD・シーケンス図・クラス図・フローチャート・状態遷移図・ER図など）。
2. Run AI review loop (up to `REVIEW_MAX_ROUNDS.DSN` rounds from `xddp.config.md`, default 2) using `xddp-reviewer` agent.
3. **Human review gate**: pause for human review of `DSN-{CR}.md`.
   - If changes made: run one final AI review pass.
4. **Feed architecture decision back to CRS**: 採用方式で判明した制約・不要要求・追加要件を `xddp-spec-writer-agent` で CRS に反映。変更があれば Excel も再生成。
5. Update `{CR}/progress.md`: step 6 ✅, next → `/xddp.06.design {CR}`.

See `.claude/skills/xddp.05.arch.md` for full orchestration logic.
