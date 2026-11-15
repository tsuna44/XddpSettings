---
name: xddp-survey
description: CR 非依存で母体コードを調査し「現状仕様」を文書化する。調査後に (a) 調査のみ (b) knowledge へ昇格
  (c) specs へ昇格 を人が選択する。CR を1本も回していない母体から仕様書を起こす場合に使用する。
  「母体を調査して」「コードの仕様を調べて」「baseline を起こして」などで起動する。
argument-hint: "[repo名] [module {モジュール名}... | topic {シード}... | promote]"
---

You are executing **XDDP Survey — CR 非依存の母体調査**.

> 本スキルは CR 非依存のため CR 解決行（xddp-common の "## CR Resolution"）は不要。

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

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Load Config"
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

> ⚠️ `{CATALOG_FILE}` が見つかりません。`/xddp-codemap {REPO_NAME}` の実行を推奨しますが、
> 縮退モードで調査を続行します（網羅性が劣る可能性があります）。

**`MODE = module` の場合:**
- `MODULE_ARGS` が `all` → 全モジュールを対象とする。トークン量（対象ファイル数から概算）の警告を表示し、
  続行確認を得る
- それ以外 → `MODULE_ARGS` の各要素を対象モジュール名 `TARGET_MODULES` とする
- `CATALOG_AVAILABLE = true` の場合: `module-catalog.md`「## 2. モジュール一覧」と照合する
- `CATALOG_AVAILABLE = false` の場合: リポジトリ直下の第1〜2階層ディレクトリを Glob で列挙し、
  `TARGET_MODULES` の各名称と一致するものをモジュール候補とする。
  **`TARGET_MODULES` の各要素について、ディレクトリ候補が1件でも一致すれば `DIR_MATCHED[module] = true`、
  1件も一致しなければエラーにせず `DIR_MATCHED[module] = false` として記録し、Step 2 のファイル名一致
  フォールバックに解決を委ねる。** `DIR_MATCHED` は `TARGET_MODULES` の各要素をキーとする
  真偽値マップであり、`module {m1} {m2}...` のように複数モジュールを同時指定した場合も要素ごとに
  独立して判定・保持する。

**`MODE = topic` の場合:** `SEED_ARGS` をそのまま `SEEDS` とする（Step 2 で処理）。

---

### Step 2: 調査対象ファイル集合の確定・MODULE_KEBAB / TOPIC_SLUG の導出

`MODE = promote` の場合はこの Step をスキップする。

#### module スコープ

`TARGET_MODULES` の各モジュールについて:
- `CATALOG_AVAILABLE = true`: `module-catalog.md` の当該モジュール定義の「**ディレクトリ：**」（`REPO_PATH` 相対）の下の
  ファイルを Glob で列挙し、`EXCLUDE_PATTERNS` / `INCLUDE_EXTENSIONS` を適用したものを `TARGET_FILES` とする
