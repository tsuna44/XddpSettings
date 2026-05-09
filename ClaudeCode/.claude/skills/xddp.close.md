---
description: XDDP CR クローズ処理: 各工程の気づきをバックログへ集約し、知見ログ（lessons-learned.md）を生成・更新してCRを完了する。「CRをクローズして」「知見をまとめて」などで起動する。
---

You are orchestrating **XDDP Close — CR Closeout & Knowledge Capture**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS. Let `TODAY` = today's date (YYYY-MM-DD).

Find `xddp.config.md` by searching upward from cwd: check cwd first, then each parent directory in order. Let `WORKSPACE_ROOT` = the directory where the file is found. If not found at filesystem root, report "xddp.config.md が見つかりません。ワークスペースルートまたはそのサブディレクトリで実行してください。" and stop.
Extract `XDDP_DIR` (default: `xddp` if the key is absent). Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## Step 0: 前提確認

Read `{CR_PATH}/progress.md`.  
工程15（最新仕様書作成）が ✅ 完了 になっていない場合は、先に `/xddp.09.specs {CR}` を実行するよう案内してから停止する。

## Step A: 気づき・提案メモの収集

以下のファイルを読み、各ファイルの「気づき・提案メモ」セクションの内容をすべて抽出する。

```
対象ファイル（存在するもののみ）:
- {CR_PATH}/01_requirements/ 配下の全 .md
- {CR_PATH}/02_analysis/ANA-{CR}.md
- {CR_PATH}/03_change-requirements/CRS-{CR}.md
- {CR_PATH}/04_specout/SPO-{CR}.md
- {CR_PATH}/05_architecture/DSN-{CR}.md
- {CR_PATH}/06_design/CHD-{CR}.md
- {CR_PATH}/09_test-spec/TSP-{CR}.md
- {CR_PATH}/10_test-results/ 配下の全 TRS-{CR}-*.md
```

抽出した全エントリを「発生源ファイル」と「対応方針」とともに一覧化する。

## Step B: 改善バックログの更新

`{XDDP_DIR}/improvement-backlog.md` を読む。ファイルが存在しない場合は
`~/.claude/templates/10_improvement-backlog-template.md` から新規作成する。

Step A で収集した気づきのうち、対応方針が **今回対応** 以外のもの（次回CR / 保留 / 検討中）を
`IDEA-{NNN}` エントリとして追記する。

- ID は既存エントリの続き番号にする
- カテゴリは内容から判断: `機能改善` `潜在的バグ` `リファクタリング` `技術的負債` `セキュリティ` `パフォーマンス` `テスト強化` `ドキュメント整備`
- 発生源に CR 番号と資料名を記載する
- サマリ表（セクション1）の件数を更新する

## Step C: 知見ログの生成・更新

`{XDDP_DIR}/lessons-learned.md` を読む。ファイルが存在しない場合は
`~/.claude/templates/lessons-learned-template.md` から新規作成する。

Step A で収集した気づき、および今回の CR 全体を通じて得られた教訓を分析し、
**次の CR 以降に活かせる知見** を `LL-{NNN}` エントリとして追記する。

### 知見抽出の観点

以下の問いに答えられる内容を知見として抽出する。なければスキップしてよい。

- **要求分析・仕様定義**（`#要求分析` `#仕様定義`）
  - 要求書では気づかなかったが、分析・設計で発覚した漏れや曖昧さはあったか？
  - ユーザ要求→システム要求→仕様への分解で判断が難しかったポイントは？
- **方式検討・設計**（`#方式検討` `#設計`）
  - 採用した方式で想定外の影響・制約が出たか？
  - 不採用案が後から見て正解だったケースはあったか？
- **実装・テスト**（`#コーディング` `#テスト`）
  - テストで初めて発覚した仕様漏れや設計ミスはあったか？
  - 回帰テストで影響が出たモジュールのパターンはあるか？
- **プロセス**（`#プロセス`）
  - この CR でスムーズだった工程・詰まった工程はどこか？
  - 次回改善すべきプロセス上の判断や手順はあるか？

### エントリ形式

各エントリを以下の形式で `lessons-learned.md` の「知見詳細」セクション末尾に追記する。

```markdown
### LL-{NNN}：{タイトル}

**CR：** {CR番号} ／ **工程：** {工程名} ／ **タグ：** {#タグ1 #タグ2}

**発生状況：**  
{どんな場面・判断でこの知見が生まれたか（1〜2文）}

**学んだこと：**  
{具体的な知見・教訓}

**次回への適用：**  
- {チェックポイント1}
- {チェックポイント2}

---
```

