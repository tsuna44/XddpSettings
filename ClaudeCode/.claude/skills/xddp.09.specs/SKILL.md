---
description: XDDP フェーズ6: 最新仕様書（{XDDP_DIR}/latest-specs/）を生成・更新してCRを完了する。「最新仕様書を作って」「latest-specsを更新して」「CRを完了して」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Step 09 (process step 15) — Generate/Update Latest Specifications**.

> This step synthesises SPO (current state) + CHD (changes) into latest-specs/ (current truth).
> New structure follows Kruchten 4+1 view model: Use Case / Logical / Development / Process / Physical.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp.common/SKILL.md; reuse WORKSPACE_ROOT, XDDP_DIR.)

---

## Step 0: Pre-flight（事前準備）

1. Read `{WORKSPACE_ROOT}/xddp.config.md`. Confirm:
   - `XDDP_DIR` (default: `xddp`)
   - `DOCS_DIR` (default: `baseline_docs`)
   - `CR_PREFIX` (default: `CR`)
   - `REPOS:` mapping → `REPOS_MAP` (repo name → path), `REPOS_KEYS` list

2. Let `IS_MULTI` = (len(REPOS_KEYS) ≥ 2).
   Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.
   Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`.

3. Let `HAS_CROSS` = (IS_MULTI and `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md` exists).
   ※ HAS_CROSS 判定は SPO 存在ベース（旧 CHD 存在ベースから変更）。specout まで実施していれば cross/ ビューを生成する方針。

4. **AFFECTED_REPOS の確定（Step 0 で完全確定）:**
   基本: `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` が存在するリポジトリを対象とする。
   追加条件（IS_MULTI and HAS_CROSS の場合）:
     `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` を Read し（存在する場合）、
     インタフェース変更サマリーで「影響リポジトリ」として列挙されているリポジトリを
     AFFECTED_REPOS に追加する（SPO がなくても overview/architecture.md 更新対象になる可能性があるため）。
     CHD cross が存在しない場合はこの追加条件は適用しない。
   Let `AFFECTED_REPOS` = 上記ロジックで確定したリポジトリのリスト。

5. **分割実行継続マーカーの確認:**
   `{CR_PATH}/progress.md` を Read し、「## 工程15 分割実行メモ」セクションが存在するかを確認する。
   存在する場合:
   - `完了済みステップ:` に含まれるステップ（UC・OV・CROSS 等）はスキップする
   - `未処理リポジトリ:` が存在する場合は AFFECTED_REPOS をその値に限定する（選択肢 A の継続）
   - `処理済みモジュール:` が存在する場合は当該 repo の MODULE_SCOPE をその値に限定する（選択肢 B の継続）
   - `処理済みUR:` フィールドが存在する場合は UC をスキップせず `未処理UR:` リストのみを対象に Step UC を再実行する
   存在しない場合は通常の全処理モードで実行する。

6. **`{DOCS}/AI_INDEX.md` の存在確認（先行更新のため）:**
   - `{DOCS}` ディレクトリが存在しない場合: Step DONE での先行更新をスキップし Step GATE で警告追記する
   - `{DOCS}` は存在するが `{DOCS}/AI_INDEX.md` が未存在の場合:
     Section 3-6-1 のセクション構成スケルトンとして新規作成し、
     「ユースケース一覧」「モジュール別最新仕様」の 2 セクションを書き込む（IS_MULTI の場合は「クロスインタフェース一覧」も追記）。
     新規作成した旨を Step GATE の完了案内コメントに記載する。
   ※ `{DOCS}` ディレクトリ自体の初回作成は xddp.01.init が担う（xddp.09.specs は作成しない）。

7. Read `{CR_PATH}/progress.md`. Set step 15 → 🔄 進行中, 詳細ステップ → `Step 0: 事前準備中`, today. Write back.

---

## Step UC: Synthesize Use Cases (system/use-cases/)

**スキップ条件（以下のいずれかに該当する場合はこのステップをスキップ）:**
- 分割実行継続マーカーの `完了済みステップ:` に `UC` が含まれる（かつ `処理済みUR:` フィールドが存在しない）
- CRS に UR（ユーザー要求）が存在しない（技術的変更のみ）

Update progress.md 詳細ステップ → `Step UC: ユースケース合成中`.

Read `{CR_PATH}/03_change-requirements/CRS-{CR}.md` → CRS §2 UR list.

**処理対象 UR の確定:**
分割実行継続マーカーの `未処理UR:` が存在する場合はその UR のみを対象とする。
存在しない場合は全 UR を対象とする。

**モジュール数 / UR 数によるコンテキスト圧迫チェック（Step UC 開始前）:**
UR 数が 20 を超える場合（かつ分割実行継続マーカーがない場合）は、Step UC 実行前に以下を提示して指示を求める:
- **A: UR 単位で分割実行（推奨）** — 今回は指定 UR のみ処理し、残りは次回実行で処理する
- **B: 一括実行** — 全 UR を一括処理する（コンテキスト圧迫のリスクあり）

For each UR in processing scope:

1. UR のタイトル・説明からユースケース名（kebab）を生成する（Section 3-0「共通命名ルール」参照）。
   既存の `{XDDP_DIR}/latest-specs/system/use-cases/` ディレクトリが存在する場合は既存名を優先する。

2. 各リポジトリの SPO サマリーを Read して `## 3. モジュール間シーケンス図` セクションを確認する。
   IS_MULTI かつ HAS_CROSS の場合は cross SPO §3 も合わせて参照する。

