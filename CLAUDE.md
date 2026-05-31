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

スキル・テンプレートを編集したら `setup.sh` を再実行してデプロイすること。
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
| `ClaudeCode/.claude/skills/` | スキルファイル（`skills/<skill-name>/SKILL.md` 形式でXDDPフェーズ実行ロジックを格納）。スキル名がそのままスラッシュコマンド名になる |
| `ClaudeCode/.claude/skills/xddp.common/SKILL.md` | スキル共通ロジック（CR 解決等）。`user-invocable: false`。変更時は全スキルの動作確認が必要 |
| `ClaudeCode/.claude/agents/` | サブエージェント定義 |
| `ClaudeCode/.claude/skills/xddp.templates/` | XDDP成果物ひな形・スキル作成ひな形（SKILL.mdなし。スキルから直接参照される） |
| `ClaudeCode/.claude/skills/xddp.rules/` | XDDP規約・ルール文書（SKILL.mdなし。スキルから直接参照される） |
| `ClaudeCode/.claude/skills/xddp.md2excel/scripts/` | `xddp.md2excel` スキルが実行するPythonスクリプト（`crs_md2excel.py`） |
| `docs/` | このリポジトリ自体の要求書 |

### アーキテクチャパターン：スキル → エージェント

- **skills/**: フェーズ実行の全ロジックを持つ。スキル名（例: `xddp.02.analysis`）がそのままスラッシュコマンド（`/xddp.02.analysis`）になる
- **agents/**: スキルから自動呼び出されるサブエージェント定義。人が直接呼ぶことはない

### project-steering.md の位置付け

`/xddp.01.init` 実行時に以下の3種類のステアリングファイルが生成される。

| ファイル | テンプレート | 説明 |
|---|---|---|
| `{XDDP_DIR}/project-steering.md` | `project-steering-template.md` | プロジェクト全体の共通規約・ADR |
| `{XDDP_DIR}/project-steering-{repo}.md` | `project-steering-repo-template.md` | リポジトリ固有の命名規約・コーディングパターン。REPOS: の各エントリに対して生成 |
| `{XDDP_DIR}/project-steering-cross.md` | `project-steering-cross-template.md` | リポジトリ間インタフェース規約・APIバージョニング。REPOS: ≥2 の場合のみ生成 |

各ファイルは工程05（実装方式検討）・工程06（変更設計書作成）で `STEERING_CONTEXT` として読み込まれる。
ファイルが存在しない場合や未記入でもXDDPプロセスは動作するが、工程04（specout）開始前に記入することで工程05・06の成果物品質が向上する。
`xddp.config.md` の `REPOS:` キー名と `project-steering-{repo}.md` のファイル名は一致させること。
`cross` はシステム予約名称であり `REPOS:` のキーとして使用してはならない。
（理由: REPOS: エントリが 2 つ以上ある場合、システムがリポジトリ間インタフェースを管理するための
仮想リポジトリとして `cross/` ディレクトリおよび関連成果物（SPO・DSN・CHD・TSP・TRS・latest-specs）を
自動生成するため予約されている）

### xddp.config.md の位置付け

`/xddp.01.init` 実行時にテンプレート（`~/.claude/skills/xddp.templates/xddp.config.md`）から**ワークスペースルート**へコピー生成される。
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
`SPECOUT_MAX_FILES_PER_MODULE` 設定で1モジュール内の波及ファイル数の上限を指定する（デフォルト: `10`）。超過時はサブディレクトリ単位でモジュールファイルを分割出力する（サブディレクトリがない場合は分割しない）。
`SPECOUT_EXCLUDE_PATTERNS` 設定で Discovery BFS から除外するディレクトリ・ファイルパターンをカンマ区切りで指定する（デフォルト: `tests/,test/,__tests__/,spec/,specs/,__mocks__/,fixtures/,vendor/,node_modules/`）。テスト除外は波及伝播のノイズ低減が目的（SPO Section 5.5 のテスト調査は別途実施）。
`SPECOUT_INCLUDE_EXTENSIONS` 設定で Discovery BFS の検索対象拡張子をカンマ区切りで指定する（デフォルト: 空 = 全ファイル）。
`SPECOUT_MAX_WAVE_DEPTH` 設定で Discovery BFS の最大波数上限を指定する（デフォルト: `10`）。超過時は一時停止し、人が継続パス A（剪定・再開）/ B（モジュール一括記録）/ C（スコープ外承認）を選択する。
`REPOS:` マッピングでリポジトリ名とパスを定義する。エントリが1つの場合はシングルリポジトリ、2つ以上の場合はマルチリポジトリとして扱われ、cross/ 成果物（SPO・DSN・CHD・TSP・TRS・latest-specs）が生成される。
`cross` はシステム予約名称であり `REPOS:` のキーとして使用してはならない。
（理由: REPOS: エントリが 2 つ以上ある場合、システムがリポジトリ間インタフェースを管理するための
仮想リポジトリとして `cross/` ディレクトリおよび関連成果物（SPO・DSN・CHD・TSP・TRS・latest-specs）を
自動生成するため予約されている）
廃止: `REPO_NAME` と `MULTI_REPO` は使用しない（旧設定キー）。

## 開発ルール

### 変更前の計画・合意（必須）

`ClaudeCode/.claude/` 以下のファイル（skills / agents）を変更する前に、以下の手順を必ず守ること。

1. `plans/_template.md` をコピーして `plans/PLAN-YYYYMMDD-{description}.md` を作成する（ファイル名は英語のみ・日本語不可）
2. 変更内容・対象ファイル・Before/After・影響範囲を記載する
3. プランの AI レビューを実施し、結果を `plans/review/PLAN-YYYYMMDD-{description}-review.md` に保存する
4. 人がプランとレビュー結果を確認・修正し、ステータスを「承認済み」に更新する
5. 承認を確認してから実装（ファイル編集）を開始する

**Claude はプランファイルの承認確認前に `ClaudeCode/.claude/` 以下を編集してはならない。**

### 実装後の関連ドキュメント更新（必須）

`ClaudeCode/.claude/` 以下のファイルを変更した後、以下のドキュメントを必ず確認し、内容が古くなっていれば更新すること。

| 変更内容 | 更新が必要なドキュメント |
|---|---|
| スキルの動作・手順を変更 | `README.md` のフェーズ説明テーブル |
| コマンドの引数・出力を変更 | `README.md` の使い方セクション |
| テンプレートの構造を変更 | `README.md` のプロジェクト固有ファイル一覧、`CLAUDE.md` の該当説明 |
| `xddp.config.md` テンプレートに設定キーを追加・削除 | `CLAUDE.md` の「xddp.config.md の位置付け」節、`README.md` |
| 任意の変更 | 承認済みプランファイルのステータスを「実装完了」に更新 |

### 新規スキル作成のルール

xddp スキルを新規作成する際は、必ず以下を守ること:

1. `ClaudeCode/.claude/skills/xddp.templates/xddp.skill-template.md` をひな形として使用する
2. `ClaudeCode/.claude/skills/<skill-name>/SKILL.md` として作成する（ドット区切りディレクトリ名を維持）
3. 引数セクションの直後に以下の CR 解決行を含めること:
   `Read \`~/.claude/skills/xddp.common/SKILL.md\`, apply "## CR Resolution" with $ARGUMENTS → let \`CR\`, \`REST_ARGS\`.`
4. CR を使わないスキル（xddp.fill-steering 等）はこの限りではない
5. `user-invocable: false` をフロントマターに追加することで「ユーザーが直接起動するスキルではない」役割を表現できる（xddp.common が使用）

### ファイル生成の承認

skills, agents, template のファイルを作成するときに write 確認を人にせず、書き込みします。

### 適用ドメインの中立性（必須）

XDDPツールはWebシステム・業務システム・組み込み開発など、特定のドメインに依存しない汎用ツールである。
スキル・テンプレート・エージェントを変更する際は、以下の点を確認すること。

- サンプルコード・用語・例示がWebシステム固有（REST API・HTTPステータス・フロントエンド等）に偏っていないか
- 業務システム固有の前提（RDB・トランザクション・画面遷移等）を暗黙的に含んでいないか
- 組み込み開発の制約（メモリ制限・リアルタイム性・ハードウェア依存等）を排除する記述になっていないか
- 特定の言語・フレームワーク・ビルドシステムを前提にした記述になっていないか

ドメイン固有の例示が必要な場合は、複数ドメインの例を並べるか、プレースホルダー（例：`{モジュール名}` `{インタフェース名}`）で抽象化すること。

### 後方互換性ポリシー

このツールは現在開発中であり、ドラスティックな変更が入る場合がある。
**後方互換性は保証しない。**
既存の CR・成果物が新しいフォーマット・仕様に追従できない場合は、再実行・再生成を求めることを許容する。
プラン作成・変更実装において、後方互換性を考慮する必要はない。

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
