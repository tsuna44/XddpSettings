---
description: XDDP フェーズ6: 最新仕様書（{XDDP_DIR}/latest-specs/）を生成・更新してCRを完了する。「最新仕様書を作って」「latest-specsを更新して」「CRを完了して」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Step 11 (process step 11) — Generate/Update Latest Specifications**.

> This step synthesises SPO (current state) + CHD (changes) into latest-specs/ (current truth).
> New structure follows Kruchten 4+1 view model: Use Case / Logical / Development / Process / Physical.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp.common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
DOCS_DIR, DOCS, REPOS_MAP, REPOS_KEYS, IS_MULTI.)

---

## Step 0: Pre-flight（事前準備）

1. Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

2. Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve HAS_CROSS" with:
     IS_MULTI: {IS_MULTI}, ARTIFACT_PATH: {CR_PATH}/04_specout/cross/SPO-{CR}-cross.md
   → let `HAS_CROSS`.
   ※ HAS_CROSS 判定は SPO 存在ベース（旧 CHD 存在ベースから変更）。specout まで実施していれば cross/ ビューを生成する方針。
   （他工程が「直前工程の cross 成果物」を見るのに対し、本工程は最新仕様書生成の起点となる
   specout の cross SPO を基準にする。design/code が未完了でも specout 済みなら cross ビューを
   生成したいため、あえて直前工程＝design の DSN ではなく specout の SPO を見る）

3. **AFFECTED_REPOS の確定（Step 0 で完全確定）:**
   Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve Affected Repos" with:
     REPOS_KEYS: {REPOS_KEYS}, IS_MULTI: {IS_MULTI}, CR_PATH: {CR_PATH}, FILTER_BY_SPO: true,
     HAS_CROSS: {HAS_CROSS}, CR: {CR}
   → let `AFFECTED_REPOS`.

4. **分割実行継続マーカーの確認:**
   `{CR_PATH}/progress.md` を Read し、「## 工程11 分割実行メモ」セクションが存在するかを確認する。
   存在する場合:
   - `完了済みステップ:` に含まれるステップ（UC・OV・CROSS 等）はスキップする
   - `未処理リポジトリ:` が存在する場合は AFFECTED_REPOS をその値に限定する（選択肢 A の継続）
   - `処理済みモジュール:` が存在する場合は当該 repo の MODULE_SCOPE をその値に限定する（選択肢 B の継続）
   - `処理済みUR:` フィールドが存在する場合は UC をスキップせず `未処理UR:` リストのみを対象に Step UC を再実行する
   存在しない場合は通常の全処理モードで実行する。

5. **`{DOCS}/AI_INDEX.md` の存在確認（先行更新のため）:**
   - `{DOCS}` ディレクトリが存在しない場合: Step DONE での先行更新をスキップし Step GATE で警告追記する
   - `{DOCS}` は存在するが `{DOCS}/AI_INDEX.md` が未存在の場合:
     `xddp.01.init/SKILL.md`「Initial file contents」節に定義済みの `{DOCS}/AI_INDEX.md` テンプレート
     （ユースケース一覧・リポジトリ別仕様書・モジュール別最新仕様・クロスインタフェース一覧（IS_MULTI の場合のみ）・
     「リポジトリ別設計書・テスト仕様書」（1見出し）・共通知識の6セクション。すべてテーブル形式で統一されている）と同一内容で新規作成する
     （このテンプレートを正本とし、他の参照先は設けない。`xddp-close-promote-agent.md` が upsert 対象とする
     「知識参照ガイド」「code-knowledge インデックス」「変更要求仕様書（CRS）ナビゲーション」セクションはテーブル形式ではなく、
     かつ初回スケルトンの対象外であり、`xddp.close` 初回実行時に当該エージェントが自動生成する）。
     新規作成した旨を Step GATE の完了案内コメントに記載する。
   ※ `{DOCS}` ディレクトリ自体の初回作成は xddp.01.init が担う（xddp.11.specs は作成しない）。

6. Read `{CR_PATH}/progress.md`. Set step 11 → 🔄 進行中, 詳細ステップ → `Step 0: 事前準備中`, today. Write back.

---

## Step UC: Synthesize Use Cases (system/use-cases/)

