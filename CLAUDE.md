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

XDDP を使うときは以下のディレクトリ構成を想定する。

```
~/workspace/           # ワークスペースルート。XDDP コマンドはここで実行する
├── xddp.config.md     # ワークスペースに1つだけ（マルチリポジトリでも共通）
├── xddp/              # XDDP_DIR（既定）。CR フォルダ・latest-specs 等
├── baseline_docs/     # DOCS_DIR（既定）。プロジェクト横断の知見・既存ドキュメント
├── repo-A/            # 母体コード（開発対象リポジトリ）
└── XddpSettings/      # このリポジトリ（XDDP 設定管理）

~/.claude/             # setup.sh によるインストール先（スキル・コマンド・テンプレート）
```

- `XddpSettings` はスキル・テンプレートの **開発リポジトリ**。編集後に `setup.sh` で `~/.claude/` へ反映する
- `~/.claude/` は `setup.sh` によるインストール先であり、直接編集しない（次回 setup.sh で上書きされる）
- XDDP の工程は `repo-A` 等の母体リポジトリのコードを対象に、ワークスペースルートで実行する

## ファイルの置き場所

各スキル・エージェント・スクリプトの役割は [README.md](README.md)、設定キーの説明は
`ClaudeCode/.claude/skills/xddp-01-init/templates/xddp.config.md`、設計根拠は `docs/adr/` を見る。

### デプロイ対象

- `ClaudeCode/.claude/` 配下を `setup.sh` が `~/.claude/` へコピーする
- このリポジトリの `CLAUDE.md`・`README.md`・`docs/`（要求書・`docs/adr/`）・`plans/`・`tools/` は開発リポジトリ限定で、デプロイしない

### スキルとエージェント

- `skills/<skill-name>/SKILL.md`: フェーズ実行の全ロジック。スキル名がそのままスラッシュコマンド名になる
- `agents/*.md`: スキルから呼ぶサブエージェント定義。人が直接呼ぶことはない
- `skills/xddp-common/SKILL.md`: スキル共通ロジック（CR 解決・設定の読み込み等。`user-invocable: false`）。変更したら全スキルの動作を確認する

### スキル配下のファイル

| 置き場所 | 置くもの | 決まり |
|---|---|---|
| `skills/<skill>/templates/` | そのスキルが所有するテンプレート | 他のスキル・エージェントからも `~/.claude/skills/<skill>/templates/…` で参照してよい（例: `xddp-03-req/templates/` を `xddp-02-analysis` が使う） |
| `skills/xddp-common/templates/` | 特定のスキルが所有しない共有テンプレート（project-rulebook-*.md 等） | |
| `skills/<skill>/scripts/` | そのスキルが所有する決定的処理スクリプト | 他のスキル・共通プロシージャからも呼んでよい（例: `xddp-04-specout/scripts/` は工程5・6・`xddp-investigate`・`xddp-common/procedures/ripple-*.md` が使う） |
| `skills/xddp-common/scripts/` | 全スキルの基盤になるスクリプト（進捗・設定・lint 等） | |
| `skills/<skill>/*.md`（SKILL.md 以外） | そのスキルの SKILL.md と、そのスキルが起動するエージェントが読む低頻度手順 | フロントマターなし。`# 見出し` + blockquote でスコープを書く。他のスキルの SKILL.md から参照しない（そのファイルを読むエージェントを他のスキルが起動するのはよい。例: `xddp-04-specout/module-documentation.md` を読む `xddp-specout-prelim-agent` は `xddp-investigate` からも起動される） |
| `skills/xddp-common/procedures/` | 複数スキルから参照する共通プロシージャ（1ファイル1プロシージャ） | フロントマターなし。`xddp-common/SKILL.md`「## Procedures Index」に索引を書く。refcheck 検査G が整合を見る（ADR-0016） |
| `skills/xddp-common/reviewer-checklists/{DOCUMENT_TYPE}.md` | `xddp-reviewer` が実行時に1つだけ読むチェックリスト | SKILL.md・フロントマターなし。refcheck 検査E が整合を見る（ADR-0014） |
| `skills/xddp-rules/` | XDDP 規約・ルール文書 | SKILL.md なし。スキルから直接参照する |
| `skills/xddp-templates/` | スキル開発用のひな形（`xddp.skill-template.md` 等） | SKILL.md なし |

- スクリプトは標準ライブラリだけで書く。例外は2つある
  - openpyxl: `xddp-md2excel`・`xddp-excel2md` が使う。`MD2EXCEL_PYTHON_BIN` で実行する Python を指定する
  - tree-sitter: `specout_slice.py` と、それを使う `specout_fieldtrace*.py` が使う。`SPECOUT_SLICE_PYTHON_BIN` で実行する Python を指定する
