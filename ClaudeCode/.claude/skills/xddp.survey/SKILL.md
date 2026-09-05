---
description: CR 非依存で母体コードを調査し「現状仕様」を文書化する。調査後に (a) 調査のみ (b) knowledge へ昇格
  (c) specs へ昇格 を人が選択する。CR を1本も回していない母体から仕様書を起こす場合に使用する。
  「母体を調査して」「コードの仕様を調べて」「baseline を起こして」などで起動する。
argument-hint: "[repo名] [module {モジュール名}... | topic {シード}... | promote]"
---

You are executing **XDDP Survey — CR 非依存の母体調査**.

> 本スキルは CR 非依存のため CR 解決行（xddp.common の "## CR Resolution"）は不要。

**Arguments:** $ARGUMENTS
- 無引数 → リポジトリ・スコープ種別・対象を対話で確認する
- `{repo}` → スコープ種別を尋ね、候補を提示して人が選択する
- `{repo} module {module}...` → 指定モジュールを調査する（複数可）
- `{repo} module all` → 全モジュール。確認ゲートでトークン量の警告を出したうえで実行する
- `{repo} topic {seed}...` → シード（識別子・ファイルパス・キーワード）起点でモジュール横断調査する
- `{repo} promote` → **調査を行わず昇格のみ実行する。** `{XDDP_DIR}/survey/{repo}/**` の既存 SURVEY
  成果物を列挙して人に選択させ、Step 0.5 → Step 4.5 へ直行する（Step 1〜4 をスキップ）

`cross` は `REPOS:` の予約名であり調査対象にできない。指定された場合はエラーで停止する。

---

### Step 0: Parse arguments, locate xddp.config.md

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Config"
→ let `WORKSPACE_ROOT`, `DOCS_DIR`, `DOCS`, `REPOS_MAP`, `REPOS_KEYS`, `IS_MULTI`,
  `EXCLUDE_PATTERNS`, `INCLUDE_EXTENSIONS`, `SPECOUT_DIAGRAM_LEVEL`, `SPECOUT_SEQUENCE_LEVELS`
  （他の戻り値は本スキルでは未使用）.

Let `TODAY` = today's date (YYYY-MM-DD).

**Resolve target repo (`REPO_NAME`):**
- 第1引数が `REPOS_KEYS` のいずれかと完全一致 → `REPO_NAME` = その値。`REPO_PATH` = `REPOS_MAP[REPO_NAME]`
- 第1引数が `cross` → エラー「`cross` は予約名のため調査対象にできません」を報告して停止する
- 第1引数が一致しない、または無指定 → 対話でリポジトリを選択させる（`REPOS_KEYS` が1件のみの場合は自動確定して報告する）

**Resolve mode (`MODE`):**
- 残り引数の先頭が `promote` → `MODE = promote`
- 残り引数の先頭が `module` → `MODE = module`。以降のトークンを `MODULE_ARGS` とする
- 残り引数の先頭が `topic` → `MODE = topic`。以降のトークンを `SEED_ARGS` とする
- 残り引数が空 → 対話で `module`/`topic` を選択させ、対象を確認して `MODULE_ARGS`/`SEED_ARGS` を確定する

#### Step 0.5（`MODE = promote` の場合のみ）: 既存 SURVEY の選択

`{WORKSPACE_ROOT}/{XDDP_DIR}/survey/{REPO_NAME}/**/SURVEY-*.md` を Glob で列挙し、番号付きリストで
人に選択させる（複数選択可）。1件も無い場合はその旨を報告して停止する。

選択された各ファイルについて、パスから以下を復元する:
- `SURVEY_FILE` = 選択されたファイルパス
- `SCOPE_KIND` = パスに `/module/` を含む場合 `module`、`/topic/` を含む場合 `topic`
- `SCOPE_NAME` / `MODULE_KEBAB`（module のときのみ）= 親ディレクトリ名
- `TOPIC_SLUG`（topic のときのみ）= ファイル名の `SURVEY-` 接頭辞・`.md` 拡張子を除いた部分