3. **前提チェック（UR × SPO マッチング）:**
   - 全リポジトリの SPO §3 が空・「対象外」・該当シーケンス図なし → description.md のみ生成（sequences/ 空）
   - 対応するシーケンスが見つからない → description.md に「（SPO に対応シーケンスなし・手動作成が必要）」と記載

4. **ユーザー層の合成（アクター補完）:**
   CRS §2 UR のアクター・クライアント種別記述から以下の優先順位で起点を補完する:
   1. UR にアクター・クライアント種別の記述がある → その記述を起点として使用
      例: 「管理者がブラウザで操作」→ `Admin → Browser → {エントリポイント}`
          「オペレーターがパネル操作」→ `Operator → HMI → {コントローラ}`
   2. UR にアクター記述はないが SPO のエントリポイント種別から推定できる
      例: REST API が起点 → `User → {HTTP Client} → {APIエンドポイント}`
          バッチ処理が起点 → `Scheduler → {ワーカー名}`
          タイマー割り込みが起点 → `Timer → ISR → {ハンドラ}`
          センサー入力が起点 → `Sensor → {ドライバ} → {処理モジュール}`
          外部システム信号が起点 → `ExternalSystem → {通信バス} → {受信モジュール}`
   3. 推定できない → `{Initiator} → {エントリポイント}` の最小形を使用し
      「（起動主体不明・最小補完）」と注記する
   ※ アクターは人（User/Operator/Admin）とは限らない（Sensor/Timer/Scheduler/ExternalSystem 等も起動主体となりうる）
   ※ 「Browser」固定の補完は行わない（システム種別が明示的に確認できる場合のみ適切なクライアントを付加する）
   ※ UR にアクター・トリガー記述がない場合は「（CRS UR に明示アクターなし・推定補完）」と注記する

5. **related-modules の生成:**
   UR タイトル・説明 → SPO モジュール名の照合（セマンティックマッチング）で対応モジュールリストを生成する。
   照合できない場合は空リスト `[]` で初期生成し Step GATE でユーザーに確認を求める。

