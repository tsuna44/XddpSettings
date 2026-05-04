# PLAN-20260430-DOCS_DIR追加

作成日: 2026-04-30  
ステータス: **実装完了**

---

## 1. 背景・目的

ワークスペース直下の `baseline_docs/` を中央知識ハブとして使う構成が決まった（`docs/knowledge-hierarchy-review.md` 参照）。
各プロジェクトがこのハブのパスを `xddp.config.md` で指定できるよう `DOCS_DIR` 設定キーを追加する。
あわせて `xddp.01.init` 実行時に `DOCS_DIR` 以下の初期ディレクトリ構造を自動生成する。

`DOCS_DIR` に蓄積されたドキュメントは **今後の開発時に AI への入力** にもなる。

**Read side（AI入力）:** 要求分析（`xddp.02.analysis`）・スペックアウト（`xddp.04.specout`）・
実装方式検討（`xddp.05.arch`）・変更設計書作成（`xddp.06.design`）・テスト設計（`xddp.08.test`）の
冒頭で `DOCS_DIR` の蓄積ドキュメントを読み込み、過去の設計判断・テスト戦略との整合チェックや
類似 CR 事例の参照を可能にする。

**Write side（蓄積）:** `xddp.close` 時に以下をすべて DOCS_DIR へ昇格する。
- 最新仕様書（SPEC、`latest-specs/` 由来）
- 実装方式設計書（DSN）・変更設計書（CHD）
- テスト仕様書（TSP）
- 知見ログ（lessons-learned）

これにより、仕様書だけでなく **設計判断・テスト戦略** が次回 CR の AI 入力として循環する。

---

## 2. 変更対象ファイル

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `ClaudeCode/.claude/templates/xddp.config.md` | 修正 | `DOCS_DIR` 設定キーを追加 |
| `ClaudeCode/.claude/skills/xddp.01.init.md` | 修正 | Step 0.5: パス解決をワークスペースルート基準に変更、Step 4.5: DOCS_DIR 初期化を追加 |
| `ClaudeCode/.claude/commands/xddp.01.init.md` | 修正 | Step 5.5 の要約を追記 |
| `ClaudeCode/.claude/skills/xddp.close.md` | 修正 | Step C2: `SPECS_APPROVED_DIR` → `DOCS_DIR` 方式に変更、Step C3: lessons-learned 昇格を追加 |
| `ClaudeCode/.claude/commands/xddp.close.md` | 修正 | Step 5 の説明を DOCS_DIR 方式に更新 |
| `ClaudeCode/.claude/skills/xddp.02.analysis.md` | 修正 | Step 0: DOCS_DIR 知識取り込みを追加 |
| `ClaudeCode/.claude/commands/xddp.02.analysis.md` | 修正 | Step 0 の要約を追記 |
| `ClaudeCode/.claude/skills/xddp.04.specout.md` | 修正 | Step 0: DOCS_DIR ベースライン読み込みを追加 |
| `ClaudeCode/.claude/commands/xddp.04.specout.md` | 修正 | Step 0 の要約を追記 |
| `ClaudeCode/.claude/skills/xddp.05.arch.md` | 修正 | Step 0: 過去 DSN 参照を追加 |
| `ClaudeCode/.claude/commands/xddp.05.arch.md` | 修正 | Step 0 の要約を追記 |
| `ClaudeCode/.claude/skills/xddp.06.design.md` | 修正 | Step 0: 過去 CHD 参照を追加 |
| `ClaudeCode/.claude/commands/xddp.06.design.md` | 修正 | Step 0 の要約を追記 |
| `ClaudeCode/.claude/skills/xddp.08.test.md` | 修正 | Step 0: 過去 TSP 参照を追加 |
| `ClaudeCode/.claude/commands/xddp.08.test.md` | 修正 | Step 0 の要約を追記 |
| `ClaudeCode/.claude/skills/xddp.01.init.md` | 修正（追加）| Step 4.5: `design/`・`test/` サブフォルダと README を追加 |
| `ClaudeCode/.claude/skills/xddp.close.md` | 修正（追加）| Step C4: DSN・CHD 昇格、Step C5: TSP 昇格を追加 |
| `ClaudeCode/.claude/commands/xddp.close.md` | 修正（追加）| Step C4・C5 の要約を追記 |
| `ClaudeCode/.claude/skills/xddp.09.specs.md` | 修正 | Step B: 更新仕様書ファイル一覧を progress.md へ記録する処理を追加 |
| `ClaudeCode/.claude/commands/xddp.09.specs.md` | 修正 | Step B 要約を更新 |
| `ClaudeCode/.claude/templates/00_progress-management-template.md` | 修正 | 「工程15 更新仕様書ファイル一覧」セクションを追加 |
| `ClaudeCode/.claude/CLAUDE.md` | 修正 | `xddp.config.md の位置付け` 節をワークスペースルート配置・`REPO_NAME` 明示設定に更新 |

---

## 3. 変更内容

### 3.1. `ClaudeCode/.claude/templates/xddp.config.md`

「成果物ディレクトリ設定」セクション末尾（最初の `---` の直前）に追加。

**前提: `xddp.config.md` はワークスペースルートに置き、ワークスペースルートから実行する。**
```
workspace/          ← ここで XDDP コマンドを実行
  xddp.config.md   ← このファイル
  xddp/
  baseline_docs/
  repo-A/
  repo-B/
```

**変更前:**
```
XDDP_DIR: xddp

XDDP の成果物（CR フォルダ・latest-specs・project-steering.md 等）を配置するディレクトリ。
リポジトリルートからの相対パスで指定する。デフォルト: `xddp`

# 例: XDDP_DIR: docs/xddp  →  {repo_root}/docs/xddp/ 配下に成果物を集約する

---
```