- スクリプトのサブコマンド・引数・終了コードはスクリプトの docstring と `--help` に書く。README.md「### 決定的処理スクリプト」の表には役割と呼び出し元を書く
- 中間ファイルを出す工程は、`{工程}/{repo}/work/` または `{工程}/{repo}/ripple/{調査}/work/` に置く（`xddp_review_brief.py` がレビューの対象から外すのは、この深さの `work/` だけ）

## 予約名と設定ファイル

- `xddp.config.md` はワークスペースルートに1つだけ置く（マルチリポジトリでも共通）。`/xddp-01-init` がテンプレートからコピーして作る
- `cross` は `REPOS:` のキーに使えない（`REPOS:` が2つ以上のとき、リポジトリ間インタフェースの成果物〔SPO・DSN・CHD・TSP・TRS・latest-specs〕を置く仮想リポジトリ名として使う）
- `{XDDP_DIR}/` 直下の `latest-specs`・`survey` は CR フォルダ名に使えない（CR 番号の自動解決が `{XDDP_DIR}/` 直下のディレクトリを列挙するため）
- CR 名に使えない名前（予約ディレクトリ名・スキルの第2引数の予約語）の正は、`xddp-common/SKILL.md`「## CR Resolution」（Step 1・Step 2 の除外と「命名上の注意」）とする。予約名を足す・変えるときは、そこと、テンプレートの「## 成果物ディレクトリ設定」の禁止リストを両方直す
- `REPOS:` のキー名と `project-rulebook-{repo}.md` のファイル名を一致させる
- 設定キーの説明はテンプレート `xddp-01-init/templates/xddp.config.md` に一本化する。キーを足すときは、テンプレートに説明を書く。標準設定バンドル（`xddp-common/SKILL.md`「## Load Config」）で配るキーなら、`xddp_config.py` の既定値と `KEY_DOCS` にも足す（`load --list-keys` で確かめる）。`REVIEW_MAX_ROUNDS`・`FIX_STRATEGY` のように、各スキルが設定ファイルから直接読むキーもある

## 開発ルール

### 決定的処理はスクリプト・意味判定はLLM

決定的処理（帳簿管理・件数照合・状態更新・機械検査等）は Python スクリプトに実装し、LLM は意味判定
（言語知識を要する分類・レビュー）に専念させる。新規に決定的処理を追加する際は、まず
`crs_md2excel.py`（`xddp-md2excel/scripts/`）や `xddp_progress.py`・`artifact_lint.py`（`xddp-common/scripts/`）
等の既存スクリプトを先例として参照すること。

### 人の依頼は LLM の関係判断で拒否しない

人が明示的に依頼した調査・資料化・追記は、LLM が変更要求（CRS 等）との関係を確かめられなくても
拒否・スキップしない。スキル・エージェント・スクリプトを設計するときは次を守ること。

- LLM の判断は「確認できず」として記録するだけにし、「関係なし」「影響なし」と断定させない（成果物にもそう書かせない）。
- 追記するか等の要否は LLM に判断させず、人に尋ねる。
- LLM の判断で扱いを変えたもの（影響の一覧から外した等）は、人が見直せる形で残す（台帳・成果物の注記等）。
- 人の依頼が無い自動の経路（例: 工程4a の追加下調べ）で LLM が対象を絞り込むのは構わない。ただし人が依頼すれば、その絞り込みより依頼を優先する。
  量を抑えるための既定の絞り込み（例: 除外パターンでプロダクションコードに限る）も、人が名指しした対象そのものには適用しない
  （ディレクトリを名指しした場合、その配下の量を抑える既定の絞り込みは効かせてよい。配下も知りたければ人がそこを名指しする）。
- 拒否はしないが、LLM の確認で依頼と食い違う点があれば、根拠を添えて質問・助言する（決めるのは人）。根拠を挙げられない推測は伝えない。