6. **生成/更新処理:**
   既存 `{XDDP_DIR}/latest-specs/system/use-cases/{usecase-kebab}/` が存在する場合:
   - AI が現在の CRS UR 内容と SPO §3 情報を既存 description.md と意味的に比較する
   - 変化がないと判断した場合はスキップ（ファイルに手を加えない）
   - 変化がある場合: description.md を Read し、**既存の「関連UR」欄・「主フロー概要」欄等に
     記録されている過去 CR で追加された内容を保持しながら** CRS 変更を反映し、版数更新する
     ※ CRS には今回の CR の UR のみ含まれるが、description.md には複数 CR にわたる UR が蓄積されている場合がある
       当該 CR の CRS に含まれない UR に関する記述は保持する（上書き・削除しない）
   存在しない場合:
   - `~/.claude/skills/xddp.templates/09_system-use-case-description-template.md` から生成
   - フロントマターに `source: ai-inferred`、`related-modules:` リストを設定する
   - SPO §3 シーケンス情報から `sequences/{scenario}-seq.md` を
     `~/.claude/skills/xddp.templates/09_system-use-case-sequence-template.md` から生成する
   ※ シーケンスファイルの `{scenario}` は SPO §3 のサブセクション見出しをケバブ変換。見出しなし・単一の場合は `main-flow-seq.md`

   **バージョニング（description.md）:**
   - 機械的先決基準（Section 3-4 参照）を最初に適用し、AI セマンティック判断で昇格方向にのみ使用する:
     | 条件 | バージョン下限 |
     |---|---|
     | 主フロー・代替フローの根本的書き換え | MAJOR |
     | 代替フロー追加・新規シーケンスファイル追加 | MINOR |
     | 関連UR 追記・誤字修正・説明の明確化 | PATCH |
   - SPO なし CHD あり の PATCH 更新では `last-verified-cr:` を更新しない

7. **照合例外ケースの処理:**
   - 複数 UR が同一シーケンスに対応 → ユースケース名は最も上位の UR を採用、description.md の「関連UR」欄に複数 UR を列挙
   - 1 UR に複数シーケンスが対応 → sequences/ に複数ファイルを生成
   - 複数の UR から同一のケバブ名が生成される場合 → 2つ目以降に `-2`・`-3` サフィックスを付与し人に確認を求める

**廃止 UR 処理（Step UC のモジュールループ完了後）:**
既存の `{XDDP_DIR}/latest-specs/system/use-cases/` 配下のディレクトリを列挙し、
対応する UR（同一ケバブ名で CRS に存在する UR）がないディレクトリを「廃止候補」として検出する。
並行 CR 保護: `description.md` のフロントマターに `last-updated-cr:` が記録されており、
かつその値が現在の CR と異なる場合は廃止候補から除外する（「他 CR（{last-updated-cr}）管理 — スキップ」として提示）。
廃止候補が存在する場合:
> ⚠️ 以下のユースケースは現在の CRS に対応する UR が見つかりません。
> 削除しますか？ [削除する / 保持する]
> - system/use-cases/{orphaned-usecase}/
削除を選択した場合はディレクトリごと削除し progress.md に記録する。
保持を選択した場合は description.md のフロントマター末尾に `status: orphaned（CR-{CR} 時点で対応 UR なし）` を追記する。

**シングルリポジトリでの重複防止:**
シングルリポジトリ（IS_MULTI=false）でも `system/use-cases/` は生成する。
`system/use-cases/sequences/` は `{repo}/overview/sequences/` へのリンク参照を推奨する方針を徹底し、
同一シナリオの重複記述を避ける。Step GATE で重複している場合は指摘して人に選択を促す。

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
  同一リポジトリに並行 CR が存在する場合は xddp.09.specs を逐次実行することを推奨する。
  将来的なロック機構は improvement-backlog に記録する（今回スコープ外）。
存在しない場合: `~/.claude/skills/xddp.templates/09_overview-architecture-template.md` から初期生成する。

**バージョニング（architecture.md）:**
| 条件 | バージョン |
|---|---|
| 新規モジュールのエントリを追加 | MINOR |
| 既存モジュール説明・依存関係を更新（内容変更あり） | PATCH |
SPO なし CHD あり の PATCH 更新では `last-verified-cr:` を更新しない。

**`overview/sequences/{feature}-seq.md` の生成/更新:**
SPO サマリーの「モジュール間シーケンス図」セクションのサブセクション見出しをケバブ変換して使用する。
見出しなし・単一の場合は `main-seq.md` をデフォルトとする。
テンプレート: `~/.claude/skills/xddp.templates/09_overview-sequence-template.md`

