# XDDP for Claude Code

Claude Code で XDDP（eXtreme Design-Driven Process）を運用するためのスキル・テンプレート・エージェント定義集です。

## セットアップ

```bash
# 1. リポジトリを取得
git clone <this-repo> xddp

# 2. .claude を ~/.claude に反映
bash xddp/ClaudeCode/setup.sh
```

これで Claude Code 上で XDDP スラッシュコマンドが使えるようになります。

> **既存の ~/.claude に設定がある場合**  
> `setup.sh` は既存ファイルをスキップします（上書きしません）。  
> 強制上書きしたい場合は手動でコピーしてください。
> ```bash
> cp -r ~/.claude ~/.claude.bak
> cp -r xddp/ClaudeCode/.claude/* ~/.claude/
> ```

## 使い方

対象プロジェクトのディレクトリで Claude Code を起動し、スラッシュコマンドを実行します。

### 標準フロー

CR番号と要求書を用意して、フェーズ順に実行します。

```
/xddp.01.init REQ-2026-001 path/to/要求書.md
/xddp.02.analysis REQ-2026-001
/xddp.03.req REQ-2026-001
/xddp.04.specout REQ-2026-001
/xddp.05.arch REQ-2026-001
/xddp.06.design REQ-2026-001
/xddp.07.code REQ-2026-001
/xddp.08.test REQ-2026-001
/xddp.09.specs REQ-2026-001
```

各コマンドは AI が成果物を生成→自動レビュー→人レビューゲートの順で進みます。

### 進捗確認

```
/xddp.status REQ-2026-001
```

### 人が成果物を直接編集した後に AI レビューしたい場合

```
/xddp.review REQ-2026-001 <ドキュメント種別>
```

| ドキュメント種別 | 対象ファイル |
|---|---|
| `analysis` | `02_analysis/ANA-{CR}.md` |
| `req` | `03_change-requirements/CRS-{CR}.md` |
| `specout` | `04_specout/SPO-{CR}.md` |
| `arch` | `05_architecture/DSN-{CR}.md` |
| `design` | `06_design/CHD-{CR}.md` |
| `test` | `09_test-spec/TSP-{CR}.md` |

例：

```
/xddp.review REQ-2026-001 design
```

レビュー結果は `{CR}/review/` に出力されます。  
指摘事項を反映する場合は `/xddp.revise` を使います。

### レビュー指摘を成果物に反映したい場合

```
/xddp.revise REQ-2026-001 <ドキュメント種別>
```

実行すると Claude から「修正箇所を教えてください」と問われるので、リスト形式で指摘を入力します。

```
- セクション3.2: 用語を「変更要求」→「変更要求仕様」に統一
- 表1: トレーサビリティ列が抜けている
```

修正後はレビュー記録ファイルに対応済みとして記録され、ドキュメントのバージョンが +0.1 されます。  
修正後に再度レビューする場合は `/xddp.review` を実行してください。

### フェーズ一覧

| コマンド | 内容 |
|---|---|
| `/xddp.01.init` | CRワークスペース初期化 |
| `/xddp.02.analysis` | 要求分析メモ作成 |
| `/xddp.03.req` | 変更要求仕様書作成 |
| `/xddp.04.specout` | スペックアウト（母体調査） |
| `/xddp.05.arch` | 実装方針設計 |
| `/xddp.06.design` | 変更設計書作成 |
| `/xddp.07.code` | コーディング・静的検証 |
| `/xddp.08.test` | テスト仕様書作成・実行 |
| `/xddp.09.specs` | 最新仕様書生成 |
| `/xddp.status` | 進捗確認 |
| `/xddp.review` | 単体AIレビュー（人が編集した成果物のレビュー） |
| `/xddp.revise` | 人レビュー指摘の反映 |

## ファイル構成

```
ClaudeCode/
├── setup.sh               ← セットアップスクリプト
└── .claude/               ← ~/.claude にコピーされる
    ├── CLAUDE.md          ← グローバルXDDP指示
    ├── settings.json      ← グローバル設定
    ├── agents/            ← サブエージェント定義
    ├── commands/          ← スラッシュコマンド定義
    ├── skills/            ← フェーズ実行ロジック
    └── templates/         ← 成果物テンプレート
docs/
└── REQ-2026-001_要求書.md   ← このリポジトリ自体の要求書
```