**スキップ条件（以下のいずれかに該当する場合はこのステップをスキップ）:**
- 分割実行継続マーカーの `完了済みステップ:` に `UC` が含まれる（かつ `処理済みUR:` フィールドが存在しない）
- CRS に UR（ユーザー要求）が存在しない（技術的変更のみ）

Update progress.md 詳細ステップ → `Step UC: ユースケース合成中`.

Read `{CR_PATH}/03_change-requirements/CRS-{CR}.md` → CRS §2 UR list. Let `UR_COUNT` = UR 総数。

**コンテキスト圧迫チェック（Step UC 開始前・オーケストレーター側で実施）:**
`UR_COUNT` が 20 を超える場合（かつ分割実行継続マーカーがない場合）は、以下を提示して指示を求める:
- **A: UR 単位で分割実行（推奨）** — 今回は指定 UR のみ処理し、残りは次回実行で処理する
- **B: 一括実行** — 全 UR を一括処理する（コンテキスト圧迫のリスクあり）
選択結果に応じて処理対象 UR リストを確定する（`RESUME_UR_LIST` に反映）。

**Agent tool** `subagent_type=xddp-specs-uc-agent`:
```
CR_NUMBER: {CR}
CR_PATH: {CR_PATH}
XDDP_DIR: {XDDP_DIR}
DOCS: {DOCS}
AFFECTED_REPOS: {AFFECTED_REPOS}
HAS_CROSS: {HAS_CROSS}
TODAY: {TODAY}
RESUME_UR_LIST: {上記チェックで確定した処理対象 UR リスト、分割実行継続マーカーの 未処理UR: リスト、または空（=全UR）}
OUTPUT_FILE: {CR_PATH}/pending-items/PENDING-UC-{CR}.md
```

Wait for completion. エージェントは廃止候補・命名衝突・related-modules 照合不能等の人判断が必要な項目を
内部で対話せず OUTPUT_FILE に**保留事項リストとして書き込む**（既存エージェントの確立されたファイル経由ハンドオフパターンに倣う。
`xddp-verifier-agent.md` の `OUTPUT_FILE` 契約と `xddp.08.verify/SKILL.md` の Read-back 処理と同じ方式）。
オーケストレーターは Agent tool 完了後に `{CR_PATH}/pending-items/PENDING-UC-{CR}.md` を
Read し、内容を Let `UC_PENDING` に保持する。保留事項は Step GATE で人に提示する。
廃止候補の削除実行は Step GATE 後にオーケストレーター側がファイル操作として直接行う（エージェントを再呼び出ししない）。

---

## Step OV: Generate/Update overview (per repo)

**スキップ条件:** 分割実行継続マーカーの `完了済みステップ:` に `OV` が含まれる場合はスキップ。

Update progress.md 詳細ステップ → `Step OV: overview 生成中`.

For each `{repo}` in `AFFECTED_REPOS`:

Read `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md`.
Get `SPECOUT_MODULES` = `{CR_PATH}/04_specout/{repo}/modules/` 配下のディレクトリ名リスト（機械的取得）。

**`overview/architecture.md` の生成/更新（マージ方式）:**
SPO サマリーの「全体アーキテクチャ図」セクション（`## 2.` または「モジュール依存・コンポーネント構成」と表記されるセクション）の内容を使用する。
既存 `{XDDP_DIR}/latest-specs/{repo}/overview/architecture.md` が存在する場合:
- **機械的先決基準（更新判断）:** SPO の Mermaid ブロックのノード数/エッジ数が既存ファイルと異なる、
  またはテキストセクションの行数が 20% 以上変化している → 即時「更新あり」と判定
- 機械的基準に該当しない場合のみ AI セマンティック比較を実施
- 更新時の方針:
  - SPECOUT_MODULES に含まれるモジュールの情報は最新 SPO の内容で更新する
  - SPECOUT_MODULES に含まれない（今回 specout 未実施）モジュールの情報は保持する
  - 削除されたモジュール（CHD に削除記述がある場合）は architecture.md から削除する
  ※ 判定は SPECOUT_MODULES（ディレクトリ名リスト）との機械的照合。AI のセマンティック判断に依存しない。