**変更後:**
```
XDDP_DIR: xddp

XDDP の成果物（CR フォルダ・latest-specs・project-steering.md 等）を配置するディレクトリ。
ワークスペースルートからの相対パスで指定する（xddp.config.md と同じディレクトリが基点）。
デフォルト: `xddp`

# 例: XDDP_DIR: xddp  →  workspace/xddp/
# 例: XDDP_DIR: repo-A/xddp  →  workspace/repo-A/xddp/  リポジトリ内に置く場合

## 知識ハブディレクトリ設定

DOCS_DIR: baseline_docs

承認済み仕様書・知見ログを集約する中央知識ハブのパス。
ワークスペースルートからの相対パスで指定する（xddp.config.md と同じディレクトリが基点）。
デフォルト: `baseline_docs`

# 例: DOCS_DIR: baseline_docs  →  workspace/baseline_docs/
# 例: DOCS_DIR: repo-A/baseline_docs  →  workspace/repo-A/baseline_docs/  リポジトリ内に置く場合

REPO_NAME: repo-A

baseline_docs/ 以下のリポジトリサブディレクトリ名。
workspace/repo-A/ のようにリポジトリが workspace 直下に置かれる場合は、そのフォルダ名を指定する。
MULTI_REPO: true の場合は REPOS: の左辺キー名と一致させること。

# 例: REPO_NAME: repo-A  →  baseline_docs/repo-A/ 以下に仕様書・知見を格納

---
```

---

### 3.2. `ClaudeCode/.claude/skills/xddp.01.init.md`

#### 変更 A: Step 0.5 の説明文を更新（パス解決はそのまま）

`xddp.config.md` がワークスペースルートに置かれ、ワークスペースルートから実行するため、
パス解決は `{cwd}/{value}` のままでよい（`../` は不要）。説明文のみ更新する。

**変更前:**
```
### 0.5. XDDP_DIR の解決

- If exists, read it and extract `XDDP_DIR` (default: `.` if the key is absent …).
- If not exists (first run), use `XDDP_DIR = xddp`.

Let `CR_PATH` = `{XDDP_DIR}/{CR}`.
```

**変更後:**
```
### 0.5. XDDP_DIR の解決

Check if `xddp.config.md` exists in the current working directory.
- If exists, read it and extract `XDDP_DIR` (default: `xddp` if the key is absent).
- If not exists (first run), use `XDDP_DIR = xddp`.

パスは xddp.config.md があるディレクトリ（= ワークスペースルート）からの相対パスとして解決する。
Let `XDDP_ABS` = resolved absolute path of `{cwd}/{XDDP_DIR}`.
Let `CR_PATH`  = `{XDDP_ABS}/{CR}`.
```

#### 変更 B: Step 4.5 を追加（DOCS_DIR 構造作成）

DOCS_DIR の解決は Step 4.5 で行う。Step 4（xddp.config.md 生成）の後ろに配置することで、
テンプレート事前編集 → init 実行という自然なワークフローが成立する（R-001 対処）。

**変更前（挿入位置）:**
```
### 4.5. Create project-steering.md (if not exists)
```

**変更後（追加するブロック — Step 4 と project-steering.md 作成の間に挿入）:**
```
### 4.5. Create DOCS_DIR structure (if not exists)

1. Read `DOCS_DIR` from `xddp.config.md` (just created/confirmed in Step 4).
   Default: `baseline_docs` if the key is absent.
   Let `DOCS` = resolved absolute path of `{cwd}/{DOCS_DIR}`.
2. Read `REPO_NAME` from `xddp.config.md`.
   If absent or empty, show: "xddp.config.md の REPO_NAME を設定してから再実行してください（例: REPO_NAME: repo-A）"
   and skip Step 4.5（DOCS_DIR 初期化をスキップして続行）。
3. If `{DOCS}` does not exist → create the following files and directories:
   - `{DOCS}/AI_INDEX.md` （初期内容: 後述）
   - `{DOCS}/shared/glossary.md` （空）
   - `{DOCS}/shared/lessons-learned.md` （空テーブル: 後述）
   - `{DOCS}/shared/design/notes.md` （空テンプレート）
   - `{DOCS}/shared/design/patterns.md` （空テンプレート）
   - `{DOCS}/shared/test/patterns.md` （空テンプレート）
   - `{DOCS}/shared/test/anti-patterns.md` （空テンプレート）
   - `{DOCS}/shared/inter-repo/repo-map.md` （空テンプレート）
   - `{DOCS}/shared/inter-repo/dependency-graph.md` （空テンプレート）
   - `{DOCS}/shared/inter-repo/design/sequence/` （空フォルダ）
   - `{DOCS}/shared/inter-repo/design/dfd/` （空フォルダ）
   - `{DOCS}/shared/inter-repo/design/architecture/` （空フォルダ）
   - `{DOCS}/shared/inter-repo/design/interface/` （空フォルダ）
   - `{DOCS}/{REPO_NAME}/specs/README.md` （初期内容: 後述）
   - `{DOCS}/{REPO_NAME}/knowledge/lessons-learned.md` （空テーブル）
   - `{DOCS}/{REPO_NAME}/design/README.md` （初期内容: 後述）
   - `{DOCS}/{REPO_NAME}/test/README.md` （初期内容: 後述）
4. If `{DOCS}` exists but `{DOCS}/{REPO_NAME}/` does not → create only:
   - `{DOCS}/{REPO_NAME}/specs/README.md`
   - `{DOCS}/{REPO_NAME}/knowledge/lessons-learned.md`
   - `{DOCS}/{REPO_NAME}/design/README.md`
   - `{DOCS}/{REPO_NAME}/test/README.md`
5. If both exist → skip.

**初期ファイル内容:**

`{DOCS}/AI_INDEX.md`:
```markdown
# AI向けナビゲーションインデックス
> 新規開発開始時に clone してこのファイルを AI に注入してください。

## 共通知識
| ファイル | 内容 |
|---|---|
| [shared/glossary.md](shared/glossary.md) | 全リポジトリ共通用語集 |
| [shared/lessons-learned.md](shared/lessons-learned.md) | 横断的な知見・教訓 |

## リポジトリ別仕様書
| リポジトリ | 承認済み仕様書 | 知見 |
|---|---|---|
| （xddp.close 実行後に自動追記） | — | — |

