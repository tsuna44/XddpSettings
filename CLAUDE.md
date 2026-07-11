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
| `ClaudeCode/.claude/skills/<skill-name>/templates/` | 各スキル専用テンプレート（スキルから直接参照される） |
| `ClaudeCode/.claude/skills/xddp.common/templates/` | 複数スキルで共有するテンプレート（project-rulebook-*.md 等） |
| `ClaudeCode/.claude/skills/xddp.templates/` | スキル開発用メタファイル（xddp.skill-template.md 等。SKILL.mdなし） |
| `ClaudeCode/.claude/skills/xddp.rules/` | XDDP規約・ルール文書（SKILL.mdなし。スキルから直接参照される） |
| `ClaudeCode/.claude/skills/xddp.md2excel/scripts/` | `xddp.md2excel` スキルが実行するPythonスクリプト（`crs_md2excel.py`） |
| `docs/` | このリポジトリ自体の要求書 |

### アーキテクチャパターン：スキル → エージェント

- **skills/**: フェーズ実行の全ロジックを持つ。スキル名（例: `xddp.02.analysis`）がそのままスラッシュコマンド（`/xddp.02.analysis`）になる
- **agents/**: スキルから自動呼び出されるサブエージェント定義。人が直接呼ぶことはない

### project-rulebook.md の位置付け

`/xddp.01.init` 実行時に以下の3種類のステアリングファイルが生成される。

| ファイル | テンプレート | 説明 |
|---|---|---|
| `{XDDP_DIR}/project-rulebook.md` | `project-rulebook-template.md` | プロジェクト全体の共通規約・ADR |
| `{XDDP_DIR}/project-rulebook-{repo}.md` | `project-rulebook-repo-template.md` | リポジトリ固有の命名規約・コーディングパターン。REPOS: が2エントリ以上の場合のみ生成（シングルリポジトリ時は省略） |
| `{XDDP_DIR}/project-rulebook-cross.md` | `project-rulebook-cross-template.md` | リポジトリ間インタフェース規約・APIバージョニング。REPOS: ≥2 の場合のみ生成 |

各ファイルは工程5（実装方式検討）・工程6a（変更設計書作成）で `RULEBOOK_CONTEXT` として読み込まれる。
ファイルが存在しない場合や未記入でもXDDPプロセスは動作するが、工程4（specout）開始前に記入することで工程5・6の成果物品質が向上する。
`xddp.config.md` の `REPOS:` キー名と `project-rulebook-{repo}.md` のファイル名は一致させること。
`cross` はシステム予約名称であり `REPOS:` のキーとして使用してはならない。
（理由: REPOS: エントリが 2 つ以上ある場合、システムがリポジトリ間インタフェースを管理するための
仮想リポジトリとして `cross/` ディレクトリおよび関連成果物（SPO・DSN・CHD・TSP・TRS・latest-specs）を
自動生成するため予約されている）

### xddp.config.md の位置付け

`/xddp.01.init` 実行時にテンプレート（`~/.claude/skills/xddp.01.init/templates/xddp.config.md`）から**ワークスペースルート**へコピー生成される。
XDDP コマンドはワークスペースルートで実行し、`xddp.config.md` もワークスペースルートに1つだけ置く（マルチリポジトリ構成でも共通）。

```
workspace/          ← xddp コマンドをここで実行
  xddp.config.md   ← このファイル
  xddp/            ← XDDP_DIR（デフォルト）
  baseline_docs/   ← DOCS_DIR（デフォルト）
  repo-A/
  repo-B/
```

`XDDP_DIR` 設定で XDDP 成果物（CR フォルダ・latest-specs・project-rulebook.md 等）の配置先をワークスペースルートからの相対パスで指定する（デフォルト: `xddp`）。
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
`DEVELOPMENT_MODE` 設定で開発モードを指定する（デフォルト: `change`）。
`change`: 既存コードへの変更（通常の CR）。工程4（スペックアウト）を実行する。
`new`: 新規開発（母体コードが存在しない状態からの開発）。工程4（4a・4b）をスキップする。
`MIN_COVERAGE` 設定でテストカバレッジの合格閾値（%）を指定する（デフォルト: `80`）。この値以上で自動合格、未満の場合は人が承認するかテストを追加するかを選択する。100 に設定すると旧動作（100% 強制）に戻る。
廃止: `REPO_NAME` と `MULTI_REPO` は使用しない（旧設定キー）。
`FIX_STRATEGY` 設定で工程種別ごとの AI レビュー修正方針を指定する（デフォルト: PLAN=`ideal`、その他=`balanced`）。
`ideal`（本来あるべき姿を優先）/ `balanced`（複数案は人に確認、AI エージェントでは `ideal` と同等）/ `efficiency`（最小インパクト優先）。`REVIEW_MAX_ROUNDS` と同形式の種別ごとの dict で指定する。

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
4. CR を使わないスキル（xddp.fill-rulebook、xddp.plan-review 等）はこの限りではない
5. `user-invocable: false` をフロントマターに追加することで「ユーザーが直接起動するスキルではない」役割を表現できる（xddp.common が使用）

### ファイル生成の承認

skills, agents, template のファイルを作成するときに write 確認を人にせず、書き込みします。

### 適用ドメインの中立性（必須）

**XDDPツールはすべてのソフトウェア開発ドメインを対象とする汎用ツールである。**
Webシステム・業務システム・組み込み・制御システム・科学技術計算・ゲーム開発など、
特定のドメインを前提とした記述をしてはならない。

#### チェックリスト：変更前に必ず確認すること

**用語・表現の偏りチェック：**

| 偏った表現（NG） | ドメイン中立な表現（OK） | 理由 |
|---|---|---|
| API・APIシグネチャ | インタフェース（API・関数シグネチャ・プロトコル・バスI/F等） | APIはWeb/サービス間通信を想起させる |
| マイグレーション・初期データ | 移行手順・初期状態定義 | マイグレーションはRDB前提の用語 |
| クラス図（必須） | データ型関連図（OOP言語の場合） | C言語等の手続き型にクラスは存在しない |
| ER図 | データモデル（ER図/データ構造定義） | ER図はRDB前提 |
| CRUD | データアクセスマトリクス（CRUD/Read-Write/Set-Clear等） | CRUDはDB操作の用語 |
| DBスキーマ変更がある場合 | データ構造・インタフェース変更がある場合 | DBを持たないシステムでも構造変更は発生する |

**成果物・セクションの網羅性チェック：**

- 新しいセクション・成果物を追加するとき、**すべてのドメインで意味を持つか** を確認すること
  - 例：「グローバル変数一覧」は組み込み・業務・Webいずれにも適用できる → OK
  - 例：「ER図（必須）」はRDBを持たないシステムには適用できない → 条件付きまたは代替表現が必要
- 条件付きセクションの条件文がドメイン固有になっていないか確認すること
  - NG例：「RDBを持つ場合は必須」→ OK例：「永続化ストア（DB・ファイル・フラッシュ等）がある場合」

**図種別の適用条件チェック：**

- classDiagram：OOP言語（Java・C++・Python等）の場合のみ必須。C言語では構造体関係図として使用可
- stateDiagram：状態管理がある場合のみ（全ドメインで適用可）
- sequenceDiagram：呼び出しフローがある場合のみ（全ドメインで適用可）
- erDiagram：RDB（リレーショナルDB）がある場合のみ
- タイミング図：リアルタイム・組み込み系では重要度が高い（オプション扱いにしない）

#### 書き方の原則

ドメイン固有の例示が必要な場合は、以下のいずれかで対処する。

1. **複数ドメインの例を並べる：** `（例：DB書き込み/レジスタ書き込み/ファイルI/O）`
2. **プレースホルダーで抽象化：** `{モジュール名}` `{インタフェース名}` `{永続化先}`
3. **条件分岐で説明：** `RDB: ～／組み込み: ～／業務システム: ～`

### 後方互換性ポリシー

このツールは現在開発中であり、ドラスティックな変更が入る場合がある。
**後方互換性は保証しない。**
既存の CR・成果物が新しいフォーマット・仕様に追従できない場合は、再実行・再生成を求めることを許容する。
プラン作成・変更実装において、後方互換性を考慮する必要はない。

### ステップ番号体系

スキルファイル番号は「担当する工程の先頭番号」であり、成果物ディレクトリ番号
（`{CR_PATH}/01_requirements/` 〜 `10_test-results/`）とも一致する。
複数の細分工程を担当するスキルは、工程をサブ番号（4a/4b 等）で表す。
スキル番号に欠番はない（工程10 = テスト実行系は xddp.10.test-run が担当）。

| スキル | 実行する工程（progress.md番号） | 主な成果物ディレクトリ |
|--------|-------------------------------|---|
| xddp.01.init | 工程1（要求書作成） | 01_requirements/ |
| xddp.02.analysis | 工程2（要求分析・整理） | 02_analysis/ |
| xddp.03.req | 工程3（変更要求仕様書作成） | 03_change-requirements/ |
| xddp.04.specout | 工程4（4a スペックアウト + 4b CRS更新・TM作成） | 04_specout/ |
| xddp.05.arch | 工程5（実装方式検討） | 05_architecture/ |
| xddp.06.design | 工程6（6a 変更設計書作成 + 6b CRSフィードバック・TM生成） | 06_design/ |
| xddp.07.code | 工程7（コーディング）+ 工程8（静的検証）※工程8は xddp.08.verify でも単体実行可 | 07_coding/, 08_code-review/ |
| xddp.08.verify | 工程8（静的検証）— 人が手動実行する場合（xddp.07.code の自動検証と同一内容） | 08_code-review/ |
| xddp.09.test | 工程9（テスト設計） | 09_test-spec/ |
| xddp.10.test-run | 工程10（10a テスト実行 + 10b 不具合修正 + 10c 不具合フィードバック） | 10_test-results/ |
| xddp.11.specs | 工程11（最新仕様書作成） | latest-specs/（CR外） |
| xddp.close | CR クローズ（気づき集約・知見ログ更新） | —（CR外・随時実行） |
| xddp.update-knowledge | 工程対象外・随時実行 | —（CR外・随時実行） |
| xddp.review | 単体AIレビュー（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp.plan-review | プランAIレビュー→修正ループ（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp.revise | 人レビュー指摘の反映（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp.status | 進捗確認（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp.excel2md | USDM形式Excel → Markdown変換（工程対象外） | —（CR外・随時実行） |
| xddp.md2excel | CRS Markdown → USDM形式Excel生成（工程対象外） | —（CR外・随時実行） |
| xddp.sync-design | コード→DSN再生成・リビジョン追加（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp.codemap | モジュールカタログ生成・更新（工程対象外・随時実行） | —（CR外・随時実行） |
