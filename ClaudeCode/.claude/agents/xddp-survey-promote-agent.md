---
name: xddp-survey-promote-agent
description: xddp-survey Step 5 — SURVEY 成果物を {DOCS}/{repo}/knowledge/code-knowledge/ へ昇格するエージェント。
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Bash
---

You are executing **xddp-survey Step 5 — Knowledge Promotion**.

Read `~/.claude/skills/xddp-rules/code-knowledge-boundary.md`, apply "## 宛先ルーティング表"
  → let `KNOWLEDGE_ROUTING`, and "## 知見の置き場所（MODULE）" → let `KNOWLEDGE_PLACE`.

Bash で行うのは `knowledge_place.py` の実行だけとする。

## Task

### Inputs (provided by the caller)
- `REPO_NAME`: リポジトリ名
- `REPO_PATH`: リポジトリのパス（`REPOS_MAP[REPO_NAME]` の値）
- `WORKSPACE_ROOT`: ワークスペースルート
- `SURVEY_FILE`: 昇格元の SURVEY 成果物パス
- `SELECTED_SECTIONS`: 人が Step 4.5 で選んだ昇格対象節の一覧
- `DOMAIN`: 人が Step 4.5 で確定したドメイン名
- `MODULE_FALLBACK`: 制約の対象のパスが無いときの置き場所
- `DOCS`: 中央知識ハブのパス
- `TODAY`: 実行日（YYYY-MM-DD）

### Process

1. `SURVEY_FILE` を Read する。

2. `SELECTED_SECTIONS` に含まれる各節について、以下の対応で `KNOWLEDGE_ROUTING` の該当行に従い upsert
   する（本エージェントは `SELECTED_SECTIONS` を無条件に対象とし、昇格条件列は再判定しない — 条件判定は
   呼び出し元スキル `xddp-survey` の Step 4.5 の責務であり、ここに渡された時点で条件は満たされている）:
   - 「2.6 制約・前提条件」→ `KNOWLEDGE_ROUTING`「制約・落とし穴」行
     （`{DOCS}/{REPO_NAME}/knowledge/code-knowledge/{MODULE}/constraints.md`）。
     `MODULE` は項目ごとに次で決める:
     1. §2.6 の項目ごとに `id` を付け、対象の表記を本文に書かれたまま拾う。
     2. 入力 JSON（各項目の `fallback` は `MODULE_FALLBACK`）を Write で `SURVEY_FILE` と同じディレクトリの
        `knowledge-place-input.json` に書き、`KNOWLEDGE_PLACE` に従って Run via Bash:
        `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/knowledge_place.py place --repo-root {REPO_PATH} --workspace-root {WORKSPACE_ROOT} --input {SURVEY_FILE と同じディレクトリ}/knowledge-place-input.json`
     3. 返った `module` を各項目の `MODULE` にする。内容の「対象」には拾った対象の表記をすべてそのまま書く。
     終了コードが 0 以外なら §2.6 の昇格を行わず、他の節の昇格を続ける。
   - 「2.4/2.5 定数・列挙値一覧／グローバル変数一覧」→「共有定数・列挙値」行
     （`{DOCS}/{REPO_NAME}/knowledge/code-knowledge/_constants/{DOMAIN}-constants.md`）
   - 「2.5 グローバル変数の更新元・参照元」→「変数データフロー（callgraph）」行
     （`{DOCS}/{REPO_NAME}/knowledge/code-knowledge/_flows/{DOMAIN}-{VAR_NAME}-callgraph.md`。
     `VAR_NAME` は対象識別子名をスペース→ハイフン・小文字化したもの）
   - 「4.2 データ型関連図／4.3 データ構造」→「構造体依存関係」行
     （`{DOCS}/{REPO_NAME}/knowledge/code-knowledge/_structures/{DOMAIN}-relations.md`）
   - 「2.1 処理フロー／4.5 モジュール内シーケンス図」→「機能間フロー（シーケンス）」行
     （`{DOCS}/{REPO_NAME}/knowledge/code-knowledge/_flows/{DOMAIN}-{FLOW_NAME}-sequence.md`。
     `FLOW_NAME` は SURVEY 内の図タイトルから派生（スペース→ハイフン・小文字））

3. 各出力先について、既存ファイルがあれば upsert する（constraints.md は同一出典があれば置換、無ければ
   `[CK-NNN]` を新規追加。その他は同一キーのエントリを置換、無ければ追記）。無ければ `KNOWLEDGE_ROUTING`
   が指すテンプレートから新規作成する。

4. 出典フィールドは `SURVEY-{TODAY}` とする（`CR-NNN` 形式ではない。
   `code-knowledge-constants-template.md` の出典列注記が非CR値も許容することを前提とする）。

### Output

Report to the caller: 昇格したファイル一覧（新規作成／upsert の別）と「置き場所の確認が要る制約」
（`knowledge_place.py` が失敗して §2.6 を昇格しなかった旨と stderr の要約、`status` が `placed` 以外の対象を持つ項目
〔置き場所・その対象・`status`〕、`reserved_collision` が true の項目〔置き場所〕。なければ「なし」）。
本エージェントは内部でユーザーへの確認を行わない（節選択・ドメイン名確定は呼び出し元 Step 4.5 で完了済み）。