- `CATALOG_AVAILABLE = false`: 以下の優先順位で `TARGET_FILES` を確定する（縮退モードのモジュール解決）。

  1. **ディレクトリ一致（既存の挙動）:** Step 1 で `DIR_MATCHED[module] = true` の場合、そのモジュール
     ディレクトリを Glob で列挙し `TARGET_FILES` とする。
  2. **ファイル名一致フォールバック（`DIR_MATCHED[module] = false` の要素のみ）:** リポジトリ直下から
     第1〜2階層まで `EXCLUDE_PATTERNS` / `INCLUDE_EXTENSIONS` を適用してファイルを Glob で列挙し、
     ファイル名（拡張子を除く）を `NORMALIZE()` した値が、モジュール名を同じ規則で `NORMALIZE()`
     した値と一致するファイルを探す。

     **`NORMALIZE(s)` の定義（ファイル名一致の照合にだけ使う）:**
     1. パス区切り `/` をハイフンに置換する（例: `src/auth` → `src-auth`）
     2. キャメルケースをハイフン区切りへ分割し小文字化する（例: `SensorReader` → `sensor-reader`）
     3. `_` を `-` に統一する
     4. 連続するハイフンを1個に畳み込む

     モジュール名側（CLI 引数）・ファイル名側（拡張子を除いたステム）の双方にこの同一関数を適用して
     比較する。
     - **一致1件:** そのファイル単体を「1ファイルモジュール」として `TARGET_FILES` に採用する。
     - **一致複数件**（同名ファイルが複数ディレクトリ・拡張子に存在）: 候補をすべて Step 3
       の確認ゲートに列挙し、人に絞り込みを求める。絞り込まれなかった場合は候補全件を
       `TARGET_FILES` として採用し、その旨を確認ゲートの注記に明記する。
     - **一致0件:** そのモジュール要素の調査を打ち切り、次のメッセージを表示する
       （他のモジュール要素の処理は継続する）:
       > ⚠️ モジュール `{name}` はディレクトリにもファイルにも一致しませんでした。
       > `/xddp-codemap {REPO_NAME}` を実行してカタログを整備するか、`topic {識別子}` スコープで
       > 直接シンボル起点の調査を行ってください。

**`MODULE_DIR`・`MODULE_KEBAB` の決定（各モジュールについて）:**
1. `MODULE_DIR`（モジュールの範囲。`REPO_PATH` 相対・末尾の `/` なし）:
   - module-catalog で解決した場合: catalog の「ディレクトリ」の値
   - ディレクトリ一致で解決した場合: そのディレクトリ
   - ファイル名一致フォールバックで1件に決まった場合: そのファイルのパス
   - ファイル名一致フォールバックで複数件を採用した場合: 空（範囲が決まらない）
   - リポジトリ直下は `.`
