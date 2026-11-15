---
name: xddp-update-knowledge
description: 任意のタイミングで baseline_docs/ の knowledge ディレクトリに知識を追加・更新する。CR 非依存。対話形式と引数形式に対応。「知識を登録して」「callgraph を記録して」「メモを保存して」などで起動する。
argument-hint: "[repo名] [constraint|flow|callgraph|lesson|note|glossary|structure]"
---

You are executing **XDDP Update Knowledge — Persist Investigation Results**.

> 本スキルは CR 非依存のため CR 解決行（xddp-common の "## CR Resolution"）は不要。

**Arguments:** $ARGUMENTS
- No args → interactive mode: ask repo, type, content sequentially
- `{repo}` → specific repository (matches a REPOS: key); then ask type and content interactively
- `{repo} {type}` → specific repo and type; ask content interactively
  Valid types: `constraint` | `flow` | `callgraph` | `lesson` | `note` | `glossary` | `structure`
- Type alone without repo → if REPOS_KEYS has 1 entry, auto-confirm repo; else ask

---

### Step 0: Parse arguments, locate xddp.config.md

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Load Config"
→ let `WORKSPACE_ROOT`, `DOCS_DIR`, `DOCS`, `REPOS_MAP`, `REPOS_KEYS`, `IS_MULTI`（他の戻り値は本スキルでは未使用）.

**Resolve target repo (`TARGET_REPO`):**
- If `{repo}` in args matches a REPOS_KEY: `TARGET_REPO` = {repo}.
- If `{repo}` in args does not match: report error and stop.
- If no repo specified and REPOS_KEYS has 1 entry: `TARGET_REPO` = that entry (report auto-confirm to user).
- If no repo specified and REPOS_KEYS has ≥2 entries: show numbered list and ask user to select.

**Resolve type (`TARGET_TYPE`):**
- If `{type}` in args and is one of `constraint|flow|callgraph|lesson|note|glossary|structure`: `TARGET_TYPE` = {type}.
- If not specified: ask user to select from numbered list.

Let `KNOW_DIR` = `{DOCS}/{TARGET_REPO}/knowledge`.
Let `TODAY` = today's date (YYYY-MM-DD).

Read `~/.claude/skills/xddp-rules/code-knowledge-boundary.md`, apply "## 宛先ルーティング表"
  → let `KNOWLEDGE_ROUTING`, and "## 知見の置き場所（MODULE）" → let `KNOWLEDGE_PLACE`.

---

### Step 1: Collect input content (interactive prompts)

Show the appropriate prompt based on `TARGET_TYPE`:

**constraint:**
```
対象のファイルまたはディレクトリ（リポジトリのルートからの相対パス。特定のファイルに結び付かない制約は空）:
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
更新する識別子・処理一覧（名称・ファイル・タイミング・条件）:
参照する識別子・処理一覧（名称・ファイル・タイミング・条件）:
備考・注意事項（並行更新リスク・タイミング制約・スレッドセーフ等）:
出典（例: manual/2026-07-04）:
```

**lesson:**
```
工程（例: 方式検討 / コーディング / テスト）:
タグ（例: #リスク, #見落とし, #コーディング）:
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

**structure:**
```
対象言語のパラダイム（OOP / 手続き型）:
含まれるモジュール一覧:
ドメイン名（例: auth, device, scheduler）:
対象データ型・構造体（名称・定義場所）:
モジュール間の依存関係（参照元 → 参照先）:
落とし穴・注意点（この構造を参照するときに気をつけること）:
出典（例: manual/2026-08-08）:
```

「対象言語のパラダイム」は、昇格先テンプレート `code-knowledge-structures-template.md` が要求する
「OOP言語: classDiagram / 手続き型（C言語等）: テキスト表または graph LR」という図の記法選択を
入力時点で確定させる質問（`flow` 種別が「図の種別（sequence / dfd）:」を明示質問するのと同じパターン）。
「含まれるモジュール一覧」はテンプレートの「含まれるモジュール」欄に対応する。

「落とし穴・注意点」は入力を強く推奨するが、機械的な必須項目としては扱わない
（`code-knowledge-boundary.md`「宛先ルーティング表」の経路ごとの拘束範囲注記により、手動登録経路
（本スキル）には昇格条件列を機械適用しない）。空で入力された場合:
- その旨と、仕様側（`specs/overview/`）への記載も選択肢であることを案内した上で、続行するかどうかを
  人に確認する。
- 「続行する」が選択された場合: Step 2 のプレビューに進む。
- 「続行しない」が選択された場合: Step 2 の「If denied or cancelled: stop.」と全く同一の挙動
  （コマンド全体を終了する。Step 0 の対話へループバックはしない）で `structure` の登録処理を終了する。

「落とし穴・注意点」以外の6項目（対象言語のパラダイム・含まれるモジュール一覧・ドメイン名・
対象データ型/構造体・モジュール間の依存関係・出典）は必須入力とする。空の場合は理由を示して再入力を求める。

---

### Step 1.5（constraint のみ）: 書き先の決定（`upsert --dry-run`）

`KNOWLEDGE_PLACE` の `upsert` に渡す入力を1件の知見として作る（`constraints.md` を直接 Edit・Write しない）:
- `id`: `manual`。`targets`: 「対象のファイルまたはディレクトリ」の1要素（空なら空のリスト `[]`）。
- `subjects`: 「対象」の入力を分けずにそのまま1要素（空なら空のリスト）。置き場所の決定には使わない。
- `fallback`: `_general`。`section`: `constraint`。`title`: 「タイトル」。
- `fields`: `content`＝「内容」、`workaround`＝「回避策」。`source`: 「出典」。`key` は書かない。
- JSON の文字列には、人の入力の `\` を `\\`、`"` を `\"`、改行を `\n` にして書く。