エントリを追加したら「エントリ一覧」テーブルにも1行追記し、`最終更新CR` を {CR} に更新する。

## Step C0: クローズ前同期（並行CR対応）

### 1. ソースコードの同期確認
- `git fetch origin` でリモートの最新状態を取得する
  - **fetch 失敗時**（オフライン・認証エラー・タイムアウト等）:
    「fetch に失敗しました（理由: {エラー内容}）。最後に fetch した時点のリモート情報で判断します。
    続行しますか？ [続行 / 中止]」と表示してユーザーに確認する。「続行」の場合のみ次へ進む。
- `git log HEAD..origin/main --oneline` でリモートに未取得のコミットがあるか確認する
- 未取得コミットがある場合 → ユーザーに `git pull` を促す
  - ユーザーが pull を完了したら次へ進む
  - 「スキップする」と明示した場合のみ next へ進む（後で仕様齟齬が起きる可能性を警告する）

### 2. {DOCS_DIR}/ の同期
`{DOCS}` が git リポジトリか（`.git` の存在）を確認し、以下のいずれかを実行する。

**ケースA: {DOCS_DIR}/ が git 管理されている（推奨運用）**
- `git -C {DOCS} pull` を実行する
- コンフリクトが発生した場合 → 人が解消してから再開するよう案内して停止する

**ケースB: {DOCS_DIR}/ が git 管理されていない・まだ存在しない**
- git pull はスキップする
- 以下を警告として表示する：
  ```
  ⚠️ DOCS_DIR（{DOCS}）は git 管理されていません。
  複数人・複数マシンで並行作業している場合、他のCRによる変更と
  競合しても自動検出できません。
  {DOCS_DIR}/ を git リポジトリとして管理することを推奨します。
  このまま続行しますか？ [続行 / 中止]
  ```
- ユーザーが「続行」を選択した場合のみ次へ進む
- ローカル単独作業であれば Step 3 のベースライン取り込みは引き続き機能する
- **注記（ネットワークドライブ）**: NFS・SMB 等のネットワークドライブ経由で `{DOCS}` を
  マウントしている場合も git 管理なしと同様に扱う。複数マシンから同一パスをマウントしている
  構成では他マシンの変更が自動検出されないため、手動での同期（コピーや rsync 等）が必要。

### 3. latest-specs/ へのベースライン取り込み
- `{DOCS}/{REPO_NAME}/specs/` が存在する場合のみ実行する（存在しない場合はスキップ）
- `{CR_PATH}/progress.md` の「**工程15 更新仕様書ファイル一覧**」セクションを読み、
  箇条書きのパス一覧（`- latest-specs/...` 形式）を取得する（= **保護対象**）。
  - セクションが存在しない（工程15スキップ済み・未実行）→ 保護対象なしとして扱う（全件コピー可）
  - セクションが存在するが内容が空（xddp.09.specs を実行したが更新ファイル0件）→ この手順全体をスキップ（Step C2 で昇格するファイルがないため、事前同期は不要）
- `{DOCS}/{REPO_NAME}/specs/` 配下のファイルを列挙し、保護対象**以外**のファイルを
  `{XDDP_DIR}/latest-specs/` にコピーする（他CRの承認済み変更を latest-specs に取り込む）
- 保護対象ファイルは上書きしない（このCRの作業成果を保護する）
- **git 管理なし・単独作業の場合**: このステップはローカルの {DOCS_DIR}/ を読むだけなので正常に動作する

### 4. specs 再生成の要否（人間が判断）
Step 1 でソースコードに新しいコミットがあった場合、AI は以下を提示してユーザーに判断を求める：

```
ソースコードに N 件の新しいコミットがありました。
変更ファイル: [一覧]
このCRの影響範囲（progress.md 工程15）: [一覧]
重複ファイル: [あり/なし + 一覧]

→ xddp.09.specs の再実行を推奨します。実行しますか？
  [実行する / スキップする]
```

- ユーザーが「実行する」→ `/xddp.09.specs {CR}` を実行してから Step C2 へ進む
- ユーザーが「スキップする」→ 仕様書が最新ソースと乖離する可能性を警告した上で Step C2 へ進む
- **AI は自律的にスキップしない**。必ず人間が判断する
- **セッション断時の再開**: 応答待ち中にセッションが切断された場合は `/xddp.close {CR}` を
  再実行することで Step C0 から再開できる。

## Step C2: 承認済み仕様書の昇格（{XDDP_DIR}/latest-specs/ → DOCS_DIR/{REPO_NAME}/specs/）