2. `MODULE_KEBAB`（SURVEY の置き場所の名前・書く仕様のディレクトリ名）: Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-11-specs/scripts/spec_version_delta.py spec-dir --latest-specs {WORKSPACE_ROOT}/{XDDP_DIR}/latest-specs/{REPO_NAME} --docs-specs {DOCS}/{REPO_NAME}/specs --name {module名} --module-dir "{MODULE_DIR}"`
   → stdout の JSON の `spec_dir` を `MODULE_KEBAB` とする（既存の仕様に同じ `module-dir` のものがあればその名前、
   無ければモジュール名から作った名前。予約名は `mod-` 付き）。`duplicates` が空でなければ Step 3 で注記する。

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
> | # | スコープ | 解決方法 | モジュールの範囲 | 対象ファイル数 | 出力先 |
> |---|---|---|---|---|---|
> | 1 | {module: {module名} / topic: {SEEDS}} | {module-catalog ／ ディレクトリ一致 ／ ファイル名一致フォールバック（縮退） ／ —（topic）} | {module: MODULE_DIR（空なら「未確定」） / topic: —} | {N} | {SURVEY_FILE} |
>
> 対象ファイル一覧: {TARGET_FILES を対象ごとに列挙}
> {ファイル名一致で複数候補が絞り込まれず全件採用した場合のみ、該当モジュールごとに1行}⚠️ モジュール `{module名}` は同名ファイルが複数見つかったため候補全件を対象にしています。絞り込む場合は「対象を絞り込む」を選択してください。
> {`spec-dir` が duplicates を返したモジュールごとに1行}⚠️ モジュール `{module名}` と同じ範囲の既存の仕様が複数あります。`{MODULE_KEBAB}` を使います（ほかに: {duplicates}）。
> 想定トークン規模: 目安 {対象ファイルの合計行数から概算}
>
> このまま調査を実行しますか？ [はい / いいえ / 対象を絞り込む]

**「解決方法」列の値:** `CATALOG_AVAILABLE = true` で解決した行は `module-catalog`、`CATALOG_AVAILABLE = false`
かつ Step 1 で `DIR_MATCHED[module] = true` の行は `ディレクトリ一致`、`DIR_MATCHED[module] = false` から
ファイル名一致で解決した行は `ファイル名一致フォールバック（縮退）`、topic スコープの行は `—（topic）` を表示する。
`CATALOG_AVAILABLE = true` 時のモジュール解決ロジック自体（Step 2 参照）は、この表示列の追加以外変更しない。

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
MODULE_DIR: {module スコープのときのみ。Step 2 で決めた値（空でもよい）}
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

Read `~/.claude/skills/xddp-rules/code-knowledge-boundary.md`, apply "## 宛先ルーティング表"
  → let `KNOWLEDGE_ROUTING`, and "## 知見の置き場所（MODULE）" → let `KNOWLEDGE_PLACE`.

**SURVEY 節 → knowledge 昇格の対応と昇格条件:**
| SURVEY 節（04_specout-module-template.md 由来） | 昇格条件 | 適用軸 | 宛先ルーティング表の行 |
|---|---|---|---|
| 2.4 定数・列挙値一覧 / 2.5 グローバル変数一覧 | モジュール横断で参照・変更されるもののみ | 軸2 | 共有定数・列挙値 |
| 2.5 グローバル変数の更新元・参照元 | モジュール横断の識別子のみ | 軸2 | 変数データフロー（callgraph） |
| 2.6 制約・前提条件 | 常に | 軸1 | 制約・落とし穴（置き場所は項目ごとに `KNOWLEDGE_PLACE` の `upsert` が決める） |
| 4.2 データ型関連図 / 4.3 データ構造 | 落とし穴・注意点の記述が伴う場合のみ | 軸1 | 構造体依存関係 |
| 2.1 処理フロー / 4.5 モジュール内シーケンス図 | 複数モジュールにまたがるフローのみ | 軸2 | 機能間フロー（シーケンス） |

上記の**昇格条件を満たす節のみ**を選択候補として人に提示し（条件を満たさない節はそもそも候補に出さない）、
「どの節を昇格するか」（`SELECTED_SECTIONS` — 候補からの部分選択。人が今回は省略したい節を外せる）と
ドメイン名（`DOMAIN`）を確定させる。module スコープの survey は単一モジュールが対象のため、軸2に該当する
項目は少ない（「module スコープで昇格対象がゼロ件」は正常。軸2の主な供給源は topic スコープ）。

**`MODULE_FALLBACK`（パスの無い制約の置き場所）の決定**（`MODE = promote` でも同じ。`SURVEY_FILE` から決める）:
- module スコープ: `SURVEY_FILE` の「## 1. モジュール概要」の「ディレクトリ」欄の値を1件の対象として、`KNOWLEDGE_PLACE` に従い
  引用符付きのヒアドキュメントで stdin に渡して Run via Bash（値の `\` は `\\`、`"` は `\"` にして JSON に書く）:
  ```
  PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/knowledge_place.py place --repo-root {REPO_PATH} --workspace-root {WORKSPACE_ROOT} <<'EOF'
  [{"id": "survey-dir", "targets": ["{「ディレクトリ」欄の値}"]}]
  EOF
  ```
  返った `module` を `MODULE_FALLBACK` にする。ただし、値が `.`・`./`・空・プレースホルダーのまま・読めない場合、
  または `module` が `_root` の場合は `_general` にする。
  終了コードが 0 以外なら `MODULE_FALLBACK` を `_general` にし、その旨を Step 9 で示す。
- topic スコープ: `_general`（§2.6 の項目は、対象のパスがあればその置き場所、無ければ `_general`）。

**Agent tool** `subagent_type=xddp-survey-promote-agent`:
```
REPO_NAME: {REPO_NAME}
REPO_PATH: {REPO_PATH}
WORKSPACE_ROOT: {WORKSPACE_ROOT}
SURVEY_FILE: {SURVEY_FILE}
SELECTED_SECTIONS: {SELECTED_SECTIONS}
DOMAIN: {DOMAIN}
MODULE_FALLBACK: {MODULE_FALLBACK}
DOCS: {DOCS}
TODAY: {TODAY}
```