これを Step 4 完了時点の状態とみなし、選択された各ファイルについて Step 4.5 以降を1件ずつ実行する
（Step 1〜4 は実行しない）。

---

### Step 1: スコープ種別・対象の確定

`MODE = promote` の場合はこの Step 全体をスキップする（Step 0.5 で完了済み）。

Let `CATALOG_FILE` = `{DOCS}/{REPO_NAME}/module-catalog.md`。

存在すれば Read し `CATALOG_AVAILABLE = true` とする。存在しなければ次の警告を表示し、
`CATALOG_AVAILABLE = false` として**停止せず**続行する（module-catalog 不在時の縮退動作）:

> ⚠️ `{CATALOG_FILE}` が見つかりません。`/xddp.codemap {REPO_NAME}` の実行を推奨しますが、
> 縮退モードで調査を続行します（網羅性が劣る可能性があります）。

**`MODE = module` の場合:**
- `MODULE_ARGS` が `all` → 全モジュールを対象とする。トークン量（対象ファイル数から概算）の警告を表示し、
  続行確認を得る
- それ以外 → `MODULE_ARGS` の各要素を対象モジュール名 `TARGET_MODULES` とする
- `CATALOG_AVAILABLE = true` の場合: `module-catalog.md`「## 2. モジュール一覧」と照合する
- `CATALOG_AVAILABLE = false` の場合: リポジトリ直下の第1〜2階層ディレクトリを Glob で列挙し、
  `TARGET_MODULES` の各名称と一致するものをモジュール候補とする
  （既存の慣行——`xddp-close-knowledge-agent.md` Step C3.6 の「ファイルパスの第1〜2階層ディレクトリ名」・
  `xddp.update-knowledge/SKILL.md` の constraint 入力プロンプト——に合わせる）

**`MODE = topic` の場合:** `SEED_ARGS` をそのまま `SEEDS` とする（Step 2 で処理）。

---

### Step 2: 調査対象ファイル集合の確定・MODULE_KEBAB / TOPIC_SLUG の導出

`MODE = promote` の場合はこの Step をスキップする。

#### module スコープ

`TARGET_MODULES` の各モジュールについて:
- `CATALOG_AVAILABLE = true`: `module-catalog.md` の当該モジュール定義（主要ファイル・ディレクトリ）から
  `TARGET_FILES` を確定する
- `CATALOG_AVAILABLE = false`: モジュールディレクトリを Glob で列挙し `TARGET_FILES` とする

**`MODULE_KEBAB` の導出（各モジュールについて）:**
1. パス区切り `/` をハイフンに置換する（`src/auth` → `src-auth`）
2. 残りをケバブケースに変換する（キャメル → ハイフン区切り小文字。`AuthService` → `auth-service`）
3. 予約名（`overview` / `cross` / `system`）と一致する場合は `mod-{module-kebab}` に自動変換する

#### topic スコープ

1. 各シードについて `Grep` で定義箇所と参照箇所を収集する。`EXCLUDE_PATTERNS` / `INCLUDE_EXTENSIONS` を適用する
2. `CATALOG_AVAILABLE = true` の場合、`module-catalog.md`「## 3. シンボル索引」でシードを引き、
   索引が示すファイルを集合に加える
3. 得られたファイル集合を `TARGET_FILES` とする

**探索深さは 1 hop 固定とする。** シードの直接の定義元・参照元までを対象とし、さらに追う必要がある場合は
人が追加シードを与えて再実行する（多段の波及展開は工程4a（specout）の役割であり、survey では担わない）。
件数の自動閾値は設けない（Step 3 で全件提示して人が承認する）。

**`TOPIC_SLUG` の導出:**
各シードを次の規則で個別にスラグ化する:「スペース・`/`・`_` をいずれもハイフンに変換し小文字化する。
連続するハイフンは1個に畳み込む」（例: `g_state` → `g-state`）。
**複数シード指定時:** 各シードを上記規則で個別にスラグ化した後、**アルファベット順にソートしてから
`--`（ハイフン2連）で連結する**（例: シード `foo`・`g_state` → `foo--g-state`）。指定順ではなくソート順を
用いるため、シードの列挙順序が異なっても同一の `TOPIC_SLUG` になる。