`{CR_PATH}/progress.md` の「工程15 更新仕様書ファイル一覧」セクションを確認し、このCRが更新したファイルを把握する（参照目的のみ）。

**昇格対象は `{XDDP_DIR}/latest-specs/` 配下の全ファイル**とする。
Step C0-3 で他CR分の承認済み specs も latest-specs/ に取り込まれているため、全件を昇格することで
baseline_docs を最新状態に保つ。他CR分は baseline_docs に既存のため上書きになるが内容は同一。

**ターゲットパスの決定:**

ヘッダーで発見した `{WORKSPACE_ROOT}/xddp.config.md` から `DOCS_DIR` を読む（デフォルト: `baseline_docs`）。
Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`.
Read `REPO_NAME` from the `xddp.config.md` found earlier. If absent or empty, report error and stop.
Let `SPECS_TARGET` = `{DOCS}/{REPO_NAME}/specs/`.

**昇格処理:**

各ファイルについて `{XDDP_DIR}/latest-specs/{path}` → `{SPECS_TARGET}/{path}` にコピーする。
既存ファイルがある場合は上書きする（バージョン情報はファイル内の変更履歴で管理する）。

その後 `{DOCS}/AI_INDEX.md` を読み込み（存在しない場合は新規作成）、
「リポジトリ別仕様書」テーブルの `{REPO_NAME}` 行を追加・更新する。

| リポジトリ | 承認済み仕様書 | 知見 |
|---|---|---|
| [{REPO_NAME}]({REPO_NAME}/specs/) | v{X.Y}（最終更新CR: {CR}） | [{REPO_NAME}/knowledge/lessons-learned.md]({REPO_NAME}/knowledge/lessons-learned.md) |

## Step C3: 知見ログの昇格（{XDDP_DIR}/lessons-learned.md → DOCS_DIR/{REPO_NAME}/knowledge/）

Step C で更新した `{XDDP_DIR}/lessons-learned.md` の今回追加分（今回 CR の LL エントリ）を
`{DOCS}/{REPO_NAME}/knowledge/lessons-learned.md` に追記する。
既存エントリは上書きせず、末尾に追記のみ行う。

## Step C3.5: project-steering.md への知見反映

`{XDDP_DIR}/project-steering.md` が存在しない場合はスキップし、その旨を記録する。

Step C で今回 CR に追加した LL エントリ（**CR: {CR}** を含むもの）を対象とする。

以下の方針で `project-steering.md` の該当セクションへ追記する。

**セクションマッピング:**

| 対象タグ / 内容 | 追記先 |
|---|---|
| `#方式検討` `#設計` — 採用した設計パターン | Section 3（ADR）または Section 4 |
| `#コーディング` — 実装パターン・慣習 | Section 4（既存パターン・慣習）|
| `#テスト` — テストパターン | Section 4（テストパターン）|
| NG パターン・制約・禁止事項的な内容 | Section 5（禁止事項・注意事項）|
| `#プロセス` `#要求分析` `#仕様定義` | 反映対象外（技術パターンでないため）|

**追記ルール:**
- 同等のパターンがすでに記載されている場合は追記しない（重複チェック）
- 追記形式は既存セクション内の記述スタイルに合わせる（コードブロックまたは箇条書き）
- 各追記の末尾に `（出典: LL-{NNN}, {CR}）` をコメントとして付与する
- コードブロック内への挿入は避け、コードブロックの直下または次のコードブロックとして追記する

Section 7（変更履歴）に 1 行追記する:

```
| {TODAY} | {CR} | LL反映: {追記した LL-NNN 一覧} |
```

LL エントリが 1 件もマッピング対象でない場合（全エントリが `#プロセス` 等）はスキップし、
Section 7 に「反映対象 LL なし」と 1 行追記する。

## Step C4: 設計書の昇格（DSN・CHD → DOCS_DIR/{REPO_NAME}/design/）

ヘッダーで発見した `{WORKSPACE_ROOT}/xddp.config.md` から `DOCS_DIR` を読む（デフォルト: `baseline_docs`）。
Let `DESIGN_TARGET` = `{DOCS}/{REPO_NAME}/design/`.

以下のファイルが存在する場合、`DESIGN_TARGET` へコピーする（既存ファイルは上書き）:
- `{CR_PATH}/05_architecture/DSN-{CR}.md` → `{DESIGN_TARGET}/DSN-{CR}.md`
  （xddp.05.arch の OUTPUT_FILE と一致: `{CR_PATH}/05_architecture/DSN-{CR}.md`）