エージェントの返答の「置き場所の確認が要る制約」を Let `PLACE_NOTES`、「前回の昇格で書き、今回は書かなかった制約」を
Let `NOT_WRITTEN_NOTES` とし、Step 9 で示す。

**AI_INDEX.md の作り直し:** Run via Bash（調べた repo だけでなく全 repo を渡す）:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/ai_index.py build --docs {DOCS} --repos-keys {REPOS_KEYS をカンマ区切り} {IS_MULTI の場合のみ}--is-multi`
失敗したら Let `AI_INDEX_ERROR` = stderr の1行目（昇格は取り消さない）。

完了後 Step 9 へ進む。`specs/` は変更しない。

---

### Step 6（(c) を選んだ場合）: 作業場所への仕様の生成・衝突判定

Let `WORK_SPECS` = `{WORKSPACE_ROOT}/{XDDP_DIR}/survey/{REPO_NAME}/specs-work/latest-specs/{REPO_NAME}`（作業場所）。
承認（Step 8）の前は latest-specs・`{DOCS}` に一切書かない。生成・レビューは作業場所で行う。

**対象モジュールごとの `SPEC_DIR`・`MODULE_DIR`（`MODE = module`・`MODE = promote` のどちらでも同じ）:**
`SURVEY_FILE` の「## 1. モジュール概要」の「モジュール名」欄と「ディレクトリ」欄を読む（Step 5 の `MODULE_FALLBACK` と同じ読み方）。
「ディレクトリ」欄の値は、末尾の `/` を除き、`.` はそのまま `.` にする。空・プレースホルダーのまま、または表の直後に
`> モジュールの範囲: 未確定（複数のファイルを採用）` の注記があれば空にする。これを `MODULE_DIR` とする。Run via Bash:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-11-specs/scripts/spec_version_delta.py spec-dir --latest-specs {WORKSPACE_ROOT}/{XDDP_DIR}/latest-specs/{REPO_NAME} --docs-specs {DOCS}/{REPO_NAME}/specs --name {「モジュール名」欄の値} --module-dir "{MODULE_DIR}"`
→ stdout の JSON の `spec_dir` を `SPEC_DIR` とする（promote の経路は Step 1・2 を飛ばすが、SURVEY 成果物から同じ値を得る）。

**冒頭で対象の全モジュールの衝突判定をまとめて実行する。** モジュールごとに
`{WORKSPACE_ROOT}/{XDDP_DIR}/latest-specs/{REPO_NAME}/{SPEC_DIR}/spec.md` と `{DOCS}/{REPO_NAME}/specs/{SPEC_DIR}/spec.md` の
frontmatter `source` を確認する（どちらか一方が `spo` なら `spo` として扱う）。

| 既存 `source` | 動作 |
|---|---|
| なし（どちらにもファイルが無い） | 新規生成 |
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

「スキップ」を選んだモジュールは以降のループから除外する（既存の仕様は一切変更しない）。

対象モジュールごとに、mod-agent の起動の前に:
1. `{WORK_SPECS}/{SPEC_DIR}/` があれば消す（前の回の残りを使わない）。
2. 既存の仕様があれば `{WORK_SPECS}/{SPEC_DIR}/` へ写す（latest-specs の `{SPEC_DIR}/` を優先、無ければ `{DOCS}/{REPO_NAME}/specs/{SPEC_DIR}/`。
   再生成の PATCH の規則が働くように）。
3. Run via Bash → stdout の JSON の `sequences` を `SEQUENCES` とする:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-11-specs/scripts/spec_version_delta.py seq-names --spo {SURVEY_FILE} --kind module`

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
MODULE_SCOPE: [{SPEC_DIR}]
MODULE_KEBAB: {SPEC_DIR}
MODULE_DIR: {MODULE_DIR}
SEQUENCES: {SEQUENCES}
SPECS_REPO_DIR: {WORK_SPECS}
OUTPUT_FILE: {WORKSPACE_ROOT}/{XDDP_DIR}/survey/{REPO_NAME}/module/{MODULE_KEBAB}/PENDING-MOD-SURVEY-{TODAY}.md
```

