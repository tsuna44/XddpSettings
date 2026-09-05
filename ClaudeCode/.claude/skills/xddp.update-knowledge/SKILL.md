---
description: 任意のタイミングで baseline_docs/ の knowledge ディレクトリに知識を追加・更新する。CR 非依存。対話形式と引数形式に対応。「知識を登録して」「callgraph を記録して」「メモを保存して」などで起動する。
argument-hint: "[repo名] [constraint|flow|callgraph|lesson|note|glossary]"
---

You are executing **XDDP Update Knowledge — Persist Investigation Results**.

> 本スキルは CR 非依存のため CR 解決行（xddp.common の "## CR Resolution"）は不要。

**Arguments:** $ARGUMENTS
- No args → interactive mode: ask repo, type, content sequentially
- `{repo}` → specific repository (matches a REPOS: key); then ask type and content interactively
- `{repo} {type}` → specific repo and type; ask content interactively
  Valid types: `constraint` | `flow` | `callgraph` | `lesson` | `note` | `glossary`
- Type alone without repo → if REPOS_KEYS has 1 entry, auto-confirm repo; else ask

---

### Step 0: Parse arguments, locate xddp.config.md

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Config"
→ let `WORKSPACE_ROOT`, `DOCS_DIR`, `DOCS`, `REPOS_KEYS`, `IS_MULTI`（他の戻り値は本スキルでは未使用）.

**Resolve target repo (`TARGET_REPO`):**
- If `{repo}` in args matches a REPOS_KEY: `TARGET_REPO` = {repo}.
- If `{repo}` in args does not match: report error and stop.
- If no repo specified and REPOS_KEYS has 1 entry: `TARGET_REPO` = that entry (report auto-confirm to user).
- If no repo specified and REPOS_KEYS has ≥2 entries: show numbered list and ask user to select.

**Resolve type (`TARGET_TYPE`):**
- If `{type}` in args and is one of `constraint|flow|callgraph|lesson|note|glossary`: `TARGET_TYPE` = {type}.
- If not specified: ask user to select from numbered list.

Let `KNOW_DIR` = `{DOCS}/{TARGET_REPO}/knowledge`.

Read `~/.claude/skills/xddp.rules/code-knowledge-boundary.md`, apply "## 宛先ルーティング表"
  → let `KNOWLEDGE_ROUTING`.

---

### Step 1: Collect input content (interactive prompts)

Show the appropriate prompt based on `TARGET_TYPE`:

**constraint:**
```
モジュール名（例: src/auth、ファイルパス第1〜2階層）:
タイトル（CK-NNN の見出し）:
対象（ファイル・インタフェース・識別子・レジスタ等）:
内容（具体的な制約・落とし穴）:
回避策:
出典（例: manual/2026-07-04）:
```

**flow:**
```
図の種別（sequence / dfd）:
ドメイン名（例: auth, device, scheduler）:
フロー名（ファイル名のベース、ハイフン区切り）:
図の内容（Mermaid テキストまたは説明）:
出典:
```

**callgraph:**
```
対象変数/識別子名:
ドメイン名（例: auth, device, scheduler）:
フロー名（ファイル名のベース、ハイフン区切り）:
更新する識別子・処理一覧（名称・ファイル・タイミング・条件）:
参照する識別子・処理一覧（名称・ファイル・タイミング・条件）:
備考・注意事項（並行更新リスク・タイミング制約・スレッドセーフ等）:
出典（例: manual/2026-07-04）:
```

**lesson:**
```
工程（例: 方式検討 / コーディング / テスト）:
タグ（例: #リスク #見落とし #コーディング）:
タイトル:
発生状況:
学んだこと:
次回への適用:
出典:
```

**note:**
```
トピック名（ファイル名のベース、ハイフン区切り）:
概要:
詳細（自由記述）:
関連ファイル・識別子（任意）:
出典:
```

**glossary:**
```
（IS_MULTI の場合）スコープ（project / {repo名} / cross）:
（IS_MULTI でない場合）スコープ（project / {repo名}）:
正式表記:
定義（1〜2文。曖昧語を使わない）:
別名・揺れ（カンマ区切り。なければ空）:
使用禁止の表記（カンマ区切り。なければ空）:
関連モジュール（任意）:
出典:
```