## リポジトリ別設計書・テスト仕様書
| リポジトリ | 設計書（DSN・CHD） | テスト仕様（TSP） |
|---|---|---|
| （xddp.close 実行後に自動追記） | — | — |
```

`{DOCS}/{REPO_NAME}/specs/README.md`:
```markdown
# 承認済み仕様書: {REPO_NAME}
xddp.close で latest-specs/ から昇格した承認済みの最新仕様書を格納します。
ドラフト（未レビュー）は各リポジトリの latest-specs/ にあります。
```

`{DOCS}/{REPO_NAME}/design/README.md`:
```markdown
# 設計書アーカイブ: {REPO_NAME}
xddp.close で各 CR の DSN（実装方式設計書）と CHD（変更設計書）を格納します。
ファイル命名規則: DSN-{CR}.md / CHD-{CR}.md
AI が過去の設計判断を参照する際のインデックスとして使用されます。
```

`{DOCS}/{REPO_NAME}/test/README.md`:
```markdown
# テスト仕様書アーカイブ: {REPO_NAME}
xddp.close で各 CR の TSP（テスト仕様書）を格納します。
ファイル命名規則: TSP-{CR}.md
AI が過去のテスト戦略・テストパターンを参照する際のインデックスとして使用されます。
```

`{DOCS}/shared/lessons-learned.md` （横断共通用）:
```markdown
# 知見ログ: 横断（全リポジトリ共通）
> xddp.close が CR クローズ時に自動追記します。

## エントリ一覧
| ID | タイトル | タグ | CR | リポジトリ | 日付 |
|---|---|---|---|---|---|
| （xddp.close 実行後に追記） | — | — | — | — | — |
```

`{DOCS}/{REPO_NAME}/knowledge/lessons-learned.md` （リポジトリ別用）:
```markdown
# 知見ログ: {REPO_NAME}
> xddp.close が CR クローズ時に自動追記します。

## エントリ一覧
| ID | タイトル | タグ | CR | 日付 |
|---|---|---|---|---|
| （xddp.close 実行後に追記） | — | — | — | — |
```
```

---

### 3.3. `ClaudeCode/.claude/commands/xddp.01.init.md`

Step 5（xddp.config.md コピー）の次に挿入する（Step 4 の後ではなく Step 5 の後）。

**変更前:**
```
4. Create `latest-specs/` with a README if not already present.
5. Copy `~/.claude/templates/xddp.config.md` to `./xddp.config.md` if not already present.
6. Copy `~/.claude/templates/project-steering-template.md` to `{XDDP_DIR}/project-steering.md` if not already present.
```

**変更後:**
```
4. Create `latest-specs/` with a README if not already present.
5. Copy `~/.claude/templates/xddp.config.md` to `./xddp.config.md` if not already present.
5.5. Read `DOCS_DIR` from `xddp.config.md`（デフォルト `baseline_docs`）。未存在なら
     `AI_INDEX.md` / `shared/` / `{repo_name}/specs/` / `{repo_name}/knowledge/` /
     `{repo_name}/design/` / `{repo_name}/test/` を作成。
     既存で `{repo_name}/` のみ未作成の場合はリポジトリサブフォルダのみ追加。
6. Copy `~/.claude/templates/project-steering-template.md` to `{XDDP_DIR}/project-steering.md` if not already present.
```

---

### 3.4. `ClaudeCode/.claude/skills/xddp.close.md`

Step C2 の前に Step C0（クローズ前同期）を新規追加し、Step C2 を DOCS_DIR 方式に置き換え、Step C3（lessons-learned 昇格）を新規追加する。

**変更前（Step C2 全体）:**
```
## Step C2: 承認済み仕様書の昇格（{XDDP_DIR}/latest-specs/ → docs/specs/）

Read `{CR_PATH}/progress.md` を確認し、工程15で更新・生成されたすべての `{XDDP_DIR}/latest-specs/` ファイルのリストを把握する。

**ターゲットパスの決定:**

`xddp.config.md`（プロジェクトルート）に `SPECS_APPROVED_DIR` が定義されている場合はその値を使う。
未定義の場合は `docs/specs/` をデフォルトとする。

**昇格処理:**

各ファイルについて `{XDDP_DIR}/latest-specs/{path}` → `{SPECS_APPROVED_DIR}/{path}` にコピーする。
既存ファイルがある場合は上書きする（バージョン情報はファイル内の変更履歴で管理する）。

その後 `{SPECS_APPROVED_DIR}/AI_INDEX.md` を読み込み（存在しない場合は新規作成）、
今回昇格したファイルのエントリを追加・更新する。

| ファイル | バージョン | 最終更新CR | 内容 |
|---|---|---|---|
| [specs/{module}-spec.md](specs/{module}-spec.md) | v{X.Y} | {CR} | {モジュール説明} |
```

**変更後（新規 Step C0 + Step C2 + 新規 Step C3）:**
```
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

`xddp.config.md` から `DOCS_DIR` を読む（デフォルト: `baseline_docs`、ワークスペースルート相対）。
Let `DOCS` = resolved absolute path of DOCS_DIR.
Read `REPO_NAME` from `xddp.config.md`. If absent or empty, report error and stop.
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
```

---

### 3.5. `ClaudeCode/.claude/commands/xddp.close.md`

**変更前:**
```
5. 承認済み仕様書の昇格: `latest-specs/` → `docs/specs/`（または `xddp.config.md` の `SPECS_APPROVED_DIR`）にコピーし、`docs/specs/AI_INDEX.md` を更新する。
```

**変更後:**
```
0.5. クローズ前同期（Step C0）:
     (1) ソースコードの未取得コミット確認 → あれば git pull を促す
     (2) {DOCS_DIR}/ の git pull
     (3) docs/{repo}/specs/ → latest-specs/ へ他CR分をベースライン取り込み
         （このCR変更ファイルは保護）
     (4) ソース変更があった場合は /xddp.09.specs {CR} の再実行を推奨
5. 承認済み仕様書の昇格（Step C2）: `latest-specs/` → `{DOCS_DIR}/{REPO_NAME}/specs/` にコピーし、`{DOCS_DIR}/AI_INDEX.md` のリポジトリ行を更新する。
5.5. 知見ログの昇格（Step C3）: 今回 CR の LL エントリを `{DOCS_DIR}/{REPO_NAME}/knowledge/lessons-learned.md` に追記する。
```

---

### 3.6. `ClaudeCode/.claude/skills/xddp.02.analysis.md`

現在の冒頭（Step 1 または入力確認ステップ）の**直前**に挿入する。

**変更前（挿入位置の目印）:**
```
## Step 1:
```
（実際のスキルファイル先頭の最初のステップに対応）

