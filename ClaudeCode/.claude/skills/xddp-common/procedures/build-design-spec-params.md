# Build Design Spec Params

> xddp-common の共通プロシージャ。呼び出し元スキルから apply される。

## Build Design Spec Params

xddp-designer-agent 呼び出しに渡す DSN_INDEX_FILE／DSN_COMPARISON_FILE／CRS_FILE／SPO_FILE／
SPO_MODULES_DIR のパラメータブロックを構築する共通手順（`xddp-06-design` Step A・Step A2 backfill が
条件文の詳細度が異なる状態で複製していたものを1箇所に統合し、詳細度は Step A 側の
「条件部にファイルパスを明記」する形へ統一する）。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `REPO_NAME`: リポジトリ名
- `CR`: CR番号

**Output:** `DESIGN_SPEC_PARAMS_BASE`（Agent tool 呼び出しへそのまま展開する複数行ブロック）

**Process:**
1. 以下のブロックを構築する:
   ```
   （{CR_PATH}/05_architecture/{REPO_NAME}/DSN-{CR}.md が存在する場合のみ追加）DSN_INDEX_FILE: {CR_PATH}/05_architecture/{REPO_NAME}/DSN-{CR}.md
   （{CR_PATH}/05_architecture/{REPO_NAME}/DSN-{CR}-comparison.md が存在する場合のみ追加）DSN_COMPARISON_FILE: {CR_PATH}/05_architecture/{REPO_NAME}/DSN-{CR}-comparison.md
   CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
   （{CR_PATH}/04_specout/{REPO_NAME}/SPO-{CR}.md が存在する場合のみ追加）SPO_FILE: {CR_PATH}/04_specout/{REPO_NAME}/SPO-{CR}.md
   （{CR_PATH}/04_specout/{REPO_NAME}/modules/ が存在する場合のみ追加）SPO_MODULES_DIR: {CR_PATH}/04_specout/{REPO_NAME}/modules/
   ```
2. Return `DESIGN_SPEC_PARAMS_BASE`.
