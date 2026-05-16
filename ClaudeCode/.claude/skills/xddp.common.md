---
description: XDDP スキル共通ロジック。CR 番号の解決などを定義する。
---

# XDDP Common Logic

## CR Resolution

**Input:** `RAW_ARGS` = trimmed string of $ARGUMENTS  
**Output:** `CR` (resolved CR number), `REST_ARGS` (remaining args after CR)  
On failure, report error and stop.

Search for `xddp.config.md` upward from cwd to determine `WORKSPACE_ROOT`.
If not found, report error and stop.
Read `XDDP_DIR` (default: `xddp`) and `CR_PREFIX` (default: `CR`).

### Step 1: Identify CR from arguments

Let `FIRST_ARG` = first token of `RAW_ARGS`.

- `FIRST_ARG` starts with `{CR_PREFIX}-`
  → `CR = FIRST_ARG`, `REST_ARGS` = remaining tokens. Done.
- `FIRST_ARG` is empty or does not start with `{CR_PREFIX}-`
  → `REST_ARGS = RAW_ARGS` (treat all tokens as secondary args). Go to Step 2.

> **Skills that use secondary args:**
> - `xddp.review`: first token of `REST_ARGS` → `DOCUMENT_TYPE`
> - `xddp.revise`: first token of `REST_ARGS` → `DOC_TYPE`
> - `xddp.excel2md`: first token of `REST_ARGS` → `EXCEL_PATH`
> - `xddp.04.specout`: remaining tokens of `REST_ARGS` → `ENTRY_POINTS`

### Step 2: Auto-detect

List all directories directly under `{WORKSPACE_ROOT}/{XDDP_DIR}/`
whose names start with `{CR_PREFIX}-` as CR candidates
(files, hidden folders, and reserved names like `latest-specs` are naturally excluded by the name filter).

- **0 found** → report `"CRフォルダが見つかりません。{WORKSPACE_ROOT}/{XDDP_DIR}/ に CR フォルダを作成するか、CR番号を引数に指定してください。"` and stop.
- **1 found** → `CR = that directory name`. Report `"CR を自動検出しました: {CR}"` and continue.
- **Multiple found** → read each directory's `progress.md`; a CR is "in progress" if any step has 🔄, 👀, or 🔁:
  - Exactly **1 in progress** → `CR = that directory name`. Report `"CR を自動検出しました: {CR}"` and continue.
  - **0 or multiple in progress** → display candidate list, report `"CR番号を引数に指定してください"` and stop.
