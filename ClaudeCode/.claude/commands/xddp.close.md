You are executing XDDP Close: CR Closeout & Knowledge Capture.

**Arguments:** $ARGUMENTS = CR_NUMBER

Delegate to the **xddp.close** skill:

0.5. クローズ前同期（Step C0）:
     (1) ソースコードの未取得コミット確認 → あれば git pull を促す
     (2) {DOCS_DIR}/ の git pull
     (3) docs/{repo}/specs/ → latest-specs/ へ他CR分をベースライン取り込み
         （このCR変更ファイルは保護）
     (4) ソース変更があった場合は /xddp.09.specs {CR} の再実行を推奨
1. 前提確認: 工程15（最新仕様書作成）が完了済みであることを確認する。
2. 各工程の資料から「気づき・提案メモ」を収集する。
3. 今回対応以外のエントリを `improvement-backlog.md` に追記する。
4. CR 全体の教訓を分析し、`lessons-learned.md` に知見エントリを追記する。
   - 抽出観点：要求分析の漏れ・方式検討の判断・テストで発覚した問題・プロセス改善
5. 承認済み仕様書の昇格（Step C2）: `latest-specs/` → `{DOCS_DIR}/{REPO_NAME}/specs/` にコピーし、`{DOCS_DIR}/AI_INDEX.md` のリポジトリ行を更新する。
5.5. 知見ログの昇格（Step C3）: 今回 CR の LL エントリを `{DOCS_DIR}/{REPO_NAME}/knowledge/lessons-learned.md` に追記する。
5.6. project-steering.md への知見反映（Step C3.5）: 今回 CR の LL エントリをタグに基づきセクションへ追記する。`#方式検討`/`#設計` → Section 3/4、`#コーディング` → Section 4、`#テスト` → Section 4、禁止事項 → Section 5。`#プロセス`等は対象外。重複チェックあり。`project-steering.md` が存在しない場合はスキップ。
6. 設計書の昇格（Step C4）: DSN・CHD を `{DOCS_DIR}/{REPO_NAME}/design/` にコピーし、`AI_INDEX.md` の設計書テーブルを更新する。
6.5. テスト仕様書の昇格（Step C5）: TSP を `{DOCS_DIR}/{REPO_NAME}/test/` にコピーし、`AI_INDEX.md` のテスト仕様列を更新する。
7. project-steering の昇格（Step C6）: `{XDDP_DIR}/project-steering.md` を
   `{DOCS_DIR}/{REPO_NAME}/project-steering.md` にコピーし、`AI_INDEX.md` の「共通知識」テーブルを更新する。
   ファイルが存在しない場合はスキップ。
8. **Human review gate**: ユーザによる確認を待つ（バックログ・知見・昇格仕様書の3点を確認）。
8. `{CR}/progress.md` にクローズ情報を記録する。

See `ClaudeCode/.claude/skills/xddp.close.md` for full orchestration logic.