- **モジュール名ドリフト検出（ノンブロッキング）:**
  SPECOUT_MODULES に新規名があり既存エントリに類似名がある場合（例: 新規 `authentication` と既存 `auth`）は
  「リネーム候補: `auth` → `authentication`」として気づきメモに記録し人に確認を求める（処理は継続）。
- **⚠️ サイレント廃止リスク（実装コメント）:**
  CHD に削除記述がなく今回 specout 対象外のモジュールは廃止候補として検出できない。
  複数 CR にわたる knowledge base の陳腐化を防ぐため、定期的な「棚卸し CR」（全モジュール specout の実施）を推奨する。
  この制約は data-model.md / crud.md にも同様に適用される。
- **⚠️ 並行 CR による同時更新リスク（実装コメント）:**
  architecture.md / data-model.md / crud.md は複数 CR が同一リポジトリを対象とする場合に同時更新リスクがある共有ファイルである。
  同一リポジトリに並行 CR が存在する場合は xddp.11.specs を逐次実行することを推奨する。
  将来的なロック機構は improvement-backlog に記録する（今回スコープ外）。
存在しない場合: `~/.claude/skills/xddp.11.specs/templates/09_overview-architecture-template.md` から初期生成する。

**バージョニング（architecture.md）:**
| 条件 | バージョン |
|---|---|
| 新規モジュールのエントリを追加 | MINOR |
| 既存モジュール説明・依存関係を更新（内容変更あり） | PATCH |
SPO なし CHD あり の PATCH 更新では `last-verified-cr:` を更新しない。

**`overview/sequences/{feature}-seq.md` の生成/更新:**
SPO サマリーの「モジュール間シーケンス図」セクションのサブセクション見出しをケバブ変換して使用する。
見出しなし・単一の場合は `main-seq.md` をデフォルトとする。
テンプレート: `~/.claude/skills/xddp.11.specs/templates/09_overview-sequence-template.md`

**廃止シーケンスファイル処理（Step OV）:**
`{XDDP_DIR}/latest-specs/{repo}/overview/sequences/` 内の既存 `{feature}-seq.md` を列挙し、
今回の SPO §3 サブセクション見出し（ケバブ変換後）に対応しないファイルを「廃止候補」として検出する。
並行 CR 保護: フロントマター `last-updated-cr:` が現在の CR と異なる場合、`{XDDP_DIR}/{last-updated-cr}/progress.md` を確認する。
  - ファイルが存在し、かつ「## CR クローズ」セクションを含まない（クローズ未完了）→ 当該他 CR が進行中とみなし
    廃止候補から除外する（「他 CR（{last-updated-cr}）進行中 — スキップ」として提示）。
  - ファイルが存在しない、または「## CR クローズ」セクションを含む（クローズ済み）→ 保護対象外とし、
    通常どおり廃止候補として検出する。
廃止候補が存在する場合はユーザーに提示して削除確認を求める。
SPO 見出し名変更（内容が同一だが名称が変わった場合）も廃止候補として検出される。
コンテンツの意味的同一性が高い場合はコピー（旧名→新名）を提案する。

**`overview/dfd.md` の生成/更新:**
SPO サマリーの「データフロー図（DFD）」（`## 4.2` または見出し名一致）セクションを参照する。
「副作用なし（省略）」または「対象外」の場合はスキップする。
テンプレート: `~/.claude/skills/xddp.11.specs/templates/09_overview-dfd-template.md`

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
テンプレート: `~/.claude/skills/xddp.11.specs/templates/09_overview-data-model-template.md`
`source:` フロントマターキー: SPO §4.3 の `source` アノテーション（`ai-inferred` または `spo`）を引き継ぐ。

**`overview/crud.md` の生成/更新（マージ方式）:**
SPO サマリーの「データアクセスマトリクス（CRUDマトリクス・Read/Writeマトリクス）」セクション（`## 4.4` または見出し名一致）を参照する。
「対象外」記載またはセクションが存在しない場合は生成スキップ（既存ファイルがあれば保持）。
マージ方式: 処理名（行）をキーに照合し、今回の SPO §4.4 に記述されているものは更新、非記載は保持。
テンプレート: `~/.claude/skills/xddp.11.specs/templates/09_overview-crud-template.md`