**変更後（追加するブロック）:**
```
## Step 0: DOCS_DIR 知識取り込み

> **既存 Step A0 との役割分担:**
> - Step 0（本ステップ）: `baseline_docs/` から**クローズ済み CR の承認済み知見**を取り込む。
>   承認済み仕様書・過去の確定した教訓・用語集が対象。
> - Step A0（既存）: `{XDDP_DIR}/lessons-learned.md` から**現ワークスペースで進行中の知見**を取り込む。
>   `#要求分析` `#仕様定義` `#見落とし` タグに絞り、analyst-agent の `LESSONS_CONTEXT` に渡す。
> 両ステップは読み元が異なり（確定済み vs 進行中）、役割は重複しない。

1. `xddp.config.md` から `DOCS_DIR` を読む（デフォルト: `baseline_docs`、ワークスペースルート相対）。
   Let `DOCS` = resolved absolute path of `DOCS_DIR`.
   Read `REPO_NAME` from `xddp.config.md`. If absent or empty, report error and stop.

2. 以下のファイルが存在すれば読み込み、分析コンテキストとして保持する（存在しなければスキップ）:
   - `{DOCS}/shared/glossary.md` — プロジェクト横断の用語集
   - `{DOCS}/shared/lessons-learned.md` — 横断的な知見・教訓（クローズ済み CR 由来）
   - `{DOCS}/{REPO_NAME}/specs/` 配下のすべての `.md` ファイル — 承認済み仕様書（最新版）
   - `{DOCS}/{REPO_NAME}/knowledge/lessons-learned.md` — リポジトリ固有の知見（クローズ済み CR 由来）

3. 読み込んだ知識を以下の目的に使用する:
   - 用語の統一（要求書に現れる概念が既存仕様書の用語と一致しているか確認）
   - 類似 CR 事例の参照（過去の lessons-learned から類似パターン・注意点を抽出）
   - 既存仕様との整合チェック（今回の要求が既承認仕様と矛盾していないか確認）

4. 取り込んだ知識の概要（使用したファイル一覧と、見つかった関連情報の要約）を
   ANA ドキュメントの「参照した既存ドキュメント」節に記録する。
   DOCS_DIR が存在しない場合や対象ファイルがゼロの場合は「参照なし（初回 CR）」と記録する。
```

---

### 3.7. `ClaudeCode/.claude/commands/xddp.02.analysis.md`

ステップ一覧の先頭に追記する。

**変更前（挿入位置）:**
```
1. （現在の最初のステップ）
```

**変更後（追加する行）:**
```
0. DOCS_DIR 知識取り込み: `{DOCS_DIR}/shared/glossary.md`・`lessons-learned.md`・
   `{REPO_NAME}/specs/` を読み込み、用語統一・類似 CR 参照・既存仕様整合チェックに使用する。
   使用ファイルと関連情報の要約を ANA の「参照した既存ドキュメント」節に記録する。
```

---

### 3.8. `ClaudeCode/.claude/skills/xddp.04.specout.md`

現在の冒頭（Step 1 または入力確認ステップ）の**直前**に挿入する。

**変更前（挿入位置の目印）:**
```
## Step 1:
```
（実際のスキルファイル先頭の最初のステップに対応）

**変更後（追加するブロック）:**
```
## Step 0: DOCS_DIR ベースライン参照（読み取り専用）

1. `xddp.config.md` から `DOCS_DIR` を読む（デフォルト: `baseline_docs`、ワークスペースルート相対）。
   Let `DOCS` = resolved absolute path of `DOCS_DIR`.
   Read `REPO_NAME` from `xddp.config.md`. If absent or empty, report error and stop.

2. `{DOCS}/{REPO_NAME}/specs/` が存在する場合:
   a. 配下のすべての `.md` ファイルを読み込み、母体調査のコンテキストとして保持する。
   b. 読み込んだファイル数と一覧を SPO の「参照したベースライン仕様書」節に記録する。

3. `{DOCS}/{REPO_NAME}/specs/` が存在しない場合:
   - スキップし、「ベースラインなし（初回 CR）」として SPO に記録する。

4. 読み込んだベースラインは、波及調査（Step 1 以降）における
   「変更前の既存仕様」として活用する。
   ファイルの書き込みはしない（latest-specs/ への書き込みは xddp.09.specs が担う）。
```

---

### 3.9. `ClaudeCode/.claude/commands/xddp.04.specout.md`

ステップ一覧の先頭に追記する。

**変更前（挿入位置）:**
```
1. （現在の最初のステップ）
```

**変更後（追加する行）:**
```
0. DOCS_DIR ベースライン参照（読み取り専用）: `{DOCS_DIR}/{REPO_NAME}/specs/` が存在すれば
   配下のファイルを読み込み、母体調査のコンテキストとして保持する（latest-specs/ への書き込みは行わない）。
   読み込んだファイル一覧を SPO の「参照したベースライン仕様書」節に記録する。
```

---

### 3.10. `ClaudeCode/.claude/skills/xddp.close.md` — Step C4・C5 追加

Step C3（lessons-learned 昇格）の直後に挿入する。

**追加するブロック:**
```
## Step C4: 設計書の昇格（DSN・CHD → DOCS_DIR/{REPO_NAME}/design/）

`xddp.config.md` から `DOCS_DIR` を読む（デフォルト: `baseline_docs`）。
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
```

---

### 3.11. `ClaudeCode/.claude/commands/xddp.close.md` — Step C4・C5 要約追記

Step C3 の次に追記する。

**変更前:**
```
5.5. 知見ログの昇格（Step C3）: 今回 CR の LL エントリを `{DOCS_DIR}/{REPO_NAME}/knowledge/lessons-learned.md` に追記する。
```

**変更後（Step C4・C5 を追加）:**
```
5.5. 知見ログの昇格（Step C3）: 今回 CR の LL エントリを `{DOCS_DIR}/{REPO_NAME}/knowledge/lessons-learned.md` に追記する。
6. 設計書の昇格（Step C4）: DSN・CHD を `{DOCS_DIR}/{REPO_NAME}/design/` にコピーし、`AI_INDEX.md` の設計書テーブルを更新する。
6.5. テスト仕様書の昇格（Step C5）: TSP を `{DOCS_DIR}/{REPO_NAME}/test/` にコピーし、`AI_INDEX.md` のテスト仕様列を更新する。
```

---

### 3.12. `ClaudeCode/.claude/skills/xddp.05.arch.md` — Step 0 追加

現在のスキルの最初のステップ直前に挿入する。

**追加するブロック:**
```
## Step 0: DOCS_DIR 過去 DSN 参照