**廃止シーケンスファイル処理（Step OV）:**
`{XDDP_DIR}/latest-specs/{repo}/overview/sequences/` 内の既存 `{feature}-seq.md` を列挙し、
今回の SPO §3 サブセクション見出し（ケバブ変換後）に対応しないファイルを「廃止候補」として検出する。
並行 CR 保護: フロントマター `last-updated-cr:` が現在の CR と異なる場合は廃止候補から除外する
（「他 CR（{last-updated-cr}）管理 — スキップ」として提示）。
廃止候補が存在する場合はユーザーに提示して削除確認を求める。
SPO 見出し名変更（内容が同一だが名称が変わった場合）も廃止候補として検出される。
コンテンツの意味的同一性が高い場合はコピー（旧名→新名）を提案する。

**`overview/dfd.md` の生成/更新:**
SPO サマリーの「データフロー図（DFD）」（`## 4.2` または見出し名一致）セクションを参照する。
「副作用なし（省略）」または「対象外」の場合はスキップする。
テンプレート: `~/.claude/skills/xddp.templates/09_overview-dfd-template.md`

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
テンプレート: `~/.claude/skills/xddp.templates/09_overview-data-model-template.md`
`source:` フロントマターキー: SPO §4.3 の `source` アノテーション（`ai-inferred` または `spo`）を引き継ぐ。

**`overview/crud.md` の生成/更新（マージ方式）:**
SPO サマリーの「データアクセスマトリクス（CRUDマトリクス・Read/Writeマトリクス）」セクション（`## 4.4` または見出し名一致）を参照する。
「対象外」記載またはセクションが存在しない場合は生成スキップ（既存ファイルがあれば保持）。
マージ方式: 処理名（行）をキーに照合し、今回の SPO §4.4 に記述されているものは更新、非記載は保持。
テンプレート: `~/.claude/skills/xddp.templates/09_overview-crud-template.md`

**`overview/deployment.md` の生成/更新:**
SPO サマリーに「ハードウェア構成・デプロイ構成」セクションが存在する場合のみ生成する。
テンプレート: `~/.claude/skills/xddp.templates/09_overview-deployment-template.md`

※ セクション参照は見出し名ベースで行う（セクション番号は SPO テンプレート種別により異なるため）。

---

## Step MOD: Generate/Update module specs (per repo, per module)

**スキップ条件:** 分割実行継続マーカーの `完了済みステップ:` に `MOD` が含まれる場合はスキップ。

Update progress.md 詳細ステップ → `Step MOD: モジュール仕様生成中`.

**コンテキスト圧迫チェック（Step MOD 開始前）:**
AFFECTED_REPOS 内の全モジュール数の合計が 10 を超える場合（かつ分割実行継続マーカーがない場合）は、
以下を提示して指示を求める:
- **A: リポジトリ単位で分割実行（推奨）** — 今回は指定 `{repo}` のみ処理し、残りは次回実行で処理する
- **B: モジュール単位で分割実行** — 今回は指定モジュールのみ処理する（モジュール名リストを提示）
- **C: 一括実行（遅い場合あり）** — 全モジュールを一括処理する（コンテキスト圧迫のリスクあり）

**処理対象モジュール（各 repo）:**
1. **SPO ありモジュール（主）:** `{CR_PATH}/04_specout/{repo}/modules/*/` 以下に SPO ファイルが存在するモジュール
2. **SPO なし・CHD あり モジュール（追加）:** 今回 CHD の変更対象モジュール記述から導出できるモジュールのうち、
   `{XDDP_DIR}/latest-specs/{repo}/` 配下に**既存のモジュールディレクトリが存在する**もの
   - 導出方法（優先順位順）:
     1. CHD に「変更対象モジュール名」として明示されている場合 → その名称を latest-specs の既存ディレクトリ名と照合する
     2. CHD に明示がない場合のみ AI セマンティック照合で対応付ける
        ※ 照合結果が一意に定まらない場合は候補をユーザーに提示して確認を求める（ノンブロッキング・デフォルト=スキップ）
   - SPO 情報がない場合: CRS §4 の SP 差分のみを適用し SPO 由来のセクション更新はスキップ（既存記述を保持）
     バージョン: PATCH 固定（SPO で確認できていないため保守的評価）。`last-verified-cr:` は更新しない。
     ※ SPO ありで MINOR だが SPO なしで同等変更が PATCH になる矛盾は意図的。SPO なし時は「確認不完全」という信号を PATCH で表現している。
   - 既存ディレクトリが存在しない場合（今回 specout 未実施の新規モジュール）は対象外とする

