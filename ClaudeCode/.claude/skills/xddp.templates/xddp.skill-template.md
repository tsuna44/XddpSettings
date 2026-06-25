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

## Step 1: ...

（以降、スキル固有のロジックを記述する）