1. `xddp.config.md` から `DOCS_DIR` を読む（デフォルト: `baseline_docs`）。
   Read `REPO_NAME` from `xddp.config.md`. If absent or empty, report error and stop.
   Let `DESIGN_DIR` = `{DOCS}/{REPO_NAME}/design/`.

2. `{DESIGN_DIR}` が存在しない場合 → スキップし「参照なし（初回 CR）」と記録する。

3. `{DESIGN_DIR}` が存在する場合:
   a. `{DOCS}/AI_INDEX.md` を読み、`{REPO_NAME}` の設計書一覧（DSN-*.md）を把握する。
   b. CRS（`{CR_PATH}/03_change-requirements/CRS-{CR}.md`）が存在する場合、
      変更対象モジュール・コンポーネントを抽出し、関連する過去 DSN を優先する。
   c. 最新 3 件（または CRS 関連のもの）を上限として DSN ファイルを読み込む。
   d. `{DOCS}/shared/design/patterns.md` が存在すれば読み込む。

4. 読み込んだ内容を以下の目的に活用する:
   - 過去の実装方式選択とその理由を把握し、今回の方式決定に活用する
   - 既存アーキテクチャパターンとの整合性を確認する
   - 過去に却下された方式案があれば参照し、同じ検討の重複を避ける

5. DSN ドキュメントの「参照した過去設計書」節に、読み込んだファイル名と
   抽出した関連知見の要約を記録する。
```

---

### 3.13. `ClaudeCode/.claude/commands/xddp.05.arch.md` — Step 0 要約追記

ステップ一覧の先頭に追記する。

**変更前（挿入位置）:**
```
1. （現在の最初のステップ）
```

**変更後（追加する行）:**
```
0. DOCS_DIR 過去 DSN 参照: `{DOCS_DIR}/{REPO_NAME}/design/DSN-*.md` から CRS 関連の
   過去実装方式設計書（最新 3 件上限）を読み込み、方式選択の根拠・却下案を参照する。
   DSN の「参照した過去設計書」節に読み込んだファイルと知見要約を記録する。
```

---

### 3.14. `ClaudeCode/.claude/skills/xddp.06.design.md` — Step 0 追加

現在のスキルの最初のステップ直前に挿入する。

**追加するブロック:**
```
## Step 0: DOCS_DIR 過去 CHD 参照

1. `xddp.config.md` から `DOCS_DIR` を読む（デフォルト: `baseline_docs`）。
   Read `REPO_NAME` from `xddp.config.md`. If absent or empty, report error and stop.
   Let `DESIGN_DIR` = `{DOCS}/{REPO_NAME}/design/`.

2. `{DESIGN_DIR}` が存在しない場合 → スキップし「参照なし（初回 CR）」と記録する。

3. `{DESIGN_DIR}` が存在する場合:
   a. `{DOCS}/AI_INDEX.md` を読み、`{REPO_NAME}` の設計書一覧（CHD-*.md）を把握する。
   b. DSN（`{CR_PATH}/05_architecture/DSN-{CR}.md`）が存在する場合、
      変更対象ファイル・クラス・関数を抽出し、同一コンポーネントを変更した過去 CHD を優先する。
   c. 最新 3 件（または DSN 関連のもの）を上限として CHD ファイルを読み込む。

4. 読み込んだ内容を以下の目的に活用する:
   - 同一コンポーネントの過去変更パターン（Before/After の書き方・粒度）を参考にする
   - 過去の設計書で使われた命名規則・コメントスタイルを踏襲する
   - 同一箇所を複数回変更している場合の累積的な影響を把握する

5. CHD ドキュメントの「参照した過去設計書」節に、読み込んだファイル名と
   抽出した関連パターンの要約を記録する。
```

---

### 3.15. `ClaudeCode/.claude/commands/xddp.06.design.md` — Step 0 要約追記

ステップ一覧の先頭に追記する。

**変更前（挿入位置）:**
```
1. （現在の最初のステップ）
```

**変更後（追加する行）:**
```
0. DOCS_DIR 過去 CHD 参照: `{DOCS_DIR}/{REPO_NAME}/design/CHD-*.md` から DSN 関連の
   過去変更設計書（最新 3 件上限）を読み込み、同一コンポーネントの変更パターンを参照する。
   CHD の「参照した過去設計書」節に読み込んだファイルと知見要約を記録する。
```

---

### 3.16. `ClaudeCode/.claude/skills/xddp.08.test.md` — Step 0 追加

現在のスキルの最初のステップ直前に挿入する。

**追加するブロック:**
```
## Step 0: DOCS_DIR 過去 TSP 参照

1. `xddp.config.md` から `DOCS_DIR` を読む（デフォルト: `baseline_docs`）。
   Read `REPO_NAME` from `xddp.config.md`. If absent or empty, report error and stop.
   Let `TEST_DIR` = `{DOCS}/{REPO_NAME}/test/`.

2. `{TEST_DIR}` が存在しない場合 → スキップし「参照なし（初回 CR）」と記録する。

3. `{TEST_DIR}` が存在する場合:
   a. `{DOCS}/AI_INDEX.md` を読み、`{REPO_NAME}` のテスト仕様一覧（TSP-*.md）を把握する。
   b. CHD（`{CR_PATH}/06_design/CHD-{CR}.md`）が存在する場合、
      変更対象コンポーネント・関数を抽出し、同一コンポーネントをテストした過去 TSP を優先する。
   c. 最新 3 件（または CHD 関連のもの）を上限として TSP ファイルを読み込む。
   d. `{DOCS}/shared/test/patterns.md` と `{DOCS}/shared/test/anti-patterns.md` が
      存在すれば読み込む。

4. 読み込んだ内容を以下の目的に活用する:
   - 過去の同一コンポーネントテストで使われたテストケース構造・命名規則を参考にする
   - 過去に発見されたバグパターンを参照し、回帰テストケースの充実度を上げる
   - anti-patterns（過去に失敗したテスト設計）を参照し、同じ失敗を避ける