**`overview/deployment.md` の生成/更新:**
SPO サマリーに「ハードウェア構成・デプロイ構成」セクションが存在する場合のみ生成する。
テンプレート: `~/.claude/skills/xddp.11.specs/templates/09_overview-deployment-template.md`

※ セクション参照は見出し名ベースで行う（セクション番号は SPO テンプレート種別により異なるため）。

---

## Step MOD: Generate/Update module specs (per repo, per module)

**スキップ条件:** 分割実行継続マーカーの `完了済みステップ:` に `MOD` が含まれる場合はスキップ。

Update progress.md 詳細ステップ → `Step MOD: モジュール仕様生成中`.

**コンテキスト圧迫チェック（Step MOD 開始前）:**
AFFECTED_REPOS 内の全モジュール数の合計が 10 を超える場合（かつ分割実行継続マーカーがない場合）は、
以下を提示して指示を求める:
- **A: リポジトリ単位で分割実行（推奨）**
- **B: モジュール単位で分割実行**
- **C: 一括実行（遅い場合あり）**

For each `{repo}` in `AFFECTED_REPOS`（またはユーザーが選択したサブセット）:

**Agent tool** `subagent_type=xddp-specs-mod-agent`:
```
CR_NUMBER: {CR}
CR_PATH: {CR_PATH}
XDDP_DIR: {XDDP_DIR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
DOCS: {DOCS}
TODAY: {TODAY}
MODULE_SCOPE: {ユーザー選択モジュール一覧、なければ空（= 全モジュール）}
OUTPUT_FILE: {CR_PATH}/pending-items/PENDING-MOD-{CR}-{repo}.md
```

Wait for completion. エージェントは廃止候補・命名衝突・SPO照合不能等の人判断が必要な項目を
内部で対話せず OUTPUT_FILE に**保留事項リストとして書き込む**（Step UC と同じファイル経由ハンドオフ方式）。
オーケストレーターは Agent tool 完了後に `{CR_PATH}/pending-items/PENDING-MOD-{CR}-{repo}.md` を Read し、
内容を Let `MOD_PENDING[{repo}]` に保持する。
保留事項は Step GATE で人に提示し、削除・リネーム実行はオーケストレーター側がファイル操作として直接行う。

---

## Step CROSS: Generate/Update cross specs (IS_MULTI のみ)

**スキップ条件:** IS_MULTI でない、またはHAS_CROSS でない、または分割実行継続マーカーに `CROSS` が含まれる場合はスキップ。

Update progress.md 詳細ステップ → `Step CROSS: クロス仕様生成中`.

Read `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md`.

**`cross/sequences/{flow}-seq.md` の生成/更新:**
クロスリポジトリ SPO §3（シーケンス図）のサブセクション見出しをケバブ変換して使用する。
見出しなし・単一の場合は `main-seq.md` をデフォルトとする。
テンプレート: `~/.claude/skills/xddp.11.specs/templates/09_cross-sequence-template.md`

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
バージョン判定: breaking 変更（後退互換性を破壊）→ MAJOR、新パラメータ・フィールド追加（後退互換性あり）→ MINOR、ドキュメントのみの修正 → PATCH
テンプレート: `~/.claude/skills/xddp.11.specs/templates/09_cross-interface-spec-template.md`

**`cross/interfaces/{interface-kebab}/schema.md` の生成/更新:**
テンプレート: `~/.claude/skills/xddp.11.specs/templates/09_cross-interface-schema-template.md`

**廃止シーケンスファイル処理（Step CROSS）:**
`{XDDP_DIR}/latest-specs/cross/sequences/` 内の既存 `{flow-kebab}-seq.md` を列挙し、
今回のクロスリポジトリ SPO §3 のサブセクション見出し（ケバブ変換後）に対応しないファイルを廃止候補として検出する。
Step OV の廃止シーケンスファイル処理と同様の並行 CR 保護・廃止確認を実施する。
※ クロス SPO が存在しない場合（HAS_CROSS=false でステップスキップ時）は廃止候補処理も実施しない。

---

