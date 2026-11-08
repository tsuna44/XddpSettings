---
name: xddp-11-specs
description: XDDP フェーズ6: 最新仕様書（{XDDP_DIR}/latest-specs/）を生成・更新してCRを完了する。「最新仕様書を作って」「latest-specsを更新して」「CRを完了して」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Step 11 (process step 11) — Generate/Update Latest Specifications**.

> This step synthesises SPO (current state) + CHD (changes) into latest-specs/ (current truth).
> New structure follows Kruchten 4+1 view model: Use Case / Logical / Development / Process / Physical.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp-common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
DOCS_DIR, DOCS, REPOS_MAP, REPOS_KEYS, IS_MULTI.)

---

## Step 0: Pre-flight（事前準備）

1. Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

2. Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Resolve HAS_CROSS" with:
     IS_MULTI: {IS_MULTI}, ARTIFACT_PATH: {CR_PATH}/04_specout/cross/SPO-{CR}-cross.md
   → let `HAS_CROSS`.
   ※ HAS_CROSS 判定は SPO 存在ベース（旧 CHD 存在ベースから変更）。specout まで実施していれば cross/ ビューを生成する方針。
   （他工程が「直前工程の cross 成果物」を見るのに対し、本工程は最新仕様書生成の起点となる
   specout の cross SPO を基準にする。design/code が未完了でも specout 済みなら cross ビューを
   生成したいため、あえて直前工程＝design の DSN ではなく specout の SPO を見る）

3. **AFFECTED_REPOS の確定（Step 0 で完全確定）:**
   Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Resolve Affected Repos" with:
     REPOS_KEYS: {REPOS_KEYS}, IS_MULTI: {IS_MULTI}, CR_PATH: {CR_PATH}, FILTER_BY_SPO: true,
     HAS_CROSS: {HAS_CROSS}, CR: {CR}
   → let `AFFECTED_REPOS`.

4. **latest-specs をそろえ、基準を記録する（変更の記録の起点）:**
   Let `SPEC_AREAS` = `AFFECTED_REPOS` の各 repo、`HAS_CROSS` が true なら `cross`、および `system` をカンマ区切りにしたもの。
   Run via Bash（この順に）:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-11-specs/scripts/spec_changes.py seed --xddp-dir {WORKSPACE_ROOT}/{XDDP_DIR} --cr {CR} --docs {DOCS} --areas {SPEC_AREAS}`
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-11-specs/scripts/spec_changes.py snapshot --xddp-dir {WORKSPACE_ROOT}/{XDDP_DIR} --cr {CR}`
   - `seed` は `{DOCS}` の写しにあって latest-specs に無い既存の仕様を latest-specs へ写す（以降の Step は、
     `{DOCS}` にだけあった仕様も latest-specs の既存の仕様として更新し、版・変更履歴を引き継ぐ）。
     今の CR が削除したもの・進行中の他の CR が削除したものは写さない。
   - `snapshot` は `{CR_PATH}/.latest-specs-baseline.json` が無いときだけ、今の latest-specs を基準として書く
     （分割実行・再実行では最初の基準を使う）。Step DONE の `record` がこの基準と比べて変更を記録する。
   - どちらかの終了コードが0以外なら stderr を表示して停止する。

5. **工程11 の入力の一覧（`SPEC_SOURCES`）:**
   For each `{repo}` in `AFFECTED_REPOS`:
   - Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Discover CHD Files" with
     `CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}` → let `CHD_CONTENT_FILES_BY_REPO[{repo}]`.
   - Let `SPEC_SOURCES_FILE[{repo}]` = `{CR_PATH}/04_specout/{repo}/work/spec-sources.json`。Run via Bash
     （`CHD_CONTENT_FILES_BY_REPO[{repo}]` が空なら `--chd` を付けない）:
     `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-11-specs/scripts/spec_version_delta.py sources --spo-dir {CR_PATH}/04_specout/{repo} --cr {CR} --latest-specs {WORKSPACE_ROOT}/{XDDP_DIR}/latest-specs/{repo} --docs-specs {DOCS}/{repo}/specs --repo {repo} --repo-path {REPOS_MAP[repo]} --exclude "{EXCLUDE_PATTERNS}" --include-ext "{INCLUDE_EXTENSIONS}" --xddp-dir {WORKSPACE_ROOT}/{XDDP_DIR} --chd {CHD_CONTENT_FILES_BY_REPO[{repo}] を空白区切りで} --out-dir {CR_PATH}/04_specout/{repo}/work/spec-sources --out {SPEC_SOURCES_FILE[{repo}]}`
   - 終了コードが0以外なら stderr を表示して停止する。0 なら `SPEC_SOURCES_FILE[{repo}]` を Read し `SPEC_SOURCES[{repo}]` とする。
   - `SPEC_SOURCES[{repo}]` の項目: `modules`（SPO のあるモジュール。`name`・`spec_dir`〔latest-specs のディレクトリ名〕・
     `module_dir`・`source_files`〔どの配置でも分割パスと同じ形の資料1つ〕・`sequences`〔§4.5 の小見出しとファイル名〕・
     `existing_spec`）、`overview_sequences`、`missing_docs`、`chd_only`・`chd_unmatched`（SPO の無い CHD の変更）、
     `missing_module_dirs`・`protected_by_concurrent_cr`（廃止候補）、`conflicts`。
   - モジュール資料の配置（統合パス・分割パス・索引）を Step 内で読み分けない。latest-specs のディレクトリ名・
     シーケンス図のファイル名も自分で作らず、この一覧の値を使う。