**再調査時の扱い:** 同一 `MODULE_KEBAB`（module）/ `TOPIC_SLUG`（topic）の SURVEY 成果物が既に存在する
場合は上書きする（過去分が必要な場合は人が事前に退避する）。

---

### Step 3（確認ゲート）: 対象ファイル一覧・出力先・想定トークン規模の確認

`MODE = promote` の場合はこの Step をスキップする。

**`SURVEY_FILE` の出力先:**
| スコープ | 出力先 |
|---|---|
| module | `{WORKSPACE_ROOT}/{XDDP_DIR}/survey/{REPO_NAME}/module/{MODULE_KEBAB}/SURVEY-{MODULE_KEBAB}.md` |
| topic | `{WORKSPACE_ROOT}/{XDDP_DIR}/survey/{REPO_NAME}/topic/SURVEY-{TOPIC_SLUG}.md` |

対象（module: モジュールごと、topic: 1件）を**一括して**次の内容で提示する:

> **調査対象確認**
> | # | スコープ | 対象ファイル数 | 出力先 |
> |---|---|---|---|
> | 1 | {module: {module名} / topic: {SEEDS}} | {N} | {SURVEY_FILE} |
>
> 対象ファイル一覧: {TARGET_FILES を対象ごとに列挙}
> 想定トークン規模: 目安 {対象ファイルの合計行数から概算}
>
> このまま調査を実行しますか？ [はい / いいえ / 対象を絞り込む]

**承認前は一切書き込まない。** 承認後、Step 4 へ進む。「対象を絞り込む」の場合は Step 2 に戻る。

---

### Step 4: xddp-survey-agent の起動（調査の完了点）

`MODE = promote` の場合はこの Step をスキップする（Step 0.5 で選択した既存 SURVEY を使う）。

対象（module スコープは対象モジュールごとに1回、topic スコープは1回）ごとに **Agent tool**
`subagent_type=xddp-survey-agent`:
```
REPO_NAME: {REPO_NAME}
REPO_PATH: {REPO_PATH}
SCOPE_KIND: module|topic
SCOPE_NAME: {module名 または SEEDS の列挙}
MODULE_KEBAB: {module スコープのときのみ}
TARGET_FILES: {Step 2 で確定した当該対象のファイル一覧}
DOCS: {DOCS}
MODULE_CATALOG_FILE: {CATALOG_FILE（不在時は空文字列）}
OUTPUT_FILE: {Step 3 で確定した SURVEY_FILE}
TODAY: {TODAY}
SPECOUT_DIAGRAM_LEVEL: {SPECOUT_DIAGRAM_LEVEL}
SPECOUT_SEQUENCE_LEVELS: {SPECOUT_SEQUENCE_LEVELS}
```

**ここが「調査」の完了点である。** 以降の Step 4.5〜8 は昇格の選択に応じてのみ実行する。

---

### Step 4.5（昇格ゲート）

対象（module: モジュールごと、topic: 1件。`MODE = promote` の場合は Step 0.5 で選択した各ファイル）
ごとに次を提示する:

> **調査が完了しました:** `{SURVEY_FILE}`
>
> この結果をどう扱いますか？
> (a) 調査のみで終了（`{XDDP_DIR}/survey/` に残す。baseline は変更しない）
> (b) knowledge へ昇格（`{DOCS}/{REPO_NAME}/knowledge/code-knowledge/` へ登録）
> (c) specs へ昇格（`{DOCS}/{REPO_NAME}/specs/{module}/` へ登録）{`SCOPE_KIND: topic` の場合は
>     「— topic スコープのため選択不可」を付記し選択肢から外す}