## Step REV: AI Review Loop（今 CR で生成/更新したファイルのみ対象）

Update progress.md 詳細ステップ → `Step REV: AIレビュー中`.

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

For each `{repo}` in `AFFECTED_REPOS`: Read `~/.claude/skills/xddp.common/SKILL.md`, apply
"## Discover CHD Files" with `CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}` → let `CHD_CONTENT_FILES`.
Let `ALL_CHD_CONTENT_FILES` = 全 repo の `CHD_CONTENT_FILES` を連結したもの。

For each batch:

**Agent tool** `subagent_type=xddp-reviewer`:
```
DOCUMENT_TYPE: SPEC
TARGET_FILES: [{batch file paths}]
REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {ALL_CHD_CONTENT_FILES を展開}]
REVIEW_ROUND: 1
OUTPUT_FILE: {CR_PATH}/review/09_specs-batch{N}-review.md
```

**AI レビュー指摘への自動修正（バッチごとに最大1サイクル）:**
以下のカテゴリの指摘を自動修正する:
- Mermaid 図の構文エラー（sequenceDiagram・erDiagram・classDiagram・graph TD / flowchart 全タイプ）
- シーケンス図の参加者漏れ・誤記（構文エラー以外の参加者不足）
- SP 差分が誤ったセクションに適用されている（別セクションへの転記で対処）
- フロントマター必須キー（`version`・`last-updated-cr`・`module`・`repo`）の漏れ
- 変更履歴エントリの形式不備（テンプレートの列定義との不一致）
- 気づきメモセクションの有無（Section 3-4 の気づきメモポリシーとの不整合）

上記以外の指摘（機能仕様の内容判断・既存設計との整合性確認が必要なもの等）は Step GATE の人レビューコメントとして提示する。
自動修正後は同バッチに対して再レビューを1回実施し、残指摘があれば Step GATE に渡す。
※ 修正サイクルは各バッチにつき最大1回とする（無限ループ防止）。

---

## Step GATE: Human Review Gate

Update `{CR_PATH}/progress.md` step 11 状態 → 👀 レビュー待ち, 詳細ステップ → `Step GATE: 人レビュー待ち`.

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
> ⚠️ **並行 CR がある場合は xddp.11.specs を逐次実行してください**（AI_INDEX.md 競合更新リスクおよび overview 共有ファイルの同時更新リスク）。
>
> 問題なければ「**確認完了**」と入力してください。修正が必要な場合は直接ファイルを編集してください。
> 複数ファイルにまたがる大きな修正を加えた場合は、確認完了の前に
> `/xddp.review {CR} spec {対象ファイル}` で単体 AI レビューを実施することを推奨します
> （ファイルごとに実行）。

{`UC_PENDING`（Step UC が実行された場合）と `MOD_PENDING[{repo}]`（各 repo について）の内容を集約して提示する:}

{UC_PENDING の廃止候補が空でない場合}
> ⚠️ 以下のユースケースは現在の CRS に対応する UR が見つかりません（廃止候補）。
> 削除しますか？ [削除する / 保持する]
> {UC_PENDING の廃止候補一覧}

{MOD_PENDING[{repo}] の廃止候補が空でない repo がある場合}
> ⚠️ 以下のモジュールは今回 CR の specout 対象に含まれていません（廃止候補）。
> 削除・統合されたモジュールであれば削除してください。
> {repo ごとの MOD_PENDING[{repo}] 廃止候補一覧}

{UC_PENDING の related-modules 照合不能ユースケースが空でない場合}
> ⚠️ 以下のユースケースの `related-modules:` が空リストです。関連モジュールを手動で設定してください:
> {UC_PENDING の related-modules 照合不能ユースケース一覧}

{UC_PENDING の命名衝突・重複記述が空でない場合}
> ⚠️ 以下のユースケースで命名衝突・重複記述が検出されました。確認してください:
> {UC_PENDING の命名衝突・重複記述一覧}

{MOD_PENDING[{repo}] のケバブ名衝突・SPO照合不能モジュールが空でない repo がある場合}
> ⚠️ 以下のモジュールでケバブ名衝突または SPO 照合不能が検出されました。確認してください:
> {repo ごとの MOD_PENDING[{repo}] ケバブ名衝突・SPO照合不能モジュール一覧}