引用符付きのヒアドキュメントで stdin に渡して Run via Bash:
```
PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/knowledge_place.py upsert --docs {DOCS} --repo {TARGET_REPO} --repo-root {REPOS_MAP[TARGET_REPO] の値} --workspace-root {WORKSPACE_ROOT} --dry-run <<'EOF'
[{"id": "manual", "targets": [...], "subjects": [...], "fallback": "_general", "section": "constraint", "title": "...", "fields": {"content": "...", "workaround": "..."}, "source": "..."}]
EOF
```
- 終了コードが 0 以外なら、stderr を示して停止する（何も書かない）。入力の書き方の誤り（`\` の書き漏らし等）なら、直して実行し直す。
- 出力の `entries[0]` の `file` を `TARGET_FILE`（`{KNOW_DIR}/code-knowledge/` からの相対パス）とする。`reserved_collision` が true なら、
  対象が予約名と同じ名前のディレクトリにあるので置き場所が `_general` になった旨を Step 2 のプレビューに添える。
- 「対象のファイルまたはディレクトリ」の `status`（`entries[0].targets[0].status`）が `placed` 以外なら、その意味（`url`＝URL、`no-path`＝パスではない、
  `outside-repo`＝リポジトリの外、`not-found`＝リポジトリに無い）を示し、人に「入力し直す／パスなし（`_general`）」を尋ねる。
  入力し直す場合は、新しい入力でこの Step をやり直す。パスなしの場合は、その表記を `subjects` の先頭に移し、`targets` を空にしてこの Step をやり直す。
- 出力の `existing[TARGET_FILE]` を `EXISTING_ENTRIES` とする。

---

### Step 2: Preview and confirm

Show a preview of the content to be written and the target file path.
- constraint: 書き先 `TARGET_FILE`（Step 1.5 の `upsert --dry-run` の出力）と `EXISTING_ENTRIES`（`[CK-NNN]` とタイトル）を示し、
  「新しいエントリとして足す（既定）／既存の [CK-NNN] を置き換える」を人に尋ねる。置き換える場合は番号を選ばせ、`REPLACE_CK` とする。
Ask user to confirm. If denied or cancelled: stop.

---

### Step 3: Write to baseline_docs/

Based on `TARGET_TYPE`:

**constraint:**
- Step 1.5 と同じ入力（`REPLACE_CK` がある場合は要素に `"replace": "{REPLACE_CK}"` を足す）で、`--dry-run` を付けずに Step 1.5 のコマンドを実行する。
  採番・ファイルの作成・書式は `upsert` が行う。終了コードが 0 以外なら stderr を示して停止する。
- 出力の `entries[0]` の `file`・`ck`・`action` を人に示す。

**flow:**
- Let `FLOW_TYPE` = `sequence` | `dfd`
- Let `TARGET_FILE` / テンプレート = `KNOWLEDGE_ROUTING` の行（sequence →「機能間フロー（シーケンス）」行、dfd →「データフロー図（DFD）」行。per-repo 系統）に従う
- Ensure directory exists.
- Create or overwrite using the template named in `KNOWLEDGE_ROUTING`.

**callgraph:**
- Let `VAR_NAME` = 対象変数/識別子名（スペース→ハイフン・小文字）
- Let `TARGET_FILE` / テンプレート = `KNOWLEDGE_ROUTING`「変数データフロー（callgraph）」行に従う
- Ensure directory exists.
- If `TARGET_FILE` exists: update tables; append row to 変更履歴.
- Else: create from the template named in `KNOWLEDGE_ROUTING`.

**lesson:**
- Let `TARGET_FILE` = `{KNOW_DIR}/lessons-learned.md`
1. Run via Bash（ファイルが無ければヘッダーを作る。`## エントリ一覧` が無ければ足す）:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-close/scripts/promote.py index --today {TODAY} --layer2-file {TARGET_FILE} --area {TARGET_REPO}`
   終了コードが 0 以外なら stderr を示して停止する。