For each repo in AFFECTED_REPOS, for each module in scope:

**`{module-kebab}/spec.md` の生成/更新:**
- モジュール SPO の `## 現状仕様` セクション（`## 2.` または見出し名一致）から取得する
  （「既存仕様の文書化」セクションが存在する場合は含める）
- CHD の SP 差分を適用する:
  CRS §4 SP-xxx アイテムを読み、各 SP 項目の仕様変更内容（Before/After）を把握する
  SP-xxx → latest-specs のファイル・セクションへのマッピングは AI セマンティック判断（SP 項目の対象モジュール・機能名と照合）
- **SP 差分適用後の仕様の合成方針:**
  spec.md は**変更後の最新仕様をダイレクトに記述する**形式とする。
  SPO §2「現状仕様」（変更前の状態）をベースとし、CRS §4 SP 差分の After 部分で該当箇所を更新したものが spec.md の本文となる。
  変更前の仕様は spec.md 本文には残さず、`変更履歴` セクションの「変更内容」列に Before を記録する。
  初回生成（SPO のみ・CHD なし）の場合は SPO §2 のみからベース状態を生成し、バージョンを `1.0.0` とする。
- **関連ドキュメントセクションの生成:**
  state-machine.md が存在する（または今回生成される）場合はリンクを記載する。
  structure.md が存在する（または今回生成される）場合はリンクを記載する。
  sequences/ ディレクトリが存在する（または今回生成される）場合はリンクを記載する。
- テンプレート: `~/.claude/skills/xddp.templates/09_module-spec-template.md`
- フロントマター: `source: spo`（SPO から生成）、`last-verified-cr: {CR}`（SPO 由来）

**`{module-kebab}/structure.md` の生成/更新:**
- モジュール SPO の `### クラス図`・`### データ構造`・`### PAD（問題分析図）` セクション（見出し名一致）から取得する
  ※ PAD は structure.md に含める（独立ファイルは作成しない）
- テンプレート: `~/.claude/skills/xddp.templates/09_module-structure-template.md`
- フロントマター: `source: spo`、`last-verified-cr: {CR}`

**`{module-kebab}/state-machine.md` の生成/更新:**
- モジュール SPO の `### 状態遷移図` セクション（見出し名一致）から取得する
- 「対象外」記載の場合は生成スキップ
- テンプレート: `~/.claude/skills/xddp.templates/09_module-state-machine-template.md`
- フロントマター: `source: spo`、`last-verified-cr: {CR}`

**`{module-kebab}/sequences/{feature}-seq.md` の生成/更新:**
- モジュール SPO の `### モジュール内シーケンス図` サブセクション見出しをケバブ変換して使用する
- 見出しなし・単一の場合は `main-seq.md` をデフォルトとする
- テンプレート: `~/.claude/skills/xddp.templates/09_module-sequence-template.md`

**廃止シーケンスファイル処理（Step MOD）:**
各 `{module-kebab}/sequences/` 内の既存 `{feature}-seq.md` を列挙し、
今回のモジュール SPO `### モジュール内シーケンス図` サブセクション見出し（ケバブ変換後）に対応しないファイルを廃止候補として検出する。
Step OV と同様の並行 CR 保護・廃止確認を実施する。

**既存ファイルの更新判断（Step MOD）:**
各ファイルが既に存在する場合:
1. 機械的先決基準を最初に適用（SPO Mermaid ブロックのノード数/エッジ数変化、テキストセクション行数の 20% 以上変化）→ 即時「更新あり」
2. 機械的基準に該当しない場合のみ AI セマンティック判断を適用:
   SPO の情報が正確に反映済み かつ CRS §4 に対応 SP 差分なし → スキップ（ファイルに手を加えない）