{MOD_PENDING[{repo}] のリネーム候補が空でない repo がある場合}
> 💡 以下のモジュールにリネーム候補があります。新ケバブ名にコピーしますか？ [コピーする / 何もしない]
> {repo ごとの MOD_PENDING[{repo}] リネーム候補一覧}

Wait for the user to confirm.

ユーザーの選択（削除する/保持する・コピーする/何もしない）に応じて、オーケストレーターが
ディレクトリ削除・リネームコピーをファイル操作として直接実行する（エージェントは再呼び出ししない）。
保持を選択した場合は当該ファイルのフロントマターに `status: orphaned`（UC）または `status: unverified`（MOD）を追記する。

---

## Step DONE: Update progress.md, Report

**分割実行継続マーカーの管理:**
分割実行（Step UC 部分完了・Step MOD 分割等）を選択した場合、progress.md §15 に以下を追記する:
```markdown
## 工程11 分割実行メモ
<!-- xddp.11.specs が記録。次回実行時に継続対象を特定するために使用する -->
- 完了済みステップ: {完了したステップ名一覧（例: UC, OV, CROSS）}
- 未処理リポジトリ: {未処理リポジトリ名一覧}  （選択肢 A の場合）
- 処理済みモジュール: {処理済みモジュール名一覧} in {repo}  （選択肢 B の場合）
- 処理済みUR: {処理済みURケバブ名一覧}  （Step UC が部分完了の場合）
- 未処理UR: {未処理URケバブ名一覧}  （Step UC が部分完了の場合）
```
全体完了後にマーカーセクションを削除する。

分割実行を選択した場合（このタイミングで「## 工程11 分割実行メモ」を書き込んだ場合）に限り、まず以下を算出する:
Let `未処理ステップ一覧` = 全体ステップ一覧（UC・OV・MOD。`IS_MULTI` の場合のみ CROSS も含む）から `完了済みステップ` を除いたもの。
（この算出式が正本であり、xddp.status 側の同名表示はこの式と同一のものを用いる。定義を2箇所に重複させず、`xddp.status` 側は progress.md に書き込まれた `完了済みステップ:` の値から都度同じ式で再計算する。）

Step 11 のステータスと `次に実行すべきコマンド` フィールドは、分割実行を選択したか・全体完了したかで以下のように分岐して設定する（`次に実行すべきコマンド` は他工程（`xddp.01.init/SKILL.md`、`xddp.04.specout/SKILL.md`）と同じ「裸コマンド1行」形式に統一する）:
- **分割実行を選択した場合**:
  Step 11 (最新仕様書作成) → 🔄 進行中, 詳細ステップ → `Step DONE: 分割実行中（未処理: {未処理ステップ一覧}）`.
  Set "次に実行すべきコマンド" → `/xddp.11.specs {CR}`
- **全体完了の場合**（分割実行マーカーを書き込まない、または既存マーカーを削除した場合）:
  Step 11 (最新仕様書作成) → ✅ 完了, 詳細ステップ → `-`.
  Set "次に実行すべきコマンド" → `/xddp.close {CR}`

**更新ファイル一覧の記録（progress.md §15）:**
新構造では 1モジュール = 複数ファイルになるため、全ファイルパスを列挙する。

**system/ ファイルの記録確認（必須チェック）:**
Step UC が実行された場合（`{XDDP_DIR}/latest-specs/system/use-cases/` が存在する場合）:
  Enumerate all `.md` files under `{XDDP_DIR}/latest-specs/system/use-cases/`.
  For each file, verify it appears in the "## 工程11 更新仕様書ファイル一覧" section.
  If any `system/use-cases/**/*.md` file is missing from the list → add it before writing the section.
  （xddp.close Step C0-3 の保護判定はこのリストに依存しており、記録漏れがあると
   C0-3 で `{DOCS}/system/specs/` から旧バージョンファイルが上書きコピーされるリスクがある）

````markdown
## 工程11 更新仕様書ファイル一覧

<!-- xddp.11.specs が自動記録。xddp.close Step C0-3 で保護対象判定に使用する。 -->