理由: LLM の判断は複雑なパターン以外では信頼できるが、調べきれていないだけで実は関係がある場合がある。
人がわざわざ依頼したものは関係する可能性がある。

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
| テンプレートの構造を変更 | `README.md` のプロジェクト固有ファイル一覧 |
| `xddp.config.md` テンプレートに設定キーを追加・削除 | テンプレート内のキーの説明、`README.md`（人が設定を選ぶ必要がある場合） |
| スクリプトを追加・削除・役割を変更 | `README.md`「決定的処理スクリプト」の表（役割と呼び出し元）。詳細はスクリプトの docstring |
| スキル・エージェントを追加・削除 | `README.md` のフェーズ一覧・サブエージェント一覧、`CLAUDE.md` の「ステップ番号体系」 |
| 置き場所の規則・予約名・ディレクトリの種類を変更 | `CLAUDE.md` の「ファイルの置き場所」「予約名と設定ファイル」、`README.md` の「ファイル構成」の図 |
| スキルの CR 番号の後に置く引数の語（サブコマンド・種別名等）を追加・変更 | `xddp-common/SKILL.md`「## CR Resolution」の「命名上の注意」、テンプレート `xddp.config.md` の CR 名の禁止リスト |
| 任意の変更 | 承認済みプランファイルのステータスを「実装完了」に更新 |

### ツール修正後のハーネス実行（必須）

`ClaudeCode/.claude/` 配下（skills / agents）を変更したら、最低限 `make test`（L1〜L3・**0トークン**・
数秒。`refcheck` ＋全 unittest）を実行し緑を確認する。スキルの分岐・手順など**挙動に関わる変更**の
場合は、該当工程を `make smoke-full PHASE=NN`（隔離HOME・予算ガード）で検証してからプランのステータスを
「実装完了」にする。`make smoke-full`（L4/L5）は `claude` CLI とトークン予算を要するが、
2026-07-26 に校正済み・有効化済みであり、成果物の構造的健全性を advisory チェックとして検証する。
詳細は [README.md](README.md) の「開発時テストハーネス（make）」節を参照。

### 新規スキル作成のルール

xddp スキルを新規作成する際は、必ず以下を守ること:

1. `ClaudeCode/.claude/skills/xddp-templates/xddp.skill-template.md` をひな形として使用する
2. `ClaudeCode/.claude/skills/<skill-name>/SKILL.md` として作成する（ハイフン区切りディレクトリ名を
   使用する。小文字・数字・ハイフンのみ使用可——ドット・大文字・空白は不可。Anthropic Agent Skills
   仕様が `name:` に課す許可文字集合と同一であり、ディレクトリ名と `name:` を完全一致させるため）
3. フロントマターに `name:` を追加する。値はディレクトリ名と完全一致させること
   （例: ディレクトリ `xddp-12-newphase` なら `name: xddp-12-newphase`）
4. 引数セクションの直後に以下の CR 解決行を含めること:
   `Read \`~/.claude/skills/xddp-common/SKILL.md\`, apply "## CR Resolution" with $ARGUMENTS → let \`CR\`, \`REST_ARGS\`.`
5. CR を使わないスキル（xddp-fill-rulebook、xddp-plan-review 等）はこの限りではない
6. `user-invocable: false` をフロントマターに追加することで「ユーザーが直接起動するスキルではない」役割を表現できる（xddp-common が使用）

### 新規エージェント作成のルール

xddp サブエージェント（`ClaudeCode/.claude/agents/*.md`）を新規作成する際、および既存エージェントの
`tools:` を変更する際は、必ず以下を守ること:

1. **`tools:` には Process に明示された手順が実際に必要とするツールのみを列挙する（最小権限原則）。**
   特に `Bash` は任意コマンド実行（書き込み・削除・ネットワークアクセスまで可能）で事故半径が最大の
   権限であるため、Process 内に外部コマンド実行を伴う具体的な手順がある場合のみ付与する。「念のため」
   「将来使うかもしれない」という理由での付与は禁止する。
2. `Grep`/`Glob` は読み取り系で事故半径が小さいため、Process に明示手順がなくても記述外の補助参照
   （関連実装の周辺確認等）のために保持してよい。
3. `Edit` は生成物（`OUTPUT_FILE`）の部分修正に使われうるため、Process 手順が「Write」のみでも
   保持してよい。
4. 既存エージェントの `tools:` を見直す場合も同じ基準を適用し、Process 全文を通読したうえで
   不要な権限がないか確認する。

### ファイル生成の承認

skills, agents, template のファイルを作成するときに write 確認を人にせず、書き込みます。

### 相互参照のルール

`ClaudeCode/.claude/skills/` `ClaudeCode/.claude/agents/` 配下のファイルで他ファイル・自ファイルの
内容を参照する際、行番号（`SKILL.md:123` `L123-145` `123行目` 等）を使用してはならない。
編集のたびに行番号がずれ、AIが実行時に誤った行を読む・照合に失敗するリスクがあるため、
見出し名（`## Step A` 等）・変数名（`ALTERNATIVES_TASK` 等）・番号付きセクションラベル
（`1. **「ユースケース一覧」セクション**` 等、当該ファイルが既に持つ安定した参照アンカー）で参照すること。