(a) を選んだ場合: 何もせず Step 9 へ進む（SURVEY 成果物は `{XDDP_DIR}/survey/` に残る）。
(b) を選んだ場合: Step 5 へ進む。(c) を選んだ場合: Step 6 へ進む。

---

### Step 5（(b) を選んだ場合）: knowledge への昇格

Read `~/.claude/skills/xddp.rules/code-knowledge-boundary.md`, apply "## 宛先ルーティング表"
  → let `KNOWLEDGE_ROUTING`.

**SURVEY 節 → knowledge 昇格の対応と昇格条件:**
| SURVEY 節（04_specout-module-template.md 由来） | 昇格条件 | 適用軸 | 昇格先 |
|---|---|---|---|
| 2.4 定数・列挙値一覧 / 2.5 グローバル変数一覧 | モジュール横断で参照・変更されるもののみ | 軸2 | `_constants/{DOMAIN}-constants.md` |
| 2.5 グローバル変数の更新元・参照元 | モジュール横断の識別子のみ | 軸2 | `_flows/{DOMAIN}-{VAR_NAME}-callgraph.md` |
| 2.6 制約・前提条件 | 常に | 軸1 | `{MODULE}/constraints.md` |
| 4.2 データ型関連図 / 4.3 データ構造 | 落とし穴・注意点の記述が伴う場合のみ | 軸1 | `_structures/{DOMAIN}-relations.md` |
| 2.1 処理フロー / 4.5 モジュール内シーケンス図 | 複数モジュールにまたがるフローのみ | 軸2 | `_flows/{DOMAIN}-{FLOW_NAME}-sequence.md` |

上記の**昇格条件を満たす節のみ**を選択候補として人に提示し（条件を満たさない節はそもそも候補に出さない）、
「どの節を昇格するか」（`SELECTED_SECTIONS` — 候補からの部分選択。人が今回は省略したい節を外せる）と
ドメイン名（`DOMAIN`）を確定させる。module スコープの survey は単一モジュールが対象のため、軸2に該当する
項目は少ない（「module スコープで昇格対象がゼロ件」は正常。軸2の主な供給源は topic スコープ）。

**Agent tool** `subagent_type=xddp-survey-promote-agent`:
```
REPO_NAME: {REPO_NAME}
SURVEY_FILE: {SURVEY_FILE}
SELECTED_SECTIONS: {SELECTED_SECTIONS}
DOMAIN: {DOMAIN}
MODULE: {MODULE_KEBAB（module スコープ）/ 空文字列（topic スコープ。2.6 由来の constraints.md 昇格は
  module スコープのみで発生する）}
DOCS: {DOCS}
TODAY: {TODAY}
```

完了後 Step 9 へ進む。`specs/` は変更しない。

---

### Step 6（(c) を選んだ場合）: specs への昇格・衝突判定

**冒頭で対象の全モジュールの衝突判定をまとめて実行する。** モジュールごとに
`{WORKSPACE_ROOT}/{XDDP_DIR}/latest-specs/{REPO_NAME}/{MODULE_KEBAB}/spec.md` の frontmatter `source` を
確認する。

| 既存 `source` | 動作 |
|---|---|
| なし（ファイル自体が不在） | 新規生成 |
| `survey` | 上書き再生成する |
| `spo` | 既定はスキップ。全対象モジュールの判定完了後、`spo` 衝突モジュールが1件以上あれば下記の
  一括確認を1回だけ行う |

`spo` 衝突モジュールが1件以上ある場合、その全件を**1回の確認でまとめて**提示する
（モジュールごとに個別のダイアログを複数回出さない。「なし」「`survey`」は自動判定のみで人に問わない）:

> 以下のモジュールは CR で検証済みの仕様（`source: spo`）が既に存在します。
> | モジュール |
> |---|
> | {module} |
>
> 全上書きしますか？（survey の内容で置き換えます。CR 検証済みの内容は失われます） [スキップ / 全上書き]

「スキップ」を選んだモジュールは以降のループから除外する（既存 `spec.md` は一切変更しない）。