6. **分割実行継続マーカーの確認:**
   `{CR_PATH}/progress.md` を Read し、「## 工程11 分割実行メモ」セクションが存在するかを確認する。
   存在する場合:
   - `完了済みステップ:` に含まれるステップ（UC・OV・CROSS 等）はスキップする
   - `未処理リポジトリ:` が存在する場合は AFFECTED_REPOS をその値に限定する（選択肢 A の継続）
   - `未処理モジュール:` が存在する場合は当該 repo の MODULE_SCOPE をその値（`spec_dir` の一覧）に限定する（選択肢 B の継続）
   - `未処理UR:` フィールドが存在する場合は UC をスキップせず、`未処理UR:` の UR のみを対象に Step UC を再実行する
   存在しない場合は通常の全処理モードで実行する。

7. Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
     CR_PATH: {CR_PATH}, STEP_NUM: 11, STATE: 🔄 進行中, DETAIL_STEP: `Step 0: 事前準備中`

Read `~/.claude/skills/xddp-common/procedures/snapshot-phase-baseline.md`, apply "## Snapshot Phase Baseline" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 11

---

## Step UC: Synthesize Use Cases (system/use-cases/)

**スキップ条件（以下のいずれかに該当する場合はこのステップをスキップ）:**
- 分割実行継続マーカーの `完了済みステップ:` に `UC` が含まれる（かつ `処理済みUR:` フィールドが存在しない）
- CRS に UR（ユーザー要求）が存在しない（技術的変更のみ）

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 11, STATE: 🔄 進行中, DETAIL_STEP: `Step UC: ユースケース合成中`

Read `{CR_PATH}/03_change-requirements/CRS-{CR}.md` → CRS §2 UR list. Let `UR_COUNT` = UR 総数。

**コンテキスト圧迫チェック（Step UC 開始前・オーケストレーター側で実施）:**
`UR_COUNT` が 20 を超える場合（かつ分割実行継続マーカーがない場合）は、以下を提示して指示を求める:
- **A: UR 単位で分割実行（推奨）** — 今回は指定 UR のみ処理し、残りは次回実行で処理する
- **B: 一括実行** — 全 UR を一括処理する（コンテキスト圧迫のリスクあり）
選択結果に応じて処理対象 UR リストを確定する（`RESUME_UR_LIST` に反映。値は CRS §2 の UR の ID〔例 `{CR}-UR-001`〕）。

**Agent tool** `subagent_type=xddp-specs-uc-agent`:
```
CR_NUMBER: {CR}
CR_PATH: {CR_PATH}
XDDP_DIR: {XDDP_DIR}
DOCS: {DOCS}
AFFECTED_REPOS: {AFFECTED_REPOS}
HAS_CROSS: {HAS_CROSS}
TODAY: {TODAY}
RESUME_UR_LIST: {上記チェックで確定した処理対象 UR の ID、分割実行継続マーカーの 未処理UR: の ID、または空（=全UR）}
SPEC_SOURCES_FILES: {AFFECTED_REPOS の各 repo の SPEC_SOURCES_FILE[{repo}]}
OUTPUT_FILE: {CR_PATH}/pending-items/PENDING-UC-{CR}.md
```

Wait for completion. エージェントは廃止候補・命名衝突・related-modules 照合不能等の人判断が必要な項目を
内部で対話せず OUTPUT_FILE に**保留事項リストとして書き込む**（既存エージェントの確立されたファイル経由ハンドオフパターンに倣う。
`xddp-verifier-agent.md` の `OUTPUT_FILE` 契約と `xddp-08-verify/SKILL.md` の Read-back 処理と同じ方式）。
オーケストレーターは Agent tool 完了後に `{CR_PATH}/pending-items/PENDING-UC-{CR}.md` を
Read し、内容を Let `UC_PENDING` に保持する。保留事項は Step GATE で人に提示する。
廃止候補の削除実行は Step GATE 後にオーケストレーター側がファイル操作として直接行う（エージェントを再呼び出ししない）。

---

## Step OV: Generate/Update overview (per repo)

**スキップ条件:** 分割実行継続マーカーの `完了済みステップ:` に `OV` が含まれる場合はスキップ。

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 11, STATE: 🔄 進行中, DETAIL_STEP: `Step OV: overview 生成中`

For each `{repo}` in `AFFECTED_REPOS`:

Read `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md`.
Let `SPECOUT_MODULES` = `SPEC_SOURCES[{repo}].modules` の `spec_dir` の一覧。

**`overview/architecture.md` の生成/更新（マージ方式）:**
SPO サマリーの `## 2. 全体アーキテクチャ図` の内容を使用する（見出しの名前で探す。`## 2.A.` …のモジュール資料は含めない）。
既存 `{XDDP_DIR}/latest-specs/{repo}/overview/architecture.md` が存在する場合:
- **機械的先決基準（更新判断）:** SPO の Mermaid ブロックのノード数/エッジ数が既存ファイルと異なる、
  またはテキストセクションの行数が 20% 以上変化している → 即時「更新あり」と判定
- 機械的基準に該当しない場合のみ AI セマンティック比較を実施
- 更新時の方針:
  - SPECOUT_MODULES に含まれるモジュールの情報は最新 SPO の内容で更新する
  - SPECOUT_MODULES に含まれない（今回 specout 未実施）モジュールの情報は保持する
  - 削除されたモジュール（CHD に削除記述がある場合）は architecture.md から削除する
  ※ 判定は SPECOUT_MODULES（`spec_dir` の一覧）との機械的照合。AI のセマンティック判断に依存しない。
- **モジュール名ドリフト検出（ノンブロッキング）:**
  SPECOUT_MODULES に新規名があり既存エントリに類似名がある場合（例: 新規 `authentication` と既存 `auth`）は
  「リネーム候補: `auth` → `authentication`」として気づきメモに記録し人に確認を求める（処理は継続）。
- **⚠️ サイレント廃止リスク（実装コメント）:**
  CHD に削除記述がなく今回 specout 対象外のモジュールは廃止候補として検出できない。
  複数 CR にわたる knowledge base の陳腐化を防ぐため、定期的な「棚卸し CR」（全モジュール specout の実施）を推奨する。
  この制約は data-model.md / crud.md にも同様に適用される。
