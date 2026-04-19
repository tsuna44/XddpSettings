# XDDP リポジトリ開発ガイドライン

このリポジトリは XDDP（eXtreme Design-Driven Process）を Claude Code で運用するための
スキル・テンプレート・エージェント定義を管理します。

## セットアップ方法

```bash
git clone <this-repo>
bash ClaudeCode/setup.sh
```

詳細は [README.md](README.md) を参照してください。

## ファイル構成

| パス | 説明 |
|---|---|
| `ClaudeCode/setup.sh` | セットアップスクリプト |
| `ClaudeCode/.claude/skills/` | スキルファイル（XDDPフェーズ実行ロジック） |
| `ClaudeCode/.claude/commands/` | スラッシュコマンド定義（スキルの薄いラッパー） |
| `ClaudeCode/.claude/agents/` | サブエージェント定義 |
| `ClaudeCode/.claude/templates/` | 成果物テンプレート |
| `ClaudeCode/.claude/CLAUDE.md` | `~/.claude/CLAUDE.md` になるグローバル指示 |
| `docs/` | このリポジトリ自体の要求書 |

## 開発ルール

### スキル・コマンドファイルの同期

`ClaudeCode/.claude/skills/xddp.0X.*.md` を変更した場合、対応する `ClaudeCode/.claude/commands/xddp.0X.*.md` の要約も必ず同時に更新すること。

| スキルファイル | コマンドファイル |
|---|---|
| `ClaudeCode/.claude/skills/xddp.01.init.md` | `ClaudeCode/.claude/commands/xddp.01.init.md` |
| `ClaudeCode/.claude/skills/xddp.02.analysis.md` | `ClaudeCode/.claude/commands/xddp.02.analysis.md` |
| `ClaudeCode/.claude/skills/xddp.03.req.md` | `ClaudeCode/.claude/commands/xddp.03.req.md` |
| `ClaudeCode/.claude/skills/xddp.04.specout.md` | `ClaudeCode/.claude/commands/xddp.04.specout.md` |
| `ClaudeCode/.claude/skills/xddp.05.arch.md` | `ClaudeCode/.claude/commands/xddp.05.arch.md` |
| `ClaudeCode/.claude/skills/xddp.06.design.md` | `ClaudeCode/.claude/commands/xddp.06.design.md` |
| `ClaudeCode/.claude/skills/xddp.07.code.md` | `ClaudeCode/.claude/commands/xddp.07.code.md` |
| `ClaudeCode/.claude/skills/xddp.08.test.md` | `ClaudeCode/.claude/commands/xddp.08.test.md` |
| `ClaudeCode/.claude/skills/xddp.09.specs.md` | `ClaudeCode/.claude/commands/xddp.09.specs.md` |
| `ClaudeCode/.claude/skills/xddp.close.md` | `ClaudeCode/.claude/commands/xddp.close.md` |
| `ClaudeCode/.claude/skills/xddp.review.md` | `ClaudeCode/.claude/commands/xddp.review.md` |
| `ClaudeCode/.claude/skills/xddp.revise.md` | `ClaudeCode/.claude/commands/xddp.revise.md` |
| `ClaudeCode/.claude/skills/xddp.status.md` | `ClaudeCode/.claude/commands/xddp.status.md` |
| `ClaudeCode/.claude/skills/xddp.excel2md.md` | `ClaudeCode/.claude/commands/xddp.excel2md.md` |
| `ClaudeCode/.claude/skills/xddp.md2excel.md` | `ClaudeCode/.claude/commands/xddp.md2excel.md` |

### commands ファイルの書き方

- スキルへの委譲を宣言し、処理ステップを番条書きで要約する
- 詳細ロジックはスキルファイルに持ち、commands には書かない
- `See ClaudeCode/.claude/skills/xddp.0X.*.md for full orchestration logic.` で締める

### ファイル生成の承認

commands, skills, template のファイルを作成するときに write 確認を人にせず、書き込みします。

### ステップ番号体系

スキルファイル番号（01〜09）とprogress.mdの工程番号（1〜15）は別体系。混同しないこと。

| スキル | 実行する工程（progress.md番号） |
|--------|-------------------------------|
| xddp.01.init | 工程1（要求書作成） |
| xddp.02.analysis | 工程2（要求分析・整理） |
| xddp.03.req | 工程3（変更要求仕様書作成） |
| xddp.04.specout | 工程4（スペックアウト）+ 工程5（CRS更新・TM作成） |
| xddp.05.arch | 工程6（実装方式検討） |
| xddp.06.design | 工程7（変更設計書作成）+ 工程8（CRSフィードバック） |
| xddp.07.code | 工程9（コーディング）+ 工程10（静的検証） |
| xddp.08.test | 工程11（テスト設計）+ 工程12（テスト実行）+ 工程13（不具合修正）+ 工程14（不具合フィードバック） |
| xddp.09.specs | 工程15（最新仕様書作成） |
| xddp.close | CR クローズ（気づき集約・知見ログ更新） |
| xddp.review | 単体AIレビュー（工程対象外・随時実行） |
| xddp.revise | 人レビュー指摘の反映（工程対象外・随時実行） |
| xddp.status | 進捗確認（工程対象外・随時実行） |
| xddp.excel2md | USDM形式Excel → Markdown変換（工程対象外） |
| xddp.md2excel | CRS Markdown → USDM形式Excel生成（工程対象外） |