- `{CR_PATH}/06_design/CHD-{CR}.md` → `{DESIGN_TARGET}/CHD-{CR}.md`
  （xddp.06.design の OUTPUT_FILE と一致: `{CR_PATH}/06_design/CHD-{CR}.md`）

コピー後、`{DOCS}/AI_INDEX.md` の「リポジトリ別設計書・テスト仕様書」テーブルの
`{REPO_NAME}` 行を追加・更新する。「テスト仕様（TSP）」列は既存値を保持し、
行が存在しない場合のみ `—（未昇格）` で初期化する（Step C5 が上書きする）:

| リポジトリ | 設計書（DSN・CHD） | テスト仕様（TSP） |
|---|---|---|
| [{REPO_NAME}]({REPO_NAME}/design/) | DSN・CHD（最終更新CR: {CR}） | —（未昇格） ← 既存値がある場合は保持 |

いずれのファイルも存在しない場合はスキップし、スキップした理由を記録する。

## Step C5: テスト仕様書の昇格（TSP → DOCS_DIR/{REPO_NAME}/test/）

Let `TEST_TARGET` = `{DOCS}/{REPO_NAME}/test/`.

以下のファイルが存在する場合、`TEST_TARGET` へコピーする（既存ファイルは上書き）:
- `{CR_PATH}/09_test-spec/TSP-{CR}.md` → `{TEST_TARGET}/TSP-{CR}.md`

コピー後、`{DOCS}/AI_INDEX.md` の「リポジトリ別設計書・テスト仕様書」テーブルの
`{REPO_NAME}` 行の「テスト仕様（TSP）」列**のみ**を更新する（設計書列は変更しない）:

| リポジトリ | 設計書（DSN・CHD） | テスト仕様（TSP） |
|---|---|---|
| [{REPO_NAME}]({REPO_NAME}/design/) | （既存値を保持） | TSP（最終更新CR: {CR}） |

ファイルが存在しない場合はスキップし、スキップした理由を記録する。
行自体が存在しない場合（Step C4 もスキップされた場合）は行を新規作成し設計書列を `—（未昇格）` とする。

## Step C6: project-steering.md の昇格（{XDDP_DIR}/ → DOCS_DIR/{REPO_NAME}/）

`{XDDP_DIR}/project-steering.md` が存在するか確認する。

存在する場合:
1. `{DOCS}/{REPO_NAME}/project-steering.md` へコピーする（既存ファイルは上書き）。
2. `{DOCS}/AI_INDEX.md` の「共通知識」テーブルに以下の行を追加・更新する
   （すでに同じ行が存在する場合は `最終更新CR` 列のみ更新する）:
   ```
   | [project-steering.md]({REPO_NAME}/project-steering.md) | 命名規約・ADR・コーディングパターン・禁止事項（最終更新CR: {CR}） |
   ```

存在しない場合: スキップし、スキップした旨を記録する。

## Step D: Human Review Gate

Tell the user:
> ✅ クローズ処理が完了しました。内容を確認してください。
>
> **生成・更新した資料：**
> - 改善バックログ: `improvement-backlog.md`（追加 {n} 件）
> - 知見ログ: `lessons-learned.md`（追加 {n} 件）
> - 承認済み仕様書: `{DOCS}/{REPO_NAME}/specs/` に昇格（{n} ファイル）
> - 設計書: `{DOCS}/{REPO_NAME}/design/` に昇格（DSN・CHD）
> - テスト仕様書: `{DOCS}/{REPO_NAME}/test/` に昇格（TSP）
> - project-steering: `{DOCS}/{REPO_NAME}/project-steering.md` に昇格（Step C6 がスキップされた場合はこの行を省略）
>
> **仕様書の昇格内容（{XDDP_DIR}/latest-specs/ → {DOCS}/{REPO_NAME}/specs/）：**
> {昇格したファイル一覧}
>
> **修正が必要な場合：**
> - 直接ファイルを編集してください
>
> 確認が完了したら「**クローズ完了**」と入力してください。

Wait for the user to confirm.

## Step E: CR 完了マーク

Read `{CR_PATH}/progress.md`.  
末尾に以下を追記する：

```
## CR クローズ

- **クローズ日：** {TODAY}
- **改善バックログ追加：** {n} 件
- **知見ログ追加：** {n} 件
- **ステータス：** ✅ 完了・クローズ済み
```

## Step F: Report in Japanese

追加した IDEA エントリ数・LL エントリ数・主な知見タイトルを報告する。

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.close.md` の要約も合わせて更新すること。