- **⚠️ 並行 CR による同時更新リスク（実装コメント）:**
  architecture.md / data-model.md / crud.md は複数 CR が同一リポジトリを対象とする場合に同時更新リスクがある共有ファイルである。
  同一リポジトリに並行 CR が存在する場合は xddp-11-specs を逐次実行することを推奨する。
  将来的なロック機構は improvement-backlog に記録する（今回スコープ外）。
存在しない場合: `~/.claude/skills/xddp-11-specs/templates/11_overview-architecture-template.md` から初期生成する。

**バージョニング（architecture.md）:**
| 条件 | バージョン |
|---|---|
| 新規モジュールのエントリを追加 | MINOR |
| 既存モジュール説明・依存関係を更新（内容変更あり） | PATCH |
SPO なし CHD あり の PATCH 更新では `last-verified-cr:` を更新しない。

**`overview/sequences/{feature}-seq.md` の生成/更新:**
SPO サマリーの「モジュール間シーケンス図」セクションのサブセクションごとに、`SPEC_SOURCES[{repo}].overview_sequences` の
`file`（`heading` の小見出しから作ったファイル名。見出しなし・単一の場合は `main-seq.md`）に書く。
テンプレート: `~/.claude/skills/xddp-11-specs/templates/11_overview-sequence-template.md`

**廃止シーケンスファイル処理（Step OV）:**
`{XDDP_DIR}/latest-specs/{repo}/overview/sequences/` 内の既存 `{feature}-seq.md` を列挙し、
今回の `overview_sequences` の `file` に対応しないファイルを「廃止候補」として検出する（ファイル名は Unicode の NFC にそろえて比べる）。
並行 CR 保護: フロントマター `last-updated-cr:` が現在の CR と異なる場合、`{XDDP_DIR}/{last-updated-cr}/progress.md` を確認する。
  - ファイルが存在し、かつ「## CR クローズ」「## CR 中止」のどちらのセクションも含まない（進行中）→ 当該他 CR が進行中とみなし
    廃止候補から除外する（「他 CR（{last-updated-cr}）進行中 — スキップ」として提示）。
  - ファイルが存在しない、または「## CR クローズ」か「## CR 中止」のセクションを含む（終わった CR）→ 保護対象外とし、
    通常どおり廃止候補として検出する。
廃止候補が存在する場合はユーザーに提示して削除確認を求める。
SPO 見出し名変更（内容が同一だが名称が変わった場合）も廃止候補として検出される。
コンテンツの意味的同一性が高い場合はコピー（旧名→新名）を提案する。

**`overview/dfd.md` の生成/更新:**
SPO サマリーの「データフロー図（DFD）」（`## 4.2` または見出し名一致）セクションを参照する。
「副作用なし（省略）」または「対象外」の場合はスキップする。
テンプレート: `~/.claude/skills/xddp-11-specs/templates/11_overview-dfd-template.md`

**`overview/data-model.md` の生成/更新（マージ方式）:**
SPO サマリーの「データモデル（エンティティ関連図・データ構造定義）」セクション（`## 4.3` または見出し名一致）を参照する。
「対象外」記載またはセクションが存在しない場合は生成スキップ（既存ファイルがあれば保持）。
既存ファイルが存在する場合は architecture.md と同様のマージ方式で更新する。
**エンティティ名正規化ルール:**
- 既存 `data-model.md` に同名候補がある場合: 既存名称を正規名として採用する
- 既存 `data-model.md` に類似名がある場合（例: `User` vs `UserEntity`）:
  AI がセマンティック類似度で同一対象と判断できる場合は既存名を優先する
  判断困難な場合は「`UserEntity`（既存: `User`）統合候補」として気づきメモに記録しノンブロッキングで継続する
- 初回生成の場合: SPO の表記をそのまま採用する
テンプレート: `~/.claude/skills/xddp-11-specs/templates/11_overview-data-model-template.md`
`source:` フロントマターキー: テンプレートの既定 `ai-inferred` のままにする（AI のエンティティ名の正規化・マージを含むため。SPO で確かめた人が `spo` に変える）。

**`overview/crud.md` の生成/更新（マージ方式）:**
SPO サマリーの「データアクセスマトリクス（CRUDマトリクス・Read/Writeマトリクス）」セクション（`## 4.4` または見出し名一致）を参照する。
「対象外」記載またはセクションが存在しない場合は生成スキップ（既存ファイルがあれば保持）。
マージ方式: 処理名（行）をキーに照合し、今回の SPO §4.4 に記述されているものは更新、非記載は保持。
テンプレート: `~/.claude/skills/xddp-11-specs/templates/11_overview-crud-template.md`

**`overview/deployment.md`:**
工程11 は生成・更新しない（SPO に材料の節が無い。人が書くビュー）。既存のファイルは保持する（`/xddp-close` で `{DOCS}` へ昇格する）。
人が新しく作るときのテンプレート: `~/.claude/skills/xddp-11-specs/templates/11_overview-deployment-template.md`

※ セクション参照は見出し名ベースで行う（セクション番号は SPO テンプレート種別により異なるため）。

---

## Step MOD: Generate/Update module specs (per repo, per module)

**スキップ条件:** 分割実行継続マーカーの `完了済みステップ:` に `MOD` が含まれる場合はスキップ。

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 11, STATE: 🔄 進行中, DETAIL_STEP: `Step MOD: モジュール仕様生成中`

**コンテキスト圧迫チェック（Step MOD 開始前）:**
AFFECTED_REPOS 内の全モジュール数（各 repo の `SPEC_SOURCES[{repo}]` の `modules` と `chd_only` の件数）の合計が 10 を超える場合（かつ分割実行継続マーカーがない場合）は、
以下を提示して指示を求める:
- **A: リポジトリ単位で分割実行（推奨）**
- **B: モジュール単位で分割実行**
- **C: 一括実行（遅い場合あり）**

