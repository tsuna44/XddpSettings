You are executing XDDP Step 02: Requirements Analysis.

**Arguments:** $ARGUMENTS = CR_NUMBER

Delegate to the **xddp.02.analysis** skill:

0. DOCS_DIR 知識取り込み: `{DOCS_DIR}/shared/glossary.md`・`lessons-learned.md`・
   `{REPO_NAME}/specs/` を読み込み、用語統一・類似 CR 参照・既存仕様整合チェックに使用する。
   使用ファイルと関連情報の要約を ANA の「参照した既存ドキュメント」節に記録する。
1. Invoke `xddp-analyst-agent` to create `{CR}/02_analysis/ANA-{CR}.md`.
   - セクション「2. 要求レベル分類」で、要求書の各 UR を UR / SR / SP に分類し、CRS表現案と理由を生成する。
2. Run AI review loop (up to `REVIEW_MAX_ROUNDS.ANA` rounds from `xddp.config.md`, default 2) using `xddp-reviewer` agent.
   - Each round: review → fix with `xddp-analyst-agent` if 🔴/🟡 found.
3. **Human review gate**: pause for human review of `ANA-{CR}.md`.
   - If changes made: run one final AI review pass.
3.5. **project-steering 追記候補の抽出**（Step B3）:
     - 冪等性チェック: 変更履歴に {CR} のエントリがあればスキップ。
     - req から命名規約・ADR・禁止事項・横断パターン（横断的なもののみ）を抽出。
     - 候補をカテゴリ名ラベル付きで提示し、ユーザ承認後に該当見出しへ追記。
     - `project-steering.md` 不在時はユーザに通知してスキップ。候補0件の場合もスキップ。
4. Update `{CR}/progress.md`: step 2 ✅, next → `/xddp.03.req {CR}`.

See `.claude/skills/xddp.02.analysis.md` for full orchestration logic.
