# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# XDDP リポジトリ開発ガイドライン

このリポジトリは XDDP（eXtreme Design-Driven Process）を Claude Code で運用するための
スキル・テンプレート・エージェント定義を管理します。

## セットアップ・デプロイ

```bash
# 初回セットアップ（~/.claude/ にコピー）
bash ClaudeCode/setup.sh
```

`setup.sh` の動作：
- `~/.claude/` に該当ファイルがなければコピー
- `ClaudeCode/.claude/` 側が新しければ **自動上書き更新**（mtime 比較）
- `~/.claude/` 側が新しければスキップ

スキル・コマンド・テンプレートを編集したら `setup.sh` を再実行してデプロイすること。
`~/.claude/` を直接編集すると次回 `setup.sh` 実行時に上書きされるため、必ず `ClaudeCode/.claude/` 側を編集する。

詳細は [README.md](README.md) を参照してください。

## 想定するプロジェクト構成

実際の開発時は以下のディレクトリ構成を想定する。

```
~/workspace/
├── docs/              # 過去の知見・既存ドキュメント（プロジェクト横断）
├── repo-A/            # 母体コード（開発対象リポジトリ）
│   ├── xddp/          # XDDP 成果物（CR フォルダ・latest-specs 等）
│   └── xddp.config.md
└── XddpSettings/      # このリポジトリ（XDDP 設定管理）

~/.claude/             # setup.sh によるインストール先（スキル・コマンド・テンプレート）
```

- `XddpSettings` はスキル・テンプレートの **開発リポジトリ**。編集後に `setup.sh` で `~/.claude/` へ反映する
- `~/.claude/` は `setup.sh` によるインストール先であり、直接編集しない（次回 setup.sh で上書きされる）
- 開発作業は `repo-A` 等の母体リポジトリ上で行う
- `docs/` はプロジェクト横断の知見・既存ドキュメントを蓄積する場所

## ファイル構成

| パス | 説明 |
|---|---|
| `ClaudeCode/setup.sh` | セットアップスクリプト |
| `ClaudeCode/.claude/skills/` | スキルファイル（XDDPフェーズ実行ロジック） |
| `ClaudeCode/.claude/skills/xddp.common.md` | スキル共通ロジック（CR 解決等）。コマンド対応なし。変更時は全スキルの動作確認が必要 |
| `ClaudeCode/.claude/commands/` | スラッシュコマンド定義（スキルの薄いラッパー） |
| `ClaudeCode/.claude/agents/` | サブエージェント定義 |
| `ClaudeCode/.claude/templates/` | 成果物テンプレート（`project-steering-template.md` 含む） |
| `ClaudeCode/.claude/templates/xddp.skill-template.md` | 新規スキル作成用ひな形（CR 解決行を含む） |
| `docs/` | このリポジトリ自体の要求書 |

### アーキテクチャパターン：スキル → コマンド → エージェント

