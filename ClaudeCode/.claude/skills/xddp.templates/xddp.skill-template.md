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
以下の優先順位で書き分けること。

1. **`{repo}` 等のループ変数に依存しないフィールド**は `{NAME}_SHARED` としてファイル冒頭など
   1箇所で定義し、複数の独立ループから安全に参照する（例: `CODE_AGENT_SHARED`、`ARCH_CALL_SHARED`）。
2. **`{repo}` 等のループ変数に依存するフィールドを複数の独立ループ（同一ファイル内・他ファイル
   問わず）で構築する場合は、まず `xddp.common/SKILL.md` への手順抽出を検討すること。**
   Input（`CR_PATH`／`REPO_NAME`／`CR` 等）と Output（構築される値）を持つ「## 手順名」節を
   `xddp.common/SKILL.md` に新設し、各呼び出し箇所は
   `Read ~/.claude/skills/xddp.common/SKILL.md, apply「## 手順名」with: ... → let ...` の1行に
   置き換える（例: `## Load Steering Context`・`## Discover CHD Files`・`## Detect Test Framework`）。
   定義が1箇所にしか存在しなくなるため、複製先どうしの同期漏れというバグクラス自体が発生しない。
   ループ内での再利用も、`RULEBOOK_CONTEXT`（`## Load Steering Context` を各 `{repo}` ループの
   先頭で毎回呼び直す形）が示す通り問題なく機能する。抽出前に構築ロジックと同一の値を返す既存手順が
   xddp.common に既にないか必ず確認すること（既存手順の出力の一部を無視して独自に再計算する
   重複を新たに作らないため）。
   呼び出し側のローカル変数名は、抽出前の名前（`_BASE` サフィックスを含む）をそのまま使ってよい
   （例: `DESIGN_SPEC_PARAMS_BASE`・`TSP_OUTPUT_FILE`）。この場合の `_BASE` サフィックスは
   単一の Read+apply 呼び出しが返す値のローカルな受け皿名であり、複製された定義を意味しない
   （下記3.のフォールバックとは異なる）。
3. **`{NAME}_BASE` ＋ grep-and-sync 注記は、xddp.common への抽出が実務上見合わない場合のみ**
   使うフォールバックとする。該当するのは主に「値の構築ロジックではなく、他スキルのステップ内容
   ブロック（複数行の処理指示・除外リストを含む）をほぼそのまま複製する」ケースで、xddp.common の
   Input/Output/Process 形式に収まらない（例: `xddp.feedback/SKILL.md` が `xddp.06.design/SKILL.md`
   の Step C' 相当ブロックを一部除外リスト付きで複製する箇所。除外理由は
   `docs/adr/ADR-0007-feedback-design-excluded-blocks.md` を参照）。このフォールバックを使う際は
   「複製先が△箇所ある」という事実だけでなく、**なぜ xddp.common へ抽出できないか**を注記に
   明記すること。

`REPO_NAME: {repo}` のような単純なループ変数の1行記述は、共有ブロック化する重複には
当たらないため、各呼び出し箇所に個別記述のままでよい。ループ変数依存フィールドと非依存
フィールドを同一の共有ブロックに混在させないこと（複数の独立ループから参照する設計にすると、
別ループの値が誤って参照される不具合の原因になる）。

---

## Step 1: ...

（以降、スキル固有のロジックを記述する）

> **注: 工程の完了・進行中に progress.md を更新する場合**は `xddp.common/SKILL.md`「## Progress Update」を
> apply し、成果物を生成・更新する工程では `ARTIFACT_LINK` を必ず渡すこと。値のフォーマット規約
> （Markdown リンク形式・progress.md からの相対パス・付与してよい STATE）は同節の `ARTIFACT_LINK` の
> 説明を参照する。