対象モジュールごとに **Agent tool** `subagent_type=xddp-specs-mod-agent`（**1モジュール1回**）:
```
CR_NUMBER: SURVEY-{TODAY}
CR_PATH: （空文字列）
XDDP_DIR: {XDDP_DIR}
REPO_NAME: {REPO_NAME}
REPO_PATH: {REPO_PATH}
DOCS: {DOCS}
TODAY: {TODAY}
SURVEY_MODE: true
SURVEY_FILE: {当該モジュールの SURVEY_FILE}
MODULE_SCOPE: [{MODULE_KEBAB}]
MODULE_KEBAB: {MODULE_KEBAB}
OUTPUT_FILE: {WORKSPACE_ROOT}/{XDDP_DIR}/survey/{REPO_NAME}/module/{MODULE_KEBAB}/PENDING-MOD-SURVEY-{TODAY}.md
```

---

### Step 7（(c) のみ）: レビュー ＋ インライン自動修正（最大1サイクル）

Step 6 で生成・更新した `latest-specs/{REPO_NAME}/{MODULE_KEBAB}/` 配下の全ファイルを `TARGET_FILES` とする。
Step 8② で `architecture.md` を新規作成・追記した場合はそれも `TARGET_FILES` に含める。

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Invoke Reviewer" with:
```
DOCUMENT_TYPE: SPEC
TARGET_FILES: {上記ファイル一覧}
REFERENCE_FILES: [{対象モジュールの SURVEY_FILE を列挙}]
REVIEW_ROUND: 1
OUTPUT_FILE: {WORKSPACE_ROOT}/{XDDP_DIR}/survey/{REPO_NAME}/review/SPEC-SURVEY-{TODAY}.md
```

Read `{OUTPUT_FILE}`。🟡（自動修正対象カテゴリ: Mermaid 図の構文エラー・フロントマター必須キーの漏れ・
変更履歴エントリの形式不備・気づきメモセクションの有無）があれば、スキル自身が直接該当ファイルを編集して
修正する（最大1回。工程11 Step REV と同一方式）。修正後、`REVIEW_ROUND: 2` で `apply "## Invoke Reviewer"`
を再実行し `{OUTPUT_FILE}` を上書きする。それ以外の指摘（🔴。SPO 内容との矛盾等）は本スキルでは自動修正せず、
Step 8 の人レビューゲートに委ねる。

**`REVIEW_MAX_ROUNDS.SPEC` / `FIX_STRATEGY.SPEC` は使用しない**（修正サイクルは常に最大1回固定）。

---

### Step 8（(c) のみ）: 人レビューゲート・DOCS への昇格

人に `{OUTPUT_FILE}` の確認を促し、承認を待つ。承認前は DOCS 側に一切書き込まない。

承認後、以下を実行する:

**① spec コピー（今回生成・更新したモジュールのみ）:**
```
For each {module} in （Step 6 で生成・更新したモジュール一覧）:
  Copy {WORKSPACE_ROOT}/{XDDP_DIR}/latest-specs/{REPO_NAME}/{module}/
    → {DOCS}/{REPO_NAME}/specs/{module}/
```
このコピーでは `overview/` および他モジュールには一切触れない（`architecture.md` への追記は②で別途行う）。

**② `latest-specs/{REPO_NAME}/overview/architecture.md` への追記（追記のみ）:**
Let `ARCH_FILE` = `{WORKSPACE_ROOT}/{XDDP_DIR}/latest-specs/{REPO_NAME}/overview/architecture.md`。
- `ARCH_FILE` が存在しない場合: `~/.claude/skills/xddp.11.specs/templates/11_overview-architecture-template.md`
  から新規作成し、対象モジュールのエントリのみを記載する（`overview/` ディレクトリも併せて作成する）。
  **このテンプレートを正本とし、セクション構成・テーブル列構成を再定義してはならない。**