3. SPO 内容の未反映または CRS §4 の SP 差分あり → 版数インクリメント・変更履歴追記を行う
※ CHD が空（変更なし）でも SPO 内容の未反映がある場合（specout 再実行等）は PATCH バージョンアップを行う
※ フォーマット差異のみ（空白・インデント）の場合はスキップ対象とする

**バージョン判定の機械的先決基準（全ファイル共通）:**
以下の基準を先に機械的に判定し、AI セマンティック判断はその結果を上書き**昇格**する方向にのみ使用する（降格しない）。
| 機械的先決条件 | バージョン下限 |
|---|---|
| セクション数が減少している（既存セクションが消えた） | MAJOR |
| セクション数が増加している（新規セクションが追加された） | MINOR |
| 既存セクションの見出し名が変更された | MINOR |
| テキストのみ変更（セクション構造変化なし） | PATCH |
| SPO なし CHD あり 適用 | PATCH 固定（昇格不可） |

**{module-kebab} の導出ルール:**
SPO モジュール調査ファイルのディレクトリ名をケバブケースに変換して使用する。
例: `04_specout/{repo}/modules/auth/` → `auth`、`04_specout/{repo}/modules/AuthService/` → `auth-service`
予約ディレクトリ名の衝突ルール: 導出した {module-kebab} が `overview`・`cross`・`system` のいずれかと一致する場合は
`mod-{module-kebab}`（例: `mod-overview`）に自動変換し progress.md に警告メモを追記する（ノンブロッキング）。

**廃止モジュール処理（Step MOD のモジュールループ完了後）:**
既存の `{XDDP_DIR}/latest-specs/{repo}/` 直下のディレクトリ一覧を取得し、
今回の CR の `{CR_PATH}/04_specout/{repo}/modules/*/` に対応するディレクトリがないものを「廃止候補」として検出する。
除外: `overview/` ディレクトリ（予約名称）、`last-updated-cr:` が現在の CR と異なるディレクトリ（並行 CR 保護）。
廃止候補が存在する場合:
> ⚠️ 以下のモジュールは今回 CR の specout 対象に含まれていません。
> 削除・統合されたモジュールであれば削除してください。
> - latest-specs/{repo}/{module}/
削除を選択した場合はディレクトリごと削除し progress.md に削除記録を追記する。
保持を選択した場合は `spec.md` のフロントマターに `status: unverified（CR-{CR} 時点で specout 未実施）` を追記する。
ケバブ名リネーム手順: 廃止候補提示時に「コンテンツを新ケバブ名ディレクトリにコピーする」オプションも提示する。
コピー選択時: 新ディレクトリに旧ファイルをコピーし、フロントマターの `last-updated-cr:` を現 CR に更新し、
変更履歴に「旧ディレクトリ名 `{旧名}` からリネーム（CR-{CR}）」を記録する。旧ディレクトリを削除する。

---

## Step CROSS: Generate/Update cross specs (IS_MULTI のみ)

**スキップ条件:** IS_MULTI でない、またはHAS_CROSS でない、または分割実行継続マーカーに `CROSS` が含まれる場合はスキップ。

Update progress.md 詳細ステップ → `Step CROSS: クロス仕様生成中`.

Read `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md`.

**`cross/sequences/{flow}-seq.md` の生成/更新:**
クロスリポジトリ SPO §3（シーケンス図）のサブセクション見出しをケバブ変換して使用する。
見出しなし・単一の場合は `main-seq.md` をデフォルトとする。
テンプレート: `~/.claude/skills/xddp.templates/09_cross-sequence-template.md`

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
テンプレート: `~/.claude/skills/xddp.templates/09_cross-interface-spec-template.md`

**`cross/interfaces/{interface-kebab}/schema.md` の生成/更新:**
テンプレート: `~/.claude/skills/xddp.templates/09_cross-interface-schema-template.md`

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