- **skills/**: フェーズ実行の全ロジックを持つ。スキルが直接エージェントを呼び出す
- **commands/**: スキルへの委譲を宣言するだけの薄いラッパー（詳細ロジックを書かない）
- **agents/**: スキルから自動呼び出されるサブエージェント定義。人が直接呼ぶことはない

スキルを修正する場合は `skills/` のみ編集し、`commands/` の要約も同期更新すること（後述）。

### project-steering.md の位置付け

`/xddp.01.init` 実行時に `{XDDP_DIR}/project-steering.md` として生成される（`project-steering-template.md` からコピー）。
プロジェクト固有の命名規約・アーキテクチャ決定・既存パターンを記録するAI参照ファイルで、工程05（実装方式検討）・工程06（変更設計書作成）で `STEERING_CONTEXT` として読み込まれる。
ファイルが存在しない場合や未記入でもXDDPプロセスは動作するが、工程04（specout）開始前に記入することで工程05・06の成果物品質が向上する。
マルチリポジトリ構成の場合は `MULTI_REPO: true` を設定し、「1.5 リポジトリ構成」セクションにリポジトリ一覧・依存関係・共有インタフェースを記入する（`xddp.config.md` の `REPOS:` と名称を一致させること）。

### xddp.config.md の位置付け

`/xddp.01.init` 実行時にテンプレート（`~/.claude/templates/xddp.config.md`）から**ワークスペースルート**へコピー生成される。
XDDP コマンドはワークスペースルートで実行し、`xddp.config.md` もワークスペースルートに1つだけ置く（マルチリポジトリ構成でも共通）。

```
workspace/          ← xddp コマンドをここで実行
  xddp.config.md   ← このファイル
  xddp/            ← XDDP_DIR（デフォルト）
  baseline_docs/   ← DOCS_DIR（デフォルト）
  repo-A/
  repo-B/
```

`XDDP_DIR` 設定で XDDP 成果物（CR フォルダ・latest-specs・project-steering.md 等）の配置先をワークスペースルートからの相対パスで指定する（デフォルト: `xddp`）。
`DOCS_DIR` 設定で中央知識ハブのパスをワークスペースルートからの相対パスで指定する（デフォルト: `baseline_docs`）。
`CR_PREFIX` 設定で CR フォルダ名のプレフィックスを指定する（デフォルト: `CR`）。スキルの引数解釈と自動検出の両方に使われる。
マルチリポジトリ対応として `MULTI_REPO` フラグと `REPOS:` マッピングが定義されており、`MULTI_REPO: true` にすると `xddp.04.specout`（工程4）と `xddp.07.code`（工程9）がリポジトリ境界をまたいで動作する。

## 開発ルール

### 変更前の計画・合意（必須）

`ClaudeCode/.claude/` 以下のファイル（skills / commands / agents / templates）を変更する前に、以下の手順を必ず守ること。

1. `plans/_template.md` をコピーして `plans/PLAN-YYYYMMDD-{description}.md` を作成する（ファイル名は英語のみ・日本語不可）
2. 変更内容・対象ファイル・Before/After・影響範囲を記載する
3. 人がプランを確認・修正し、ステータスを「承認済み」に更新する
4. 承認を確認してから実装（ファイル編集）を開始する

**Claude はプランファイルの承認確認前に `ClaudeCode/.claude/` 以下を編集してはならない。**

### 実装後の関連ドキュメント更新（必須）

`ClaudeCode/.claude/` 以下のファイルを変更した後、以下のドキュメントを必ず確認し、内容が古くなっていれば更新すること。

| 変更内容 | 更新が必要なドキュメント |
|---|---|
| スキルの動作・手順を変更 | 対応する `commands/` の要約、`README.md` のフェーズ説明 |
| コマンドの引数・出力を変更 | `README.md` の使い方セクション |
| テンプレートの構造を変更 | `README.md` のプロジェクト固有ファイル一覧、`CLAUDE.md` の該当説明 |
| `xddp.config.md` テンプレートに設定キーを追加・削除 | `CLAUDE.md` の「xddp.config.md の位置付け」節、`README.md` |
| 任意の変更 | 承認済みプランファイルのステータスを「実装完了」に更新 |

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
| `ClaudeCode/.claude/skills/xddp.fill-steering.md` | `ClaudeCode/.claude/commands/xddp.fill-steering.md` |

### commands ファイルの書き方

- スキルへの委譲を宣言し、処理ステップを番条書きで要約する
- 詳細ロジックはスキルファイルに持ち、commands には書かない
- `See ClaudeCode/.claude/skills/xddp.0X.*.md for full orchestration logic.` で締める

### 新規スキル作成のルール

xddp スキルを新規作成する際は、必ず以下を守ること:

1. `ClaudeCode/.claude/templates/xddp.skill-template.md` をひな形として使用する
2. 引数セクションの直後に以下の CR 解決行を含めること:
   `Read \`~/.claude/skills/xddp.common.md\`, apply "## CR Resolution" with $ARGUMENTS → let \`CR\`, \`REST_ARGS\`.`
3. CR を使わないスキル（xddp.fill-steering 等）はこの限りではない

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