### 実行時ファイルへの設計根拠・履歴の混入禁止

`ClaudeCode/.claude/skills/` `ClaudeCode/.claude/agents/` 配下の `.md` には、
**「今何をすべきか」のみを書く**。以下は書いてはならない。

- プランへの参照（`PLAN-YYYYMMDD-*`）
- 変更履歴・削除された旧手順の説明（「旧 Step A にあった〜は削除した」「従来は〜だった」）
- 手順の実行に不要な設計根拠

理由: 実行時に不要な情報がトークンを消費するだけでなく、LLM が「今の手順」と
「過去の経緯」を区別できず、廃止済み手順を復活させるリスクを生む。
設計根拠は `docs/adr/`、変更経緯は `plans/` に記録する。
`tools/harness/refcheck.py` 検査F が機械検査する（`templates/`・`scripts/`・
`xddp-plan-review` は除外）。

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
スキル番号に欠番はない（工程10 = テスト実行系は xddp-10-test-run が担当）。

| スキル | 実行する工程（progress.md番号） | 主な成果物ディレクトリ |
|--------|-------------------------------|---|
| xddp-01-init | 工程1（要求書作成） | 01_requirements/ |
| xddp-02-analysis | 工程2（要求分析・整理） | 02_analysis/ |
| xddp-03-req | 工程3（変更要求仕様書作成） | 03_change-requirements/ |
| xddp-04-specout | 工程4（4a スペックアウト + 4b CRS更新） | 04_specout/ |
| xddp-05-arch | 工程5（実装方式検討） | 05_architecture/ |
| xddp-06-design | 工程6（6a 変更設計書作成 + 6b CRSフィードバック・TM生成） | 06_design/ |
| xddp-07-code | 工程7（コーディング）+ 工程8（静的検証）※工程8は xddp-08-verify でも単体実行可 | 07_coding/, 08_code-review/ |
| xddp-08-verify | 工程8（静的検証）— 人が手動実行する場合（xddp-07-code の自動検証と同一内容） | 08_code-review/ |
| xddp-09-test | 工程9（テスト設計） | 09_test-spec/ |
| xddp-10-test-run | 工程10（10a テスト実行 + 10b 不具合修正 + 10c 不具合フィードバック） | 10_test-results/ |
| xddp-11-specs | 工程11（最新仕様書作成） | latest-specs/（CR外） |
| xddp-close | CR クローズ（気づき集約・知見ログ更新） | —（CR外・随時実行） |
| xddp-abort | CR 中止（気づき記録・VCS 後片付け案内・progress.md への終端状態記録） | —（CR外・随時実行。CR を再開しない前提の終端操作。`xddp-close` の「一時中断」とは異なる） |
| xddp-update-knowledge | 工程対象外・随時実行 | —（CR外・随時実行） |
| xddp-review | 単体AIレビュー（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp-plan-review | プランAIレビュー→修正ループ（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp-revise | 人レビュー指摘の反映（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp-feedback | arch/design/test/code の内容をCRSへ反映（工程対象外・随時実行） | —（CR外・随時実行。CRS・design/code時はTMも更新。codeは事前にCHDも直接更新） |
| xddp-status | 進捗確認（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp-set-profile | CR_PROFILE の切替（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp-excel2md | USDM形式Excel → Markdown変換（工程対象外） | —（CR外・随時実行） |
| xddp-md2excel | CRS Markdown → USDM形式Excel生成（工程対象外） | —（CR外・随時実行） |
| xddp-crs-view | CRS を階層的に閲覧できる HTML ビューア／CLIツリーを生成する（工程対象外・随時実行。Excel を要さない） | —（CR外・随時実行） |
| xddp-sync-design | コード→DSN再生成・リビジョン追加（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp-codemap | モジュールカタログ生成・更新（工程対象外・随時実行） | —（CR外・随時実行） |
| xddp-survey | 工程対象外・随時実行 | `{XDDP_DIR}/survey/`（CR外・随時実行。人の選択で knowledge／latest-specs へ昇格） |
| xddp-investigate | 工程対象外・随時実行（下調べの完了後） | `04_specout/{repo}/ripple/{調査}/`（波紋調査の追加・採用・取り消し・取り除き。採用が変わると SPO を仕上げ直す）、モジュール資料・台帳（依頼調査。人の依頼による資料の追加） |