> `cross` は `IS_MULTI`（REPOS: が2エントリ以上）の場合のみ選択可能な特別スコープであり、
> リポジトリ間で共通の用語を表す（`cross` は `REPOS:` の予約名のため、通常の `{repo名}` 選択肢とは
> 別枠で扱う）。
>
> **既存 Step 0「Resolve target repo」との重複について:** Step 0 は `TARGET_TYPE` の確定前に
> 無条件でリポジトリ選択を要求するため、glossary で `project` または `cross` スコープを意図する
> 利用者も、Step 0 でいったん無関係なリポジトリを選ぶことになる（Step 0 で選んだリポジトリは、
> 本 Step 1 のスコープ回答が `project`／`cross` の場合は使用されない）。これは意図的な設計判断で
> あり、Step 0 を「TARGET_TYPE を先に確定してからリポジトリを解決する」順序に変更する代替案も
> あるが、その変更は constraint/flow/callgraph/lesson/note の既存5種別の対話フローにも影響する
> リファクタリングになるため、本プランでは Step 0 を変更せず、glossary 1種別に閉じた本 Step 1 の
> 追加質問で完結させる方を選択した。二重質問の UX コストは、glossary 登録の頻度が高くない
> CR 非依存の随時実行コマンドであることを踏まえ許容する。

---

### Step 2: Preview and confirm

Show a preview of the content to be written and the target file path.
Ask user to confirm. If denied or cancelled: stop.

---

### Step 3: Write to baseline_docs/

Based on `TARGET_TYPE`:

**constraint:**
- Let `MODULE` = 入力されたモジュール名
- Let `TARGET_FILE` / テンプレート = `KNOWLEDGE_ROUTING`「制約・落とし穴」行に従う
- Ensure directory exists (mkdir -p via Bash).
- If `TARGET_FILE` exists: read existing CK-NNN entries; assign next available NNN.
  Upsert: if same 出典 exists → replace entry; else → append new [CK-NNN] entry.
- Else: create from the template named in `KNOWLEDGE_ROUTING`.

**flow:**
- Let `FLOW_TYPE` = `sequence` | `dfd`
- Let `TARGET_FILE` = `{KNOW_DIR}/code-knowledge/_flows/{DOMAIN}-{FLOW_NAME}-{FLOW_TYPE}.md`
- Ensure directory exists.
- Create or overwrite using appropriate template:
  - sequence → `~/.claude/skills/xddp.close/templates/code-knowledge-flows-sequence-template.md`
  - dfd → `~/.claude/skills/xddp.close/templates/code-knowledge-flows-dfd-template.md`

**callgraph:**
- Let `VAR_NAME` = 対象変数/識別子名（スペース→ハイフン・小文字）
- Let `TARGET_FILE` = `{KNOW_DIR}/code-knowledge/_flows/{DOMAIN}-{VAR_NAME}-callgraph.md`
- Ensure directory exists.
- If `TARGET_FILE` exists: update tables; append row to 変更履歴.
- Else: create from template `~/.claude/skills/xddp.update-knowledge/templates/callgraph-template.md`.

**lesson:**
- Let `TARGET_FILE` = `{KNOW_DIR}/lessons-learned.md`
- Ensure file exists (create with header if not).
- Read existing LL-NNN; assign next NNN. Append new entry at end.

**note:**
- Let `TOPIC` = トピック名（スペース→ハイフン・小文字）
- Let `TARGET_FILE` = `{KNOW_DIR}/notes/{TOPIC}.md`
- Ensure directory exists.
- If `TARGET_FILE` exists: append new content block with 更新日.
- Else: create from template `~/.claude/skills/xddp.update-knowledge/templates/notes-template.md`.

**glossary:**

- スコープが `project` の場合: Let `TARGET_FILE` = `{DOCS}/glossary.md`
- スコープが `{repo}` の場合: Let `TARGET_FILE` = `{KNOW_DIR}/glossary.md`
- スコープが `cross` の場合（`IS_MULTI` の場合のみ選択可能）:
  Let `TARGET_FILE` = `{DOCS}/cross/knowledge/glossary.md`
- ファイルが存在する場合: 「用語一覧」テーブルに行を upsert する
  （**正式表記**列をキーとし、既存行があれば上書きする）
- ファイルが存在しない場合: テンプレート
  `~/.claude/skills/xddp.update-knowledge/templates/glossary-template.md` から作成する
- 「変更履歴」テーブルに1行追記する（CR 非依存の実行のため CR 列は `—` とする）

---

### Step 4: Report

Tell the user:

> **知識の登録が完了しました**
>
> | 項目 | 内容 |
> |---|---|
> | 種別 | {TARGET_TYPE} |
> | リポジトリ | {TARGET_REPO} |
> | 格納先 | `{TARGET_FILE}` |
>
> **次のステップ:**
> - 内容を確認してください: `{TARGET_FILE}`
> - 修正が必要な場合は直接編集するか、再度 `/xddp.update-knowledge` を実行してください

---
> **保守メモ:** このファイルを変更した場合は、`README.md`（スキル一覧テーブル）、`CLAUDE.md`
> （ステップ番号体系テーブル）も合わせて更新すること。