For each batch:

**Agent tool** `subagent_type=xddp-reviewer`:
```
DOCUMENT_TYPE: SPEC
TARGET_FILES: [{batch file paths}]
REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/06_design/{repo}/CHD-{CR}.md]
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

Update `{CR_PATH}/progress.md` step 15 状態 → 👀 レビュー待ち, 詳細ステップ → `Step GATE: 人レビュー待ち`.

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
> ⚠️ **並行 CR がある場合は xddp.09.specs を逐次実行してください**（AI_INDEX.md 競合更新リスクおよび overview 共有ファイルの同時更新リスク）。
>
> 問題なければ「**確認完了**」と入力してください。修正が必要な場合は直接ファイルを編集してください。
> 複数ファイルにまたがる大きな修正を加えた場合は、確認完了の前に `/xddp.review` で
> 単体 AI レビューを実施することを推奨します（`DOCUMENT_TYPE: SPEC` を指定）。

{Step UC で related-modules が空リストのユースケースがある場合}
> ⚠️ 以下のユースケースの `related-modules:` が空リストです。関連モジュールを手動で設定してください:
> {ユースケース名一覧}

Wait for the user to confirm.

---

## Step DONE: Update progress.md, Report

**分割実行継続マーカーの管理:**
分割実行（Step UC 部分完了・Step MOD 分割等）を選択した場合、progress.md §15 に以下を追記する:
```markdown
## 工程15 分割実行メモ
<!-- xddp.09.specs が記録。次回実行時に継続対象を特定するために使用する -->
- 完了済みステップ: {完了したステップ名一覧（例: UC, OV, CROSS）}
- 未処理リポジトリ: {未処理リポジトリ名一覧}  （選択肢 A の場合）
- 処理済みモジュール: {処理済みモジュール名一覧} in {repo}  （選択肢 B の場合）
- 処理済みUR: {処理済みURケバブ名一覧}  （Step UC が部分完了の場合）
- 未処理UR: {未処理URケバブ名一覧}  （Step UC が部分完了の場合）
- 継続実行: `/xddp.09.specs {CR}` を再実行すると未処理分のみ処理します
```
全体完了後にマーカーセクションを削除する。

Step 15 (最新仕様書作成) → ✅ 完了, 詳細ステップ → `-`.
Set "次に実行すべきコマンド" → "このCRは完了です。続いて `/xddp.close {CR}` でCRをクローズしてください。"

**更新ファイル一覧の記録（progress.md §15）:**
新構造では 1モジュール = 複数ファイルになるため、全ファイルパスを列挙する。
`system/use-cases/**/*.md` も必ずこの一覧に含めること
（xddp.close Step C0-3 の保護判定はこのリストに依存しており、記録漏れがあると
C0-3 で `{DOCS}/system/specs/` から旧バージョンファイルが上書きコピーされるリスクがある）。

````markdown
## 工程15 更新仕様書ファイル一覧

<!-- xddp.09.specs が自動記録。xddp.close Step C0-3 で保護対象判定に使用する。 -->

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

**先行更新時の注意（broken リンク許容）:**
先行更新時点では xddp.close Step C2（`{DOCS}` への昇格）が未完了のため、
AI_INDEX.md の全リンク（`{repo}/specs/`・`cross/specs/`・`system/specs/` 配下を含む全セクション）は
xddp.close Step C2 完了まで broken になる。これは意図的に許容する。

Tell the user:
> 工程15が完了しました。続いて CR クローズ処理（気づき集約・知見ログ更新）を実行してください。
> ```
> /xddp.close {CR}
> ```
>
> ⚠️ **知識参照 degraded mode**: xddp.close 未実施のため `{DOCS}` への昇格が未完了です。
> 次の CR の xddp.02.analysis は `latest-specs/` から直接参照しますが、
> AI_INDEX.md の全リンクは機能しません。xddp.close を実施してから次の CR を開始することを推奨します。
>
> 並行 CR が存在する場合は xddp.09.specs を逐次実行してください（AI_INDEX.md の競合更新リスク）。
