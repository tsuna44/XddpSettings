---
description: （スキルの説明。「〇〇して」「〇〇作って」などで起動する）
---

You are orchestrating **XDDP Step XX — （スキル名）**.

**Arguments:** $ARGUMENTS = [CR_NUMBER]（省略可）[, （二次引数があれば記載）]

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date (YYYY-MM-DD).

(xddp.config.md lookup done in xddp.common/SKILL.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

（二次引数がある場合はここで REST_ARGS から取得する）
（例: Let `DOCUMENT_TYPE` = first token of `REST_ARGS`.）

---

## 参考: エージェント呼び出し共有パラメータの命名規約

同一のエージェント呼び出しパラメータが複数箇所（`For each {repo}` ループ内の通常呼び出し・
Review Loop の FIXER_PARAMS・`--detail` 等の代替モード呼び出し等）で繰り返される場合、
以下の命名規約で書き分けること。

- **`{NAME}_SHARED`**: `{repo}` 等のループ変数に依存しないフィールドのみで構成し、
  ファイル冒頭など1箇所で定義して複数の独立ループから安全に参照する
  （例: `CODE_AGENT_SHARED`、`ARCH_TEMPLATE_PATHS`、`ARCH_CALL_SHARED`）。
- **`{NAME}_BASE`**: `{repo}` 等のループ変数に依存するフィールドを含むため、各独立ループの
  先頭で同一の定義を複製し、「この式は○○の△箇所に同一の文字列で存在する。変更時は
  grep し△箇所すべてを同期させること」という注記を付ける
  （例: `ARCH_AGENT_PATHS`、`TSP_OUTPUT_FILE`、`DESIGN_INDEX_FILE_BASE`）。
  複製先の各ループが異なるループ変数名を使う場合（例: Step A は `{repo}`、Step A2 backfill は
  `{その有力repo}`）は、対象repo変数名を差し替えた定義を複製し、注記にも両方の変数名を明記する
  （例: `DESIGN_SPEC_PARAMS_BASE`）。この場合、複製元と複製先で対象repo変数名以外の部分
  （条件文の詳細度・付随フィールドの有無等）が実ソース上すでに異なっていることがある。その際は
  「対象repo変数名のみ異なる同一構造」と決めつけて注記せず、実際の相違点（例: 一方は条件部に
  ファイルパスを明記した詳細な条件文、他方は詳細を省いた簡略な条件文）を注記に明記し、同期時にも
  その相違点ごと維持すること（`DESIGN_SPEC_PARAMS_BASE` の Step A／Step A2 backfill 間の
  条件文詳細度の相違が実例）。

`REPO_NAME: {repo}` のような単純なループ変数の1行記述は、共有ブロック化する重複には
当たらないため、各呼び出し箇所に個別記述のままでよい。ループ変数依存フィールドと非依存
フィールドを同一の共有ブロックに混在させないこと（複数の独立ループから参照する設計にすると、
別ループの値が誤って参照される不具合の原因になる）。

（例示の `ARCH_TEMPLATE_PATHS`／`ARCH_AGENT_PATHS`／`TSP_OUTPUT_FILE` は本規約制定前から
存在する既存の命名であり、`_SHARED`/`_BASE` サフィックスを持たない。これは規約制定前からの
例外であり、サフィックスの有無自体を規約適合の判定基準にしないこと。分類の実質的な基準は
サフィックスではなく、上記の「ループ変数に依存しないか／依存するか」という性質である。）

---

## Step 1: ...

（以降、スキル固有のロジックを記述する）