For each `{repo}` in `AFFECTED_REPOS`（またはユーザーが選択したサブセット）:

**機械的先決処理1: ベースライン退避（オーケストレータ・Bash）:**
`MODULE_SCOPE` が空でない場合: `{XDDP_DIR}/latest-specs/{repo}/{module}/`（`MODULE_SCOPE` の各モジュール）を
`{CR_PATH}/pending-items/specs-baseline/{repo}/{module}/` へコピーする。
`MODULE_SCOPE` が空の場合: `{XDDP_DIR}/latest-specs/{repo}/` 全体を
`{CR_PATH}/pending-items/specs-baseline/{repo}/` へコピーする。
Let `BASELINE_OK` = コピー成功可否。失敗した場合（権限・容量等）は `BASELINE_OK: false` とし、
`PENDING-MOD-{CR}-{repo}.md` に「ベースライン退避失敗 — 事後バージョン検証スキップ」と記録する
（後述の compare 実行・後始末はスキップする）。

**機械的先決処理2: precheck 実行（オーケストレータ・Bash）:**
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-11-specs/scripts/spec_version_delta.py precheck --existing {XDDP_DIR}/latest-specs/{repo} --sources {SPEC_SOURCES_FILE[{repo}]} --line-change-threshold-pct 20 --out {CR_PATH}/pending-items/.precheck-{repo}.json`
終了コード0の場合、JSON の `force_update_files`（`{module}/{file}` 形式の相対パスのリスト）を
改行区切りの文字列にしたものを `FORCE_UPDATE_FILES` とする。
終了コードが0以外の場合は `FORCE_UPDATE_FILES` を空とし、当該 repo は現行どおり全件 AI セマンティック判断に
委ねる（フェイルセーフ。人には報告のみ行い停止しない）。

**Agent tool** `subagent_type=xddp-specs-mod-agent`:
```
CR_NUMBER: {CR}
CR_PATH: {CR_PATH}
XDDP_DIR: {XDDP_DIR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
DOCS: {DOCS}
TODAY: {TODAY}
MODULE_SCOPE: {ユーザー選択モジュール（spec_dir）の一覧、なければ空（= 全モジュール）}
SPEC_SOURCES_FILE: {SPEC_SOURCES_FILE[{repo}]}
SPECS_REPO_DIR: {WORKSPACE_ROOT}/{XDDP_DIR}/latest-specs/{repo}
OUTPUT_FILE: {CR_PATH}/pending-items/PENDING-MOD-{CR}-{repo}.md
FORCE_UPDATE_FILES: {上記 precheck 結果から得た改行区切りの文字列}
```

Wait for completion. エージェントは廃止候補・命名衝突・SPO照合不能等の人判断が必要な項目を
内部で対話せず OUTPUT_FILE に**保留事項リストとして書き込む**（Step UC と同じファイル経由ハンドオフ方式）。
オーケストレーターは Agent tool 完了後に `{CR_PATH}/pending-items/PENDING-MOD-{CR}-{repo}.md` を Read し、
内容を Let `MOD_PENDING[{repo}]` に保持する。
保留事項は Step GATE で人に提示し、削除・リネーム実行はオーケストレーター側がファイル操作として直接行う。

**機械的先決処理3: compare 実行（バージョン下限の事後検証・自動書き換え。`BASELINE_OK` が true の場合のみ）:**
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-11-specs/scripts/spec_version_delta.py compare --baseline {CR_PATH}/pending-items/specs-baseline/{repo} --current {XDDP_DIR}/latest-specs/{repo} --modules {SPEC_SOURCES[{repo}].modules の spec_dir（MODULE_SCOPE があればその範囲）をカンマ区切りで} --out {CR_PATH}/pending-items/.compare-{repo}.json`
（「SPO なし・CHD あり」のモジュール〔`chd_only`〕は `--modules` に入れない。PATCH 固定のまま扱う）
終了コード0の場合、JSON の `rewritten_files`（自動書き換えされたファイル一覧）を
`PENDING-MOD-{CR}-{repo}.md` に「## バージョン下限の自動書き換え」セクションとして追記する
（空の場合は「なし」と記載。監査のため人が事後に確認できるようにする）。
終了コードが0以外の場合は事後検証をスキップした旨を同ファイルに記録する。

**機械的先決処理4: ベースラインの後始末:**
機械的先決処理3が正常完了した場合は `{CR_PATH}/pending-items/specs-baseline/{repo}/` を削除する。
`BASELINE_OK` が false、または機械的先決処理3が失敗・スキップされた場合は診断用に残す。

---

## Step CROSS: Generate/Update cross specs (IS_MULTI のみ)

**スキップ条件:** IS_MULTI でない、またはHAS_CROSS でない、または分割実行継続マーカーに `CROSS` が含まれる場合はスキップ。

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 11, STATE: 🔄 進行中, DETAIL_STEP: `Step CROSS: クロス仕様生成中`

Read `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md`.

**`cross/sequences/{flow}-seq.md` の生成/更新:**
ファイル名は次の出力 JSON の `sequences` の `file` を使う（小見出し `### 3.n {レベル名}レベルのシーケンス図` のレベル名から作る。
見出しなし・単一の場合は `main-seq.md`）:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-11-specs/scripts/spec_version_delta.py seq-names --spo {CR_PATH}/04_specout/cross/SPO-{CR}-cross.md --kind cross`
→ `CROSS_SEQUENCES`。
テンプレート: `~/.claude/skills/xddp-11-specs/templates/11_cross-sequence-template.md`

※ cross SPO §2（構造図）は AFFECTED_REPOS 各リポジトリの `overview/architecture.md` への補完情報として使用する。
  cross/ 配下に独立した architecture ファイルは作成しない。

**CHD cross インタフェース変更（`{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` が存在する場合）:**
「インタフェース変更サマリ」テーブルを Read する。

For each interface in the table:

`{interface-kebab}` の命名ルール:
- HTTP API: `{method}-{path-kebab}`（例: `POST /api/jobs` → `post-api-jobs`）
- イベント・キュー: `{event-name-kebab}`（例: `job.completed` → `job-completed`）
- 関数API: `{functionName}` のキャメルケース・アンダースコアをケバブ変換
- CANバスメッセージ: `can-{msg-name-kebab}` プレフィックス形式
- シリアルコマンド（UART/SPI/I2C等）: `cmd-{command-name-kebab}` プレフィックス形式
- IPC・共有メモリ: `ipc-{resource-name-kebab}` プレフィックス形式
- その他: CHD インタフェース名の英訳ケバブ形式。翻訳困難な場合は `if-{連番}` フォールバックを使用し progress.md に対応表を記録する

**`cross/interfaces/{interface-kebab}/spec.md` の生成/更新:**
フロントマター `provider`・`affected-repos` の材料: cross SPO §4「共有インタフェース一覧」の提供リポジトリ・消費リポジトリの列。
SPO に無い新しいインタフェースは cross CHD の「実装依存関係」の表から取る。どちらにも無ければ空にし、
`{CR_PATH}/pending-items/PENDING-CROSS-{CR}.md` に「provider・affected-repos の材料なし: {interface-kebab}」と記録する（Step GATE で人に示す）。
バージョン判定: breaking 変更（後退互換性を破壊）→ MAJOR、新パラメータ・フィールド追加（後退互換性あり）→ MINOR、ドキュメントのみの修正 → PATCH
テンプレート: `~/.claude/skills/xddp-11-specs/templates/11_cross-interface-spec-template.md`
フロントマター `breaking:`: 今回の CHD の「インタフェース変更サマリ」にあるインタフェースは、その行の `breaking` の値
（`true`／`false`）を書く。サマリに無いインタフェースの仕様は `breaking:` を変えない
（`breaking:` は `last-updated-cr` の CR での更新が破壊的変更だったかを表す）。

**`cross/interfaces/{interface-kebab}/schema.md` の生成/更新:**
テンプレート: `~/.claude/skills/xddp-11-specs/templates/11_cross-interface-schema-template.md`

**廃止シーケンスファイル処理（Step CROSS）:**
`{XDDP_DIR}/latest-specs/cross/sequences/` 内の既存 `{flow-kebab}-seq.md` を列挙し、
今回の `CROSS_SEQUENCES` の `file` に対応しないファイルを廃止候補として検出する（ファイル名は NFC にそろえて比べる）。
Step OV の廃止シーケンスファイル処理と同様の並行 CR 保護・廃止確認を実施する。
※ クロス SPO が存在しない場合（HAS_CROSS=false でステップスキップ時）は廃止候補処理も実施しない。

---

## Step REV: AI Review Loop（今 CR で生成/更新したファイルのみ対象）

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 11, STATE: 🔄 進行中, DETAIL_STEP: `Step REV: AIレビュー中`

> ※ DOCUMENT_TYPE は `SPEC` を使用する（旧設計の `CRS` は誤りのため修正）。

生成ファイルをファイル種別単位で以下の4バッチにまとめ、バッチごとに1回のレビュアーエージェント呼び出しを行う:
- バッチ1: モジュール仕様群（`{module}/spec.md` / `state-machine.md` / `structure.md` / `sequences/`）
- バッチ2: overview 群（`overview/architecture.md` / `data-model.md` / `crud.md` / `dfd.md` / `sequences/`）
- バッチ3: クロス群（`cross/interfaces/**/*` / `cross/sequences/`）—— IS_MULTI かつ今回生成した場合のみ
- バッチ4: ユースケース群（`system/use-cases/**/*`）—— Step UC が実行された場合のみ

各バッチにファイルがない場合はそのバッチをスキップする。

**バッチ内ファイル数上限:**
バッチ1（モジュール仕様群）内のファイル総数が 30 を超える場合は、リポジトリ単位でさらに分割して呼び出す。
他バッチも 30 超の場合は同様に分割する。
（上限 30 は 1 ファイル平均 200〜400 行想定の暫定値。将来的に設定キーとして外出し検討。）

`CHD_CONTENT_FILES_BY_REPO[{repo}]` は Step 0 で取得したものを使う。
Let `ALL_CHD_CONTENT_FILES` = 全 repo の `CHD_CONTENT_FILES_BY_REPO` を連結したもの（バッチ3専用に残す）。

Let `BATCH_TARGET_FILES_MAP` = {}（バッチ番号 → TARGET_FILES。Step GATE で参照するため
for-each ループの外側で宣言し、ループの全イテレーションを通じて保持する）
Let `BATCH_REFERENCE_FILES_MAP` = {}（バッチ番号 → REFERENCE_FILES。同上）
Let `BATCH_LAST_ROUND_MAP` = {}（バッチ番号 → 最終レビューラウンド番号。自動修正が
発動せず初回のみで完了した場合は 1、自動修正後に再レビューした場合は 2）
（バッチ番号はスキップされたバッチの番号が欠番になる「バッチ1〜4の固定ラベル」を用いる
——既存の `batch{N}` 表記と同一の採番規則）

For each batch:
  Let `TARGET_FILES` = {当該バッチのファイルパス一覧}（既存どおり）。
  - バッチ3（クロス群）:
    REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {ALL_CHD_CONTENT_FILES を展開}, {CR_PATH}/04_specout/cross/SPO-{CR}-cross.md]
  - バッチ4（ユースケース群）:
    REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {AFFECTED_REPOS の各 repo の {CR_PATH}/04_specout/{repo}/SPO-{CR}.md}]
    ← CHD を除外（xddp-specs-uc-agent は CHD を受け取らない生成契約のため）。SPO サマリーは §3 の照合に使う
  - バッチ1・2（モジュール仕様群／overview群）:
    Let `BATCH_REPOS` = `TARGET_FILES` の各パスを `latest-specs/{repo}/` プレフィックスで走査し
    抽出した repo 名の重複なし集合。
    Let `CHD_SCOPE_FILES` = `BATCH_REPOS` に含まれる repo の `CHD_CONTENT_FILES_BY_REPO` の合併。
    Let `SPO_SCOPE_FILES` = バッチ1 は `BATCH_REPOS` の `SPEC_SOURCES[{repo}].modules` のうち `TARGET_FILES` のモジュール
    （`spec_dir`）の `source_files`、バッチ2 は `BATCH_REPOS` の `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md`。
    REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {CHD_SCOPE_FILES を展開}, {SPO_SCOPE_FILES を展開}]

  Read `~/.claude/skills/xddp-common/procedures/invoke-reviewer.md`, apply "## Invoke Reviewer" with:
    DOCUMENT_TYPE: SPEC, TARGET_FILES: {TARGET_FILES}, REFERENCE_FILES: {上記で決定した値},
    REVIEW_ROUND: 1, OUTPUT_FILE: {CR_PATH}/review/11_specs-batch{N}-review.md,
    PROGRESS_CR_PATH: {CR_PATH}, PROGRESS_STEP_NUM: 11, METRICS_TARGET: batch{N}

  Let `BATCH_TARGET_FILES_MAP[N]` = {TARGET_FILES}
  Let `BATCH_REFERENCE_FILES_MAP[N]` = {上記で決定した REFERENCE_FILES の値}
  Let `BATCH_LAST_ROUND_MAP[N]` = 1（この時点で暫定値。自動修正が発動した場合は下記で 2 に更新）

**AI レビュー指摘への自動修正（バッチごとに最大1サイクル）:**
以下のカテゴリの指摘を自動修正する:
- Mermaid 図の構文エラー（sequenceDiagram・erDiagram・classDiagram・graph TD / flowchart 全タイプ）
- シーケンス図の参加者漏れ・誤記（構文エラー以外の参加者不足）
- SP 差分が誤ったセクションに適用されている（別セクションへの転記で対処）
- フロントマター必須キーの漏れ（`LINT_RESULTS.frontmatter.missing_keys` に挙がったキー。必須キーの定義は `artifact_lint.py`）
- 変更履歴エントリの形式不備（テンプレートの列定義との不一致）
- 気づきメモセクションの有無（フロントマター `has_insights` と節の有無の不一致。`has_insights` の値は変えず、節を足す・消す。値が期待値と違う〔`insights_expected_mismatch`〕ときだけ値を期待値に直す）

上記以外の指摘（機能仕様の内容判断・既存設計との整合性確認が必要なもの等）は Step GATE の人レビューコメントとして提示する。
自動修正後は同バッチに対して再レビューを1回実施し、残指摘があれば Step GATE に渡す。
再レビューは初回と同一の入力で `## Invoke Reviewer` を apply するが、`REVIEW_ROUND: 2`、
`METRICS_TARGET: batch{N}-recheck` とする（初回は `REVIEW_ROUND: 1` / `METRICS_TARGET: batch{N}`）:

  Read `~/.claude/skills/xddp-common/procedures/invoke-reviewer.md`, apply "## Invoke Reviewer" with:
    DOCUMENT_TYPE: SPEC, TARGET_FILES: {TARGET_FILES}, REFERENCE_FILES: {初回と同一の値},
    REVIEW_ROUND: 2, OUTPUT_FILE: {CR_PATH}/review/11_specs-batch{N}-review.md,
    PROGRESS_CR_PATH: {CR_PATH}, PROGRESS_STEP_NUM: 11, METRICS_TARGET: batch{N}-recheck

  Let `BATCH_LAST_ROUND_MAP[N]` = 2

※ 修正サイクルは各バッチにつき最大1回とする（無限ループ防止）。

---

## Step GATE: Human Review Gate

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 11, STATE: 👀 レビュー待ち, DETAIL_STEP: `Step GATE: 人レビュー待ち`

Let `EXTRA_FILES` = `BATCH_TARGET_FILES_MAP` に含まれる全バッチ番号 `N` の `TARGET_FILES` を
連結した一覧（Step REV で実際に実行されたバッチのみ。latest-specs 配下の全成果物ではなく、
今回レビューされたファイルのみに絞ることで、他の並行 CR の編集を誤検知しない）。

Read `~/.claude/skills/xddp-common/scripts/xddp_review_brief.py` generate（レビューブリーフ生成）:
Run via Bash:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_review_brief.py generate --root {CR_PATH} --step 11 --baseline {CR_PATH}/.phase-baseline-11.json --out {CR_PATH}/.review-brief.md {EXTRA_FILES の各エントリについて}--extra-file {エントリ}`
→ stdout の JSON を `BRIEF_SUMMARY`（`top`/`counts`/`brief_path`/`est_total_min`）として取得する。
If the script is not found: tell the user to run `setup.sh` and continue without a brief（ゲートは止めない）。
If it errors: display stderr and continue without a brief.

続けてゲートスナップショットを取得する（ユーザーの確認待ちに入る前に実行すること）:
Run via Bash:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_gate_snapshot.py snapshot --root {CR_PATH} --out {CR_PATH}/.gate-snapshot.json {EXTRA_FILES の各エントリについて}--extra-file {エントリ}`
If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.

Tell the user:
> ✅ 最新仕様書の生成・AIレビューが完了しました。内容を確認してください。
>
> **⚠️ 優先確認ファイル（MAJOR/MINOR バージョンアップ・初回生成・AI合成）**
> ※ これらは誤りが混入しやすい・影響が大きいため、先に確認してください。
> {Step UC が実行された場合}
> - 🔴 system/use-cases/ 以下（AI が CRS UR + SPO §3 から合成。意味的誤りが入りやすい）: {生成・更新ファイルの一覧}
> {今回 MAJOR/MINOR バージョンアップのファイルがある場合}
> - 🟡 MAJOR/MINOR 更新ファイル: {該当ファイルの一覧}
> {今回 PATCH のみのファイルがある場合}
> - ⚪ PATCH 更新ファイル（確認省略可）: {該当ファイルの一覧}
>
> **全生成・更新ファイル一覧:**
> {Step OV で各 repo について}
> - {repo}/overview/ 以下: {生成・更新ファイルの一覧}
> {Step MOD で各 repo・各モジュールについて}
> - {repo}/{module}/ 以下: {生成・更新ファイルの一覧}
> {IS_MULTI かつ Step CROSS が実行された場合}
> - cross/ 以下: {生成・更新ファイルの一覧}
> {Step UC が実行された場合}
> - system/use-cases/ 以下: {生成・更新ファイルの一覧}
>
> {Step REV で未修正の指摘がある場合}
> **AIレビューの未修正指摘:**
> {指摘内容の概要}
>
> ⚠️ **並行 CR がある場合は xddp-11-specs を逐次実行してください**（overview 共有ファイルの同時更新リスク）。
>
> {BRIEF_SUMMARY が取得できている場合のみ挿入}
> 📋 レビューブリーフを生成しました: {BRIEF_SUMMARY.brief_path}
> ⚠️ 重点確認箇所トップN:
> {BRIEF_SUMMARY.top の各件について} - {file}: {marker_type}（{location}）
> 推奨レビュー時間の目安: 約 {BRIEF_SUMMARY.est_total_min} 分
>
> 問題なければ「**確認完了**」と入力してください。修正が必要な場合は直接ファイルを編集してください。
> 複数ファイルにまたがる大きな修正を加えた場合は、確認完了の前に
> `/xddp-review {CR} spec {対象ファイル}` で単体 AI レビューを実施することを推奨します
> （ファイルごとに実行）。

{`UC_PENDING`（Step UC が実行された場合）と `MOD_PENDING[{repo}]`（各 repo について）の内容を集約して提示する:}

{UC_PENDING の廃止候補が空でない場合}
> ⚠️ 以下のユースケースは廃止候補です（候補にした理由: UR を取り下げた／UR が廃止・置き換えを述べる）。
> 削除しますか？ [削除する / 保持する]
> {UC_PENDING の廃止候補一覧（理由と UR を添える）}

{MOD_PENDING[{repo}] の廃止候補が空でない repo がある場合}
> ⚠️ 以下のモジュールは廃止候補です（候補にした理由: 母体にディレクトリ・ファイルが無い／母体に対象のファイルが無い）。
> 削除・統合されたモジュールであれば削除してください。
> {repo ごとの MOD_PENDING[{repo}] 廃止候補一覧（理由を添える）}
> {`protected_by_concurrent_cr` がある場合: 「他 CR（{last_updated_cr}）進行中 — スキップ」として併記する}

{PENDING-CROSS-{CR}.md に provider・affected-repos の材料なしの記録がある場合}
> ⚠️ 以下のインタフェースは `provider`・`affected-repos` の材料が見つかりませんでした。値を書いてください:
> {一覧}

{UC_PENDING の related-modules 照合不能ユースケースが空でない場合}
> ⚠️ 以下のユースケースの `related-modules:` が空リストです。関連モジュールを手動で設定してください:
> {UC_PENDING の related-modules 照合不能ユースケース一覧}

{UC_PENDING の命名衝突・重複記述が空でない場合}
> ⚠️ 以下のユースケースで命名衝突・重複記述が検出されました。確認してください:
> {UC_PENDING の命名衝突・重複記述一覧}

{MOD_PENDING[{repo}] のケバブ名衝突・SPO照合不能モジュールが空でない repo がある場合（`SPEC_SOURCES[{repo}].conflicts`・`chd_unmatched` の照合結果を含む）}
> ⚠️ 以下のモジュールでケバブ名衝突・同じ `module-dir` の仕様の重複、または SPO 照合不能が検出されました。確認してください:
> {repo ごとの MOD_PENDING[{repo}] ケバブ名衝突・SPO照合不能モジュール一覧}

{MOD_PENDING[{repo}] のリネーム候補が空でない repo がある場合}
> 💡 以下のモジュールにリネーム候補があります。新ケバブ名にコピーしますか？ [コピーする / 何もしない]
> {repo ごとの MOD_PENDING[{repo}] リネーム候補一覧}

Wait for the user to confirm.

`CHANGED` の判定: Run via Bash:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_gate_snapshot.py diff --snapshot {CR_PATH}/.gate-snapshot.json`
（`diff` に `--extra-file` を再指定する必要はない——snapshot 時に保存した `extra_files` 一覧を
JSON から読み出して自動的に再スキャンする。）
出力 JSON の `changed`（true/false）を `CHANGED` として採用する（`changed_files` は
現時点ではバッチ単位フィルタに使用しない——今回実行した全バッチを再レビュー対象とする
粗粒度な方針を採る。05.arch/06.design 等の既存 `If CHANGED:` も repo 単位の粗粒度であり、
本件固有の後退ではない。`changed_files` を用いたバッチ単位フィルタへの絞り込みは、
効果とコストが未検証のため本プランのスコープ外とし、改善余地として本節にコメントを残す）。

会話的フォールバック: `## Human Review Gate`（共通節）の Step 4 と同様、ユーザーの発言が具体的な
修正内容に言及しているにもかかわらず `CHANGED = false` の場合のみ、「ファイルを変更しましたか？」と
確認してから判定を上書きする。`xddp-11-specs` は `--extra-file`（`EXTRA_FILES`）が「今回レビューされた
`BATCH_TARGET_FILES_MAP` 内のファイルのみ」に意図的に限定されている（並行 CR の誤検知回避のため）ため、
それ以外の `latest-specs/` 配下ファイル（例: 今回の specout 対象外の既存モジュール、または新規作成した
ファイル）の直接編集は `--root {CR_PATH}` にも `--extra-file` にも捕捉されない。この会話的フォールバックは、
その捕捉漏れに対する最後の安全網として他の3スキル以上に重要となる。

If `CHANGED`:
  For each バッチ番号 `{N}` in `BATCH_TARGET_FILES_MAP`（Step REV で実行されたバッチのみ。
  スキップされたバッチは `BATCH_TARGET_FILES_MAP` に存在しないため自動的に対象外）:
    Read `~/.claude/skills/xddp-common/procedures/final-review-pass.md`, apply "## Final Review Pass" with:
      DOCUMENT_TYPE: SPEC, TARGET_FILES: {BATCH_TARGET_FILES_MAP[N]},
      REFERENCE_FILES: {BATCH_REFERENCE_FILES_MAP[N]},
      REVIEW_ROUND: (BATCH_LAST_ROUND_MAP[N] + 1),
      OUTPUT_FILE: {CR_PATH}/review/11_specs-batch{N}-review.md
  （Fixer は呼ばない。指摘が残る場合は人に判断を委ねる——他スキルの `If CHANGED:` と同一方針）

ユーザーの選択（削除する/保持する・コピーする/何もしない）に応じて、オーケストレーターが
ディレクトリ削除・リネームコピーをファイル操作として直接実行する（エージェントは再呼び出ししない）。
保持を選択したものには何もしない。

---

## Step DONE: Update progress.md, Report

**latest-specs の変更の記録:**
Run via Bash:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-11-specs/scripts/spec_changes.py record --xddp-dir {WORKSPACE_ROOT}/{XDDP_DIR} --cr {CR}`
progress.md の「## 工程11 更新仕様書ファイル一覧」「## 工程11 削除した仕様書ファイル一覧」を、Step 0 の基準と今の latest-specs の
比較から作り直す（GATE で削除したもの・人の編集・分割実行の前の回の更新を含む。一覧を手で書かない）。
終了コードが0以外なら stderr を表示して停止する。

**分割実行継続マーカーの管理:**
分割実行（Step UC 部分完了・Step MOD 分割等）を選択した場合、progress.md の「## 工程11 分割実行メモ」セクションに以下を書く
（セクションが無ければ「## 次に実行すべきコマンド」の前に作る。あれば上書きする）:
```markdown
## 工程11 分割実行メモ
<!-- xddp-11-specs が記録。次回実行時に継続対象を特定するために使用する -->
- 完了済みステップ: {完了したステップ名一覧（例: UC, OV, CROSS）}
- 未処理リポジトリ: {未処理リポジトリ名一覧}  （選択肢 A の場合）
- 未処理モジュール: {repo}: {未処理モジュールの spec_dir 一覧}  （選択肢 B の場合）
- 処理済みUR: {処理済み UR の ID 一覧（例 {CR}-UR-001）}  （Step UC が部分完了の場合）
- 未処理UR: {未処理 UR の ID 一覧}  （Step UC が部分完了の場合）
```
全体完了後にマーカーセクションを削除する。

分割実行を選択した場合（このタイミングで「## 工程11 分割実行メモ」を書き込んだ場合）に限り、まず以下を算出する:
Let `未処理ステップ一覧` = 全体ステップ一覧（UC・OV・MOD。`IS_MULTI` の場合のみ CROSS も含む）から `完了済みステップ` を除いたもの。
（この算出式が正本であり、xddp-status 側の同名表示はこの式と同一のものを用いる。定義を2箇所に重複させず、`xddp-status` 側は progress.md に書き込まれた `完了済みステップ:` の値から都度同じ式で再計算する。）

Step 11 のステータスと `次に実行すべきコマンド` フィールドは、分割実行を選択したか・全体完了したかで以下のように分岐して設定する（`次に実行すべきコマンド` は他工程（`xddp-01-init/SKILL.md`、`xddp-04-specout/SKILL.md`）と同じ「裸コマンド1行」形式に統一する）:
- **分割実行を選択した場合**:
  Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: 11, STATE: 🔄 進行中, DETAIL_STEP: `Step DONE: 分割実行中（未処理: {未処理ステップ一覧}）`
  Set "次に実行すべきコマンド" → `/xddp-11-specs {CR}`
- **全体完了の場合**（分割実行マーカーを書き込まない、または既存マーカーを削除した場合）:
  Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: 11, STATE: ✅ 完了, DETAIL_STEP: `-`,
    ARTIFACT_LINK: `[latest-specs/](../latest-specs/)`
  Set "次に実行すべきコマンド" → `/xddp-close {CR}`

Step DONE 末尾の `Tell the user` ブロックも同じ分岐条件で出し分ける（`未処理ステップ一覧` は上で算出済みの値をそのまま使う）:

- **分割実行を選択した場合:**
  Tell the user:
  > 🧩 工程11（最新仕様書作成）の一部が完了しました（未処理: {未処理ステップ一覧}）。
  > 続けて以下のコマンドを再実行すると、未処理分のみ処理します:
  > ```
  > /xddp-11-specs {CR}
  > ```
  > 進捗確認は `/xddp-status {CR}` でも確認できます。

- **全体完了の場合:**
  Tell the user:
  > 工程11が完了しました。続いて CR クローズ処理（気づき集約・知見ログ更新）を実行してください。
  > ```
  > /xddp-close {CR}
  > ```
  >
  > ⚠️ **知識参照 degraded mode**: xddp-close 未実施のため `{DOCS}` への昇格が未完了です。
  > 次の CR の工程2 は、`{DOCS}` に無い最新仕様を `latest-specs/` から読みます（degraded）。
  > xddp-close を実施してから次の CR を開始することを推奨します。
  >
  > 並行 CR が存在する場合は xddp-11-specs を逐次実行してください（overview 共有ファイルの同時更新リスク）。
