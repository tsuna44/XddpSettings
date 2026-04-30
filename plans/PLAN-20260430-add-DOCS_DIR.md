# PLAN-20260430-DOCS_DIR追加

作成日: 2026-04-30  
ステータス: **承認待ち**

---

## 1. 背景・目的

ワークスペース直下の `docs/` を中央知識ハブとして使う構成が決まった（`docs/knowledge-hierarchy-review.md` 参照）。
各プロジェクトがこのハブのパスを `xddp.config.md` で指定できるよう `DOCS_DIR` 設定キーを追加する。
あわせて `xddp.01.init` 実行時に `DOCS_DIR` 以下の初期ディレクトリ構造を自動生成する。

---

## 2. 変更対象ファイル

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `ClaudeCode/.claude/templates/xddp.config.md` | 修正 | `DOCS_DIR` 設定キーを追加 |
| `ClaudeCode/.claude/skills/xddp.01.init.md` | 修正 | Step 3.6: DOCS_DIR 初期化ステップを追加 |
| `ClaudeCode/.claude/commands/xddp.01.init.md` | 修正 | Step 4.5 の要約を追記 |
| `ClaudeCode/.claude/skills/xddp.close.md` | 修正 | Step C2: `SPECS_APPROVED_DIR` → `DOCS_DIR` 方式に変更、Step C3: lessons-learned 昇格を追加 |
| `ClaudeCode/.claude/commands/xddp.close.md` | 修正 | Step 5 の説明を DOCS_DIR 方式に更新 |

---

## 3. 変更内容

### 3.1. `ClaudeCode/.claude/templates/xddp.config.md`

「成果物ディレクトリ設定」セクション末尾（最初の `---` の直前）に追加。

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
リポジトリルートからの相対パスで指定する。デフォルト: `xddp`

# 例: XDDP_DIR: docs/xddp  →  {repo_root}/docs/xddp/ 配下に成果物を集約する

---

## 知識ハブディレクトリ設定

DOCS_DIR: ../docs

承認済み仕様書・知見ログを集約する中央知識ハブのパス。
リポジトリルートからの相対パスで指定する。デフォルト: ../docs（ワークスペースルートの docs/）

# 例: DOCS_DIR: docs  →  リポジトリ内 docs/ を使う場合
```

---

### 3.2. `ClaudeCode/.claude/skills/xddp.01.init.md`

「### 3.5. Create latest-specs/」の直後、「### 4. Create xddp.config.md」の直前に挿入。

**変更前（挿入位置）:**
```
### 4. Create xddp.config.md (if not exists)
```

**変更後（追加するブロック）:**
```
### 3.6. Create DOCS_DIR structure (if not exists)

1. Read `DOCS_DIR` from `xddp.config.md` (default: `../docs` if key is absent).
   Resolve the path relative to the repository root (same convention as `XDDP_DIR`).
   Let `DOCS` = resolved absolute path of `DOCS_DIR`.
2. Let `REPO_NAME` = basename of the current working directory.
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
4. If `{DOCS}` exists but `{DOCS}/{REPO_NAME}/` does not → create only:
   - `{DOCS}/{REPO_NAME}/specs/README.md`
   - `{DOCS}/{REPO_NAME}/knowledge/lessons-learned.md`
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
```

`{DOCS}/{REPO_NAME}/specs/README.md`:
```markdown
# 承認済み仕様書: {REPO_NAME}
xddp.close で latest-specs/ から昇格した承認済みの最新仕様書を格納します。
ドラフト（未レビュー）は各リポジトリの latest-specs/ にあります。
```

`lessons-learned.md` （共通フォーマット）:
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

ステップ 4（`latest-specs/` 作成）の次に挿入。

**変更前:**
```
4. Create `latest-specs/` with a README if not already present.
5. Copy `~/.claude/templates/xddp.config.md` to `./xddp.config.md` if not already present.
```

**変更後:**
```
4. Create `latest-specs/` with a README if not already present.
4.5. Resolve `DOCS_DIR`（デフォルト `../docs`、リポジトリルート相対）。`docs/` が未存在なら
     `AI_INDEX.md` / `shared/` / `{repo_name}/specs/` / `{repo_name}/knowledge/` を作成。
     `docs/` 既存で `{repo_name}/` のみ未作成の場合はリポジトリサブフォルダのみ追加。
5. Copy `~/.claude/templates/xddp.config.md` to `./xddp.config.md` if not already present.
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
- `git log HEAD..origin/main --oneline` でリモートに未取得のコミットがあるか確認する
- 未取得コミットがある場合 → ユーザーに `git pull` を促す
  - ユーザーが pull を完了したら次へ進む
  - 「スキップする」と明示した場合のみ next へ進む（後で仕様齟齬が起きる可能性を警告する）

### 2. docs/ の同期
`{DOCS}` が git リポジトリか（`.git` の存在）を確認し、以下のいずれかを実行する。

**ケースA: docs/ が git 管理されている（推奨運用）**
- `git -C {DOCS} pull` を実行する
- コンフリクトが発生した場合 → 人が解消してから再開するよう案内して停止する