5. TSP ドキュメントの「参照した過去テスト仕様」節に、読み込んだファイル名と
   抽出したパターン・anti-pattern の要約を記録する。
```

---

### 3.17. `ClaudeCode/.claude/commands/xddp.08.test.md` — Step 0 要約追記

ステップ一覧の先頭に追記する。

**変更前（挿入位置）:**
```
1. （現在の最初のステップ）
```

**変更後（追加する行）:**
```
0. DOCS_DIR 過去 TSP 参照: `{DOCS_DIR}/{REPO_NAME}/test/TSP-*.md` から CHD 関連の
   過去テスト仕様書（最新 3 件上限）と共通 test パターン・anti-pattern を読み込む。
   TSP の「参照した過去テスト仕様」節に読み込んだファイルと知見要約を記録する。
```

---

### 3.18. `ClaudeCode/.claude/skills/xddp.09.specs.md` — Step B に更新ファイル記録を追加（R-003 対処）

Step B（完了処理）に、更新した仕様書のパス一覧を `progress.md` へ書き込む処理を追加する。

**変更前（Step B 全体）:**
```
## Step B: Update progress.md
Step 15 (最新仕様書作成) → ✅ 完了, 詳細ステップ → `-`.
Set "次に実行すべきコマンド" → "このCRは完了です。次のCRは `/xddp.01.init {次のCR番号}` で開始してください。"
```

**変更後（Step B に追記）:**
```
## Step B: Update progress.md
Step 15 (最新仕様書作成) → ✅ 完了, 詳細ステップ → `-`.
Set "次に実行すべきコマンド" → "このCRは完了です。次のCRは `/xddp.01.init {次のCR番号}` で開始してください。"

Step A で作成・更新したすべてのファイルパス（`{XDDP_DIR}/latest-specs/` からの相対パス）を
`{CR_PATH}/progress.md` の「工程15 更新仕様書ファイル一覧」セクションに書き込む:

```
## 工程15 更新仕様書ファイル一覧

<!-- xddp.09.specs が自動記録。xddp.close Step C0-3 で保護対象判定に使用する。 -->

- latest-specs/auth/login-spec.md
- latest-specs/auth/signup-spec.md
```

（セクションが既存の場合は上書きする）
```

---

### 3.19. `ClaudeCode/.claude/commands/xddp.09.specs.md` — Step B 要約更新（R-003 対処）

**変更前（Step B に関する要約の箇所）:**
```
5. Update progress.md: step 15 → ✅ 完了.
```

**変更後:**
```
5. Update progress.md: step 15 → ✅ 完了。更新した仕様書ファイル一覧を
   「工程15 更新仕様書ファイル一覧」セクションに記録する（xddp.close Step C0-3 の保護対象判定に使用）。
```

---

### 3.20. `ClaudeCode/.claude/templates/00_progress-management-template.md` — 工程15 更新仕様書ファイル一覧セクション追加（R-003 対処）

「次に実行すべきコマンド」セクションの直前（最後の `---` の前）に追加する。

**変更前（末尾付近）:**
```
---

## 次に実行すべきコマンド
```

**変更後（セクション追加）:**
```
---

## 工程15 更新仕様書ファイル一覧

<!-- xddp.09.specs が自動記録。xddp.close Step C0-3 で保護対象判定に使用する。-->
<!-- 工程15を実施しない場合は空のままにする。 -->

---