---

### Step 6.5（(c) のみ）: architecture.md への追記（作業場所で）

Let `WORK_ARCH` = `{WORK_SPECS}/overview/architecture.md`。追記の前に、`WORK_ARCH` を毎回写し直す
（`{DOCS}/{REPO_NAME}/specs/overview/architecture.md` があればそれを写す。無ければ
`~/.claude/skills/xddp-11-specs/templates/11_overview-architecture-template.md` から新規作成する。却下した前回の追記を残さない）。
写し直した直後の内容を `ARCH_BASE` として覚えておく（Step 8 の比較に使う）。
**テンプレートを正本とし、セクション構成・テーブル列構成を再定義してはならない。**

`WORK_ARCH` に、Step 6 で生成・更新したモジュールについて追記だけを行う:
- 「## 3. モジュール一覧」テーブルに今回対象モジュールの行が無ければ追記する（既に存在する場合はスキップ）。
- 「## 2. アーキテクチャ図（コンポーネント図）」に今回モジュールのノードが無い場合はノードのみ追加する。
- **他モジュールのエントリの更新・削除・並べ替え、図の全体再生成は禁止。**

---

### Step 7（(c) のみ）: レビュー ＋ インライン自動修正（最大1サイクル）

Step 6 で生成・更新した `{WORK_SPECS}/{SPEC_DIR}/` 配下の全ファイルと、Step 6.5 の `WORK_ARCH` を `TARGET_FILES` とする。

Read `~/.claude/skills/xddp-common/procedures/invoke-reviewer.md`, apply "## Invoke Reviewer" with:
```
DOCUMENT_TYPE: SPEC
TARGET_FILES: {上記ファイル一覧}
REFERENCE_FILES: [{対象モジュールの SURVEY_FILE を列挙}]
REVIEW_ROUND: 1
OUTPUT_FILE: {WORKSPACE_ROOT}/{XDDP_DIR}/survey/{REPO_NAME}/review/SPEC-SURVEY-{TODAY}.md
```

Read `{OUTPUT_FILE}`。🟡（自動修正対象カテゴリ: Mermaid 図の構文エラー・フロントマター必須キーの漏れ〔`LINT_RESULTS.frontmatter.missing_keys` に挙がったキー〕・
変更履歴エントリの形式不備・気づきメモセクションの有無（フロントマター `has_insights` と節の有無の不一致。`has_insights` の値は変えず、節を足す・消す。値が期待値と違う〔`insights_expected_mismatch`〕ときだけ値を期待値に直す））があれば、スキル自身が直接該当ファイルを編集して
修正する（最大1回。工程11 Step REV と同一方式）。修正後、`REVIEW_ROUND: 2` で `apply "## Invoke Reviewer"`
を再実行し `{OUTPUT_FILE}` を上書きする。それ以外の指摘（🔴。SPO 内容との矛盾等）は本スキルでは自動修正せず、
Step 8 の人レビューゲートに委ねる。

**`REVIEW_MAX_ROUNDS.SPEC` / `FIX_STRATEGY.SPEC` は使用しない**（修正サイクルは常に最大1回固定）。

---

### Step 8（(c) のみ）: 人レビューゲート・latest-specs と DOCS への昇格

人に `{OUTPUT_FILE}` と作業場所の生成物の確認を促し、承認か却下かを尋ねる。承認前は latest-specs・`{DOCS}` に一切書き込まない。

**承認された場合:**