**ケースB: docs/ が git 管理されていない・まだ存在しない**
- git pull はスキップする
- 以下を警告として表示する：
  ```
  ⚠️ DOCS_DIR（{DOCS}）は git 管理されていません。
  複数人・複数マシンで並行作業している場合、他のCRによる変更と
  競合しても自動検出できません。
  docs/ を git リポジトリとして管理することを推奨します。
  このまま続行しますか？ [続行 / 中止]
  ```
- ユーザーが「続行」を選択した場合のみ次へ進む
- ローカル単独作業であれば Step 3 のベースライン取り込みは引き続き機能する

### 3. latest-specs/ へのベースライン取り込み
- `{DOCS}/{REPO_NAME}/specs/` が存在する場合のみ実行する（存在しない場合はスキップ）
- progress.md の工程15に記録された「このCRが更新したファイル」一覧を取得する（= **保護対象**）
- `{DOCS}/{REPO_NAME}/specs/` 配下のファイルを列挙し、保護対象**以外**のファイルを
  `{XDDP_DIR}/latest-specs/` にコピーする（他CRの承認済み変更を latest-specs に取り込む）
- 保護対象ファイルは上書きしない（このCRの作業成果を保護する）
- **git 管理なし・単独作業の場合**: このステップはローカルの docs/ を読むだけなので正常に動作する

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

## Step C2: 承認済み仕様書の昇格（{XDDP_DIR}/latest-specs/ → DOCS_DIR/{REPO_NAME}/specs/）

Read `{CR_PATH}/progress.md` を確認し、工程15で更新・生成されたすべての `{XDDP_DIR}/latest-specs/` ファイルのリストを把握する。

**ターゲットパスの決定:**

`xddp.config.md` から `DOCS_DIR` を読む（デフォルト: `../docs`、リポジトリルート相対）。
Let `DOCS` = resolved absolute path of DOCS_DIR.
Let `REPO_NAME` = basename of the current working directory.
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
     (2) docs/ の git pull
     (3) docs/{repo}/specs/ → latest-specs/ へ他CR分をベースライン取り込み
         （このCR変更ファイルは保護）
     (4) ソース変更があった場合は /xddp.09.specs {CR} の再実行を推奨
5. 承認済み仕様書の昇格（Step C2）: `latest-specs/` → `{DOCS_DIR}/{REPO_NAME}/specs/` にコピーし、`{DOCS_DIR}/AI_INDEX.md` のリポジトリ行を更新する。
5.5. 知見ログの昇格（Step C3）: 今回 CR の LL エントリを `{DOCS_DIR}/{REPO_NAME}/knowledge/lessons-learned.md` に追記する。
```

---

## 4. 影響範囲

- 影響するスキル・コマンド: `xddp.01.init`、`xddp.close`
- 影響する工程: 工程1（CRワークスペース初期化）、CRクローズ
- 後方互換性:
  - `DOCS_DIR` 未設定時は `../docs` をデフォルトとする
  - `xddp.close` の `SPECS_APPROVED_DIR` キーは廃止し `DOCS_DIR` に統一する（既存プロジェクトで `SPECS_APPROVED_DIR` を設定済みの場合は `DOCS_DIR` への移行が必要）
- docs/ の git 管理状態による動作差異:
  - git 管理あり: Step C0-2 で pull、並行CR間の競合を自動検出できる（推奨）
  - git 管理なし: Step C0-2 をスキップ、警告を表示して続行確認。ローカル単独作業なら Step C0-3 は正常動作。複数人・複数マシンの並行作業は手動調整が必要

---

## 5. 確認項目

- [ ] スキル・コマンドの同期（xddp.01.init・xddp.close ともに commands も更新済み）
- [ ] `sample-project` で `xddp.01.init` を実行し以下が生成されることを確認
  - `../docs/AI_INDEX.md`
  - `../docs/shared/`
  - `../docs/{repo_name}/specs/`
  - `../docs/{repo_name}/knowledge/`
- [ ] 2回目の実行で重複作成されないことを確認
- [ ] `DOCS_DIR: docs` に変更してリポジトリ内 `docs/` が作成されることを確認
- [ ] `sample-project` で `xddp.close` を実行し以下が確認できる
  - Step C0: リモートの未取得コミット有無が検出・報告される
  - Step C0: docs/ の git pull が実行される
  - Step C0: 他CRの承認済み specs が latest-specs/ に取り込まれる（このCR変更ファイルは保護される）
  - Step C0: ソース変更がある場合に xddp.09.specs 再実行の推奨が表示される
  - Step C2: `../docs/{repo_name}/specs/` に latest-specs の変更ファイルがコピーされる
  - Step C2: `../docs/AI_INDEX.md` のリポジトリ行が追加・更新される
  - Step C3: `../docs/{repo_name}/knowledge/lessons-learned.md` に LL エントリが追記される
- [ ] CLAUDE.md の `xddp.config.md の位置付け` 節と整合している

---

## 6. 承認

| 項目 | 内容 |
|---|---|
| 承認者 | |
| 承認日 | |
| 備考 | |