2. ID は stdout の JSON の `next_manual_id`（`LL-M{YYYYMMDD}-{NN}`）を使う（番号を数えない）。
3. エントリは `~/.claude/skills/xddp-close/SKILL.md` の「### Entry Format」（Step C）の書式で書き、`**次回への適用：**` の後に `**出典：** {出典}` の行を足して、ファイルの末尾に書く。
   メタ行は `**CR：** — ／ **工程：** {工程} ／ **repo：** {TARGET_REPO} ／ **タグ：** {#タグ1, #タグ2}`（タグはカンマ区切り）。
4. 1. と同じコマンドをもう一度実行する（エントリ一覧を作り直す）。stdout の `duplicate_ids`・`unparsed_ll`・`unknown_tags` が空でなければ人に示す。

**note:**
- Let `TOPIC` = トピック名（スペース→ハイフン・小文字）
- Let `TARGET_FILE` = `{KNOW_DIR}/notes/{TOPIC}.md`
- Ensure directory exists.
- If `TARGET_FILE` exists: append new content block with 更新日.
- Else: create from template `~/.claude/skills/xddp-update-knowledge/templates/notes-template.md`.

**glossary:**

- スコープが `project` の場合: Let `TARGET_FILE` = `{DOCS}/glossary.md`
- スコープが `{repo}` の場合: Let `TARGET_FILE` = `{KNOW_DIR}/glossary.md`
- スコープが `cross` の場合（`IS_MULTI` の場合のみ選択可能）:
  Let `TARGET_FILE` = `{DOCS}/cross/knowledge/glossary.md`
- ファイルが存在する場合: 「用語一覧」テーブルに行を upsert する
  （**正式表記**列をキーとし、既存行があれば上書きする）
- ファイルが存在しない場合: テンプレート
  `~/.claude/skills/xddp-update-knowledge/templates/glossary-template.md` から作成し、「用語一覧」テーブルの見本の行
  （正式表記が `{用語}` の行）を登録する用語の行に置き換える（見本の行を残さない）。「用語間の関係」テーブルの見本の行は、
  登録する関係が無ければ「なし」の1行にする
- 「変更履歴」テーブルに1行追記する（CR 非依存の実行のため CR 列は `—` とする）

**structure:**
- Let `DOMAIN` = 入力されたドメイン名
- Let `TARGET_FILE` / テンプレート = `KNOWLEDGE_ROUTING`「構造体依存関係」行（per-repo 系統）に従う
- Ensure directory exists (mkdir -p via Bash).
- If `TARGET_FILE` exists: Upsert（同一ドメインの図を上書き更新）。
- Else: create from the template named in `KNOWLEDGE_ROUTING`。
- テンプレートへの入力項目マッピング（`code-knowledge-structures-template.md` の節に対応）:
  - 「モジュール間の構造体依存関係」節: 対象言語のパラダイムが OOP の場合は mermaid `classDiagram`、
    手続き型の場合はテキスト表または `graph LR` で、対象データ型・構造体とモジュール間の依存関係を記入する
  - 「含まれるモジュール:」欄 ← 入力された「含まれるモジュール一覧」
  - 「出典:」欄 ← 入力された「出典」（CR 非依存実行のため CR 番号ではなく入力値をそのまま使用）
  - 「注意事項・制約」節（`KNOWLEDGE_ROUTING`「構造体依存関係」行のセクション列に対応）
    ← 入力された「落とし穴・注意点」（`_structures/` 存在意義の中核フィールド。Step 1 で空欄のまま
    続行が選択された場合は、その旨を明記した上で節を空のまま作成する）

**AI_INDEX.md の作り直し（どの種別でも、書いた後に実行する）:** Run via Bash（`TARGET_REPO` だけでなく全 repo を渡す）:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/ai_index.py build --docs {DOCS} --repos-keys {REPOS_KEYS をカンマ区切り} {IS_MULTI の場合のみ}--is-multi`
失敗したら Let `AI_INDEX_ERROR` = stderr の1行目（登録は取り消さない）。

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
> {AI_INDEX_ERROR がある場合: ⚠️ AI_INDEX.md の作り直しに失敗しました（{AI_INDEX_ERROR}）。登録は済んでいます。`ai_index.py build` を再実行してください}
>
> **次のステップ:**
> - 内容を確認してください: `{TARGET_FILE}`
> - 修正が必要な場合は直接編集するか、再度 `/xddp-update-knowledge` を実行してください

---
> **保守メモ:** このファイルを変更した場合は、`README.md`（スキル一覧テーブル）、`CLAUDE.md`
> （ステップ番号体系テーブル）も合わせて更新すること。