- latest-specs/{repo}/overview/architecture.md
- latest-specs/{repo}/{module}/spec.md
- latest-specs/{repo}/{module}/structure.md
- latest-specs/{repo}/{module}/sequences/main-seq.md
- latest-specs/cross/interfaces/{interface-kebab}/spec.md
- latest-specs/cross/interfaces/{interface-kebab}/schema.md
- latest-specs/cross/sequences/{flow}-seq.md
- latest-specs/system/use-cases/{usecase}/description.md
- latest-specs/system/use-cases/{usecase}/sequences/{scenario}-seq.md
````

(Overwrite the section if it already exists.)

**AI_INDEX.md 先行更新（Step DONE 完了前に実施）:**
`{DOCS}/AI_INDEX.md` の「モジュール別最新仕様」セクションと「ユースケース一覧」セクションのみを先行 upsert する。
IS_MULTI の場合は「クロスインタフェース一覧」セクションも upsert する。
これにより xddp.close 実行前に次 CR の xddp.02.analysis が参照できる状態にする。
`{DOCS}` が存在しない場合はこの先行更新をスキップし、Step GATE で警告を追記する。

**テーブル列構成・リンクパス形式・フロントマターキーは `xddp-close-promote-agent.md` の該当セクション
定義に従うこと（拘束力のある指示）:** 本先行 upsert が生成する「モジュール別最新仕様」「ユースケース一覧」
「クロスインタフェース一覧」の内容は、`xddp-close-promote-agent.md` のセクション1「「ユースケース一覧」
セクション（upsert）」（テーブル列構成、フロントマターキー `related-modules`〔`module:` ではない〕、
リンクパス `system/specs/use-cases/{usecase-kebab}/description.md`）・セクション3「「モジュール別最新仕様」
セクション（upsert）」（テーブル列構成・リンクパス）・セクション4「「クロスインタフェース一覧」セクション
（IS_MULTI のみ・upsert）」（テーブル列構成・リンクパス）と完全に同一のテーブル列構成・リンクパス規則・
フロントマターキー参照に従うこと。promote-agent 側の定義を正本とし、xddp.11.specs 側はこれを独自に
再定義してはならない。

**「モジュール別最新仕様」セクションの行スコープは `SPECOUT_MODULES` に限定すること（拘束力のある指示）:**
本先行 upsert が「モジュール別最新仕様」セクションに upsert する行（`{repo}/{module}` キー）は、
`AFFECTED_REPOS` に含まれる各 `{repo}` について、Step OV で取得済みの `SPECOUT_MODULES`
（`{CR_PATH}/04_specout/{repo}/modules/` 配下のディレクトリ名リスト）に含まれるモジュールのみとする。
これは `xddp-close-promote-agent.md` のセクション3「モジュール別最新仕様」の「今回 CR で生成・更新した
全モジュールの行を upsert」という記述の
行選択ロジックと同一の集合であり、両者が同一の行集合を導出することの根拠となる。`SPECOUT_MODULES` に
含まれないモジュール（今回 specout 未実施）の行を upsert してはならない。
なお「ユースケース一覧」「クロスインタフェース一覧」の2セクションは、promote-agent 側の導出ロジックが
`latest-specs/system/use-cases/` および `latest-specs/cross/interfaces/` の**ディレクトリ全件列挙**である
（CR スコープでの絞り込みを行わない）ため、先行 upsert 側もこの2セクションについてはディレクトリ全件を
対象とすればよく、別途 CR スコープの行スコープ指定は不要である。

**先行更新結果を progress.md に記録する（xddp.close Step C2 の再導出スキップ判定に使用）:**
`{CR_PATH}/progress.md` に以下のセクションを upsert する（既存があれば上書き）:
```markdown
## 工程11 AI_INDEX先行更新セクション
<!-- xddp.close Step C2（xddp-close-promote-agent）が読み取り、
     ここに「済」と記録されたセクションの再導出をスキップする。 -->
- ユースケース一覧: {済 / スキップ(DOCS不在)}
- モジュール別最新仕様: {済 / スキップ(DOCS不在)}
- クロスインタフェース一覧: {済 / スキップ(DOCS不在) / 対象外(IS_MULTI=false)}
```
`{DOCS}` 不在で先行更新自体をスキップした場合は全セクションに「スキップ(DOCS不在)」を記録する
（xddp.close 側にフル再導出させるためのフォールバック。値を空にしたり省略してはならない）。
`{DOCS}` が存在し、かつ `IS_MULTI=false` の場合（「クロスインタフェース一覧」セクション自体を upsert しない
ケース）は、「クロスインタフェース一覧」の行に `対象外(IS_MULTI=false)` を記録する。
AI_INDEX.md への先行 upsert がエラーになった場合、当該セクションには「済」を記録せず
「スキップ(DOCS不在)」相当の安全側の値を記録する（xddp.close 側にフル再導出させるため）。