- `ARCH_FILE` が存在する場合: 「## 3. モジュール一覧」テーブルに今回対象モジュールの行が無ければ追記する
  （既に存在する場合はスキップ）。「## 2. アーキテクチャ図（コンポーネント図）」に今回モジュールのノードが
  無い場合はノードのみ追加する。**他モジュールのエントリの更新・削除・並べ替え、図の全体再生成は禁止。**

**③ `{DOCS}/AI_INDEX.md` への追記:**
- `{DOCS}` ディレクトリが存在しない場合: AI_INDEX 更新をスキップし、次の警告を表示する（`{DOCS}` の
  初回作成は `xddp.01.init` が担うため survey は作成しない）:
  > ⚠️ `{DOCS}` が存在しないため AI_INDEX.md の更新をスキップしました。`/xddp.01.init` の実行後に
  > `/xddp.survey {REPO_NAME} promote` を再実行してください。
- `{DOCS}` は存在するが `{DOCS}/AI_INDEX.md` が無い場合: `xddp.01.init/SKILL.md`「Initial file contents」に
  定義済みの内容と同一で新規作成してから以下を実行する。
- 「モジュール別最新仕様」セクション（列: `リポジトリ | モジュール | spec | structure | state | 最終更新CR`。
  キー列: リポジトリ・モジュール）に `{REPO_NAME}`/`{module}` の行を upsert する。`spec`/`structure` 列は
  該当ファイルが存在する場合のみ `[spec.md]({REPO_NAME}/specs/{module}/spec.md)` 形式のリンク、無ければ `—`。
  `state` 列は `—`。最終更新CR列は `SURVEY-{TODAY}`。
- 「リポジトリ別仕様書」セクション（列: `リポジトリ | バージョン | overview | モジュール数 | 最終更新CR`。
  キー列: リポジトリ）の `{REPO_NAME}` 行を upsert する（無ければ新規追加）。バージョンは `ARCH_FILE`
  frontmatter の `version` から `v{version}（最終更新CR: SURVEY-{TODAY}）`。overview 列は
  `[overview]({REPO_NAME}/specs/overview/)`。モジュール数列は `{XDDP_DIR}/latest-specs/{REPO_NAME}/`
  直下のディレクトリ数（`overview/` 除く）から `{N} モジュール`。
  **列構成・リンクパス形式は `xddp.close/scripts/promote.py`「## Step C2 続き: AI_INDEX.md update」の
  `_repo_spec_rows`/`_module_spec_rows` が upsert する既存の列定義と一致させる。survey 側で再定義しない。**
- 他セクション・他リポジトリの行には一切触れない。

Step 9 のサマリーに①〜③それぞれの結果（実施／スキップ／新規作成）を明示する。

---

### Step 9: 結果サマリー

Tell the user（日本語）:

> **母体調査が完了しました**
>
> | 項目 | 内容 |
> |---|---|
> | リポジトリ | {REPO_NAME} |
> | スコープ | {SCOPE_KIND}: {SCOPE_NAME} |
> | 調査結果 | `{SURVEY_FILE}` |
> | 選択 | (a) 調査のみ ／ (b) knowledge 昇格 ／ (c) specs 昇格 |
> {選択に応じた出力先・Step 8 ①〜③ の結果を記載}
>
> **`{XDDP_DIR}/survey/` の扱い:** SURVEY 成果物は人が任意に削除してください。ツール側では自動削除しません
> （CR フォルダと異なりクローズ契機を持たないため。`xddp.close` は `survey/` を参照しません）。VCS 管理の
> 要否はプロジェクト判断です。
>
> **次のステップ:**
> - 追加調査する場合: `/xddp.survey {REPO_NAME} module {module}` または `topic {seed}` を再実行してください
> - 保留中の SURVEY 成果物を後から昇格する場合: `/xddp.survey {REPO_NAME} promote` を実行してください

progress.md は CR 非依存のため更新しない。

---
> **保守メモ:** このファイルを変更した場合は、`README.md`（スキル一覧テーブル）、`CLAUDE.md`
> （ファイル構成テーブル・ステップ番号体系テーブル）も合わせて更新すること。
