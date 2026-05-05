You are executing XDDP Fill Steering (project-steering.md 自動ドラフト生成).

**Arguments:** $ARGUMENTS
- 引数なし: 全未記入セクションを対象
- セクション番号: 指定セクションのみ（複数指定可、例: `1.5` / `2 6`）

---

## Instructions

1. カレントディレクトリから親ディレクトリへ向かって `xddp.config.md` を検索し、`XDDP_DIR` / `MULTI_REPO` / `REPOS` / `REPO_NAME` を取得する
2. `{XDDP_DIR}/project-steering.md` を確認する（なければテンプレートからコピーして続行）
3. プレースホルダー文字列を検出して未記入セクションを特定する
4. 未記入セクションごとにコードを調査してドラフトを生成する
   - §1: `xddp.config.md` + 依存ファイル（requirements.txt / package.json / go.mod 等）
   - §1.5: REPOS の各リポジトリを並列調査（MULTI_REPO: true のみ）
   - §2: ソースファイルのサンプリングから命名規約を推定
   - §6: ディレクトリ構造 + LANGUAGE に応じたエントリポイントファイル
   - §3・§5: 手動記入の注記を挿入
   - §4: スペックアウト（工程4）で記入される旨の注記を挿入
5. 全ドラフトをまとめて提示し、差分指示を受け付ける（OK が出るまで繰り返す）
6. 確定後に `project-steering.md` へ一括書き込み

See ClaudeCode/.claude/skills/xddp.fill-steering.md for full orchestration logic.