**「クロスインタフェース一覧」を「済」と記録する条件（IS_MULTI 初回移行時の見出し作成を含む・拘束力のある指示）:**
IS_MULTI への初回移行 CR で既存 `{DOCS}/AI_INDEX.md` に「クロスインタフェース一覧」セクション見出しが
存在しない場合、先行 upsert はこの見出し自体を新規作成した上で内容を upsert すること
（`xddp-close-promote-agent.md` のセクション4「クロスインタフェース一覧」の既存ロジック
「IS_MULTI への移行対応: 既存 AI_INDEX.md にセクションが存在しない状態で IS_MULTI=true となった場合は
新規追加する」と同じ契約に従う）。
見出し作成を含めて upsert が成功した場合のみ「済」を記録する。見出し作成が行われずに内容のみ追記してしまう
実装は誤りであり、その場合は「クロスインタフェース一覧」を「済」にしてはならない（promote-agent 側の
スキップガードによって見出しが永久に作成されないデグレードを防ぐため）。

**設計書ナビゲーション先行更新（同タイミング・DOCS 存在時のみ）:**
For each `{repo}` in `AFFECTED_REPOS`:
  If `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-comparison.md` exists:
    Upsert row in AI_INDEX.md「設計書ナビゲーション」セクション:
    "`{CR}` 設計比較・採用方式 → `{DOCS}/{repo}/design/DSN-{CR}-comparison.md`"
  Else if `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-A.md` exists:
    Upsert row: "`{CR}` 採用設計 → `{DOCS}/{repo}/design/DSN-{CR}-approach-A.md`"
If `HAS_CROSS` and `{CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md` exists:
  Upsert row: "`{CR}` cross 設計 → `{DOCS}/cross/design/DSN-{CR}-cross.md`"
（リンク先は xddp.close Step C4 完了後に有効になる。broken リンクは許容する）

**先行更新時の注意（broken リンク許容）:**
先行更新時点では xddp.close Step C2（`{DOCS}` への昇格）が未完了のため、
AI_INDEX.md の全リンク（`{repo}/specs/`・`cross/specs/`・`system/specs/` 配下を含む全セクション）は
xddp.close Step C2 完了まで broken になる。これは意図的に許容する。

Step DONE 末尾の `Tell the user` ブロックも同じ分岐条件で出し分ける（`未処理ステップ一覧` は上で算出済みの値をそのまま使う）:

- **分割実行を選択した場合:**
  Tell the user:
  > 🧩 工程11（最新仕様書作成）の一部が完了しました（未処理: {未処理ステップ一覧}）。
  > 続けて以下のコマンドを再実行すると、未処理分のみ処理します:
  > ```
  > /xddp.11.specs {CR}
  > ```
  > 進捗確認は `/xddp.status {CR}` でも確認できます。

- **全体完了の場合:**
  Tell the user:
  > 工程11が完了しました。続いて CR クローズ処理（気づき集約・知見ログ更新）を実行してください。
  > ```
  > /xddp.close {CR}
  > ```
  >
  > ⚠️ **知識参照 degraded mode**: xddp.close 未実施のため `{DOCS}` への昇格が未完了です。
  > 次の CR の xddp.02.analysis は `latest-specs/` から直接参照しますが、
  > AI_INDEX.md の全リンクは機能しません。xddp.close を実施してから次の CR を開始することを推奨します。
  >
  > 並行 CR が存在する場合は xddp.11.specs を逐次実行してください（AI_INDEX.md の競合更新リスク）。
