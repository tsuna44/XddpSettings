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
/xddp.close REQ-2026-001
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
| `/xddp.close` | CRクローズ・気づき集約・知見ログ更新 |
| `/xddp.excel2md` | USDM形式ExcelをMarkdownに変換 |
| `/xddp.md2excel` | CRS MarkdownをUSDM形式Excelに生成 |
| `/xddp.fill-steering` | project-steering.md の未記入セクションをコード調査で自動ドラフト生成 |

## サブエージェント一覧

各フェーズのスキルから自動的に呼び出されます。直接呼び出す必要はありません。

| エージェント | 役割 |
|---|---|
| `xddp-analyst-agent` | 要求分析メモ（ANA）生成（工程2） |
| `xddp-spec-writer-agent` | 変更要求仕様書（CRS）作成・更新（工程3・5） |
| `xddp-specout-agent` | 母体コード調査・スペックアウト（工程4） |
| `xddp-architect-agent` | 実装方式検討・アーキテクチャメモ（DSN）作成（工程6） |
| `xddp-designer-agent` | 変更設計書（CHD）作成（工程7） |
| `xddp-coder-agent` | CHDに基づくコーディング（工程9） |
| `xddp-verifier-agent` | コーディング後の静的検証（工程10） |
| `xddp-test-writer-agent` | テスト仕様書（TSP）生成（工程11） |
| `xddp-test-runner-agent` | テスト実行・不具合修正（工程12〜14） |
| `xddp-reviewer` | 任意成果物の単体AIレビュー |

## プロジェクト固有ファイル

`/xddp.01.init` 実行時に対象プロジェクトのルートに生成されるファイルです。

| ファイル / ディレクトリ | 生成タイミング | 説明 |
|---|---|---|
| `{CR}/` | `/xddp.01.init` | CRワークスペース。`01_requirements/` 〜 `10_test-results/`・`review/` の工程別フォルダを含む。 |
| `{CR}/progress.md` | `/xddp.01.init` | 各工程の進捗・状態・次コマンドを記録する進捗管理ファイル。各スキルが自動更新する。 |
| `project-steering.md` | `/xddp.01.init` | プロジェクト固有の命名規約・アーキテクチャ決定・既存パターンを記録するAI参照ファイル。工程04（specout）開始前に記入することで工程05・06の成果物品質が上がる。なくても動作するが、記入推奨。マルチリポジトリの場合は「1.5 リポジトリ構成」セクションも記入する。 |
| `xddp.config.md` | `/xddp.01.init` | specout粒度・AIレビュー最大回数・テストフレームワーク・テストケース粒度などの設定ファイル。マルチリポジトリ構成の場合は `MULTI_REPO: true` と `REPOS:` セクションを設定する。 |
| `latest-specs/` | `/xddp.01.init` | `/xddp.09.specs` で生成された最新仕様書の格納先（ドラフト領域）。初回 specout 時は空でよい。 |
| `docs/specs/` | `/xddp.close` | 人レビュー済みの承認済み仕様書の格納先。`latest-specs/` から昇格されたファイルが置かれる。`xddp.config.md` の `SPECS_APPROVED_DIR` で変更可能。 |
| `improvement-backlog.md` | `/xddp.close` | 改善バックログ。各工程の「気づき・提案メモ」のうち今回対応しなかったものを `IDEA-NNN` エントリとして蓄積する。 |
| `lessons-learned.md` | `/xddp.close` | 知見ログ。CR全体を通じて得た教訓を `LL-NNN` エントリとして記録し、次のCR以降に活かす。 |

## マルチリポジトリ対応

複数リポジトリにまたがる変更要求（マイクロサービス構成など）に対応しています。

### セットアップ

**1. `xddp.config.md` の設定**

```yaml
MULTI_REPO: true

REPOS:
  api: ../tasksaas-api
  worker: ../tasksaas-worker
  notify: ../tasksaas-notify
  shared: ../tasksaas-shared
```

パスは `xddp.config.md` からの相対パスまたは絶対パスで指定します。
リポジトリ名（左辺）は CHD・SPO の `リポジトリ:` フィールドや変更対象ファイル一覧で使用される識別子になります。

テストフレームワークをリポジトリごとに個別指定することもできます：

```yaml
TEST_FRAMEWORK_REPOS:
  api: pytest
  worker: pytest
  notify: pytest
  shared: pytest
```

**2. `project-steering.md` の設定**

`MULTI_REPO: true` に設定し、「1.5 リポジトリ構成」セクションにリポジトリ一覧・依存関係・共有インタフェースを記入します。
`xddp.config.md` の `REPOS:` のリポジトリ名と一致させてください。

### 動作

| フェーズ | マルチリポジトリ時の動作 |
|---|---|
| `/xddp.04.specout` | エントリポイントから波及調査を開始し、他リポジトリへの呼び出しを検出したら `REPOS_MAP` を参照して調査を延長する |
| `/xddp.07.code` | CHD の各 Before/After ブロックの `リポジトリ:` フィールドを読み取り、実際のリポジトリパスを解決してコードを適用する |

---

## ファイル構成

```
ClaudeCode/
├── setup.sh               ← セットアップスクリプト
└── .claude/               ← ~/.claude にコピーされる（CLAUDE.md を除く）
    ├── settings.json      ← グローバル設定
    ├── agents/            ← サブエージェント定義（10種）
    ├── commands/          ← スラッシュコマンド定義（15種）
    ├── skills/            ← フェーズ実行ロジック
    └── templates/         ← 成果物テンプレート（project-steering-template.md 含む）
docs/
└── REQ-2026-001_要求書.md   ← このリポジトリ自体の要求書
```