**① spec コピー（今回生成・更新したモジュールのみ）:**
```
For each {SPEC_DIR} in （Step 6 で生成・更新したモジュール一覧）:
  Copy {WORK_SPECS}/{SPEC_DIR}/ → {WORKSPACE_ROOT}/{XDDP_DIR}/latest-specs/{REPO_NAME}/{SPEC_DIR}/
  Copy {WORK_SPECS}/{SPEC_DIR}/ → {DOCS}/{REPO_NAME}/specs/{SPEC_DIR}/
```
このコピーでは `overview/` および他モジュールには一切触れない（`architecture.md` は②で別途行う）。

**② architecture.md:**
- `{DOCS}/{REPO_NAME}/specs/overview/architecture.md` へ `WORK_ARCH` を写す（`overview/` が無ければ作る）。
- `{WORKSPACE_ROOT}/{XDDP_DIR}/latest-specs/{REPO_NAME}/overview/architecture.md` は:
  - 無いか、内容が `ARCH_BASE` と同じ → `WORK_ARCH` を写す
  - 内容が `ARCH_BASE` と違う（まだ昇格していない CR の変更がある）→ そのファイルに Step 6.5 と同じ追記だけを行う
    （他の記述は変えない）

**承認されなかった場合（却下）:** latest-specs・`{DOCS}` に何も書かない（①〜③を行わない）。

**承認・却下のどちらでも:** 最後に `{WORK_SPECS}/{SPEC_DIR}/`（対象モジュールすべて）と `WORK_ARCH` を消す
（SURVEY 成果物は残るので、`/xddp-survey {REPO_NAME} promote` の Step 0.5 → Step 4.5 → Step 6 の経路で作り直せる）。

**③ AI_INDEX.md の作り直し（承認された場合のみ）:**
- `{DOCS}` ディレクトリが存在しない場合: 作り直しをスキップし、次の警告を表示する（`{DOCS}` の
  初回作成は `xddp-01-init` が担うため survey は作成しない）:
  > ⚠️ `{DOCS}` が存在しないため AI_INDEX.md の更新をスキップしました。`/xddp-01-init` の実行後に
  > `/xddp-survey {REPO_NAME} promote` を再実行してください。
- それ以外: Run via Bash（調べた repo だけでなく全 repo を渡す）:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/ai_index.py build --docs {DOCS} --repos-keys {REPOS_KEYS をカンマ区切り} {IS_MULTI の場合のみ}--is-multi`
  失敗したら Let `AI_INDEX_ERROR` = stderr の1行目（①・② は取り消さない）。

Step 9 のサマリーに承認・却下と、①〜③それぞれの結果（実施／スキップ／新規作成）を明示する。

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
> {(b) の場合: **置き場所の確認が要る制約:** {PLACE_NOTES と、MODULE_FALLBACK の決定で置き場所のスクリプトが失敗した旨, or "なし"}}
> {(b) の場合: **前回の昇格で書き、今回は書かなかった制約（不要なら `constraints.md` から直接消してください）:** {NOT_WRITTEN_NOTES, or "なし"}}
> {AI_INDEX_ERROR がある場合: ⚠️ AI_INDEX.md の作り直しに失敗しました（{AI_INDEX_ERROR}）。昇格は済んでいます。`ai_index.py build` を再実行してください}
>
> **`{XDDP_DIR}/survey/` の扱い:** SURVEY 成果物は人が任意に削除してください。ツール側では自動削除しません
> （CR フォルダと異なりクローズ契機を持たないため。`xddp-close` は `survey/` を参照しません）。VCS 管理の
> 要否はプロジェクト判断です。
>
> **次のステップ:**
> - 追加調査する場合: `/xddp-survey {REPO_NAME} module {module}` または `topic {seed}` を再実行してください
> - 保留中の SURVEY 成果物を後から昇格する場合: `/xddp-survey {REPO_NAME} promote` を実行してください

progress.md は CR 非依存のため更新しない。

---
> **保守メモ:** このファイルを変更した場合は、`README.md`（スキル一覧テーブル）、`CLAUDE.md`
> （ステップ番号体系テーブル）も合わせて更新すること。