## 次に実行すべきコマンド
```

---

## 4. 影響範囲

- 影響するスキル・コマンド: `xddp.01.init`、`xddp.close`、`xddp.02.analysis`、`xddp.04.specout`、`xddp.05.arch`、`xddp.06.design`、`xddp.08.test`、`xddp.09.specs`
- 影響するテンプレート: `00_progress-management-template.md`（工程15 更新仕様書ファイル一覧セクション追加）
- 影響する工程: 工程1（init）・2（analysis）・4（specout）・6（arch）・7（design）・11〜12（test）・15（最新仕様書作成）・CRクローズ
- 破壊的変更（運用変更）:
  - **`xddp.config.md` の配置場所が変わる**: これまでは `repo-A/` 直下に置いていたが、Case A ではワークスペースルート（`repo-A/` の親）に置く。マルチリポジトリ構成でも1つの `xddp.config.md` で管理できる
  - 既存プロジェクトで `repo-A/xddp.config.md` を使っていた場合は、`workspace/xddp.config.md` に移動し、`XDDP_DIR: xddp` を `XDDP_DIR: repo-A/xddp` に変更する
  - `xddp.close` の `SPECS_APPROVED_DIR` キーは廃止し `DOCS_DIR` に統一する（XddpSettings は運用開始前のため既存ユーザーへの移行対応は不要）
- CLAUDE.md の更新が必要: `xddp.config.md の位置付け` 節を「ワークスペースルートに配置」に修正
- 後方互換性:
  - `DOCS_DIR` 未設定時は `baseline_docs` をデフォルトとする
  - `XDDP_DIR` 未設定時は `xddp` をデフォルトとする（変更なし）
- {DOCS_DIR}/ の git 管理状態による動作差異:
  - git 管理あり: Step C0-2 で pull、並行CR間の競合を自動検出できる（推奨）
  - git 管理なし: Step C0-2 をスキップ、警告を表示して続行確認。ローカル単独作業なら Step C0-3 は正常動作。複数人・複数マシンの並行作業は手動調整が必要
- マルチリポジトリ CR（MULTI_REPO: true）との関係:
  - 1つの CR で repo-A と repo-B を同時に変更する場合、`xddp.close` のStep C2〜C5 は `REPOS:` に列挙された各リポジトリについて繰り返す必要がある
  - **本プランのスコープ外**: MULTI_REPO 時の DOCS_DIR 昇格（repo-A/design/ と repo-B/design/ に分けて格納）は別タスクで設計する。本プランはシングルリポジトリ運用（または MULTI_REPO でも1つのメインリポジトリの成果物昇格）のみを対象とする
  - REPO_NAME は `xddp.config.md` に明示設定する（`basename(cwd)` は使わない）。ワークスペース直下のリポジトリフォルダ名（例: `repo-A`）を指定する。未設定の場合はエラーで停止（`xddp.01.init` のみスキップして続行）

---

## 5. 確認項目

- [ ] スキル・コマンドの同期（xddp.01.init・xddp.close・xddp.02.analysis・xddp.04.specout・xddp.05.arch・xddp.06.design・xddp.08.test・xddp.09.specs ともに commands も更新済み）
- [ ] `sample-project` で `xddp.01.init` を実行し以下が生成されることを確認
  - `baseline_docs/AI_INDEX.md`（「リポジトリ別設計書・テスト仕様書」テーブルを含む）
  - `baseline_docs/shared/`
  - `baseline_docs/{repo_name}/specs/`
  - `baseline_docs/{repo_name}/knowledge/`
  - `baseline_docs/{repo_name}/design/README.md`
  - `baseline_docs/{repo_name}/test/README.md`
- [ ] 2回目の実行で重複作成されないことを確認
- [ ] `DOCS_DIR: baseline_docs`（デフォルト）で `./baseline_docs/` ディレクトリが生成されることを確認
- [ ] `sample-project` で `xddp.close` を実行し以下が確認できる
  - Step C0: リモートの未取得コミット有無が検出・報告される
  - Step C0: {DOCS_DIR}/ の git pull が実行される
  - Step C0: 他CRの承認済み specs が latest-specs/ に取り込まれる（progress.md「工程15 更新仕様書ファイル一覧」に記載のファイルは保護される）
  - Step C0: ソース変更がある場合に xddp.09.specs 再実行の推奨が表示される
  - Step C2: `baseline_docs/{repo_name}/specs/` に latest-specs の変更ファイルがコピーされる
  - Step C2: `baseline_docs/AI_INDEX.md` のリポジトリ行が追加・更新される
  - Step C3: `baseline_docs/{repo_name}/knowledge/lessons-learned.md` に LL エントリが追記される
  - Step C4: `baseline_docs/{repo_name}/design/DSN-{CR}.md` にコピーされる
  - Step C4: `baseline_docs/{repo_name}/design/CHD-{CR}.md` にコピーされる
  - Step C4: `baseline_docs/AI_INDEX.md` の設計書テーブルが更新される
  - Step C5: `baseline_docs/{repo_name}/test/TSP-{CR}.md` にコピーされる
  - Step C5: `baseline_docs/AI_INDEX.md` のテスト仕様列が更新される
  - Step C4・C5: 対象ファイルが存在しない場合はスキップされ理由が記録される
  - Step C4: ソースパスが `xddp.05.arch`（`05_architecture/DSN-{CR}.md`）・`xddp.06.design`（`06_design/CHD-{CR}.md`）の OUTPUT_FILE と一致することをスキルファイルで確認済み
  - Step C5: ソースパスが `xddp.08.test`（`09_test-spec/TSP-{CR}.md`）の OUTPUT_FILE と一致することをスキルファイルで確認済み
- [ ] `sample-project` で `xddp.02.analysis` を実行し以下が確認できる
  - Step 0: `baseline_docs/{repo_name}/specs/` が存在する場合に読み込まれる
  - Step 0: 用語・lessons-learned の参照結果が ANA の「参照した既存ドキュメント」節に記録される
  - Step 0: `DOCS_DIR` が存在しない場合は「参照なし（初回 CR）」と記録されてスキップされる
- [ ] `sample-project` で `xddp.04.specout` を実行し以下が確認できる
  - Step 0: `baseline_docs/{repo_name}/specs/` が存在する場合にファイルが読み込まれる（latest-specs/ への書き込みは行われない）
  - Step 0: 読み込んだファイル一覧が SPO の「参照したベースライン仕様書」節に記録される
  - Step 0: `DOCS_DIR` が存在しない場合は「ベースラインなし（初回 CR）」として記録されスキップされる
- [ ] `sample-project` で `xddp.05.arch` を実行し以下が確認できる
  - Step 0: `baseline_docs/{repo_name}/design/DSN-*.md` が存在する場合に最新 3 件を読み込む
  - Step 0: CRS の変更対象モジュールに関連する DSN が優先される
  - Step 0: 読み込んだファイル名と知見要約が DSN の「参照した過去設計書」節に記録される
  - Step 0: `DOCS_DIR` が存在しない場合は「参照なし（初回 CR）」として記録されスキップされる
- [ ] `sample-project` で `xddp.06.design` を実行し以下が確認できる
  - Step 0: `baseline_docs/{repo_name}/design/CHD-*.md` が存在する場合に最新 3 件を読み込む
  - Step 0: DSN の変更対象ファイルに関連する CHD が優先される
  - Step 0: 読み込んだファイル名と知見要約が CHD の「参照した過去設計書」節に記録される
  - Step 0: `DOCS_DIR` が存在しない場合は「参照なし（初回 CR）」として記録されスキップされる
- [ ] `sample-project` で `xddp.08.test` を実行し以下が確認できる
  - Step 0: `baseline_docs/{repo_name}/test/TSP-*.md` が存在する場合に最新 3 件を読み込む
  - Step 0: CHD の変更対象コンポーネントに関連する TSP が優先される
  - Step 0: `shared/test/patterns.md` と `anti-patterns.md` が存在する場合に読み込まれる
  - Step 0: 読み込んだファイル名と知見要約が TSP の「参照した過去テスト仕様」節に記録される
  - Step 0: `DOCS_DIR` が存在しない場合は「参照なし（初回 CR）」として記録されスキップされる
- [ ] `sample-project` で `xddp.09.specs` を実行し以下が確認できる
  - Step B 完了後、`{CR_PATH}/progress.md` に「工程15 更新仕様書ファイル一覧」セクションが生成される
  - セクションの箇条書きに Step A で作成・更新したファイルパスが列挙される
  - 既にセクションが存在する場合は上書きされる
- [ ] `xddp.09.specs` → `xddp.close` の連続実行で Step C0-3 の保護が正しく動作する
  - `progress.md` の「工程15 更新仕様書ファイル一覧」に記載のファイルは baseline_docs から上書きされない
  - 記載外のファイルは baseline_docs から latest-specs/ に取り込まれる
  - 工程15 未実施（セクションが空）の場合は全件コピー可として動作する
- [ ] `baseline_docs/AI_INDEX.md` を Claude Code に注入し、過去の specs・設計書が参照されることを確認する（手動テスト）
- [ ] CLAUDE.md の `xddp.config.md の位置付け` 節と整合している

---

## 6. データフロー図（全成果物の蓄積・活用）

XDDP プロセス全体における知識の Read/Write フローを示す。実装の完全性確認に使用する。

> **注記（D1 の書き込み元）:** D1（CR成果物: ANA/CRS/SPO/DSN/CHD/TSP/TSR）は
> 各 XDDP スキル（xddp.02〜xddp.09）が `{XDDP_DIR}/{CR}/` 配下に生成するファイル群。
> このフローはスキル実行後の **知識蓄積（Write side）と AI 入力（Read side）** のみを表す。
> 各スキルが D1 を生成する処理自体はこの DFD の前提（スコープ外）として扱う。

```mermaid
flowchart LR
  %% 外部エンティティ
  SRC([ソースコード\n母体リポジトリ])
  REMOTE([baseline_docs/\nリモート\nGitHub等])
  REQ([要求書\nUR等])

  %% CR内 データストア
  D1[(CR成果物\nxddp/{CR}/\nANA/CRS/SPO\nDSN/CHD/TSP/TSR)]
  D2[(latest-specs/)]
  D3[(progress.md\n工程15記録)]
  D4[(xddp_dir/\nlessons-learned.md)]
  D8[(xddp.config.md\nDOCS_DIR)]

  %% DOCS_DIR データストア
  D5[(baseline_docs/repo/specs/\n承認済み仕様書)]
  D6[(baseline_docs/repo/knowledge/\nlessons-learned.md)]
  D7[(baseline_docs/AI_INDEX.md)]
  D9[(baseline_docs/shared/\nglossary・LL・patterns)]
  DA[(baseline_docs/repo/design/\nDSN・CHD アーカイブ)]
  DB[(baseline_docs/repo/test/\nTSP アーカイブ)]

  %% ===== Read side（AI入力） =====

  %% P0a: xddp.02.analysis Step 0
  P0a[P0a\nxddp.02.analysis\nStep 0: 知識取り込み]
  REQ -->|要求書| P0a
  D5  -->|承認済み仕様書| P0a
  D9  -->|用語集・横断LL| P0a
  D6  -->|リポジトリ固有LL| P0a
  D8  -->|DOCS_DIR| P0a
  P0a -->|整合チェック結果\n参照記録→ANA| D1

  %% P0b: xddp.04.specout Step 0
  P0b[P0b\nxddp.04.specout\nStep 0: ベースライン参照]
  D5  -->|承認済み仕様書\n読み取り専用| P0b
  D8  -->|DOCS_DIR| P0b
  P0b -->|参照記録→SPO| D1

  %% P0c: xddp.05.arch Step 0
  P0c[P0c\nxddp.05.arch\nStep 0: 過去DSN参照]
  DA  -->|DSN-*.md 最新3件| P0c
  D9  -->|design/patterns| P0c
  D8  -->|DOCS_DIR| P0c
  P0c -->|方式選択根拠参照\n参照記録→DSN| D1

  %% P0d: xddp.06.design Step 0
  P0d[P0d\nxddp.06.design\nStep 0: 過去CHD参照]
  DA  -->|CHD-*.md 最新3件| P0d
  D8  -->|DOCS_DIR| P0d
  P0d -->|変更パターン参照\n参照記録→CHD| D1

  %% P0e: xddp.08.test Step 0
  P0e[P0e\nxddp.08.test\nStep 0: 過去TSP参照]
  DB  -->|TSP-*.md 最新3件| P0e
  D9  -->|test/patterns\nanti-patterns| P0e
  D8  -->|DOCS_DIR| P0e
  P0e -->|テストパターン参照\n参照記録→TSP| D1

  %% ===== 最新仕様書生成 =====

  %% P1: xddp.09.specs
  P1[P1\nxddp.09.specs\n最新仕様書生成]
  SRC -->|ソースコード| P1
  D1  -->|CHD| P1
  D2  -->|既存specs| P1
  P1  -->|更新specs| D2
  P1  -->|完了記録\n更新ファイル一覧| D3

  %% ===== Write side（知識蓄積）=====

  %% P2: xddp.close Step C0
  P2[P2\nxddp.close Step C0\nクローズ前同期]
  REMOTE -->|git pull| P2
  D5     -->|承認済みspecs| P2
  D3     -->|保護対象ファイル一覧| P2
  D8     -->|DOCS_DIR| P2
  P2     -->|ベースライン取り込み\n非保護ファイルのみ| D2

  %% P3: xddp.close Step C
  P3[P3\nxddp.close Step C\n知見抽出]
  D1 -->|全CR成果物| P3
  D4 -->|既存ログ| P3
  P3 -->|新LLエントリ追記| D4

  %% P4: xddp.close Step C2
  P4[P4\nxddp.close Step C2\n仕様書昇格]
  D2 -->|変更ファイル| P4
  D3 -->|変更ファイル一覧| P4
  D8 -->|DOCS_DIR| P4
  P4 -->|上書きコピー| D5
  P4 -->|リポジトリ行 upsert| D7

  %% P5: xddp.close Step C3
  P5[P5\nxddp.close Step C3\nLL昇格]
  D4 -->|今回CR分のLLエントリ| P5
  D6 -->|既存ログ| P5
  P5 -->|LLエントリ追記| D6

  %% P6: xddp.close Step C4
  P6[P6\nxddp.close Step C4\n設計書昇格\nDSN・CHD]
  D1 -->|DSN-CR.md\nCHD-CR.md| P6
  D8 -->|DOCS_DIR| P6
  P6 -->|CR別アーカイブ| DA
  P6 -->|設計書テーブル upsert| D7

  %% P7: xddp.close Step C5
  P7[P7\nxddp.close Step C5\nテスト仕様書昇格\nTSP]
  D1 -->|TSP-CR.md| P7
  D8 -->|DOCS_DIR| P7
  P7 -->|CR別アーカイブ| DB
  P7 -->|テスト仕様列 upsert| D7
```

---

## 7. 承認

| 項目 | 内容 |
|---|---|
| 承認者 | |
| 承認日 | |
| 備考 | |
